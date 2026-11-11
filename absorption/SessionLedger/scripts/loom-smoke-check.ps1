<#
.SYNOPSIS
  Machine-check soft loom concurrency smoke anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/concurrency-safety.md documents the soft loom lane and that
  the loom-smoke workflow, loom_model test, and this script stay wired.
  Hermetic: no cargo, no loom download — suitable for default Windows cargo test.

  Does not claim full loom/shuttle permutation coverage or blocking Miri.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/loom-smoke-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/loom-smoke.yml"
$loomModelPath = Join-Path $repoRoot "tests/loom_model.rs"
$cargoTomlPath = Join-Path $repoRoot "Cargo.toml"
$selfPath = Join-Path $repoRoot "scripts/loom-smoke-check.ps1"

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

Write-Host "Soft loom concurrency smoke check (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + cfg anchors; no cargo / no loom)"
}

Assert-File -Path $docPath -Label "concurrency safety doc"
Assert-File -Path $workflowPath -Label "loom-smoke workflow"
Assert-File -Path $loomModelPath -Label "loom_model test"
Assert-File -Path $cargoTomlPath -Label "Cargo.toml"
Assert-File -Path $selfPath -Label "loom smoke check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$loomModel = Get-Content -LiteralPath $loomModelPath -Raw
$cargoToml = Get-Content -LiteralPath $cargoTomlPath -Raw

Write-Host "Concurrency safety doc anchors:"
Test-DocContains -Doc $doc -Needle "Soft loom smoke" `
    -Label "soft loom section heading"
Test-DocContains -Doc $doc -Needle "scripts/loom-smoke-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Soft loom SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "loom-smoke.yml" `
    -Label "loom-smoke workflow reference"
Test-DocContains -Doc $doc -Needle "continue-on-error" `
    -Label "soft continue-on-error note"
Test-DocContains -Doc $doc -Needle "RUSTFLAGS='--cfg loom'" `
    -Label "cfg loom RUSTFLAGS note"
Test-DocContains -Doc $doc -Needle "tests/loom_model.rs" `
    -Label "loom_model test reference"
Test-DocContains -Doc $doc -Needle "Full loom / shuttle permutation checkers | **unpaid**" `
    -Label "full checkers unpaid gate"

Write-Host "Workflow soft-gate anchors:"
if ($workflow -notmatch 'continue-on-error:\s*true') {
    throw "loom-smoke.yml must set continue-on-error: true (soft gate)."
}
[void](Write-Check -Label "workflow continue-on-error: true" -Ok $true)

if ($workflow -notmatch 'loom_model') {
    throw "loom-smoke.yml must exercise tests/loom_model.rs."
}
[void](Write-Check -Label "workflow references loom_model" -Ok $true)

if ($workflow -notmatch '--cfg loom') {
    throw "loom-smoke.yml must pass RUSTFLAGS --cfg loom."
}
[void](Write-Check -Label "workflow sets --cfg loom" -Ok $true)

Write-Host "Cargo / test cfg anchors:"
if ($cargoToml -notmatch "target\.'cfg\(loom\)'\.dev-dependencies") {
    throw "Cargo.toml missing [target.'cfg(loom)'.dev-dependencies] loom entry."
}
[void](Write-Check -Label "Cargo.toml cfg(loom) dev-dependencies" -Ok $true)

if ($cargoToml -notmatch '(?m)^loom\s*=') {
    throw "Cargo.toml cfg(loom) block must declare loom dependency."
}
[void](Write-Check -Label "Cargo.toml loom package" -Ok $true)

if ($loomModel -notmatch '#\[cfg\(loom\)\]') {
    throw "tests/loom_model.rs must gate the permutation body on cfg(loom)."
}
[void](Write-Check -Label "loom_model cfg(loom) gate" -Ok $true)

if ($loomModel -notmatch '#\[cfg\(not\(loom\)\)\]') {
    throw "tests/loom_model.rs must keep a not(loom) skip marker for default cargo test."
}
[void](Write-Check -Label "loom_model not(loom) skip marker" -Ok $true)

Write-Host "Soft loom SelfCheck passed"
exit 0
