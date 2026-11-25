<#
.SYNOPSIS
  Machine-check Socket.dev supply-chain posture doc anchors (C06 L33).

.DESCRIPTION
  Verifies docs/ops/socket-posture.md + socket-posture.json document Socket.dev
  as an optional org GitHub App complement to in-repo cargo-deny / cargo-audit /
  gitleaks / TruffleHog. Cross-checks SECURITY.md, security.yml job wiring, and
  CVE feed subscription links.
  Hermetic: no network, no Socket API token, no org install attestation.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/socket-posture-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/socket-posture.md"
$policyPath = Join-Path $repoRoot "docs/ops/socket-posture.json"
$cveFeedPath = Join-Path $repoRoot "docs/ops/cve-feed-subscription.md"
$securityPath = Join-Path $repoRoot "SECURITY.md"
$denyPath = Join-Path $repoRoot "deny.toml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$selfPath = Join-Path $repoRoot "scripts/socket-posture-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/socket_posture.rs"

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
        [string]$Context = "docs/ops/socket-posture.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Socket.dev posture check (C06 L33)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no Socket API / no network)"
}

Assert-File -Path $docPath -Label "socket posture doc"
Assert-File -Path $policyPath -Label "socket posture policy JSON"
Assert-File -Path $cveFeedPath -Label "CVE feed subscription doc"
Assert-File -Path $securityPath -Label "SECURITY.md"
Assert-File -Path $denyPath -Label "deny.toml"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $selfPath -Label "socket posture check script"
Assert-File -Path $wrapperTest -Label "socket_posture.rs test wrapper"

$doc = Get-Content -LiteralPath $docPath -Raw
$policy = Get-Content -LiteralPath $policyPath -Raw
$cveFeed = Get-Content -LiteralPath $cveFeedPath -Raw
$security = Get-Content -LiteralPath $securityPath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw

Write-Host "Socket posture doc anchors:"
Test-DocContains -Doc $doc -Needle "Socket.dev supply-chain posture" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "**C06 L33**" `
    -Label "C06 L33 status"
Test-DocContains -Doc $doc -Needle "## Layered controls" `
    -Label "layered controls heading"
Test-DocContains -Doc $doc -Needle "Socket Security: Pull Request Alerts" `
    -Label "expected PR check name"
Test-DocContains -Doc $doc -Needle "NOT_VERIFIABLE_IN_REPO" `
    -Label "org install disclaimer"
Test-DocContains -Doc $doc -Needle "socket-posture-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "socket-posture-check.ps1 -SelfCheck" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "cargo deny" `
    -Label "cargo-deny named"
Test-DocContains -Doc $doc -Needle "cargo audit" `
    -Label "cargo-audit named"
Test-DocContains -Doc $doc -Needle "cve-feed-subscription.md" `
    -Label "CVE feed cross-link"

Write-Host "Policy JSON anchors:"
Test-DocContains -Doc $policy -Needle '"schema_version"' `
    -Label "schema_version" -Context "socket-posture.json"
Test-DocContains -Doc $policy -Needle "Socket Security: Pull Request Alerts" `
    -Label "expected PR checks" -Context "socket-posture.json"
Test-DocContains -Doc $policy -Needle "socket-posture-check.ps1" `
    -Label "verify_command" -Context "socket-posture.json"

Write-Host "Evidence path anchors:"
Test-DocContains -Doc $security -Needle "docs/ops/socket-posture.md" `
    -Label "SECURITY.md -> socket-posture" -Context "SECURITY.md"
Test-DocContains -Doc $security -Needle "socket-posture-check.ps1" `
    -Label "SECURITY.md SelfCheck reference" -Context "SECURITY.md"

if ($securityWf -notmatch 'socket-posture-check\.ps1') {
    throw "security.yml missing socket-posture-check.ps1 SelfCheck job."
}
[void](Write-Check -Label "security.yml socket-posture SelfCheck" -Ok $true)

if ($securityWf -notmatch 'cargo-deny') {
    throw "security.yml missing cargo-deny job/reference."
}
[void](Write-Check -Label "security.yml cargo-deny" -Ok $true)

if ($securityWf -notmatch 'cargo.?audit') {
    throw "security.yml missing cargo-audit job/reference."
}
[void](Write-Check -Label "security.yml cargo-audit" -Ok $true)

if ($securityWf -notmatch 'gitleaks') {
    throw "security.yml missing gitleaks job/reference."
}
[void](Write-Check -Label "security.yml gitleaks" -Ok $true)

if ($securityWf -notmatch 'trufflehog') {
    throw "security.yml missing trufflehog job/reference."
}
[void](Write-Check -Label "security.yml trufflehog" -Ok $true)

if ($cveFeed -notmatch 'socket-posture') {
    throw "cve-feed-subscription.md should cross-link socket-posture (complementary feeds)."
}
[void](Write-Check -Label "cve-feed socket cross-link" -Ok $true)

$summary = @"
## Socket posture SelfCheck

SelfCheck passed: ``docs/ops/socket-posture.md`` anchors, ``socket-posture.json``
manifest, SECURITY.md cross-link, and complementary cargo-deny / cargo-audit /
gitleaks / TruffleHog evidence. Does not claim live Socket.org install.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Socket posture SelfCheck passed (C06 L33; no Socket API / no org install claim)."
exit 0
