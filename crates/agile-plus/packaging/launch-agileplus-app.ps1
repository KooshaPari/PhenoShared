#Requires -Version 7.0
<#
.SYNOPSIS
    Launches the AgilePlus application.

.DESCRIPTION
    This is a stopgap launcher. The full dashboard web UI (Axum + Askama server)
    exists in crates/agileplus-dashboard/ but currently cannot build due to
    upstream dependency issues in agileplus-domain.

    Interim: Opens the AgilePlus CLI instead.
    Final: Will launch the compiled dashboard binary and open it in the browser.

.NOTES
    NOTE: This .ps1 is a temporary solution. The real artifact will be an
    Electrobun-wrapped or MSI-packaged native app that doesn't require PowerShell.
#>

$ErrorActionPreference = "Stop"

# Port for the dashboard server
$dashboardPort = 3000

# Check if the dashboard binary exists
$dashboardBinary = "E:\agileplus-target\release\agileplus-dashboard.exe"
if (Test-Path $dashboardBinary) {
    Write-Host "Starting AgilePlus Dashboard..." -ForegroundColor Cyan

    # Start the dashboard in a background job
    $job = Start-Job -ScriptBlock {
        $env:AGILEPLUS_DASHBOARD_PORT = $using:dashboardPort
        & $using:dashboardBinary
    }

    # Wait a moment for the server to start
    Start-Sleep -Milliseconds 500

    # Open in browser
    $url = "http://localhost:$dashboardPort"
    Write-Host "Opening $url in your browser..." -ForegroundColor Green
    Start-Process $url

    Write-Host "Dashboard is running. Press Ctrl+C in your terminal to stop." -ForegroundColor Yellow
} else {
    Write-Host "AgilePlus Dashboard binary not found at $dashboardBinary" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Interim: Opening AgilePlus CLI instead..." -ForegroundColor Cyan
    Write-Host "The dashboard web UI is being built. Check project notes." -ForegroundColor Gray
    Write-Host ""

    # Open the CLI as a fallback
    & agileplus --help | head -20

    Write-Host ""
    Write-Host "To use the CLI: agileplus <command> [options]" -ForegroundColor Cyan
}
