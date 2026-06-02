@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem 스크립트가 위치한 폴더를 기준으로 경로 설정 (PC마다 클론 위치가 달라도 동작)
set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"
set "BACKEND=%BASE%\backend"
set "FRONTEND=%BASE%\frontend"
set "LOG=%BASE%\logs"

if not exist "%LOG%" mkdir "%LOG%"

cls
echo Starting Framework5.0 Manager...
echo.

if not exist "%BACKEND%\package.json" (
    echo [ERROR] Backend package.json not found.
    echo Path: %BACKEND%
    pause
    exit /b 1
)

if not exist "%FRONTEND%\package.json" (
    echo [ERROR] Frontend package.json not found.
    echo Path: %FRONTEND%
    pause
    exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm.cmd not found. Please check Node.js installation.
    pause
    exit /b 1
)

rem Create or clear log files first, so you can confirm that this script reached the launch step.
copy /y nul "%LOG%\backend.log" >nul
copy /y nul "%LOG%\frontend.log" >nul
copy /y nul "%LOG%\start-launch.log" >nul
copy /y nul "%LOG%\start-error.log" >nul

echo [START] Backend - port 3000
echo [START] Frontend - port 5173
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $base='%BASE%'; $backend=Join-Path $base 'backend'; $frontend=Join-Path $base 'frontend'; $log=Join-Path $base 'logs'; New-Item -ItemType Directory -Force -Path $log | Out-Null; $q=[char]34; $backendLog=Join-Path $log 'backend.log'; $frontendLog=Join-Path $log 'frontend.log'; $backendCmd='/d /c npm.cmd run dev >> ' + $q + $backendLog + $q + ' 2>&1'; $frontendCmd='/d /c npm.cmd run dev >> ' + $q + $frontendLog + $q + ' 2>&1'; Start-Process -FilePath 'cmd.exe' -ArgumentList $backendCmd -WorkingDirectory $backend -WindowStyle Hidden; Start-Sleep -Seconds 2; Start-Process -FilePath 'cmd.exe' -ArgumentList $frontendCmd -WorkingDirectory $frontend -WindowStyle Hidden" > "%LOG%\start-launch.log" 2> "%LOG%\start-error.log"

if errorlevel 1 (
    echo [ERROR] Failed to launch background processes.
    echo.
    echo Start error log:
    type "%LOG%\start-error.log"
    echo.
    pause
    exit /b 1
)

echo Waiting for server ports...
echo.

set "BACKEND_OK=0"
set "FRONTEND_OK=0"

for /l %%I in (1,1,20) do (
    call :IsPortListening 3000
    if not errorlevel 1 set "BACKEND_OK=1"

    call :IsPortListening 5173
    if not errorlevel 1 set "FRONTEND_OK=1"

    if "!BACKEND_OK!"=="1" if "!FRONTEND_OK!"=="1" goto RESULT

    timeout /t 1 /nobreak >nul
)

:RESULT
echo Result
echo ----------------------------------------
if "%BACKEND_OK%"=="1" (
    echo [OK]   Backend : http://localhost:3000
) else (
    echo [FAIL] Backend : port 3000 not detected
)

if "%FRONTEND_OK%"=="1" (
    echo [OK]   Frontend: http://localhost:5173
) else (
    echo [FAIL] Frontend: port 5173 not detected
)
echo ----------------------------------------
echo Logs:
echo   %LOG%\backend.log
echo   %LOG%\frontend.log
echo   %LOG%\start-error.log
echo.

if "%BACKEND_OK%"=="1" if "%FRONTEND_OK%"=="1" (
    echo Window will close in 3 seconds...
    timeout /t 3 /nobreak >nul
    exit /b 0
)

echo Startup failed or port detection failed.
echo This window will stay open so you can read the message.
echo.
echo Backend log:
type "%LOG%\backend.log"
echo.
echo Frontend log:
type "%LOG%\frontend.log"
echo.
pause
exit /b 1

:IsPortListening
netstat -ano -p tcp | findstr /R /C:":%~1 .*LISTENING" >nul
exit /b %errorlevel%
