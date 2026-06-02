# SStock dev server start helper
# - Launches backend (uvicorn :8000) + frontend (Vite :5173) as hidden processes
#   with logs under logs/, then waits and reports which ports came up.
# - Uses Start-Process -FilePath (native arg/quote handling) to avoid the
#   cmd /c double-quote pitfall when the interpreter path is quoted.
#
# ASCII-only on purpose (Windows PowerShell 5.1 may misread non-ASCII .ps1).

$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$log = Join-Path $root 'logs'
$py = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host "[ERROR] Backend venv not found: $py"
    Write-Host "        Run setup.bat first."
    exit 1
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host "[ERROR] Frontend deps not found. Run setup.bat first."
    exit 1
}
New-Item -ItemType Directory -Force -Path $log | Out-Null

Write-Host "[START] Backend  - http://127.0.0.1:8000 (uvicorn)"
Write-Host "[START] Frontend - http://localhost:5173 (vite)"
Write-Host ""

Start-Process -FilePath $py `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
    -WorkingDirectory $backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $log 'backend.log') `
    -RedirectStandardError (Join-Path $log 'backend.err')

Start-Sleep -Seconds 2

Start-Process -FilePath 'npm.cmd' `
    -ArgumentList 'run', 'dev' `
    -WorkingDirectory $frontend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $log 'frontend.log') `
    -RedirectStandardError (Join-Path $log 'frontend.err')

function Test-Port([int]$p) {
    [bool](Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue)
}

$backendOk = $false
$frontendOk = $false
for ($i = 0; $i -lt 30; $i++) {
    if (-not $backendOk) { $backendOk = Test-Port 8000 }
    if (-not $frontendOk) { $frontendOk = Test-Port 5173 }
    if ($backendOk -and $frontendOk) { break }
    Start-Sleep -Seconds 1
}

Write-Host "----------------------------------------"
if ($backendOk) { Write-Host "[OK]   Backend : http://127.0.0.1:8000" }
else { Write-Host "[FAIL] Backend : port 8000 not detected (see logs\backend.err)" }
if ($frontendOk) { Write-Host "[OK]   Frontend: http://localhost:5173" }
else { Write-Host "[FAIL] Frontend: port 5173 not detected (see logs\frontend.log)" }
Write-Host "----------------------------------------"
Write-Host "Logs: $log"
Write-Host "Stop: stop.bat"

if ($backendOk -and $frontendOk) { exit 0 } else { exit 1 }
