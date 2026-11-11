<#
.SYNOPSIS
  Machine-check C11 L119 versioning / CHANGELOG tagged-section anchors.

.PARAMETER SelfCheck
  Explicit docs/path smoke.

.EXAMPLE
  pwsh ./scripts/versioning-policy-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param([switch]$SelfCheck)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$changelog = Join-Path $repoRoot "CHANGELOG.md"
$policy = Join-Path $repoRoot "docs/ops/versioning-policy.md"
$dist = Join-Path $repoRoot "docs/ops/distribution.md"
$script = Join-Path $repoRoot "scripts/versioning-policy-check.ps1"
$wrapper = Join-Path $repoRoot "tests/versioning_policy.rs"

function Assert-File([string]$Path,[string]$Label) {
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Label at '$Path'." }
}
function Write-Check([string]$Label,[bool]$Ok) {
  $mark = if ($Ok) { "PASS" } else { "FAIL" }; Write-Host "  [$mark] $Label"; return $Ok
}
function Assert-Contains([string]$Doc,[string]$Needle,[string]$Label,[string]$Context="document") {
  $ok = $Doc.Contains($Needle); [void](Write-Check -Label $Label -Ok $ok)
  if (-not $ok) { throw "$Context missing required anchor: '$Needle'" }
}

Write-Host "Versioning policy check (C11 L119)"
if ($SelfCheck) { Write-Host "Mode: SelfCheck (CHANGELOG tagged section + policy doc)" }

Assert-File $changelog "CHANGELOG.md"
Assert-File $policy "versioning-policy.md"
Assert-File $dist "distribution.md"
Assert-File $script "versioning-policy-check.ps1"
Assert-File $wrapper "versioning_policy.rs"

$cl = Get-Content -LiteralPath $changelog -Raw
$pol = Get-Content -LiteralPath $policy -Raw
$d = Get-Content -LiteralPath $dist -Raw

Assert-Contains $cl "## [Unreleased]" "Unreleased section" "CHANGELOG.md"
Assert-Contains $cl "## [0.2.0]" "tagged 0.2.0 section" "CHANGELOG.md"
Assert-Contains $cl "Keep a Changelog" "Keep a Changelog mention" "CHANGELOG.md"
Assert-Contains $pol "C11 L119" "policy L119 marker" "versioning-policy.md"
Assert-Contains $pol "SemVer" "SemVer" "versioning-policy.md"
Assert-Contains $pol "Keep a Changelog" "Keep a Changelog" "versioning-policy.md"
Assert-Contains $pol "rust-version" "rust-version" "versioning-policy.md"
Assert-Contains $pol "scripts/versioning-policy-check.ps1" "SelfCheck script ref" "versioning-policy.md"
Assert-Contains $d "CHANGELOG.md" "distribution links CHANGELOG" "distribution.md"
Assert-Contains $d "versioning-policy.md" "distribution links versioning policy" "distribution.md"

Write-Host "Versioning policy SelfCheck passed (C11 L119 tagged CHANGELOG + policy SSOT)."
