<#
.SYNOPSIS
  Machine-check the C06 L53 protected-environment SLSA Build L3 checklist.

.DESCRIPTION
  Single source of truth for GitHub Environments / protected-branch requirements.
  Verifies docs/ops/slsa-protected-environment.md checklist anchors, done-gate
  evidence paths, cross-links in hermetic-builds.md and branch-protection.md,
  and that release.yml documents the blocking oci-image release path.

  Unpaid L3 gates are reported but do not fail SelfCheck — they remain
  operator/maintainer work until a GitHub Environment is wired and publish
  jobs bind `environment: release`.

  -SelfCheck (default when no other mode is requested): docs + path consistency
  only — no cargo build, no network, no gh API. Safe for soft CI.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.PARAMETER Strict
  Also fail when unpaid checklist gates are still marked unpaid in the doc
  (not recommended for CI until Environments land).

.EXAMPLE
  pwsh ./scripts/slsa-protected-env-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,

    [switch]$Strict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/slsa-protected-environment.md"
$hermeticDocPath = Join-Path $repoRoot "docs/ops/hermetic-builds.md"
$branchProtectionDocPath = Join-Path $repoRoot "docs/ops/branch-protection.md"
$releaseWorkflow = Join-Path $repoRoot ".github/workflows/release.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$selfPath = Join-Path $repoRoot "scripts/slsa-protected-env-check.ps1"

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
        [string]$Context = "docs/ops/slsa-protected-environment.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "SLSA protected-environment checklist check (C06 L53)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no cargo / no network)"
}

Assert-File -Path $docPath -Label "protected environment policy doc"
Assert-File -Path $hermeticDocPath -Label "hermetic builds doc"
Assert-File -Path $branchProtectionDocPath -Label "branch protection doc"
Assert-File -Path $releaseWorkflow -Label "release workflow"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $selfPath -Label "SLSA protected environment check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$hermeticDoc = Get-Content -LiteralPath $hermeticDocPath -Raw
$branchProtectionDoc = Get-Content -LiteralPath $branchProtectionDocPath -Raw
$release = Get-Content -LiteralPath $releaseWorkflow -Raw
$security = Get-Content -LiteralPath $securityWorkflow -Raw

Write-Host "Protected-environment doc anchors:"
Test-DocContains -Doc $doc -Needle "Protected environment policy (SLSA Build L3)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "**C06 L53**" `
    -Label "C06 L53 status"
Test-DocContains -Doc $doc -Needle "GitHub Environments" `
    -Label "GitHub Environments policy"
Test-DocContains -Doc $doc -Needle "protected branches" `
    -Label "protected branches policy"
Test-DocContains -Doc $doc -Needle "does **not** claim full protected-environment attestation" `
    -Label "no false full attestation claim"
Test-DocContains -Doc $doc -Needle "scripts/slsa-protected-env-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "hermetic-builds.md" `
    -Label "hermetic-builds.md link in doc"
Test-DocContains -Doc $doc -Needle "branch-protection.md" `
    -Label "branch-protection.md link in doc"
Test-DocContains -Doc $doc -Needle "NOT_VERIFIABLE_IN_REPO" `
    -Label "NOT_VERIFIABLE_IN_REPO human row"

$doneNeedles = @(
    @{ Needle = "Protected-environment policy documented | **done**"; Label = "policy doc marked done" },
    @{ Needle = "Protected-environment SelfCheck | **done**"; Label = "SelfCheck gate marked done" },
    @{ Needle = "``hermetic-builds.md`` cross-link | **done**"; Label = "hermetic-builds cross-link marked done" },
    @{ Needle = "``branch-protection.md`` cross-link | **done**"; Label = "branch-protection cross-link marked done" },
    @{ Needle = "Release workflow + blocking ``oci-image`` documented | **done**"; Label = "release oci-image row marked done" }
)
Write-Host "Done-gate status marks:"
foreach ($item in $doneNeedles) {
    Test-DocContains -Doc $doc -Needle $item.Needle -Label $item.Label
}

$unpaidNeedles = @(
    "GitHub Environment ``release`` with required reviewers | unpaid",
    "``environment: release`` on publish jobs | unpaid",
    "Environment deployment branch / tag rules | unpaid",
    "Full SLSA Build L3 protected-environment attestation | unpaid"
)
Write-Host "Unpaid L3 gap rows (documented, not yet closed):"
$unpaidStillOpen = 0
foreach ($needle in $unpaidNeedles) {
    $present = $doc.Contains($needle)
    if ($present) {
        Write-Host "  [OPEN] $needle"
        $unpaidStillOpen++
    }
    else {
        Write-Host "  [CLOSED-or-renamed] expected unpaid row missing: $needle"
    }
}

Write-Host "Hermetic-builds cross-links:"
if ($hermeticDoc -notmatch 'slsa-protected-environment\.md') {
    throw "docs/ops/hermetic-builds.md must cross-link docs/ops/slsa-protected-environment.md."
}
[void](Write-Check -Label "hermetic-builds.md links protected-environment SSOT" -Ok $true)
if ($hermeticDoc -notmatch 'slsa-protected-env-check\.ps1') {
    throw "docs/ops/hermetic-builds.md must reference scripts/slsa-protected-env-check.ps1."
}
[void](Write-Check -Label "hermetic-builds.md references slsa-protected-env-check.ps1" -Ok $true)

Write-Host "Branch-protection cross-links:"
if ($branchProtectionDoc -notmatch 'slsa-protected-environment\.md') {
    throw "docs/ops/branch-protection.md must cross-link docs/ops/slsa-protected-environment.md."
}
[void](Write-Check -Label "branch-protection.md links protected-environment SSOT" -Ok $true)
if ($doc -notmatch 'branch-protection\.md') {
    throw "docs/ops/slsa-protected-environment.md must cross-link branch-protection.md."
}
[void](Write-Check -Label "protected-environment doc links branch-protection.md" -Ok $true)

Write-Host "Release workflow anchors:"
if ($release -notmatch '(?m)^\s*oci-image:\s*$') {
    throw "release.yml missing oci-image job."
}
if ($release -notmatch 'detect OCI release gate') {
    throw "release.yml missing detect OCI release gate step for canonical blocking / fork skip."
}
if ($release -notmatch '(?s)needs:.*?\boci-image\b') {
    throw "release.yml release job should depend on oci-image for blocking publication."
}
[void](Write-Check -Label "release.yml blocking oci-image release path documented" -Ok $true)

if ($release -match '(?m)^\s*environment:\s*release\s*$') {
    Write-Host "  [NOTE] release.yml already binds environment: release (update unpaid row when intentional)."
}
else {
    Write-Host "  [OPEN] release.yml has no environment: release binding (expected unpaid)."
}

Write-Host "Security workflow wiring:"
if ($security -notmatch 'slsa-protected-env-check\.ps1') {
    throw "security.yml must run scripts/slsa-protected-env-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "security.yml runs slsa-protected-env-check SelfCheck" -Ok $true)

if ($security -match '(?ms)^  slsa-protected-env:(.*?)(?=^  [a-z][a-z0-9-]*:)') {
    $slsaBlock = $Matches[1]
    if ($slsaBlock -match 'continue-on-error:\s*true') {
        throw "security.yml slsa-protected-env job must be blocking (no continue-on-error)."
    }
} else {
    throw "security.yml must define a slsa-protected-env job block."
}
[void](Write-Check -Label "slsa-protected-env job is blocking" -Ok $true)

$summary = @"
## SLSA protected-environment checklist (C06 L53)

SelfCheck passed: ``docs/ops/slsa-protected-environment.md`` checklist anchors +
done-gate evidence paths + hermetic-builds / branch-protection cross-links +
release.yml blocking oci-image documentation + blocking ``security.yml`` gate.

Unpaid L3 rows still documented as open: $unpaidStillOpen
(GitHub Environment ``release``, ``environment:`` YAML binding, deployment rules,
full protected-environment attestation). Blocking SelfCheck only — **not** a SLSA
Build L3 attestation; live Environment protection cannot be proven from checkout alone.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

if ($Strict -and $unpaidStillOpen -gt 0) {
    Write-Host "Strict mode: $unpaidStillOpen unpaid L3 checklist row(s) remain."
    exit 1
}

Write-Host "SLSA protected-environment SelfCheck passed ($unpaidStillOpen unpaid L3 gap row(s) still documented)."
exit 0
