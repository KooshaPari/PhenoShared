<#
.SYNOPSIS
  Machine-check default-on platform allocator policy anchors (C00 L8).

.DESCRIPTION
  Verifies docs/ops/jemalloc-default-on.md + jemalloc-default-on.json document
  default-on jemalloc (Unix) and mimalloc (Windows) for sl-daemon, cross-checks
  Cargo.toml default features, main.rs cfg gates, and blocking PR workflow wiring.
  Hermetic: -SelfCheck needs no allocator compile on Windows cargo test graph.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.PARAMETER Build
  On Unix CI: cargo build --locked in crates/sl-daemon (default features).

.EXAMPLE
  pwsh ./scripts/jemalloc-default-on-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,
    [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/jemalloc-default-on.md"
$policyPath = Join-Path $repoRoot "docs/ops/jemalloc-default-on.json"
$jemallocDocPath = Join-Path $repoRoot "docs/ops/jemalloc.md"
$hardWorkflowPath = Join-Path $repoRoot ".github/workflows/jemalloc-default-on-hard.yml"
$softHardWorkflowPath = Join-Path $repoRoot ".github/workflows/jemalloc-hard.yml"
$daemonCargoPath = Join-Path $repoRoot "crates/sl-daemon/Cargo.toml"
$daemonMainPath = Join-Path $repoRoot "crates/sl-daemon/src/main.rs"
$selfPath = Join-Path $repoRoot "scripts/jemalloc-default-on-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/jemalloc_default_on.rs"

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
        [string]$Context = "docs/ops/jemalloc-default-on.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Default-on platform allocator check (C00 L8)"
if ($SelfCheck -or -not $Build) {
    Write-Host "Mode: SelfCheck (docs + Cargo/default-feature anchors; no allocator compile on Windows test graph)"
}

Assert-File -Path $docPath -Label "jemalloc-default-on doc"
Assert-File -Path $policyPath -Label "jemalloc-default-on policy JSON"
Assert-File -Path $jemallocDocPath -Label "jemalloc doc"
Assert-File -Path $hardWorkflowPath -Label "jemalloc-default-on-hard workflow"
Assert-File -Path $softHardWorkflowPath -Label "jemalloc-hard workflow"
Assert-File -Path $daemonCargoPath -Label "sl-daemon Cargo.toml"
Assert-File -Path $daemonMainPath -Label "sl-daemon main.rs"
Assert-File -Path $selfPath -Label "jemalloc-default-on check script"
Assert-File -Path $wrapperTest -Label "jemalloc_default_on.rs test wrapper"

$doc = Get-Content -LiteralPath $docPath -Raw
$policyRaw = Get-Content -LiteralPath $policyPath -Raw
$policy = $policyRaw | ConvertFrom-Json
$jemallocDoc = Get-Content -LiteralPath $jemallocDocPath -Raw
$hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
$cargoToml = Get-Content -LiteralPath $daemonCargoPath -Raw
$mainRs = Get-Content -LiteralPath $daemonMainPath -Raw
$wrapperRs = Get-Content -LiteralPath $wrapperTest -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "# Default-on platform allocators (C00 L8)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "scripts/jemalloc-default-on-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Windows mimalloc parity | **done**" `
    -Label "Windows parity marked done"
Test-DocContains -Doc $doc -Needle "Unix default jemalloc | **done**" `
    -Label "Unix default jemalloc marked done"
Test-DocContains -Doc $doc -Needle "Blocking jemalloc-default-on-hard CI workflow | **done**" `
    -Label "blocking workflow marked done"
Test-DocContains -Doc $doc -Needle "Continuous profiling push to production backends | **unpaid**" `
    -Label "continuous profiling unpaid gate"
Test-DocContains -Doc $doc -Needle ".github/workflows/jemalloc-default-on-hard.yml" `
    -Label "hard workflow path documented"

Write-Host "Policy JSON anchors:"
Test-DocContains -Doc $policyRaw -Needle '"schema_version"' `
    -Label "schema_version" -Context "jemalloc-default-on.json"
if ($policy.default_features -notcontains "platform-allocator") {
    throw "jemalloc-default-on.json default_features must include platform-allocator."
}
[void](Write-Check -Label "default_features platform-allocator" -Ok $true)
if ($policy.platform_allocators.unix.feature -ne "jemalloc") {
    throw "jemalloc-default-on.json unix.feature must be jemalloc."
}
[void](Write-Check -Label "unix jemalloc feature" -Ok $true)
if ($policy.platform_allocators.windows.feature -ne "mimalloc-alloc") {
    throw "jemalloc-default-on.json windows.feature must be mimalloc-alloc."
}
[void](Write-Check -Label "windows mimalloc-alloc feature" -Ok $true)

Write-Host "jemalloc.md cross-link anchors:"
Test-DocContains -Doc $jemallocDoc -Needle "jemalloc-default-on.md" `
    -Label "cross-link to default-on doc" -Context "docs/ops/jemalloc.md"
Test-DocContains -Doc $jemallocDoc -Needle "Windows mimalloc parity | **done**" `
    -Label "Windows parity done in jemalloc.md" -Context "docs/ops/jemalloc.md"

Write-Host "sl-daemon Cargo / main anchors:"
if ($cargoToml -notmatch '(?m)^default\s*=\s*\[[^\]]*"platform-allocator"') {
    throw "crates/sl-daemon/Cargo.toml default must include platform-allocator."
}
[void](Write-Check -Label "Cargo.toml default platform-allocator" -Ok $true)

if ($cargoToml -notmatch '(?m)^platform-allocator\s*=') {
    throw "crates/sl-daemon/Cargo.toml missing platform-allocator feature."
}
[void](Write-Check -Label "Cargo.toml platform-allocator feature" -Ok $true)

if ($cargoToml -notmatch 'tikv-jemallocator') {
    throw "crates/sl-daemon/Cargo.toml missing tikv-jemallocator dependency."
}
[void](Write-Check -Label "Cargo.toml tikv-jemallocator dep" -Ok $true)

if ($cargoToml -notmatch 'mimalloc') {
    throw "crates/sl-daemon/Cargo.toml missing mimalloc Windows dependency."
}
[void](Write-Check -Label "Cargo.toml mimalloc dep" -Ok $true)

if ($mainRs -notmatch 'cfg\(all\(unix, feature = "platform-allocator", not\(feature = "system-allocator"\)\)\)') {
    throw "main.rs must gate Unix jemalloc on cfg(all(unix, feature = `"platform-allocator`", not(feature = `"system-allocator`")))."
}
[void](Write-Check -Label "main.rs unix jemalloc cfg gate" -Ok $true)

if ($mainRs -notmatch 'cfg\(all\(windows, feature = "platform-allocator", not\(feature = "system-allocator"\)\)\)') {
    throw "main.rs must gate Windows mimalloc on cfg(all(windows, feature = `"platform-allocator`", not(feature = `"system-allocator`")))."
}
[void](Write-Check -Label "main.rs windows mimalloc cfg gate" -Ok $true)

if ($mainRs -notmatch 'tikv_jemallocator::Jemalloc') {
    throw "main.rs must use tikv_jemallocator::Jemalloc."
}
[void](Write-Check -Label "main.rs Jemalloc type" -Ok $true)

if ($mainRs -notmatch 'mimalloc::MiMalloc') {
    throw "main.rs must use mimalloc::MiMalloc."
}
[void](Write-Check -Label "main.rs MiMalloc type" -Ok $true)

Write-Host "Hard default-on CI blocking-gate anchors:"
if ($hardWorkflow -match 'continue-on-error:\s*true') {
    throw "jemalloc-default-on-hard.yml must not set continue-on-error (blocking PR CI)."
}
[void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)

if ($hardWorkflow -notmatch 'pull_request:') {
    throw "jemalloc-default-on-hard.yml must run on pull_request."
}
[void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)

if ($hardWorkflow -notmatch 'jemalloc-default-on-check\.ps1 -SelfCheck') {
    throw "jemalloc-default-on-hard.yml must run jemalloc-default-on-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hard workflow runs SelfCheck" -Ok $true)

if ($hardWorkflow -notmatch 'ubuntu-latest') {
    throw "jemalloc-default-on-hard.yml must include a unix default build job."
}
[void](Write-Check -Label "hard workflow unix job" -Ok $true)

if ($hardWorkflow -notmatch 'windows-latest') {
    throw "jemalloc-default-on-hard.yml must include a windows default build job."
}
[void](Write-Check -Label "hard workflow windows job" -Ok $true)

if ($wrapperRs -notmatch 'jemalloc-default-on-check\.ps1') {
    throw "tests/jemalloc_default_on.rs must invoke jemalloc-default-on-check.ps1."
}
[void](Write-Check -Label "jemalloc_default_on.rs invokes SelfCheck script" -Ok $true)

Write-Host "Jemalloc default-on hard CI SelfCheck passed (C00 L8; soft jemalloc-hard retained; continuous profiling unpaid)."

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Default-on platform allocator SelfCheck (C00 L8)

SelfCheck passed: ``docs/ops/jemalloc-default-on.md`` policy rows, blocking
``jemalloc-default-on-hard.yml`` workflow, and ``tests/jemalloc_default_on.rs``
wrapper. Soft ``jemalloc-hard`` explicit feature CI retained. Continuous
profiling push remains unpaid.
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

if ($Build) {
    if (-not $env:CARGO_TARGET_DIR) {
        $env:CARGO_TARGET_DIR = Join-Path $repoRoot "target-w43-jemalloc-default-on"
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
    }

    Write-Host "Running cargo build --locked (sl-daemon default features) ..."
    Push-Location (Join-Path $repoRoot "crates/sl-daemon")
    try {
        & cargo build --locked
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build --locked failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "Default-on platform allocator build passed."
}

exit 0
