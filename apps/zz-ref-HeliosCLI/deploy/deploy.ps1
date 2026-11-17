#Requires -Version 5.1
<#
.SYNOPSIS
    Helios CLI — Production OTel Collector Deployment Script (Windows)

.DESCRIPTION
    Deploys the production OpenTelemetry collector stack using Docker Compose.

.PARAMETER EnvFile
    Path to the environment file. Defaults to .env in the deploy directory.

.PARAMETER DryRun
    Show what would be deployed without making changes.

.PARAMETER HealthOnly
    Run health checks only, skip deployment.

.PARAMETER NoWait
    Don't wait for services to become healthy.

.PARAMETER Timeout
    Seconds to wait for services to become healthy. Default: 60.

.EXAMPLE
    .\deploy.ps1
    .\deploy.ps1 -EnvFile .env.prod -DryRun
    .\deploy.ps1 -HealthOnly
#>

[CmdletBinding()]
param(
    [string]$EnvFile = "",
    [switch]$DryRun,
    [switch]$HealthOnly,
    [switch]$NoWait,
    [int]$Timeout = 60
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $ScriptDir "docker-compose.production.yml"

if (-not $EnvFile) {
    $EnvFile = Join-Path $ScriptDir ".env"
}

# ── Helpers ──────────────────────────────────────────────
function Write-Info  { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Blue }
function Write-Ok    { param([string]$Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Err   { param([string]$Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }

# ── Prerequisites ────────────────────────────────────────
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Err "Docker is not installed. See https://docs.docker.com/get-docker/"
        exit 1
    }

    try { docker info 2>$null | Out-Null } catch {
        Write-Err "Docker daemon is not running."
        exit 1
    }

    $composeVersion = docker compose version 2>$null
    if (-not $composeVersion) {
        Write-Err "Docker Compose v2 is required."
        exit 1
    }

    Write-Ok "All prerequisites met."
}

# ── Environment validation ───────────────────────────────
function Test-Environment {
    if (-not (Test-Path $EnvFile)) {
        Write-Warn "No .env file found at $EnvFile"
        Write-Warn "Copying from .env.production template..."
        Copy-Item (Join-Path $ScriptDir ".env.production") $EnvFile
        Write-Warn "Please edit $EnvFile with production values before deploying."
        exit 1
    }

    # Parse .env file
    $envVars = @{}
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $key, $value = $line -split "=", 2
            $envVars[$key.Trim()] = $value.Trim()
        }
    }

    if ($envVars["GF_SECURITY_ADMIN_PASSWORD"] -eq "CHANGE_ME") {
        Write-Err "Grafana admin password is still 'CHANGE_ME'. Edit $EnvFile first."
        exit 1
    }

    Write-Ok "Environment validated."
}

# ── Deploy ────────────────────────────────────────────────
function Invoke-Deploy {
    Write-Info "Deploying Helios CLI OTel stack..."
    Write-Info "  Compose file: $ComposeFile"
    Write-Info "  Env file:     $EnvFile"

    $composeArgs = @("-f", $ComposeFile, "--env-file", $EnvFile)

    if ($DryRun) {
        Write-Info "Dry run — services that would be deployed:"
        docker compose @composeArgs config --services
        return
    }

    # Pull images
    Write-Info "Pulling images..."
    docker compose @composeArgs pull

    # Start stack
    Write-Info "Starting services..."
    docker compose @composeArgs up -d --remove-orphans

    Write-Ok "Services started."
}

# ── Health check ──────────────────────────────────────────
function Wait-ForReady {
    if ($NoWait) { return }

    Write-Info "Waiting for services to become healthy (timeout: ${Timeout}s)..."

    $composeArgs = @("-f", $ComposeFile, "--env-file", $EnvFile)
    $services = @("collector", "jaeger", "prometheus", "grafana")
    $elapsed = 0
    $interval = 3

    while ($elapsed -lt $Timeout) {
        $allHealthy = $true

        foreach ($svc in $services) {
            try {
                $json = docker compose @composeArgs ps --format json $svc 2>$null
                if ($json) {
                    $obj = $json | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($obj.Health -ne "healthy") {
                        $allHealthy = $false
                        break
                    }
                } else {
                    $allHealthy = $false
                    break
                }
            } catch {
                $allHealthy = $false
                break
            }
        }

        if ($allHealthy) {
            Write-Ok "All services healthy."
            return
        }

        Start-Sleep -Seconds $interval
        $elapsed += $interval
        Write-Host "." -NoNewline
    }

    Write-Host ""
    Write-Warn "Timeout reached. Some services may not be healthy yet."
    Write-Warn "Run .\health-check.sh for detailed status."
}

# ── Summary ───────────────────────────────────────────────
function Show-Summary {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  Helios CLI OTel Stack — Deployment Complete" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Collector OTLP gRPC:  localhost:4317"
    Write-Host "  Collector OTLP HTTP:  localhost:4318"
    Write-Host "  Collector Health:     localhost:13133"
    Write-Host "  Collector Metrics:    localhost:8889"
    Write-Host "  Jaeger UI:            localhost:16686"
    Write-Host "  Prometheus:           localhost:9090"
    Write-Host "  Grafana:              localhost:3000"
    Write-Host ""
    Write-Host "  Configuration: $ComposeFile"
    Write-Host "  Environment:   $EnvFile"
    Write-Host ""
}

# ── Main ──────────────────────────────────────────────────
function Main {
    Write-Host ""
    Write-Host "Helios CLI — OTel Collector Production Deployment" -ForegroundColor Blue
    Write-Host ""

    Test-Prerequisites

    if ($HealthOnly) {
        Write-Info "Running health checks..."
        $services = @("collector", "jaeger", "prometheus", "grafana")
        $containers = @(
            @{ Name = "OTel Collector"; Container = "helios-otel-collector"; Url = "http://localhost:13133" }
            @{ Name = "Jaeger";         Container = "helios-jaeger";         Url = "http://localhost:16686" }
            @{ Name = "Prometheus";     Container = "helios-prometheus";     Url = "http://localhost:9090/-/healthy" }
            @{ Name = "Grafana";        Container = "helios-grafana";        Url = "http://localhost:3000/api/health" }
        )
        $failures = 0
        foreach ($svc in $containers) {
            $status = docker inspect --format='{{.State.Status}}' $svc.Container 2>$null
            if ($status -eq "running") {
                Write-Ok "$($svc.Name) — running"
            } else {
                Write-Err "$($svc.Name) — $status"
                $failures++
            }
            try {
                $code = (Invoke-WebRequest -Uri $svc.Url -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue).StatusCode
                if ($code -eq 200) { Write-Ok "$($svc.Name) HTTP — $code" }
                else { Write-Warn "$($svc.Name) HTTP — $code"; $failures++ }
            } catch {
                Write-Err "$($svc.Name) HTTP — unreachable"
                $failures++
            }
        }
        exit $failures
    }

    Test-Environment
    Invoke-Deploy
    Wait-ForReady
    Show-Summary
}

Main
