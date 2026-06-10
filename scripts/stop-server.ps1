# SStock dev server stop helper
# - Stops backend (uvicorn) + frontend (Vite) (ports from repo-root .env)
# - Kills by listening port AND by python/node processes launched from this repo
#   directory, so fallback ports and orphaned processes are reliably cleaned up.
#
# ASCII-only on purpose: Windows PowerShell 5.1 may misread non-ASCII .ps1 files
# without a UTF-8 BOM.

$ErrorActionPreference = 'SilentlyContinue'

# scripts/ -> repo root
$root = Split-Path -Parent $PSScriptRoot

# Ports come from repo-root .env (single source). Fall back to defaults if absent.
$cfg = @{ BACKEND_PORT = '8000'; FRONTEND_PORT = '8001' }
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*#') { continue }
        if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.+?)\s*$') { $cfg[$matches[1]] = $matches[2] }
    }
}
$ports = @([int]$cfg['BACKEND_PORT'], [int]$cfg['FRONTEND_PORT'])
$killed = New-Object System.Collections.Generic.HashSet[int]

function Stop-Pid([int]$procId) {
    if ($procId -gt 0) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            [void]$killed.Add($procId)
        } catch {}
    }
}

# 1) by listening port
foreach ($port in $ports) {
    foreach ($c in (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)) {
        Stop-Pid $c.OwningProcess
    }
}

# 2) by python/node processes launched from this repo (fallback ports / orphans)
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='node.exe'"
foreach ($p in $procs) {
    if ($p.CommandLine -and $p.CommandLine -like "*$root*") {
        Stop-Pid $p.ProcessId
    }
}

if ($killed.Count -gt 0) {
    Write-Host ("[SStock] Stopped PIDs: " + (($killed) -join ', '))
} else {
    Write-Host "[SStock] No SStock dev server processes found."
}
exit 0
