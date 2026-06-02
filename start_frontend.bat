@echo off
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo [SStock] Frontend deps not found. Run setup.bat first.
  pause
  exit /b 1
)
echo [SStock] Frontend on http://localhost:5173  (Ctrl+C to stop)
call npm run dev
