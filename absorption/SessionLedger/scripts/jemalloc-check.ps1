<#
.SYNOPSIS
  Machine-check soft optional jemalloc feature anchors (C00 L8).

.DESCRIPTION
  Verifies docs/ops/jemalloc.md documents soft + hard jemalloc gates and that
  sl-daemon Cargo.toml / main.rs, ops-load soft job, and jemalloc-hard blocking
  workflow stay wired. Hermetic: no cargo jemalloc compile — suitable for default
  Windows cargo test.

  Does not claim continuous production profiling push or verify default-on
  platform allocator policy (see jemalloc-default-on-check.ps1).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.PARAMETER Build
  On Unix CI: cargo build --features jemalloc in crates/sl-daemon (soft).

.EXAMPLE
  pwsh ./scripts/jemalloc-check.ps1 -SelfCheck

.EXAMPLE
  pwsh ./scripts/jemalloc-check.ps1 -SelfCheck -Build
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,
    [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/jemalloc.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/ops-load.yml"
$hardWorkflowPath = Join-Path $repoRoot ".github/workflows/jemalloc-hard.yml"
$daemonCargoPath = Join-Path $repoRoot "crates/sl-daemon/Cargo.toml"
$daemonMainPath = Join-Path $repoRoot "crates/sl-daemon/src/main.rs"
$selfPath = Join-Path $repoRoot "scripts/jemalloc-check.ps1"
$softTestPath = Join-Path $repoRoot "tests/jemalloc_soft.rs"
$hardTestPath = Join-Path $repoRoot "tests/jemalloc_hard.rs"

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
        [string]$Context = "docs/ops/jemalloc.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Soft jemalloc feature check (C00 L8)"
if ($SelfCheck -or -not $Build) {
    Write-Host "Mode: SelfCheck (docs + Cargo/feature/cfg anchors; no jemalloc compile)"
}

Assert-File -Path $docPath -Label "jemalloc doc"
Assert-File -Path $workflowPath -Label "ops-load workflow"
Assert-File -Path $daemonCargoPath -Label "sl-daemon Cargo.toml"
Assert-File -Path $daemonMainPath -Label "sl-daemon main.rs"
Assert-File -Path $selfPath -Label "jemalloc check script"
Assert-File -Path $softTestPath -Label "jemalloc_soft test"
Assert-File -Path $hardWorkflowPath -Label "jemalloc-hard workflow"
Assert-File -Path $hardTestPath -Label "jemalloc_hard test"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$cargoToml = Get-Content -LiteralPath $daemonCargoPath -Raw
$mainRs = Get-Content -LiteralPath $daemonMainPath -Raw

Write-Host "jemalloc doc anchors:"
Test-DocContains -Doc $doc -Needle "Optional jemalloc allocator" `
    -Label "jemalloc section heading"
Test-DocContains -Doc $doc -Needle "scripts/jemalloc-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Soft jemalloc SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "tikv-jemallocator" `
    -Label "tikv-jemallocator reference"
Test-DocContains -Doc $doc -Needle "--features jemalloc" `
    -Label "Cargo feature enable note"
Test-DocContains -Doc $doc -Needle "continue-on-error" `
    -Label "soft continue-on-error note"
Test-DocContains -Doc $doc -Needle "Windows-safe" `
    -Label "Windows-safe default note"
Test-DocContains -Doc $doc -Needle "## Soft vs hard gates" `
    -Label "soft vs hard gates matrix section"
Test-DocContains -Doc $doc -Needle "Blocking jemalloc-hard CI workflow | **done**" `
    -Label "blocking hard CI gate marked done"
Test-DocContains -Doc $doc -Needle ".github/workflows/jemalloc-hard.yml" `
    -Label "jemalloc-hard workflow path documented"
Test-DocContains -Doc $doc -Needle "tests/jemalloc_hard.rs" `
    -Label "jemalloc_hard test wrapper documented"
Test-DocContains -Doc $doc -Needle "Continuous jemalloc profiling / production always-on jemalloc | **unpaid**" `
    -Label "continuous profiling unpaid gate"
Test-DocContains -Doc $doc -Needle "Windows mimalloc parity | **done**" `
    -Label "Windows mimalloc parity done gate"
Test-DocContains -Doc $doc -Needle "jemalloc-default-on.md" `
    -Label "default-on policy cross-link"

Write-Host "sl-daemon Cargo / main anchors:"
if ($cargoToml -notmatch '(?m)^jemalloc\s*=') {
    throw "crates/sl-daemon/Cargo.toml missing jemalloc feature."
}
[void](Write-Check -Label "Cargo.toml jemalloc feature" -Ok $true)

if ($cargoToml -notmatch '(?m)^platform-allocator\s*=') {
    throw "crates/sl-daemon/Cargo.toml missing platform-allocator feature."
}
[void](Write-Check -Label "Cargo.toml platform-allocator feature" -Ok $true)

if ($cargoToml -notmatch 'tikv-jemallocator') {
    throw "crates/sl-daemon/Cargo.toml missing tikv-jemallocator dependency."
}
[void](Write-Check -Label "Cargo.toml tikv-jemallocator dep" -Ok $true)

if ($mainRs -notmatch 'cfg\(all\(unix, feature = "platform-allocator", not\(feature = "system-allocator"\)\)\)') {
    throw "main.rs must gate #[global_allocator] on cfg(all(unix, feature = `"platform-allocator`", not(feature = `"system-allocator`")))."
}
[void](Write-Check -Label "main.rs jemalloc+unix cfg gate" -Ok $true)

if ($mainRs -notmatch '#\[global_allocator\]') {
    throw "main.rs must declare #[global_allocator] for jemalloc."
}
[void](Write-Check -Label "main.rs global_allocator" -Ok $true)

if ($mainRs -notmatch 'tikv_jemallocator::Jemalloc') {
    throw "main.rs must use tikv_jemallocator::Jemalloc."
}
[void](Write-Check -Label "main.rs Jemalloc type" -Ok $true)

Write-Host "Workflow soft-gate anchors:"
if ($workflow -notmatch '(?m)^\s*jemalloc:') {
    throw "ops-load.yml must declare a jemalloc soft job."
}
[void](Write-Check -Label "ops-load jemalloc job" -Ok $true)

if ($workflow -notmatch 'jemalloc-check\.ps1') {
    throw "ops-load.yml jemalloc job must invoke scripts/jemalloc-check.ps1."
}
[void](Write-Check -Label "ops-load invokes jemalloc-check.ps1" -Ok $true)

if ($workflow -notmatch '--features jemalloc') {
    throw "ops-load.yml must cargo build with --features jemalloc."
}
[void](Write-Check -Label "ops-load --features jemalloc" -Ok $true)

# Soft job block should set continue-on-error near the jemalloc job.
$jemallocBlock = if ($workflow -match '(?s)jemalloc:.*?continue-on-error:\s*true') { $true } else { $false }
if (-not $jemallocBlock) {
    throw "ops-load.yml jemalloc job must set continue-on-error: true (soft gate)."
}
[void](Write-Check -Label "jemalloc job continue-on-error: true" -Ok $true)

$hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
$hardTestRs = Get-Content -LiteralPath $hardTestPath -Raw

Write-Host "Hard jemalloc CI blocking-gate anchors:"
if ($hardWorkflow -match 'continue-on-error:\s*true') {
    throw "jemalloc-hard.yml must not set continue-on-error (blocking PR CI)."
}
[void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)

if ($hardWorkflow -notmatch 'pull_request:') {
    throw "jemalloc-hard.yml must run on pull_request."
}
[void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)

if ($hardWorkflow -notmatch 'jemalloc-check\.ps1 -SelfCheck') {
    throw "jemalloc-hard.yml must run scripts/jemalloc-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hard workflow runs jemalloc-check.ps1 -SelfCheck" -Ok $true)

if ($hardWorkflow -notmatch 'jemalloc-check\.ps1 -Build') {
    throw "jemalloc-hard.yml must run scripts/jemalloc-check.ps1 -Build."
}
[void](Write-Check -Label "hard workflow runs jemalloc-check.ps1 -Build" -Ok $true)

if ($hardWorkflow -notmatch '--features jemalloc') {
    throw "jemalloc-hard.yml must exercise --features jemalloc build evidence."
}
[void](Write-Check -Label "hard workflow references --features jemalloc" -Ok $true)

Write-Host "cargo test wrapper anchors:"
if ($hardTestRs -notmatch 'jemalloc-check\.ps1') {
    throw "tests/jemalloc_hard.rs must invoke scripts/jemalloc-check.ps1."
}
[void](Write-Check -Label "jemalloc_hard.rs invokes SelfCheck script" -Ok $true)

if ($hardTestRs -notmatch 'Jemalloc hard CI SelfCheck passed') {
    throw "tests/jemalloc_hard.rs must assert Jemalloc hard CI SelfCheck passed success line."
}
[void](Write-Check -Label "jemalloc_hard.rs asserts hard success line" -Ok $true)

Write-Host "Soft jemalloc SelfCheck passed"

$summary = @"
## Hard jemalloc CI SelfCheck (C00 L8)

SelfCheck passed: ``docs/ops/jemalloc.md`` soft/hard gate rows, blocking
``jemalloc-hard.yml`` workflow, and ``tests/jemalloc_hard.rs`` wrapper.
Soft ``ops-load`` jemalloc job retained. Default-on platform allocator policy
is ``jemalloc-default-on-check.ps1``. Continuous profiling push remains unpaid.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Jemalloc hard CI SelfCheck passed (C00 L8 blocking PR gate; soft ops-load retained; default-on policy in jemalloc-default-on-check.ps1; continuous profiling unpaid)."

if ($Build) {
    if ($IsWindows -or $env:OS -match 'Windows') {
        Write-Host "Skip -Build on Windows (jemalloc is Unix-only); SelfCheck already passed."
        exit 0
    }

    if (-not $env:CARGO_TARGET_DIR) {
        $env:CARGO_TARGET_DIR = Join-Path $repoRoot "target-w33-c00-jemalloc"
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
    }

    Write-Host "Running cargo build --features jemalloc --locked (sl-daemon) ..."
    Push-Location (Join-Path $repoRoot "crates/sl-daemon")
    try {
        & cargo build --features jemalloc --locked
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build --features jemalloc failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "Soft jemalloc feature build passed."
}

exit 0
