@echo off
setlocal
set BASE=%~dp0
echo [SStock] Setup starting...

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH. Install Python 3.12+ from https://python.org
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found in PATH. Install Node.js 20+ from https://nodejs.org
  pause
  exit /b 1
)

echo [1/3] Backend virtual environment
cd /d "%BASE%backend"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

echo [2/3] Backend dependencies
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 ( echo [ERROR] Backend install failed & pause & exit /b 1 )

echo [3/3] Frontend dependencies
cd /d "%BASE%frontend"
call npm install
if errorlevel 1 ( echo [ERROR] Frontend install failed & pause & exit /b 1 )

echo.
echo [SStock] Setup complete.
echo   1) Create backend\.env from backend\.env.example (KIS app key/secret + account no)
echo   2) (Optional) Create .env from .env.example to change ports / enable LAN access
echo      (defaults: backend 8000, frontend 8001, local-only)
echo   3) Run start.bat to launch backend + frontend
pause
