<#
.SYNOPSIS
  Machine-check shuttle permutation checker anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/concurrency-safety.md documents the shuttle permutation lane
  (done vs unpaid rows), that the shuttle-permutation workflow, shuttle_permutation
  test, soft shuttle cross-links, and this script stay wired. Hermetic: no cargo,
  no shuttle download — suitable for default Windows cargo test.

  Does not claim full tokio broadcast / daemon graph ports or a cfg-gated shuttle crate.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/shuttle-permutation-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$shuttleSoftDocPath = Join-Path $repoRoot "docs/ops/shuttle-soft.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/shuttle-permutation.yml"
$shuttlePermTestPath = Join-Path $repoRoot "tests/shuttle_permutation.rs"
$shuttleSoftTestPath = Join-Path $repoRoot "tests/shuttle_soft.rs"
$raceModelPath = Join-Path $repoRoot "tests/race_model.rs"
$cargoTomlPath = Join-Path $repoRoot "Cargo.toml"
$selfPath = Join-Path $repoRoot "scripts/shuttle-permutation-check.ps1"

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

Write-Host "Shuttle permutation checker smoke (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + cfg anchors; no cargo / no shuttle)"
}

Assert-File -Path $docPath -Label "concurrency safety doc"
Assert-File -Path $shuttleSoftDocPath -Label "shuttle soft doc"
Assert-File -Path $workflowPath -Label "shuttle-permutation workflow"
Assert-File -Path $shuttlePermTestPath -Label "shuttle_permutation test wrapper"
Assert-File -Path $shuttleSoftTestPath -Label "shuttle_soft test"
Assert-File -Path $raceModelPath -Label "race_model test"
Assert-File -Path $cargoTomlPath -Label "Cargo.toml"
Assert-File -Path $selfPath -Label "shuttle permutation check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$shuttleSoftDoc = Get-Content -LiteralPath $shuttleSoftDocPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$raceModel = Get-Content -LiteralPath $raceModelPath -Raw
$cargoToml = Get-Content -LiteralPath $cargoTomlPath -Raw

Write-Host "Concurrency safety doc anchors (done vs unpaid):"
Test-DocContains -Doc $doc -Needle "Shuttle permutation checkers" `
    -Label "shuttle permutation section heading"
Test-DocContains -Doc $doc -Needle "scripts/shuttle-permutation-check.ps1" `
    -Label "permutation SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Shuttle permutation SelfCheck | **done**" `
    -Label "permutation SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Shuttle permutation suite CI | **done**" `
    -Label "permutation suite CI gate marked done"
Test-DocContains -Doc $doc -Needle "shuttle-permutation.yml" `
    -Label "shuttle-permutation workflow reference"
Test-DocContains -Doc $doc -Needle "Full tokio broadcast / daemon graph under shuttle | **unpaid**" `
    -Label "full daemon graph unpaid gate"
Test-DocContains -Doc $doc -Needle "Full shuttle crate permutation | **unpaid**" `
    -Label "shuttle crate permutation unpaid gate"
Test-DocContains -Doc $doc -Needle "bounded_capacity_is_respected_then_cancel_drains_exactly" `
    -Label "race_model bounded capacity reference"
Test-DocContains -Doc $doc -Needle "concurrent_producers_conserve_messages_under_cancel" `
    -Label "race_model concurrent producers reference"

Write-Host "Shuttle soft doc cross-link anchors:"
Test-DocContains -Doc $shuttleSoftDoc -Needle "shuttle-permutation.yml" `
    -Label "shuttle-soft links blocking permutation workflow" `
    -Context "docs/ops/shuttle-soft.md"
Test-DocContains -Doc $shuttleSoftDoc -Needle "shuttle-permutation-check.ps1" `
    -Label "shuttle-soft links permutation SelfCheck script" `
    -Context "docs/ops/shuttle-soft.md"
Test-DocContains -Doc $shuttleSoftDoc -Needle "Shuttle permutation SelfCheck | **done**" `
    -Label "shuttle-soft permutation SelfCheck gate marked done" `
    -Context "docs/ops/shuttle-soft.md"

Write-Host "Workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "shuttle-permutation.yml must not set continue-on-error (blocking permutation CI)."
}
[void](Write-Check -Label "workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'shuttle-permutation-check\.ps1') {
    throw "shuttle-permutation.yml must exercise scripts/shuttle-permutation-check.ps1."
}
[void](Write-Check -Label "workflow references shuttle-permutation-check.ps1" -Ok $true)

if ($workflow -notmatch 'cargo test shuttle_permutation') {
    throw "shuttle-permutation.yml must run cargo test shuttle_permutation."
}
[void](Write-Check -Label "workflow runs cargo test shuttle_permutation" -Ok $true)

Write-Host "Cargo / test cfg anchors:"
if ($cargoToml -match '(?m)^\s*shuttle\s*=') {
    throw "Cargo.toml must not declare a shuttle dependency for this hermetic permutation lane."
}
[void](Write-Check -Label "Cargo.toml has no shuttle package" -Ok $true)

if ($raceModel -notmatch 'bounded_capacity_is_respected_then_cancel_drains_exactly') {
    throw "tests/race_model.rs must include bounded capacity permutation target."
}
[void](Write-Check -Label "race_model bounded capacity test" -Ok $true)

if ($raceModel -notmatch 'concurrent_producers_conserve_messages_under_cancel') {
    throw "tests/race_model.rs must include concurrent producers permutation target."
}
[void](Write-Check -Label "race_model concurrent producers test" -Ok $true)

Write-Host "Shuttle permutation SelfCheck passed"
exit 0
