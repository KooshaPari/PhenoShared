<#
.SYNOPSIS
  Machine-check the C06 L59 source provenance policy doc anchors.

.DESCRIPTION
  Verifies docs/ops/source-provenance.md documents signed commits, CODEOWNERS
  review gates, human org gates (branch protection, maintainer 2FA), and
  NOT_VERIFIABLE_IN_REPO evidence rows. Cross-checks CONTRIBUTING.md,
  commit-signing.md, branch-protection.md, CODEOWNERS, and the branch-protection
  PolicyOnly hook.
  Hermetic: no network, no GitHub API, no false org-gate enforcement claims.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/source-provenance-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/source-provenance.md"
$commitSigningPath = Join-Path $repoRoot "docs/ops/commit-signing.md"
$branchProtectionDocPath = Join-Path $repoRoot "docs/ops/branch-protection.md"
$contributingPath = Join-Path $repoRoot "CONTRIBUTING.md"
$codeownersPath = Join-Path $repoRoot "CODEOWNERS"
$adrPath = Join-Path $repoRoot "docs/adr/0004-commit-signing-policy.md"
$branchProtectionScriptPath = Join-Path $repoRoot "scripts/branch-protection-check.ps1"
$selfPath = Join-Path $repoRoot "scripts/source-provenance-check.ps1"

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
        [string]$Context = "docs/ops/source-provenance.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Source provenance policy check (C06 L59)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no network / no GitHub API)"
}

Assert-File -Path $docPath -Label "source provenance policy doc"
Assert-File -Path $commitSigningPath -Label "commit signing doc"
Assert-File -Path $branchProtectionDocPath -Label "branch protection doc"
Assert-File -Path $contributingPath -Label "CONTRIBUTING.md"
Assert-File -Path $codeownersPath -Label "CODEOWNERS"
Assert-File -Path $adrPath -Label "ADR 0004"
Assert-File -Path $branchProtectionScriptPath -Label "branch protection check script"
Assert-File -Path $selfPath -Label "source provenance check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$commitSigning = Get-Content -LiteralPath $commitSigningPath -Raw
$branchProtectionDoc = Get-Content -LiteralPath $branchProtectionDocPath -Raw
$contributing = Get-Content -LiteralPath $contributingPath -Raw
$codeowners = Get-Content -LiteralPath $codeownersPath -Raw
$branchProtectionScript = Get-Content -LiteralPath $branchProtectionScriptPath -Raw

Write-Host "Source provenance doc anchors:"
Test-DocContains -Doc $doc -Needle "Source code provenance policy" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "**C06 L59**" `
    -Label "C06 L59 status"
Test-DocContains -Doc $doc -Needle "## Policy layers" `
    -Label "policy layers heading"
Test-DocContains -Doc $doc -Needle "GPG / SSH" `
    -Label "signed commits policy"
Test-DocContains -Doc $doc -Needle "## CODEOWNERS review gates" `
    -Label "CODEOWNERS heading"
Test-DocContains -Doc $doc -Needle "## Human org gates (Settings)" `
    -Label "human org gates heading"
Test-DocContains -Doc $doc -Needle "cannot assert the toggle from checkout" `
    -Label "no false CODEOWNERS toggle claim"
Test-DocContains -Doc $doc -Needle "NOT_VERIFIABLE_IN_REPO" `
    -Label "NOT_VERIFIABLE_IN_REPO human rows"
Test-DocContains -Doc $doc -Needle "Human org gate" `
    -Label "human org gate label"
Test-DocContains -Doc $doc -Needle "scripts/source-provenance-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Source provenance SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "branch-protection-check.ps1 -PolicyOnly" `
    -Label "PolicyOnly hook reference"
Test-DocContains -Doc $doc -Needle "Branch protection PolicyOnly hook | **done**" `
    -Label "PolicyOnly gate marked done"

Write-Host "CODEOWNERS anchors:"
if ($codeowners -notmatch '@\w') {
    throw "CODEOWNERS must list at least one owner handle."
}
[void](Write-Check -Label "CODEOWNERS owner handle present" -Ok $true)

Write-Host "Branch protection PolicyOnly hook:"
Test-DocContains -Doc $branchProtectionScript -Needle "PolicyOnly" `
    -Label "branch-protection-check.ps1 defines PolicyOnly" `
    -Context "scripts/branch-protection-check.ps1"

Write-Host "Cross-link anchors:"
Test-DocContains -Doc $contributing -Needle "docs/ops/source-provenance.md" `
    -Label "CONTRIBUTING.md -> source-provenance" -Context "CONTRIBUTING.md"
Test-DocContains -Doc $contributing -Needle "source-provenance-check.ps1" `
    -Label "CONTRIBUTING.md SelfCheck script" -Context "CONTRIBUTING.md"
Test-DocContains -Doc $commitSigning -Needle "branch-protection-check.ps1" `
    -Label "commit-signing.md branch-protection script" -Context "docs/ops/commit-signing.md"
Test-DocContains -Doc $branchProtectionDoc -Needle "source-provenance.md" `
    -Label "branch-protection.md -> source-provenance" -Context "docs/ops/branch-protection.md"

$summary = @"
## Source provenance policy SelfCheck

SelfCheck passed: ``docs/ops/source-provenance.md`` policy anchors (signed commits,
CODEOWNERS, human org gates), NOT_VERIFIABLE_IN_REPO rows, and CONTRIBUTING.md
cross-links. Does not claim GitHub Settings enforcement from checkout.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Source provenance SelfCheck passed (C06 L59 policy SSOT; NOT_VERIFIABLE_IN_REPO human org rows; no false Settings claim)."
exit 0
