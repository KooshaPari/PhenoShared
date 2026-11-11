<#
.SYNOPSIS
Allocation-budget smoke for the session-ledger process_session pipeline (L8).

.DESCRIPTION
Parses docs/ops/allocation-budget.json and optionally runs the counting-allocator
integration test (cargo test --test allocation_budget). This is the cheap L8
companion to scripts/rss-budget-check.ps1: it catches gross heap allocation
regressions without enabling jemalloc or continuous dhat profiling.

Hermetic. Use -SelfCheck to validate args + ceiling config without compiling.
#>
[CmdletBinding()]
param(
    [string]$BudgetConfig = "",

    [ValidateRange(0, 9223372036854775807)]
    [long]$BytesCeiling = 0,

    [ValidateRange(0, 9223372036854775807)]
    [long]$AllocationsCeiling = 0,

    [switch]$SelfCheck,

    [switch]$RunTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot

if ([string]::IsNullOrWhiteSpace($BudgetConfig)) {
    $BudgetConfig = Join-Path $repoRoot "docs/ops/allocation-budget.json"
}

function Get-AllocationBudget {
    param(
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [long]$OverrideBytes,
        [long]$OverrideAllocations
    )

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Allocation budget config not found at '$ConfigPath'."
    }

    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($null -eq $config.schema -or $config.schema -ne "sessionledger.allocation-budget.v1") {
        throw "Budget config '$ConfigPath' must declare schema sessionledger.allocation-budget.v1."
    }
    if ($null -eq $config.bytes_allocated_ceiling) {
        throw "Budget config '$ConfigPath' is missing bytes_allocated_ceiling."
    }
    if ($null -eq $config.allocations_ceiling) {
        throw "Budget config '$ConfigPath' is missing allocations_ceiling."
    }

    $bytes = if ($OverrideBytes -gt 0) { $OverrideBytes } else { [long]$config.bytes_allocated_ceiling }
    $allocs = if ($OverrideAllocations -gt 0) { $OverrideAllocations } else { [long]$config.allocations_ceiling }

    if ($bytes -le 0) {
        throw "bytes_allocated_ceiling must be a positive integer (got $bytes)."
    }
    if ($allocs -le 0) {
        throw "allocations_ceiling must be a positive integer (got $allocs)."
    }

    return [pscustomobject]@{
        BytesCeiling        = $bytes
        AllocationsCeiling  = $allocs
        Workload            = [string]$config.workload
        ConfigPath          = $ConfigPath
    }
}

$budget = Get-AllocationBudget `
    -ConfigPath $BudgetConfig `
    -OverrideBytes $BytesCeiling `
    -OverrideAllocations $AllocationsCeiling

Write-Host ("Bytes ceiling: {0:N0} ({1:N1} MiB)" -f $budget.BytesCeiling, ($budget.BytesCeiling / 1MB))
Write-Host ("Allocations ceiling: {0:N0}" -f $budget.AllocationsCeiling)
Write-Host ("Workload: {0}" -f $budget.Workload)
Write-Host ("Config: {0}" -f $budget.ConfigPath)

if ($SelfCheck) {
    Write-Host "Self-check passed: allocation budget config parses and ceilings are positive."
    if (-not $RunTest) {
        exit 0
    }
}

if (-not $RunTest -and -not $SelfCheck) {
    # Default interactive path: self-check then run the Rust smoke.
    $RunTest = $true
}

if ($RunTest) {
    if (-not $env:CARGO_TARGET_DIR) {
        $env:CARGO_TARGET_DIR = Join-Path $repoRoot "target-w27-c00-alloc"
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
    }

    Write-Host "Running cargo test --test allocation_budget --locked ..."
    Push-Location $repoRoot
    try {
        & cargo test --test allocation_budget --locked -- --nocapture
        if ($LASTEXITCODE -ne 0) {
            throw "allocation_budget tests failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "Allocation budget smoke passed."
}
