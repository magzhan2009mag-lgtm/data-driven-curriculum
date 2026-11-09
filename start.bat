@echo off
chcp 65001 >nul
setlocal
title EdTech: запуск
cd /d "%~dp0"

set "VENV_PY=backend\.venv\Scripts\python.exe"

python --version >nul 2>nul
if errorlevel 1 (
  set "MESSAGE=Не найден Python. Установите Python 3.11 или новее с python.org, отметьте Add to PATH и запустите снова."
  goto :fail
)

node --version >nul 2>nul
if errorlevel 1 (
  set "MESSAGE=Не найден Node.js. Установите его с nodejs.org и запустите снова."
  goto :fail
)

if not exist "%VENV_PY%" (
  echo Создаю окружение Python...
  python -m venv backend\.venv
  if errorlevel 1 (
    set "MESSAGE=Не удалось создать окружение Python."
    goto :fail
  )
)

fc /b backend\requirements.txt backend\.venv\requirements.installed >nul 2>nul
if errorlevel 1 (
  echo Устанавливаю зависимости Python, это может занять несколько минут...
  "%VENV_PY%" -m pip install --disable-pip-version-check -r backend\requirements.txt
  if errorlevel 1 (
    set "MESSAGE=Не удалось установить зависимости Python. Проверьте интернет и запустите снова."
    goto :fail
  )
  copy /y backend\requirements.txt backend\.venv\requirements.installed >nul
)

if not exist backend\data.db (
  echo Создаю демонстрационные данные...
  pushd backend
  .venv\Scripts\python.exe -m scripts.seed
  if errorlevel 1 (
    popd
    set "MESSAGE=Не удалось создать демонстрационные данные."
    goto :fail
  )
  popd
)

if not exist frontend\node_modules (
  echo Устанавливаю зависимости интерфейса, это может занять несколько минут...
  pushd frontend
  call npm install --no-fund --no-audit
  if errorlevel 1 (
    popd
    set "MESSAGE=Не удалось установить зависимости интерфейса. Проверьте интернет и запустите снова."
    goto :fail
  )
  popd
)

call :port_busy 8000
if errorlevel 1 (
  echo Запускаю сервер аналитики...
  start "EdTech Backend" /d "%~dp0backend" cmd /k "chcp 65001 >nul & .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
) else (
  echo Сервер аналитики уже работает на порту 8000.
)

call :port_busy 3000
if errorlevel 1 (
  echo Запускаю интерфейс...
  start "EdTech Frontend" /d "%~dp0frontend" cmd /k "chcp 65001 >nul & npm run dev"
) else (
  echo Интерфейс уже работает на порту 3000.
)

echo Жду, пока всё запустится...
call :wait_port 8000
if errorlevel 1 (
  set "MESSAGE=Сервер аналитики не запустился за минуту. Посмотрите ошибку в окне EdTech Backend."
  goto :fail
)
call :wait_port 3000
if errorlevel 1 (
  set "MESSAGE=Интерфейс не запустился за минуту. Посмотрите ошибку в окне EdTech Frontend."
  goto :fail
)

if not defined EDTECH_NO_BROWSER start "" http://localhost:3000
echo.
echo Готово: http://localhost:3000
echo Чтобы остановить проект, закройте окна EdTech Backend и EdTech Frontend.
timeout /t 5 >nul 2>nul
exit /b 0

:fail
echo.
echo ОШИБКА: %MESSAGE%
echo.
pause
exit /b 1

:port_busy
powershell -NoProfile -Command "$c = New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1', %1); exit 0 } catch { exit 1 } finally { $c.Close() }"
exit /b %errorlevel%

:wait_port
powershell -NoProfile -Command "$end = (Get-Date).AddSeconds(60); while ((Get-Date) -lt $end) { $c = New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1', %1); exit 0 } catch { Start-Sleep -Milliseconds 500 } finally { $c.Close() } }; exit 1"
exit /b %errorlevel%
