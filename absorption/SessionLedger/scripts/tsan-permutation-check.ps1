<#
.SYNOPSIS
  Machine-check TSan permutation checker anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/concurrency-safety.md documents the TSan permutation lane
  (done vs unpaid rows), that the tsan-permutation workflow, tsan_permutation
  test wrapper, race_model subset, and this script stay wired. Hermetic: no cargo,
  no nightly TSan build — suitable for default Windows cargo test.

  Does not claim full tokio broadcast / daemon graph ports or rusqlite/zstd FFI
  under TSan.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/tsan-permutation-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/tsan-permutation.yml"
$tsanPermTestPath = Join-Path $repoRoot "tests/tsan_permutation.rs"
$raceModelPath = Join-Path $repoRoot "tests/race_model.rs"
$cargoTomlPath = Join-Path $repoRoot "Cargo.toml"
$selfPath = Join-Path $repoRoot "scripts/tsan-permutation-check.ps1"

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
        [string]$Context = "docs/ops/concurrency-safety.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "TSan permutation checker smoke (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + paths; no cargo / no TSan build)"
}

Assert-File -Path $docPath -Label "concurrency safety doc"
Assert-File -Path $workflowPath -Label "tsan-permutation workflow"
Assert-File -Path $tsanPermTestPath -Label "tsan_permutation test wrapper"
Assert-File -Path $raceModelPath -Label "race_model test"
Assert-File -Path $cargoTomlPath -Label "Cargo.toml"
Assert-File -Path $selfPath -Label "tsan permutation check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$raceModel = Get-Content -LiteralPath $raceModelPath -Raw
$cargoToml = Get-Content -LiteralPath $cargoTomlPath -Raw

Write-Host "Concurrency safety doc anchors (done vs unpaid):"
Test-DocContains -Doc $doc -Needle "TSan permutation checkers" `
    -Label "tsan permutation section heading"
Test-DocContains -Doc $doc -Needle "scripts/tsan-permutation-check.ps1" `
    -Label "permutation SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "TSan permutation SelfCheck | **done**" `
    -Label "permutation SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "TSan permutation race_model CI | **done**" `
    -Label "permutation race_model CI gate marked done"
Test-DocContains -Doc $doc -Needle "tsan-permutation.yml" `
    -Label "tsan-permutation workflow reference"
Test-DocContains -Doc $doc -Needle "Full tokio broadcast / daemon graph under TSan | **unpaid**" `
    -Label "full daemon graph under TSan unpaid gate"
Test-DocContains -Doc $doc -Needle "Full daemon SSE graph ports under TSan | **unpaid**" `
    -Label "daemon SSE graph ports under TSan unpaid gate"
Test-DocContains -Doc $doc -Needle "bounded_capacity_is_respected_then_cancel_drains_exactly" `
    -Label "race_model bounded capacity reference"
Test-DocContains -Doc $doc -Needle "concurrent_producers_conserve_messages_under_cancel" `
    -Label "race_model concurrent producers reference"

Write-Host "Workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "tsan-permutation.yml must not set continue-on-error (blocking permutation CI)."
}
[void](Write-Check -Label "workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'tsan-permutation-check\.ps1') {
    throw "tsan-permutation.yml must exercise scripts/tsan-permutation-check.ps1."
}
[void](Write-Check -Label "workflow references tsan-permutation-check.ps1" -Ok $true)

if ($workflow -notmatch 'cargo \+nightly test --test race_model') {
    throw "tsan-permutation.yml must run cargo +nightly test --test race_model."
}
[void](Write-Check -Label "workflow runs cargo +nightly test --test race_model" -Ok $true)

if ($workflow -notmatch 'sanitizer=thread') {
    throw "tsan-permutation.yml must pass -Zsanitizer=thread via RUSTFLAGS."
}
[void](Write-Check -Label "workflow sets thread sanitizer RUSTFLAGS" -Ok $true)

if ($workflow -notmatch 'build-std') {
    throw "tsan-permutation.yml must use -Zbuild-std for TSan (rust-src)."
}
[void](Write-Check -Label "workflow uses -Zbuild-std" -Ok $true)

if ($workflow -notmatch 'x86_64-unknown-linux-gnu') {
    throw "tsan-permutation.yml must target x86_64-unknown-linux-gnu for TSan."
}
[void](Write-Check -Label "workflow targets x86_64-unknown-linux-gnu" -Ok $true)

Write-Host "Cargo / test anchors:"
if ($cargoToml -notmatch "target\.'cfg\(not\(miri\)\)'\.dev-dependencies") {
    throw "Cargo.toml missing [target.'cfg(not(miri))'.dev-dependencies] entry."
}
[void](Write-Check -Label "Cargo.toml cfg(not(miri)) dev-dependencies" -Ok $true)

if ($raceModel -notmatch 'sync_channel') {
    throw "tests/race_model.rs must model bounded sync_channel concurrency."
}
[void](Write-Check -Label "race_model sync_channel model" -Ok $true)

if ($raceModel -notmatch 'AtomicBool') {
    throw "tests/race_model.rs must model cooperative cancel via AtomicBool."
}
[void](Write-Check -Label "race_model cancel flag model" -Ok $true)

if ($raceModel -notmatch 'bounded_capacity_is_respected_then_cancel_drains_exactly') {
    throw "tests/race_model.rs must include bounded capacity permutation target."
}
[void](Write-Check -Label "race_model bounded capacity test" -Ok $true)

if ($raceModel -notmatch 'concurrent_producers_conserve_messages_under_cancel') {
    throw "tests/race_model.rs must include concurrent producers permutation target."
}
[void](Write-Check -Label "race_model concurrent producers test" -Ok $true)

Write-Host "TSan permutation SelfCheck passed"
exit 0
