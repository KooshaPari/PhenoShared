<#
.SYNOPSIS
  Machine-check soft shuttle concurrency smoke anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/shuttle-soft.md documents the hermetic soft shuttle lane and
  that the shuttle-soft workflow, shuttle_soft test, and this script stay wired.
  Hermetic: no cargo, no shuttle crate download — suitable for default Windows cargo test.

  Explicitly does not claim full shuttle permutation coverage.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/shuttle-soft-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/shuttle-soft.md"
$concurrencyDocPath = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/shuttle-soft.yml"
$shuttleSoftTestPath = Join-Path $repoRoot "tests/shuttle_soft.rs"
$cargoTomlPath = Join-Path $repoRoot "Cargo.toml"
$selfPath = Join-Path $repoRoot "scripts/shuttle-soft-check.ps1"

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
        [string]$Context = "docs/ops/shuttle-soft.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Soft shuttle concurrency smoke check (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow anchors; no cargo / no shuttle crate)"
}

Assert-File -Path $docPath -Label "shuttle soft doc"
Assert-File -Path $concurrencyDocPath -Label "concurrency safety doc"
Assert-File -Path $workflowPath -Label "shuttle-soft workflow"
Assert-File -Path $shuttleSoftTestPath -Label "shuttle_soft test"
Assert-File -Path $cargoTomlPath -Label "Cargo.toml"
Assert-File -Path $selfPath -Label "shuttle soft check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$concurrencyDoc = Get-Content -LiteralPath $concurrencyDocPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$shuttleSoftTest = Get-Content -LiteralPath $shuttleSoftTestPath -Raw
$cargoToml = Get-Content -LiteralPath $cargoTomlPath -Raw

Write-Host "Shuttle soft doc anchors:"
Test-DocContains -Doc $doc -Needle "Soft shuttle permutation evidence" `
    -Label "soft shuttle section heading"
Test-DocContains -Doc $doc -Needle "scripts/shuttle-soft-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Soft shuttle SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "shuttle-soft.yml" `
    -Label "shuttle-soft workflow reference"
Test-DocContains -Doc $doc -Needle "continue-on-error" `
    -Label "soft continue-on-error note"
Test-DocContains -Doc $doc -Needle "tests/shuttle_soft.rs" `
    -Label "shuttle_soft test reference"
Test-DocContains -Doc $doc -Needle "Full shuttle permutation coverage | **unpaid**" `
    -Label "full shuttle unpaid gate"
Test-DocContains -Doc $doc -Needle "Full shuttle permutation coverage remains unpaid" `
    -Label "explicit unpaid statement (prose)"

Write-Host "Concurrency safety cross-link anchors:"
Test-DocContains -Doc $concurrencyDoc -Needle "Soft shuttle" `
    -Label "concurrency-safety soft shuttle section" `
    -Context "docs/ops/concurrency-safety.md"
Test-DocContains -Doc $concurrencyDoc -Needle "shuttle-soft.md" `
    -Label "concurrency-safety links shuttle-soft.md" `
    -Context "docs/ops/concurrency-safety.md"
Test-DocContains -Doc $concurrencyDoc -Needle "Full loom / shuttle permutation checkers | **unpaid**" `
    -Label "shared unpaid loom/shuttle gate retained" `
    -Context "docs/ops/concurrency-safety.md"

Write-Host "Workflow soft-gate anchors:"
if ($workflow -notmatch 'continue-on-error:\s*true') {
    throw "shuttle-soft.yml must set continue-on-error: true (soft gate)."
}
[void](Write-Check -Label "workflow continue-on-error: true" -Ok $true)

if ($workflow -notmatch 'shuttle-soft-check\.ps1') {
    throw "shuttle-soft.yml must exercise scripts/shuttle-soft-check.ps1."
}
[void](Write-Check -Label "workflow references shuttle-soft-check.ps1" -Ok $true)

if ($workflow -notmatch '-SelfCheck') {
    throw "shuttle-soft.yml must pass -SelfCheck."
}
[void](Write-Check -Label "workflow passes -SelfCheck" -Ok $true)

Write-Host "Hermetic / no-heavy-dep anchors:"
if ($cargoToml -match '(?m)^\s*shuttle\s*=') {
    throw "Cargo.toml must not declare a shuttle dependency for this hermetic soft lane."
}
[void](Write-Check -Label "Cargo.toml has no shuttle package" -Ok $true)

if ($shuttleSoftTest -notmatch 'shuttle-soft-check\.ps1') {
    throw "tests/shuttle_soft.rs must invoke shuttle-soft-check.ps1."
}
[void](Write-Check -Label "shuttle_soft invokes SelfCheck script" -Ok $true)

if ($shuttleSoftTest -notmatch 'Soft shuttle SelfCheck passed') {
    throw "tests/shuttle_soft.rs must assert the SelfCheck success line."
}
[void](Write-Check -Label "shuttle_soft asserts success line" -Ok $true)

Write-Host "Soft shuttle SelfCheck passed"
exit 0
