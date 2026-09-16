#Requires -Version 5.1
<#
.SYNOPSIS
  Master harness install: cloud tiers, middleware, routing sync, sunset metrics.

.DESCRIPTION
  Wires pheno-harness into OmniRoute and documents lane entry points:
    routine  -> local Qwen3.5 0.8B via OmniRoute
    ci       -> agent-runner queue via OmniRoute (codex-spark)
    architecture -> forge -p via OmniRoute

.PARAMETER OmniRouteDb
  Path to OmniRoute SQLite (default: %USERPROFILE%\.omniroute\storage.sqlite).

.PARAMETER SkipDeps
  Skip pip install.

.PARAMETER SkipPhase0
  Skip export/backfill/middleware steps (only apply tiers + sunset metrics).

.PARAMETER SkipSunset
  Skip initial sunset_metrics append.

.EXAMPLE
  .\scripts\wire_harness.ps1
#>
[CmdletBinding()]
param(
    [string]$OmniRouteDb = "$env:USERPROFILE\.omniroute\storage.sqlite",
    [switch]$SkipDeps,
    [switch]$SkipPhase0,
    [switch]$SkipSunset
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

if (-not (Test-Path $OmniRouteDb)) {
    throw "OmniRoute DB not found: $OmniRouteDb"
}

Write-Step "pheno-harness wire (root: $Root)"

if (-not $SkipDeps) {
    Write-Step "Installing Python dependencies"
    python -m pip install -r requirements.txt
}

Write-Step "Applying cloud four-role tier mapping to Main combo"
python scripts/apply_cloud_tiers.py --db $OmniRouteDb --mode both

if (-not $SkipPhase0) {
    Write-Step "Exporting OmniRoute training data"
    python scripts/export_omniroute_training.py --db $OmniRouteDb

    Write-Step "Backfilling routing_decisions from call_logs"
    python scripts/sync_routing_decisions.py --db $OmniRouteDb --backfill

    Write-Step "Installing Pheno middleware hooks (sqlite)"
    python scripts/install_middleware.py --db $OmniRouteDb --mode sqlite
}

if (-not $SkipSunset) {
    Write-Step "Appending sunset transition metrics"
    python scripts/sunset_metrics.py --db $OmniRouteDb --print
}

Write-Step "Harness wired"
Write-Host ""
Write-Host "Lane map (harness/lanes.yaml):" -ForegroundColor Green
Write-Host "  routine      -> local/qwen35-08b via OmniRoute (http://127.0.0.1:8080/v1)"
Write-Host "  ci           -> agent-runner queue, gpt-5.3-codex-spark"
Write-Host "  architecture -> forge -p, claude-opus-4-8"
Write-Host ""
Write-Host "Run examples:" -ForegroundColor Yellow
Write-Host "  .\scripts\agent_runner_omniroute.ps1 `"$env:USERPROFILE\.claude\forge-dispatch\codex-jobs.jsonl`""
Write-Host "  .\scripts\forge_lane.ps1 -Prompt `"Review harness architecture`""
Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Yellow
Write-Host "  Tier export:  $env:USERPROFILE\.omniroute\training\combo_main.json"
Write-Host "  Sunset log:   $env:USERPROFILE\.omniroute\training\sunset_metrics.jsonl"
Write-Host "  Sync state:   $Root\state\routing_sync.json"
Write-Host ""
Write-Host "Restart OmniRoute to load combo tier overlay + middleware hooks." -ForegroundColor Yellow
