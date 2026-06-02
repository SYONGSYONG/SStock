@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo [SStock] Backend venv not found. Run setup.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo [SStock][WARN] backend\.env not found. Copy backend\.env.example and fill KIS keys.
)
echo [SStock] Backend on http://127.0.0.1:8000  (Ctrl+C to stop)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
