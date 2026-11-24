<#
.SYNOPSIS
  Machine-check the C04 L36 maintainer 2FA policy doc anchors.

.DESCRIPTION
  Verifies docs/ops/maintainer-2fa.md documents org/account 2FA + hardware-key
  policy, human attestation steps, and a NOT_VERIFIABLE_IN_REPO evidence row.
  Cross-checks SECURITY.md and CONTRIBUTING.md links.
  Hermetic: no network, no GitHub API, no false 2FA enforcement claims.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/maintainer-2fa-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/maintainer-2fa.md"
$securityPath = Join-Path $repoRoot "SECURITY.md"
$contributingPath = Join-Path $repoRoot "CONTRIBUTING.md"
$codeownersPath = Join-Path $repoRoot "CODEOWNERS"
$selfPath = Join-Path $repoRoot "scripts/maintainer-2fa-check.ps1"

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
        [string]$Context = "docs/ops/maintainer-2fa.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Maintainer 2FA policy check (C04 L36)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no network / no GitHub API)"
}

Assert-File -Path $docPath -Label "maintainer 2FA policy doc"
Assert-File -Path $securityPath -Label "SECURITY.md"
Assert-File -Path $contributingPath -Label "CONTRIBUTING.md"
Assert-File -Path $codeownersPath -Label "CODEOWNERS"
Assert-File -Path $selfPath -Label "maintainer 2FA check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$security = Get-Content -LiteralPath $securityPath -Raw
$contributing = Get-Content -LiteralPath $contributingPath -Raw

Write-Host "Maintainer 2FA doc anchors:"
Test-DocContains -Doc $doc -Needle "Maintainer 2FA policy (org hygiene)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "**C04 L36**" `
    -Label "C04 L36 status"
Test-DocContains -Doc $doc -Needle "## Policy (org-level)" `
    -Label "policy heading"
Test-DocContains -Doc $doc -Needle "hardware security key" `
    -Label "hardware key policy"
Test-DocContains -Doc $doc -Needle "## Human attestation process" `
    -Label "human attestation heading"
Test-DocContains -Doc $doc -Needle "cannot prove these controls from a git checkout" `
    -Label "no false in-repo 2FA claim"
Test-DocContains -Doc $doc -Needle "NOT_VERIFIABLE_IN_REPO" `
    -Label "NOT_VERIFIABLE_IN_REPO human row"
Test-DocContains -Doc $doc -Needle "Human attestation row" `
    -Label "human attestation row label"
Test-DocContains -Doc $doc -Needle "scripts/maintainer-2fa-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Maintainer 2FA SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "SECURITY.md" `
    -Label "SECURITY.md link in doc"
Test-DocContains -Doc $doc -Needle "CONTRIBUTING.md" `
    -Label "CONTRIBUTING.md link in doc"
Test-DocContains -Doc $doc -Needle "CODEOWNERS" `
    -Label "CODEOWNERS reference"

Write-Host "Cross-link anchors:"
Test-DocContains -Doc $security -Needle "docs/ops/maintainer-2fa.md" `
    -Label "SECURITY.md -> maintainer-2fa" -Context "SECURITY.md"
Test-DocContains -Doc $security -Needle "maintainer-2fa-check.ps1" `
    -Label "SECURITY.md SelfCheck script" -Context "SECURITY.md"
Test-DocContains -Doc $security -Needle "NOT_VERIFIABLE_IN_REPO" `
    -Label "SECURITY.md NOT_VERIFIABLE_IN_REPO reference" -Context "SECURITY.md"

Test-DocContains -Doc $contributing -Needle "docs/ops/maintainer-2fa.md" `
    -Label "CONTRIBUTING.md -> maintainer-2fa" -Context "CONTRIBUTING.md"
Test-DocContains -Doc $contributing -Needle "maintainer-2fa-check.ps1" `
    -Label "CONTRIBUTING.md SelfCheck script" -Context "CONTRIBUTING.md"
Test-DocContains -Doc $contributing -Needle "cannot be verified from checkout" `
    -Label "CONTRIBUTING.md no false checkout claim" -Context "CONTRIBUTING.md"

$summary = @"
## Maintainer 2FA policy SelfCheck

SelfCheck passed: ``docs/ops/maintainer-2fa.md`` policy anchors,
NOT_VERIFIABLE_IN_REPO human attestation row, and SECURITY.md / CONTRIBUTING.md
cross-links. Does not claim org 2FA enforcement from checkout.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Maintainer 2FA SelfCheck passed (C04 L36 policy SSOT; NOT_VERIFIABLE_IN_REPO human row; no false 2FA claim)."
exit 0
