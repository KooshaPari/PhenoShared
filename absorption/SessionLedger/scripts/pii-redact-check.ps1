<#
.SYNOPSIS
  Machine-check the C02 L24 in-tree PII redaction helper anchors.

.DESCRIPTION
  Verifies src/pii_redact.rs (redact / email / API-key APIs),
  docs/ops/pii-redaction.md Phase-0 decision + non-multi-tenant disclaimer,
  and the hermetic SelfCheck wiring. No daemon, no network, no cargo.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/pii-redact-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$helperPath = Join-Path $repoRoot "src/pii_redact.rs"
$docPath = Join-Path $repoRoot "docs/ops/pii-redaction.md"
$privacyPath = Join-Path $repoRoot "docs/ops/privacy-hygiene.md"
$checkScript = Join-Path $repoRoot "scripts/pii-redact-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/pii_redact.rs"

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

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "document"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "PII redaction helper check (C02 L24)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (helper + docs; no cargo / no network / no multi-tenant claim)"
}

Assert-File -Path $helperPath -Label "PII redaction Rust helper"
Assert-File -Path $docPath -Label "PII redaction ops doc"
Assert-File -Path $privacyPath -Label "privacy hygiene doc"
Assert-File -Path $checkScript -Label "PII redaction check script"
Assert-File -Path $rustWrapper -Label "PII redaction rust SelfCheck wrapper"

$helper = Get-Content -LiteralPath $helperPath -Raw
$doc = Get-Content -LiteralPath $docPath -Raw
$privacy = Get-Content -LiteralPath $privacyPath -Raw

Write-Host "Helper anchors:"
Assert-Contains -Doc $helper -Needle "C02 L24" `
    -Label "C02 L24 marker" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "pub const REDACTED_EMAIL" `
    -Label "REDACTED_EMAIL const" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "pub const REDACTED_API_KEY" `
    -Label "REDACTED_API_KEY const" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "pub fn redact(" `
    -Label "pub fn redact" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "pub fn redact_emails(" `
    -Label "pub fn redact_emails" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "pub fn redact_api_keys(" `
    -Label "pub fn redact_api_keys" -Context "src/pii_redact.rs"
Assert-Contains -Doc $helper -Needle "not** multi-tenant" `
    -Label "no multi-tenant claim in helper docs" -Context "src/pii_redact.rs"

Write-Host "Doc anchors:"
Assert-Contains -Doc $doc -Needle "## Phase-0 decision" `
    -Label "Phase-0 decision heading" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "not** multi-tenant" `
    -Label "no multi-tenant disclaimer" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "src/pii_redact.rs" `
    -Label "helper path reference" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "session_ledger::pii_redact::redact" `
    -Label "API path mention" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "## Future hooks" `
    -Label "future hooks heading" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "scripts/pii-redact-check.ps1" `
    -Label "SelfCheck script reference" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation" -Context "docs/ops/pii-redaction.md"
Assert-Contains -Doc $doc -Needle "PII redaction SelfCheck | **done**" `
    -Label "SelfCheck gate marked done" -Context "docs/ops/pii-redaction.md"

Write-Host "Privacy hygiene cross-link:"
Assert-Contains -Doc $privacy -Needle "pii-redaction.md" `
    -Label "privacy-hygiene -> pii-redaction" -Context "docs/ops/privacy-hygiene.md"

Write-Host "PII redaction SelfCheck passed (C02 L24 helper stub; single-tenant opt-in scrub only)."
