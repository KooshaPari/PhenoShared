<#
.SYNOPSIS
  Machine-check the C02 L24 privacy hygiene doc anchors.

.DESCRIPTION
  Verifies docs/ops/privacy-hygiene.md documents single-tenant privacy hygiene
  (PII in logs, transcript retention, redaction guidance, loopback trust) and
  cross-links from SECURITY.md, THREAT_MODEL.md, and local-trust-boundary.md.
  Hermetic: no daemon, no network, no cargo.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/privacy-hygiene-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/privacy-hygiene.md"
$securityPath = Join-Path $repoRoot "SECURITY.md"
$threatPath = Join-Path $repoRoot "docs/THREAT_MODEL.md"
$trustPath = Join-Path $repoRoot "docs/ops/local-trust-boundary.md"
$checkScript = Join-Path $repoRoot "scripts/privacy-hygiene-check.ps1"

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
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "docs/ops/privacy-hygiene.md missing required anchor: '$Needle'"
    }
}

function Test-CrossLink {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "Missing required cross-link anchor: '$Needle' ($Label)"
    }
}

Write-Host "Privacy hygiene checklist check (C02 L24)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no cargo / no network)"
}

Assert-File -Path $docPath -Label "privacy hygiene doc"
Assert-File -Path $checkScript -Label "privacy hygiene check script"
Assert-File -Path $securityPath -Label "SECURITY.md"
Assert-File -Path $threatPath -Label "THREAT_MODEL.md"
Assert-File -Path $trustPath -Label "local trust boundary doc"

$doc = Get-Content -LiteralPath $docPath -Raw
$security = Get-Content -LiteralPath $securityPath -Raw
$threat = Get-Content -LiteralPath $threatPath -Raw
$trust = Get-Content -LiteralPath $trustPath -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "## Single-tenant scope" `
    -Label "single-tenant scope heading"
Test-DocContains -Doc $doc -Needle "not** multi-tenant" `
    -Label "no multi-tenant disclaimer"
Test-DocContains -Doc $doc -Needle "## PII in logs and structured telemetry" `
    -Label "PII in logs heading"
Test-DocContains -Doc $doc -Needle "Do not** log full" `
    -Label "no full transcript logging guidance"
Test-DocContains -Doc $doc -Needle "## Transcript and artifact retention" `
    -Label "transcript retention heading"
Test-DocContains -Doc $doc -Needle "## Redaction before export or share" `
    -Label "redaction guidance heading"
Test-DocContains -Doc $doc -Needle "## Loopback trust and local boundaries" `
    -Label "loopback trust heading"
Test-DocContains -Doc $doc -Needle "local-trust-boundary.md" `
    -Label "local-trust-boundary link in doc"
Test-DocContains -Doc $doc -Needle "scripts/privacy-hygiene-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"

Write-Host "Cross-links:"
Test-CrossLink -Doc $security -Needle "docs/ops/privacy-hygiene.md" `
    -Label "SECURITY.md -> privacy-hygiene"
Test-CrossLink -Doc $threat -Needle "privacy-hygiene.md" `
    -Label "THREAT_MODEL.md -> privacy-hygiene"
Test-CrossLink -Doc $trust -Needle "privacy-hygiene.md" `
    -Label "local-trust-boundary -> privacy-hygiene"

Write-Host "Privacy hygiene SelfCheck passed (C02 L24 doc anchors present; single-tenant only)."
