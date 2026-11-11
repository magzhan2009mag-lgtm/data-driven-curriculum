#!/bin/sh
# Запуск внутри Docker: сначала аналитика (FastAPI), потом интерфейс (Next.js) на $PORT.
set -e

cd /app/backend
# --root-path /api: Swagger на /api/docs знает, что он за прокси, и «Try it out» ходит на /api/…
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /api &

# Интерфейс берёт все данные из API, поэтому ждём, пока API ответит (до 60 секунд).
python - <<'EOF'
import time
import urllib.request

for _ in range(120):
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/stats", timeout=2)
        break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit("API не запустился за 60 секунд")
EOF

cd /app/frontend
export HOSTNAME=0.0.0.0
exec node server.js
