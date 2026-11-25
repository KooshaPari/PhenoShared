# AgilePlus Dashboard Launcher + Electrobun Desktop Shell
# Idempotent daemon launcher that:
# 1. Checks if AGILEPLUS_DASHBOARD_PORT is free
# 2. If free → starts agileplus-dashboard as hidden daemon
# 3. If occupied → health-checks http://localhost:$PORT/health
#    - Healthy → reuse existing instance
#    - Unhealthy/foreign → kill + start fresh
# 4. Builds Electrobun desktop shell (if needed)
# 5. Launches Electrobun app window pointing at the daemon

$ErrorActionPreference = "SilentlyContinue"

# Configuration
$DashboardBinary = "E:\agileplus-target\release\agileplus-dashboard.exe"
$DashboardPort = [int]$env:AGILEPLUS_DASHBOARD_PORT
if (-not $DashboardPort -or $DashboardPort -le 0) { $DashboardPort = 8770 }
$HealthCheckUrl = "http://127.0.0.1:$DashboardPort/health"
$DashboardUrl = "http://127.0.0.1:$DashboardPort"
$RepoPath = "E:\Dev\AgilePlus"
$ElectrobunDir = "$RepoPath\crates\agileplus-dashboard\desktop-electrobun"
$ElectrobunBinary = "$ElectrobunDir\build\AgilePlus.exe"  # Post-build artifact

# Validate binary exists
if (-not (Test-Path $DashboardBinary)) {
    Write-Host "[ERROR] Dashboard binary not found: $DashboardBinary" -ForegroundColor Red
    Write-Host "[INFO] Build with: CARGO_TARGET_DIR=E:/agileplus-target cargo build --release -p agileplus-dashboard" -ForegroundColor Yellow
    timeout /t 3 > $null
    exit 1
}

# Helper: Check if port is in use
function Test-PortInUse {
    param([int]$Port)
    try {
        $tcpConnection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return $null -ne $tcpConnection
    } catch {
        return $false
    }
}

# Helper: Health-check the dashboard
function Test-DashboardHealth {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Helper: Kill any process using the port
function Kill-ProcessOnPort {
    param([int]$Port)
    try {
        $tcpConnection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($tcpConnection) {
            $process = Get-Process -Id $tcpConnection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "[WARN] Killing process on port $Port : $($process.ProcessName)" -ForegroundColor Yellow
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }
        }
    } catch {
        # Silent catch
    }
}

# Helper: Build Electrobun app (if needed)
function Build-ElectrobunApp {
    if (-not (Test-Path $ElectrobunDir)) {
        Write-Host "[ERROR] Electrobun directory not found: $ElectrobunDir" -ForegroundColor Red
        return $false
    }

    # Check if build artifact exists and is recent
    $buildCacheValid = $false
    if (Test-Path $ElectrobunBinary) {
        $binaryAge = (Get-Date) - (Get-Item $ElectrobunBinary).LastWriteTime
        if ($binaryAge.TotalHours -lt 24) {
            Write-Host "[OK] Electrobun build is recent (< 24h). Skipping rebuild." -ForegroundColor Green
            $buildCacheValid = $true
        }
    }

    if (-not $buildCacheValid) {
        Write-Host "[INFO] Building Electrobun app..." -ForegroundColor Blue
        Push-Location $ElectrobunDir
        try {
            # Ensure Bun dependencies are installed
            bunx bun install 2>&1 | Out-Null

            # Build Electrobun app
            bunx electrobun build --release 2>&1 | Out-Null

            # Verify build succeeded
            if (Test-Path $ElectrobunBinary) {
                Write-Host "[OK] Electrobun build succeeded: $ElectrobunBinary" -ForegroundColor Green
                return $true
            } else {
                Write-Host "[ERROR] Electrobun build failed. Binary not found at: $ElectrobunBinary" -ForegroundColor Red
                return $false
            }
        } catch {
            Write-Host "[ERROR] Failed to build Electrobun: $_" -ForegroundColor Red
            return $false
        } finally {
            Pop-Location
        }
    }

    return $true
}

# Main logic
Write-Host "[AgilePlus Dashboard Launcher + Electrobun Desktop Shell]" -ForegroundColor Cyan

# ── Step 1: Ensure dashboard daemon is running ────────────────────────────────
Write-Host "[INFO] Checking dashboard daemon..." -ForegroundColor Blue

$portInUse = Test-PortInUse $DashboardPort

if ($portInUse) {
    Write-Host "[INFO] Port $DashboardPort is occupied. Health-checking..." -ForegroundColor Blue
    if (Test-DashboardHealth $HealthCheckUrl) {
        Write-Host "[OK] Healthy dashboard found on port $DashboardPort. Reusing." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Port $DashboardPort occupied by unhealthy service. Freeing & restarting..." -ForegroundColor Yellow
        Kill-ProcessOnPort $DashboardPort
        $portInUse = $false
    }
}

if (-not $portInUse) {
    Write-Host "[INFO] Starting agileplus-dashboard on port $DashboardPort..." -ForegroundColor Blue
    Push-Location $RepoPath
    try {
        # Start as hidden, detached daemon
        $proc = Start-Process -FilePath $DashboardBinary `
            -NoNewWindow `
            -WindowStyle Hidden `
            -PassThru `
            -EnvironmentVariables @{ "AGILEPLUS_DASHBOARD_PORT" = $DashboardPort }

        Write-Host "[OK] Dashboard PID $($proc.Id) started (detached)" -ForegroundColor Green

        # Give it a moment to bind
        Start-Sleep -Seconds 2
    } catch {
        Write-Host "[ERROR] Failed to start dashboard: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
}

# ── Step 2: Build Electrobun app (if needed) ───────────────────────────────────
Write-Host "[INFO] Preparing Electrobun desktop shell..." -ForegroundColor Blue
if (-not (Build-ElectrobunApp)) {
    Write-Host "[ERROR] Failed to build Electrobun app. Falling back to browser." -ForegroundColor Red
    Start-Process $DashboardUrl
    exit 0
}

# ── Step 3: Launch Electrobun app window ───────────────────────────────────────
Write-Host "[INFO] Launching Electrobun app window..." -ForegroundColor Blue

# Pass the dashboard port to Electrobun via RENDERER_URL environment variable
$env:RENDERER_URL = $DashboardUrl
$env:APP_NAME = "AgilePlus"
$env:WINDOW_WIDTH = "1400"
$env:WINDOW_HEIGHT = "900"

try {
    Start-Process -FilePath $ElectrobunBinary `
        -EnvironmentVariables @{
            "RENDERER_URL" = $DashboardUrl
            "APP_NAME" = "AgilePlus"
            "WINDOW_WIDTH" = "1400"
            "WINDOW_HEIGHT" = "900"
        }
    Write-Host "[OK] Electrobun app launched" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to launch Electrobun app: $_" -ForegroundColor Red
    Write-Host "[INTERIM] Opening in default browser..." -ForegroundColor DarkYellow
    Start-Process $DashboardUrl
}

Write-Host "[OK] Done. Dashboard is live at $DashboardUrl" -ForegroundColor Green
exit 0
