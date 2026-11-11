<#
.SYNOPSIS
  Machine-check Miri permutation checker anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/concurrency-safety.md documents the Miri permutation lane
  (done vs unpaid rows), that the miri-permutation workflow, race_model test,
  soft miri-smoke split, and this script stay wired. Hermetic: no cargo, no
  miri download — suitable for default Windows cargo test.

  Does not claim loom_model under Miri or full tokio broadcast / daemon graph ports.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/miri-permutation-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/miri-permutation.yml"
$miriSmokePath = Join-Path $repoRoot ".github/workflows/miri-smoke.yml"
$raceModelPath = Join-Path $repoRoot "tests/race_model.rs"
$cargoTomlPath = Join-Path $repoRoot "Cargo.toml"
$selfPath = Join-Path $repoRoot "scripts/miri-permutation-check.ps1"

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

function Test-DocContent {
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

function Test-DocPattern {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "docs/ops/concurrency-safety.md"
    )
    $ok = $Doc -cmatch $Pattern
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required pattern: '$Pattern'"
    }
}

Write-Host "Miri permutation checker smoke (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + miri anchors; no cargo / no miri)"
}

Assert-File -Path $docPath -Label "concurrency safety doc"
Assert-File -Path $workflowPath -Label "miri-permutation workflow"
Assert-File -Path $miriSmokePath -Label "miri-smoke workflow"
Assert-File -Path $raceModelPath -Label "race_model test"
Assert-File -Path $cargoTomlPath -Label "Cargo.toml"
Assert-File -Path $selfPath -Label "miri permutation check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$miriSmoke = Get-Content -LiteralPath $miriSmokePath -Raw
$raceModel = Get-Content -LiteralPath $raceModelPath -Raw
$cargoToml = Get-Content -LiteralPath $cargoTomlPath -Raw

Write-Host "Concurrency safety doc anchors (done vs unpaid):"
Test-DocContent -Doc $doc -Needle "Miri permutation checkers" `
    -Label "miri permutation section heading"
Test-DocContent -Doc $doc -Needle "scripts/miri-permutation-check.ps1" `
    -Label "permutation SelfCheck script reference"
Test-DocPattern -Doc $doc -Pattern "(?m)^\| Miri permutation SelfCheck\s+\|\s+\*\*done\*\*\s+\|" `
    -Label "permutation SelfCheck gate marked done"
Test-DocPattern -Doc $doc -Pattern "(?m)^\| Miri permutation race_model CI\s+\|\s+\*\*done\*\*\s+\|" `
    -Label "permutation race_model CI gate marked done"
Test-DocContent -Doc $doc -Needle "miri-permutation.yml" `
    -Label "miri-permutation workflow reference"
Test-DocContent -Doc $doc -Needle "miri-smoke.yml" `
    -Label "miri-smoke soft workflow reference retained"
Test-DocPattern -Doc $doc -Pattern "(?m)^\| loom_model under Miri\s+\|\s+\*\*unpaid\*\*\s+\|" `
    -Label "loom_model under Miri unpaid gate"
Test-DocContent -Doc $doc -Needle "Full loom / shuttle permutation checkers | **unpaid**" `
    -Label "shared loom/shuttle unpaid gate retained"

Write-Host "Workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "miri-permutation.yml must not set continue-on-error (blocking permutation CI)."
}
[void](Write-Check -Label "miri-permutation workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'miri-permutation-check\.ps1') {
    throw "miri-permutation.yml must exercise scripts/miri-permutation-check.ps1."
}
[void](Write-Check -Label "workflow references miri-permutation-check.ps1" -Ok $true)

if ($workflow -notmatch 'cargo miri test --test race_model') {
    throw "miri-permutation.yml must run cargo miri test --test race_model."
}
[void](Write-Check -Label "workflow runs cargo miri test --test race_model" -Ok $true)

if ($workflow -notmatch 'MIRIFLAGS') {
    throw "miri-permutation.yml must pass MIRIFLAGS for strict provenance."
}
[void](Write-Check -Label "workflow sets MIRIFLAGS" -Ok $true)

Write-Host "Soft miri-smoke split anchors:"
if ($miriSmoke -notmatch 'continue-on-error:\s*true') {
    throw "miri-smoke.yml must remain soft (continue-on-error: true)."
}
[void](Write-Check -Label "miri-smoke workflow remains continue-on-error" -Ok $true)

if ($miriSmoke -notmatch 'cargo miri test --test race_model') {
    throw "miri-smoke.yml must still run cargo miri test --test race_model."
}
[void](Write-Check -Label "miri-smoke workflow runs race_model subset" -Ok $true)

Write-Host "Cargo / test miri anchors:"
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

Write-Host "Miri permutation SelfCheck passed"
exit 0
