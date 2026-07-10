@echo off
setlocal
rem 포트는 저장소 루트 .env 단일 출처에서 읽는다(미설정 시 기본값).
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8010"
if exist "%~dp0.env" (
  for /f "usebackq eol=# tokens=1,2 delims==" %%a in ("%~dp0.env") do (
    if /i "%%a"=="BACKEND_HOST" set "BACKEND_HOST=%%b"
    if /i "%%a"=="BACKEND_PORT" set "BACKEND_PORT=%%b"
  )
)
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo [SStock] Backend venv not found. Run setup.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo [SStock][WARN] backend\.env not found. Copy backend\.env.example and fill KIS keys.
)
echo [SStock] Backend on http://%BACKEND_HOST%:%BACKEND_PORT%  (Ctrl+C to stop)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%
