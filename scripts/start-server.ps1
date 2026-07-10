# SStock dev server start helper
# - Launches backend (uvicorn) + frontend (Vite) as hidden processes
#   (ports read from repo-root .env: BACKEND_PORT / FRONTEND_PORT)
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

# Ports come from repo-root .env (single source). Fall back to defaults if absent.
$cfg = @{ BACKEND_HOST = '127.0.0.1'; BACKEND_PORT = '8010'; FRONTEND_PORT = '8001' }
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*#' ) { continue }
        if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.+?)\s*$') { $cfg[$matches[1]] = $matches[2] }
    }
}
$bHost = $cfg['BACKEND_HOST']; $bPort = $cfg['BACKEND_PORT']; $fPort = $cfg['FRONTEND_PORT']

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

Write-Host "[START] Backend  - http://${bHost}:${bPort} (uvicorn)"
Write-Host "[START] Frontend - http://localhost:${fPort} (vite)"
Write-Host ""

Start-Process -FilePath $py `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', $bHost, '--port', $bPort `
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
    if (-not $backendOk) { $backendOk = Test-Port ([int]$bPort) }
    if (-not $frontendOk) { $frontendOk = Test-Port ([int]$fPort) }
    if ($backendOk -and $frontendOk) { break }
    Start-Sleep -Seconds 1
}

Write-Host "----------------------------------------"
if ($backendOk) { Write-Host "[OK]   Backend : http://${bHost}:${bPort}" }
else { Write-Host "[FAIL] Backend : port ${bPort} not detected (see logs\backend.err)" }
if ($frontendOk) { Write-Host "[OK]   Frontend: http://localhost:${fPort}" }
else { Write-Host "[FAIL] Frontend: port ${fPort} not detected (see logs\frontend.log)" }
Write-Host "----------------------------------------"
Write-Host "Logs: $log"
Write-Host "Stop: stop.bat"

if ($backendOk -and $frontendOk) { exit 0 } else { exit 1 }
