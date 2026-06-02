# SStock dev server stop helper
# - Stops backend (uvicorn :8000) + frontend (Vite :5173, incl. fallback 5174+)
# - Kills by listening port AND by python/node processes launched from this repo
#   directory, so fallback ports and orphaned processes are reliably cleaned up.
#
# ASCII-only on purpose: Windows PowerShell 5.1 may misread non-ASCII .ps1 files
# without a UTF-8 BOM.

$ErrorActionPreference = 'SilentlyContinue'

# scripts/ -> repo root
$root = Split-Path -Parent $PSScriptRoot
$ports = @(8000) + (5173..5180)
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
