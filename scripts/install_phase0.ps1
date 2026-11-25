#Requires -Version 5.1
<#
.SYNOPSIS
  Phase 0 bootstrap: export training data, backfill routing_decisions, install middleware, bench dry-run.

.DESCRIPTION
  Chains the pheno-harness Phase 0 scripts in order. Requires Python 3.10+ and an OmniRoute
  storage.sqlite at %USERPROFILE%\.omniroute\storage.sqlite (override with -OmniRouteDb).

.PARAMETER OmniRouteDb
  Path to OmniRoute SQLite database (default: $env:USERPROFILE\.omniroute\storage.sqlite).

.PARAMETER SkipDeps
  Skip pip install -r requirements.txt.

.PARAMETER SkipBench
  Skip bench_ik_llama.py --dry-run.

.EXAMPLE
  .\scripts\install_phase0.ps1
#>
[CmdletBinding()]
param(
    [string]$OmniRouteDb = "$env:USERPROFILE\.omniroute\storage.sqlite",
    [switch]$SkipDeps,
    [switch]$SkipBench
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

Write-Step "pheno-harness Phase 0 (root: $Root)"

if (-not $SkipDeps) {
    Write-Step "Installing Python dependencies"
    python -m pip install -r requirements.txt
}

Write-Step "Exporting OmniRoute training data"
python scripts/export_omniroute_training.py --db $OmniRouteDb

Write-Step "Backfilling routing_decisions from call_logs"
python scripts/sync_routing_decisions.py --db $OmniRouteDb --backfill

Write-Step "Installing Pheno middleware hooks (sqlite)"
python scripts/install_middleware.py --db $OmniRouteDb --mode sqlite

if (-not $SkipBench) {
    Write-Step "Running ik_llama baseline bench (dry-run)"
    python scripts/bench_ik_llama.py --dry-run
}

Write-Step "Phase 0 complete"
Write-Host "  Training exports: $env:USERPROFILE\.omniroute\training"
Write-Host "  Bench results:    $Root\bench\results"
Write-Host "  Sync state:       $Root\state\routing_sync.json"
Write-Host ""
Write-Host "Restart OmniRoute to load middleware hooks from SQLite." -ForegroundColor Yellow
