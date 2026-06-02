@echo off
setlocal EnableExtensions

rem ----------------------------------------------------------------
rem Start SStock backend + frontend dev servers (hidden, with logs).
rem Delegates to scripts\start-server.ps1 (avoids cmd /c quoting issues
rem and uses reliable port detection). Use stop.bat to stop.
rem ----------------------------------------------------------------

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"
set "PS1=%BASE%\scripts\start-server.ps1"

echo Starting SStock dev servers...
echo.

if not exist "%PS1%" (
    echo [ERROR] PowerShell helper not found: %PS1%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "CODE=%errorlevel%"

echo.
if not "%CODE%"=="0" (
    echo [ERROR] Startup or port detection failed. See logs\backend.err , logs\frontend.log
    pause
    exit /b %CODE%
)

echo Servers running. Window closes in 3 seconds...
timeout /t 3 /nobreak >nul
exit /b 0
