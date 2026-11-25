# scripts/install_wsl_pheno_serve.ps1
#
# Windows-side wrapper that calls scripts/install_wsl_pheno_serve.sh inside
# Ubuntu-22.04 WSL2. This bootstrap installs runtime dependencies only; model
# downloads remain a separate, explicit operation.
#
# Usage:
#   powershell -File scripts\install_wsl_pheno_serve.ps1
#
# Output:
#   bench\results\2026-07-04\_wsl_install_<ts>.log  (full transcript)
#   bench\results\2026-07-04\_wsl_install_heartbeat.json  (current step)

param([string]$Distro = "Ubuntu-22.04")

$ErrorActionPreference = "Stop"

# Locate the bootstrap script inside WSL (derive from repo root, not a stale drive letter)
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
function ConvertTo-WslPath([string]$WindowsPath) {
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = ($WindowsPath -replace '\\', '/').Substring(2)
    return "/mnt/$drive$rest"
}
$ScriptPath = "$(ConvertTo-WslPath $RepoRoot)/scripts/install_wsl_pheno_serve.sh"

# Sanity: distro must exist
$distroList = wsl --list --quiet 2>&1 | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
if ($distroList -notcontains $Distro) {
    Write-Host "ERROR: WSL distro '$Distro' not found. Available:" -ForegroundColor Red
    $distroList | ForEach-Object { Write-Host "  $_" }
    exit 11
}

# Pre-flight: distro reachable, kernel version captured
Write-Host "=== pheno-serve WSL install ===" -ForegroundColor Cyan
Write-Host "Distro:        $Distro"
Write-Host "Bootstrap:     $ScriptPath"

Write-Host ""
Write-Host "--- WSL preflight ---" -ForegroundColor Yellow
wsl -d $Distro -- uname -a

# Launch the bootstrap inside WSL and capture heartbeat.
$LogDir = Join-Path $RepoRoot "bench\results\2026-07-04"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

$Ts = Get-Date -Format "yyyy-MM-ddTHH-mm-ssZ"
$FullLog = Join-Path $LogDir "_wsl_install_${Ts}.log"
$Heartbeat = Join-Path $LogDir "_wsl_install_heartbeat.json"

Write-Host ""
Write-Host "--- Running bootstrap (full log: $FullLog) ---" -ForegroundColor Yellow

$proc = Start-Process -FilePath "wsl" `
    -ArgumentList @("-d", $Distro, "--", "bash", $ScriptPath) `
    -RedirectStandardOutput $FullLog `
    -RedirectStandardError "$FullLog.err" `
    -WindowStyle Hidden `
    -PassThru

# Don't Wait (the shell tool times out at 5 min). Poll heartbeat instead.
$ProcId = $proc.Id
Write-Host "Bootstrap launched as PID $ProcId; will poll heartbeat at $Heartbeat"

if (Test-Path $Heartbeat) {
    Write-Host ""
    Write-Host "--- Final heartbeat ---" -ForegroundColor Yellow
    Get-Content $Heartbeat | Write-Host
} else {
    Write-Host "WARNING: no heartbeat file at $Heartbeat" -ForegroundColor Yellow
}

if (Test-Path "$FullLog.err") {
    $errSize = (Get-Item "$FullLog.err").Length
    if ($errSize -gt 0) {
        Write-Host ""
        Write-Host "--- stderr ($errSize bytes) ---" -ForegroundColor Yellow
        Get-Content "$FullLog.err" -Tail 40 | Write-Host
    }
}

exit 0
