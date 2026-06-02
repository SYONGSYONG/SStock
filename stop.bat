@echo off
setlocal EnableExtensions

rem ----------------------------------------------------------------
rem Stop SStock backend + frontend dev servers.
rem Delegates to scripts\stop-server.ps1 which kills by listening port
rem AND by repo-directory processes (catches Vite fallback ports, orphans).
rem ----------------------------------------------------------------

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"
set "PS1=%BASE%\scripts\stop-server.ps1"

echo Stopping SStock dev servers...
echo.

rem -- admin rights probe (warn only; do not abort) --
net session >nul 2>&1
if errorlevel 1 (
    echo [WARN] Running without administrator rights.
    echo        If a process refuses to die, re-run from an elevated prompt.
    echo.
)

if not exist "%PS1%" (
    echo [ERROR] PowerShell helper not found: %PS1%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "PS_CODE=%errorlevel%"

echo.
if not "%PS_CODE%"=="0" (
    echo [ERROR] stop-server.ps1 returned exit code %PS_CODE%.
    exit /b %PS_CODE%
)

echo Done.
exit /b 0
