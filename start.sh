#!/usr/bin/env bash
# Запуск всего проекта на macOS и Linux одной командой: ./start.sh
# То же, что start.bat на Windows. Остановить — Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

fail() {
  echo
  echo "ОШИБКА: $1"
  exit 1
}

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
[ -n "$PYTHON" ] || fail "Не найден Python 3.11 или новее. Установите его с python.org и запустите снова."
command -v node >/dev/null 2>&1 || fail "Не найден Node.js. Установите его с nodejs.org (версия LTS) и запустите снова."

VENV_PY="backend/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "Создаю окружение Python..."
  "$PYTHON" -m venv backend/.venv || fail "Не удалось создать окружение Python."
fi

if ! cmp -s backend/requirements.txt backend/.venv/requirements.installed; then
  echo "Устанавливаю зависимости Python, это может занять несколько минут..."
  "$VENV_PY" -m pip install --disable-pip-version-check -r backend/requirements.txt \
    || fail "Не удалось установить зависимости Python. Проверьте интернет и запустите снова."
  cp backend/requirements.txt backend/.venv/requirements.installed
fi

echo "Проверяю демонстрационные данные..."
(cd backend && .venv/bin/python -m scripts.seed --if-outdated) || fail "Не удалось создать демонстрационные данные."

if [ ! -d frontend/node_modules ]; then
  echo "Устанавливаю зависимости интерфейса, это может занять несколько минут..."
  (cd frontend && npm install --no-fund --no-audit) \
    || fail "Не удалось установить зависимости интерфейса. Проверьте интернет и запустите снова."
fi

port_busy() {
  "$VENV_PY" -c "import socket, sys; s = socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1', $1)) == 0 else 1)"
}

wait_port() {
  for _ in $(seq 120); do
    port_busy "$1" && return 0
    sleep 0.5
  done
  return 1
}

PIDS=()
stop() {
  if [ ${#PIDS[@]} -gt 0 ]; then
    echo
    echo "Останавливаю..."
    kill "${PIDS[@]}" 2>/dev/null || true
    wait 2>/dev/null || true
  fi
}
trap stop EXIT
trap 'exit 130' INT TERM

if port_busy 8000; then
  echo "Сервер аналитики уже работает на порту 8000."
else
  echo "Запускаю сервер аналитики..."
  (cd backend && exec .venv/bin/python -m uvicorn app.main:app --port 8000) &
  PIDS+=($!)
fi

if port_busy 3000; then
  echo "Интерфейс уже работает на порту 3000."
else
  echo "Запускаю интерфейс..."
  # next напрямую, без npm: тогда при остановке не остаётся «осиротевшего» процесса.
  (cd frontend && exec node node_modules/next/dist/bin/next dev -p 3000) &
  PIDS+=($!)
fi

echo "Жду, пока всё запустится..."
wait_port 8000 || fail "Сервер аналитики не запустился за минуту. Ошибка — в сообщениях выше."
wait_port 3000 || fail "Интерфейс не запустился за минуту. Ошибка — в сообщениях выше."

URL="http://localhost:3000"
if [ -z "${EDTECH_NO_BROWSER:-}" ]; then
  if command -v open >/dev/null 2>&1; then
    open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
fi

echo
echo "Готово: $URL"
echo "API и его описание: http://localhost:8000/docs"
echo "Чтобы остановить проект, нажмите Ctrl+C."

if [ ${#PIDS[@]} -gt 0 ]; then
  wait
fi
