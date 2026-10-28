@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe

if not exist "%PY%" (
  echo [!] Python venv not found at .venv
  echo     Run: python -m venv .venv ^&^& .venv\Scripts\python -m pip install -r backend\requirements.txt
  pause
  exit /b 1
)

if not exist "backend\data\adx.db" (
  echo [*] First run - seeding database ...
  "%PY%" -m backend.seed
  if errorlevel 1 (
    echo [!] Seed failed.
    pause
    exit /b 1
  )
)

if not exist "frontend\dist\index.html" (
  echo [!] Frontend build not found: frontend\dist
  echo     The API still works, but the web UI needs a build.
  echo     Run scripts\build.ps1 first, or start dev mode: scripts\dev.ps1
  echo.
)

echo [*] Starting Ad Discovery at http://127.0.0.1:8000
echo     Press Ctrl+C to stop.
echo.
"%PY%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

endlocal
