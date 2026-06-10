@echo off
rem 프론트 포트는 저장소 루트 .env 단일 출처(vite.config.ts도 같은 .env를 읽음).
set "FRONTEND_PORT=8001"
if exist "%~dp0.env" (
  for /f "usebackq eol=# tokens=1,2 delims==" %%a in ("%~dp0.env") do (
    if /i "%%a"=="FRONTEND_PORT" set "FRONTEND_PORT=%%b"
  )
)
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo [SStock] Frontend deps not found. Run setup.bat first.
  pause
  exit /b 1
)
echo [SStock] Frontend on http://localhost:%FRONTEND_PORT%  (Ctrl+C to stop)
call npm run dev
