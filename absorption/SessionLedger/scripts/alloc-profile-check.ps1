<#
.SYNOPSIS
Optional dhat heap-profiling smoke for the session-ledger process_session pipeline (L8).

.DESCRIPTION
Parses docs/ops/alloc-profile.json and optionally runs the feature-gated dhat
integration test (cargo test --test alloc_profile_dhat --features alloc-profile).
This is the cheap L8 companion beyond scripts/allocation-budget-check.ps1: it
records real allocator statistics without jemalloc or continuous daemon profiling.

Hermetic. Use -SelfCheck to validate args + ceiling config without compiling dhat.
#>
[CmdletBinding()]
param(
    [string]$ProfileConfig = "",

    [ValidateRange(0, 9223372036854775807)]
    [long]$MaxBytesCeiling = 0,

    [ValidateRange(0, 9223372036854775807)]
    [long]$TotalBlocksCeiling = 0,

    [switch]$SelfCheck,

    [switch]$RunTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot

if ([string]::IsNullOrWhiteSpace($ProfileConfig)) {
    $ProfileConfig = Join-Path $repoRoot "docs/ops/alloc-profile.json"
}

function Get-AllocProfileBudget {
    param(
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [long]$OverrideMaxBytes,
        [long]$OverrideTotalBlocks
    )

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Allocator profile config not found at '$ConfigPath'."
    }

    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($null -eq $config.schema -or $config.schema -ne "sessionledger.alloc-profile.v1") {
        throw "Profile config '$ConfigPath' must declare schema sessionledger.alloc-profile.v1."
    }
    if ($null -eq $config.max_bytes_ceiling) {
        throw "Profile config '$ConfigPath' is missing max_bytes_ceiling."
    }
    if ($null -eq $config.total_blocks_ceiling) {
        throw "Profile config '$ConfigPath' is missing total_blocks_ceiling."
    }
    if ($null -eq $config.profiler -or $config.profiler -ne "dhat") {
        throw "Profile config '$ConfigPath' must declare profiler dhat."
    }

    $maxBytes = if ($OverrideMaxBytes -gt 0) { $OverrideMaxBytes } else { [long]$config.max_bytes_ceiling }
    $blocks = if ($OverrideTotalBlocks -gt 0) { $OverrideTotalBlocks } else { [long]$config.total_blocks_ceiling }

    if ($maxBytes -le 0) {
        throw "max_bytes_ceiling must be a positive integer (got $maxBytes)."
    }
    if ($blocks -le 0) {
        throw "total_blocks_ceiling must be a positive integer (got $blocks)."
    }

    return [pscustomobject]@{
        MaxBytesCeiling     = $maxBytes
        TotalBlocksCeiling  = $blocks
        Workload            = [string]$config.workload
        Profiler            = [string]$config.profiler
        ConfigPath          = $ConfigPath
    }
}

$budget = Get-AllocProfileBudget `
    -ConfigPath $ProfileConfig `
    -OverrideMaxBytes $MaxBytesCeiling `
    -OverrideTotalBlocks $TotalBlocksCeiling

Write-Host ("Max bytes ceiling: {0:N0} ({1:N1} MiB)" -f $budget.MaxBytesCeiling, ($budget.MaxBytesCeiling / 1MB))
Write-Host ("Total blocks ceiling: {0:N0}" -f $budget.TotalBlocksCeiling)
Write-Host ("Workload: {0}" -f $budget.Workload)
Write-Host ("Profiler: {0}" -f $budget.Profiler)
Write-Host ("Config: {0}" -f $budget.ConfigPath)

if ($SelfCheck) {
    $docPath = Join-Path $repoRoot "docs/ops/alloc-profile.md"
    $configPath = Join-Path $repoRoot "docs/ops/alloc-profile.json"
    $workflowPath = Join-Path $repoRoot ".github/workflows/ops-load.yml"
    $hardWorkflowPath = Join-Path $repoRoot ".github/workflows/alloc-profile-hard.yml"
    $selfPath = Join-Path $repoRoot "scripts/alloc-profile-check.ps1"
    $softTestPath = Join-Path $repoRoot "tests/alloc_profile.rs"
    $dhatTestPath = Join-Path $repoRoot "tests/alloc_profile_dhat.rs"
    $hardTestPath = Join-Path $repoRoot "tests/alloc_profile_hard.rs"

    function Assert-File {
        param(
            [Parameter(Mandatory = $true)][string]$Path,
            [Parameter(Mandatory = $true)][string]$Label
        )
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Missing $Label at '$Path'."
        }
    }

    function Write-Check {
        param([string]$Label, [bool]$Ok)
        $mark = if ($Ok) { "PASS" } else { "FAIL" }
        Write-Host "  [$mark] $Label"
        return $Ok
    }

    function Test-DocContains {
        param(
            [Parameter(Mandatory = $true)][string]$Doc,
            [Parameter(Mandatory = $true)][string]$Needle,
            [Parameter(Mandatory = $true)][string]$Label,
            [string]$Context = "docs/ops/alloc-profile.md"
        )
        $ok = $Doc.Contains($Needle)
        [void](Write-Check -Label $Label -Ok $ok)
        if (-not $ok) {
            throw "$Context missing required anchor: '$Needle'"
        }
    }

    Assert-File -Path $docPath -Label "alloc-profile doc"
    Assert-File -Path $configPath -Label "alloc-profile config"
    Assert-File -Path $workflowPath -Label "ops-load workflow"
    Assert-File -Path $hardWorkflowPath -Label "alloc-profile-hard workflow"
    Assert-File -Path $selfPath -Label "alloc-profile check script"
    Assert-File -Path $softTestPath -Label "alloc_profile test"
    Assert-File -Path $dhatTestPath -Label "alloc_profile_dhat test"
    Assert-File -Path $hardTestPath -Label "alloc_profile_hard test"

    $doc = Get-Content -LiteralPath $docPath -Raw
    $workflow = Get-Content -LiteralPath $workflowPath -Raw
    $hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
    $hardTestRs = Get-Content -LiteralPath $hardTestPath -Raw

    Write-Host "alloc-profile doc anchors:"
    Test-DocContains -Doc $doc -Needle "Allocator profiling smoke" `
        -Label "alloc-profile section heading"
    Test-DocContains -Doc $doc -Needle "scripts/alloc-profile-check.ps1" `
        -Label "SelfCheck script reference"
    Test-DocContains -Doc $doc -Needle "-SelfCheck" `
        -Label "SelfCheck invocation"
    Test-DocContains -Doc $doc -Needle "continue-on-error" `
        -Label "soft continue-on-error note"
    Test-DocContains -Doc $doc -Needle "## Soft vs hard gates" `
        -Label "soft vs hard gates matrix section"
    Test-DocContains -Doc $doc -Needle "Blocking alloc-profile-hard CI workflow | **done**" `
        -Label "blocking hard CI gate marked done"
    Test-DocContains -Doc $doc -Needle ".github/workflows/alloc-profile-hard.yml" `
        -Label "alloc-profile-hard workflow path documented"
    Test-DocContains -Doc $doc -Needle "tests/alloc_profile_hard.rs" `
        -Label "alloc_profile_hard test wrapper documented"

    Write-Host "ops-load soft-gate anchors:"
    if ($workflow -notmatch '(?m)^\s*alloc-profile:') {
        throw "ops-load.yml must declare an alloc-profile soft job."
    }
    [void](Write-Check -Label "ops-load alloc-profile job" -Ok $true)

    if ($workflow -notmatch 'alloc-profile-check\.ps1') {
        throw "ops-load.yml alloc-profile job must invoke scripts/alloc-profile-check.ps1."
    }
    [void](Write-Check -Label "ops-load invokes alloc-profile-check.ps1" -Ok $true)

    if ($workflow -notmatch '(?s)alloc-profile:.*?continue-on-error:\s*true') {
        throw "ops-load.yml alloc-profile job must set continue-on-error: true (soft gate)."
    }
    [void](Write-Check -Label "alloc-profile job continue-on-error: true" -Ok $true)

    Write-Host "Hard alloc-profile CI blocking-gate anchors:"
    if ($hardWorkflow -match 'continue-on-error:\s*true') {
        throw "alloc-profile-hard.yml must not set continue-on-error (blocking PR CI)."
    }
    [void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)

    if ($hardWorkflow -notmatch 'pull_request:') {
        throw "alloc-profile-hard.yml must run on pull_request."
    }
    [void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)

    if ($hardWorkflow -notmatch 'alloc-profile-check\.ps1 -SelfCheck') {
        throw "alloc-profile-hard.yml must run scripts/alloc-profile-check.ps1 -SelfCheck."
    }
    [void](Write-Check -Label "hard workflow runs alloc-profile-check.ps1 -SelfCheck" -Ok $true)

    if ($hardWorkflow -notmatch 'alloc-profile-check\.ps1 -RunTest') {
        throw "alloc-profile-hard.yml must run scripts/alloc-profile-check.ps1 -RunTest."
    }
    [void](Write-Check -Label "hard workflow runs alloc-profile-check.ps1 -RunTest" -Ok $true)

    if ($hardTestRs -notmatch 'alloc-profile-check\.ps1') {
        throw "tests/alloc_profile_hard.rs must invoke scripts/alloc-profile-check.ps1."
    }
    [void](Write-Check -Label "alloc_profile_hard.rs invokes SelfCheck script" -Ok $true)

    if ($hardTestRs -notmatch 'Alloc profile hard CI SelfCheck passed') {
        throw "tests/alloc_profile_hard.rs must assert Alloc profile hard CI SelfCheck passed success line."
    }
    [void](Write-Check -Label "alloc_profile_hard.rs asserts hard success line" -Ok $true)

    Write-Host "Self-check passed: alloc-profile config parses and ceilings are positive."
    Write-Host "Alloc profile hard CI SelfCheck passed (C00 L8 blocking PR gate; soft ops-load retained; always-on jemalloc + Windows parity unpaid)."
    if (-not $RunTest) {
        exit 0
    }
}

if (-not $RunTest -and -not $SelfCheck) {
    $RunTest = $true
}

if ($RunTest) {
    if (-not $env:CARGO_TARGET_DIR) {
        $env:CARGO_TARGET_DIR = Join-Path $repoRoot "target-w29-c00-dhat"
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
    }

    Write-Host "Running cargo test --test alloc_profile --locked (hermetic wiring) ..."
    Push-Location $repoRoot
    try {
        & cargo test --test alloc_profile --locked
        if ($LASTEXITCODE -ne 0) {
            throw "alloc_profile tests failed with exit code $LASTEXITCODE."
        }

        Write-Host "Running cargo test --test alloc_profile_dhat --features alloc-profile --locked ..."
        & cargo test --test alloc_profile_dhat --features alloc-profile --locked -- --nocapture
        if ($LASTEXITCODE -ne 0) {
            throw "alloc_profile_dhat tests failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "Allocator profile smoke passed."
}
