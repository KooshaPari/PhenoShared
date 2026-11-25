<#
.SYNOPSIS
  Machine-check the platform signing readiness checklist (C11 L112 hard evidence).

.DESCRIPTION
  Verifies that docs/adr/0003-platform-code-signing.md and
  docs/ops/signing-readiness.md document the deferred signing posture, that
  .github/workflows/release.yml retains unsigned MSI/PKG packaging and smoke
  anchors, and that signing-hard.yml + ci.yml provide blocking PR/release gates.
  Does not access signing certificates, notarization credentials, or external
  secret stores.

  -SelfCheck: docs + workflow smoke only (no cargo / no network).

.PARAMETER SelfCheck
  Explicit docs/workflow smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/signing-readiness-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$adrPath = Join-Path $repoRoot "docs/adr/0003-platform-code-signing.md"
$readinessPath = Join-Path $repoRoot "docs/ops/signing-readiness.md"
$releasePath = Join-Path $repoRoot ".github/workflows/release.yml"
$hardWorkflowPath = Join-Path $repoRoot ".github/workflows/signing-hard.yml"
$ciWorkflowPath = Join-Path $repoRoot ".github/workflows/ci.yml"
$distributionPath = Join-Path $repoRoot "docs/ops/distribution.md"
$hardTestPath = Join-Path $repoRoot "tests/signing_hard.rs"
$selfPath = Join-Path $repoRoot "scripts/signing-readiness-check.ps1"

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
        [string]$Context = "docs"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle' ($Label)"
    }
}

function Get-YamlJobBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Document,
        [Parameter(Mandatory = $true)][string]$JobName
    )

    $lines = $Document -split "\r?\n"
    $start = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -eq "  ${JobName}:") {
            $start = $index
            break
        }
    }
    if ($start -lt 0) {
        throw "Workflow missing '$JobName' job definition."
    }

    $end = $lines.Count
    for ($index = $start + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^  [A-Za-z0-9_-]+:\s*$') {
            $end = $index
            break
        }
    }
    return ($lines[$start..($end - 1)] -join "`n")
}

Write-Host "Platform signing readiness check (C11 L112 hard evidence)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (ADR + release.yml unsigned anchors + blocking hard CI; no secrets / no network)"
}

Assert-File -Path $adrPath -Label "ADR 0003"
Assert-File -Path $readinessPath -Label "signing readiness checklist"
Assert-File -Path $releasePath -Label "release workflow"
Assert-File -Path $hardWorkflowPath -Label "signing-hard workflow"
Assert-File -Path $ciWorkflowPath -Label "ci workflow"
Assert-File -Path $distributionPath -Label "distribution guide"
Assert-File -Path $hardTestPath -Label "signing_hard test wrapper"
Assert-File -Path $selfPath -Label "signing readiness check script"

$adr = Get-Content -LiteralPath $adrPath -Raw
$readiness = Get-Content -LiteralPath $readinessPath -Raw
$release = Get-Content -LiteralPath $releasePath -Raw
$hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
$ciWorkflow = Get-Content -LiteralPath $ciWorkflowPath -Raw
$distribution = Get-Content -LiteralPath $distributionPath -Raw
$hardTestRs = Get-Content -LiteralPath $hardTestPath -Raw

Write-Host "ADR 0003 anchors:"
Test-DocContains -Doc $adr -Needle "Platform code-signing and notarization remain deferred" `
    -Label "ADR deferral title" -Context "docs/adr/0003-platform-code-signing.md"
Test-DocContains -Doc $adr -Needle "SHA256SUMS" `
    -Label "ADR portable SHA256SUMS trust path" -Context "docs/adr/0003-platform-code-signing.md"
Test-DocContains -Doc $adr -Needle "Authenticode" `
    -Label "ADR Authenticode deferral" -Context "docs/adr/0003-platform-code-signing.md"
Test-DocContains -Doc $adr -Needle "notarization" `
    -Label "ADR notarization deferral" -Context "docs/adr/0003-platform-code-signing.md"
Test-DocContains -Doc $adr -Needle "## Reconsider when" `
    -Label "ADR reconsider triggers" -Context "docs/adr/0003-platform-code-signing.md"
Test-DocContains -Doc $adr -Needle "signing-readiness.md" `
    -Label "ADR cross-link to signing readiness checklist" -Context "docs/adr/0003-platform-code-signing.md"

Write-Host "Signing readiness checklist anchors:"
Test-DocContains -Doc $readiness -Needle "Platform signing readiness checklist" `
    -Label "checklist heading" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Current unsigned state" `
    -Label "unsigned current state section" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "SessionLedger-<ver>-x64.msi" `
    -Label "unsigned MSI artifact naming" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "SessionLedger-<ver>-<arch>.pkg" `
    -Label "unsigned PKG artifact naming" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "signing-readiness-check.ps1" `
    -Label "SelfCheck script reference" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Signing readiness SelfCheck | **done**" `
    -Label "SelfCheck gate marked done" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "## Soft vs hard gates" `
    -Label "soft vs hard gates matrix section" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Blocking signing-hard CI workflow | **done**" `
    -Label "blocking hard CI gate marked done" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle ".github/workflows/signing-hard.yml" `
    -Label "signing-hard workflow path documented" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "tests/signing_hard.rs" `
    -Label "signing_hard test wrapper documented" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Maintainer-held Apple Developer ID certificate in approved secret store | **unpaid**" `
    -Label "unpaid Apple credential gate" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Maintainer-held Windows Authenticode certificate in approved secret store | **unpaid**" `
    -Label "unpaid Windows credential gate" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Signed clean-host install → launch → uninstall smoke (macOS + Windows) | **unpaid**" `
    -Label "signed clean-host smoke unpaid gate" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "ADR 0001 auto-update requirements satisfied or explicitly out of scope | **unpaid**" `
    -Label "ADR 0001 auto-update unpaid gate" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "Do **not** add placeholder secret names" `
    -Label "no fake secrets policy" -Context "docs/ops/signing-readiness.md"
Test-DocContains -Doc $readiness -Needle "**not** claim platform-native signing" `
    -Label "no false platform signing claim" -Context "docs/ops/signing-readiness.md"

Write-Host "release.yml unsigned path anchors:"
Test-DocContains -Doc $release -Needle "Platform signing / notarization: DEFERRED" `
    -Label "release.yml deferral header comment" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "package Windows MSI (unsigned)" `
    -Label "unsigned Windows MSI packaging step" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "package macOS app + PKG (unsigned)" `
    -Label "unsigned macOS PKG packaging step" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "package-msi.ps1" `
    -Label "package-msi.ps1 invocation" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "smoke-windows:" `
    -Label "smoke-windows job" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "smoke-macos-pkg:" `
    -Label "smoke-macos-pkg job" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "SessionLedger-*-x64.msi" `
    -Label "MSI silent install smoke anchor" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "ADR 0003" `
    -Label "ADR 0003 reference in release workflow" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "signing-readiness:" `
    -Label "release signing-readiness job" -Context ".github/workflows/release.yml"
Test-DocContains -Doc $release -Needle "signing-readiness-check.ps1" `
    -Label "release invokes signing-readiness SelfCheck" -Context ".github/workflows/release.yml"

if ($release -notmatch '(?m)^\s*smoke-windows:\s*$') {
    throw "release.yml missing smoke-windows job definition."
}
if ($release -notmatch '(?ms)^  smoke-macos-pkg:\s*$') {
    throw "release.yml missing smoke-macos-pkg job definition."
}
$signingBlock = Get-YamlJobBlock -Document $release -JobName "signing-readiness"
if ($signingBlock -match 'continue-on-error:\s*true') {
    throw "release.yml signing-readiness job must be blocking (no continue-on-error)."
}
[void](Write-Check -Label "release.yml smoke + signing-readiness job definitions present" -Ok $true)

Write-Host "signing-hard workflow blocking-gate anchors:"
if ($hardWorkflow -match 'continue-on-error:\s*true') {
    throw "signing-hard.yml must not set continue-on-error (blocking SelfCheck CI)."
}
[void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)

if ($hardWorkflow -notmatch 'pull_request:') {
    throw "signing-hard.yml must run on pull_request."
}
[void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)

if ($hardWorkflow -notmatch 'signing-readiness-check\.ps1 -SelfCheck') {
    throw "signing-hard.yml must run scripts/signing-readiness-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hard workflow runs signing-readiness-check.ps1 -SelfCheck" -Ok $true)

Write-Host "ci.yml cross-reference anchors:"
Test-DocContains -Doc $ciWorkflow -Needle "signing-hard.yml" `
    -Label "ci.yml references signing-hard workflow" -Context ".github/workflows/ci.yml"
Test-DocContains -Doc $ciWorkflow -Needle "signing-readiness-check.ps1" `
    -Label "ci.yml references signing-readiness SelfCheck script" -Context ".github/workflows/ci.yml"

$signingPolicyBlock = Get-YamlJobBlock -Document $ciWorkflow -JobName "signing-readiness-policy"
if ($signingPolicyBlock -match 'continue-on-error:\s*true') {
    throw "ci.yml signing-readiness-policy job must be blocking (no continue-on-error)."
}
[void](Write-Check -Label "ci.yml signing-readiness-policy job is blocking when present" -Ok $true)

Write-Host "Distribution cross-links:"
Test-DocContains -Doc $distribution -Needle "Platform code-signing & notarization — DEFERRED" `
    -Label "distribution deferral section" -Context "docs/ops/distribution.md"
Test-DocContains -Doc $distribution -Needle "0003-platform-code-signing.md" `
    -Label "distribution ADR 0003 link" -Context "docs/ops/distribution.md"

Write-Host "cargo test wrapper anchors:"
if ($hardTestRs -notmatch 'signing-readiness-check\.ps1') {
    throw "tests/signing_hard.rs must invoke scripts/signing-readiness-check.ps1."
}
[void](Write-Check -Label "signing_hard.rs invokes SelfCheck script" -Ok $true)

if ($hardTestRs -notmatch 'Platform signing readiness hard SelfCheck passed') {
    throw "tests/signing_hard.rs must assert Platform signing readiness hard SelfCheck passed success line."
}
[void](Write-Check -Label "signing_hard.rs asserts hard success line" -Ok $true)

$summary = @"
## Platform signing readiness hard SelfCheck (C11 L112)

SelfCheck passed: ADR 0003 deferral + ``docs/ops/signing-readiness.md`` unsigned
state checklist + ``release.yml`` unsigned MSI/PKG packaging and smoke anchors +
blocking ``signing-hard.yml`` / ``ci.yml`` / ``release.yml`` gates.

Platform Authenticode / notarization credentials remain **unpaid** — no CI
secret claims were made.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Platform signing readiness hard SelfCheck passed (C11 L112 blocking PR + release gate; Authenticode / notarization credentials unpaid)."
exit 0
