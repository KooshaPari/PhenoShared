#Requires -Version 5.1
<#
.SYNOPSIS
    Helios CLI — OTel Stack Teardown (Windows)

.PARAMETER Volumes
    Also remove persistent data volumes.

.PARAMETER All
    Remove containers, volumes, and network.
#>

[CmdletBinding()]
param(
    [switch]$Volumes,
    [switch]$All
)

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ScriptDir "docker-compose.production.yml"
$EnvFile = Join-Path $ScriptDir ".env"

function Write-Info  { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Blue }
function Write-Ok    { param([string]$Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "Helios CLI — OTel Stack Teardown" -ForegroundColor Blue
Write-Host ""

if (-not (Test-Path $ComposeFile)) {
    Write-Warn "Compose file not found: $ComposeFile"
    Write-Warn "Attempting to stop containers by name..."
    $containers = @("helios-otel-collector", "helios-jaeger", "helios-prometheus", "helios-grafana")
    foreach ($c in $containers) {
        docker stop $c 2>$null | Out-Null
        docker rm $c 2>$null | Out-Null
    }
    Write-Ok "Containers stopped and removed."
    exit 0
}

$composeArgs = @("-f", $ComposeFile, "--env-file", $EnvFile)

Write-Info "Stopping services..."
docker compose @composeArgs down --remove-orphans
Write-Ok "Services stopped."

if ($Volumes -or $All) {
    Write-Info "Removing persistent volumes..."
    docker compose @composeArgs down -v
    Write-Ok "Volumes removed."
}

if ($All) {
    Write-Info "Pruning orphaned images..."
    docker image prune -f --filter "label=com.docker.compose.project=helios-otel" 2>$null | Out-Null
    Write-Ok "Orphaned resources cleaned."
}

Write-Host ""
Write-Ok "Teardown complete."
Write-Host ""
