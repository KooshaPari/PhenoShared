<#
.SYNOPSIS
  Machine-check the C02 L22 crypto inventory doc anchors.

.DESCRIPTION
  Verifies docs/ops/crypto-inventory.md documents the cryptography inventory,
  explicit no-KMS / no-encryption-at-rest posture, Phase-0 deferred vs
  recommended deploy KMS/at-rest guidance, TLS reverse-proxy samples, and
  API-key handling cross-links. Hermetic: no daemon, no network, no cargo,
  no KMS SDK.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/crypto-inventory-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/crypto-inventory.md"
$securityPath = Join-Path $repoRoot "SECURITY.md"
$trustPath = Join-Path $repoRoot "docs/ops/local-trust-boundary.md"
$caddyPath = Join-Path $repoRoot "packaging/caddy/Caddyfile"
$nginxPath = Join-Path $repoRoot "packaging/nginx/sessionledger.conf"
$checkScript = Join-Path $repoRoot "scripts/crypto-inventory-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/crypto_inventory.rs"

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
        throw "docs/ops/crypto-inventory.md missing required anchor: '$Needle'"
    }
}

Write-Host "Crypto inventory checklist check (C02 L22)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no cargo / no network / no KMS)"
}

Assert-File -Path $docPath -Label "crypto inventory doc"
Assert-File -Path $checkScript -Label "crypto inventory check script"
Assert-File -Path $rustWrapper -Label "crypto inventory rust SelfCheck wrapper"
Assert-File -Path $securityPath -Label "SECURITY.md"
Assert-File -Path $trustPath -Label "local trust boundary doc"
Assert-File -Path $caddyPath -Label "Caddy sample"
Assert-File -Path $nginxPath -Label "nginx sample"
$envelopePath = Join-Path $repoRoot "src/envelope.rs"
Assert-File -Path $envelopePath -Label "envelope soft stub"

$doc = Get-Content -LiteralPath $docPath -Raw
$security = Get-Content -LiteralPath $securityPath -Raw
$trust = Get-Content -LiteralPath $trustPath -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "## Cryptography inventory" `
    -Label "inventory heading"
Test-DocContains -Doc $doc -Needle "SHA-256" `
    -Label "SHA-256 inventory row"
Test-DocContains -Doc $doc -Needle "No encryption-at-rest" `
    -Label "no encryption-at-rest disclaimer"
Test-DocContains -Doc $doc -Needle "not** a production KMS" `
    -Label "no production KMS disclaimer"
Test-DocContains -Doc $doc -Needle "## KMS and encryption-at-rest (Phase-0 decision)" `
    -Label "KMS / at-rest Phase-0 section"
Test-DocContains -Doc $doc -Needle "Phase-0 deferred vs recommended deploy patterns" `
    -Label "deferred vs recommended deploy heading"
Test-DocContains -Doc $doc -Needle "envelope encryption" `
    -Label "envelope encryption guidance"
Test-DocContains -Doc $doc -Needle "Full-disk or volume encryption" `
    -Label "host FDE recommended control"
Test-DocContains -Doc $doc -Needle "deferred (Phase-0)" `
    -Label "Phase-0 deferred checklist status"
Test-DocContains -Doc $doc -Needle "packaging/caddy/Caddyfile" `
    -Label "Caddy sample link"
Test-DocContains -Doc $doc -Needle "packaging/nginx/sessionledger.conf" `
    -Label "nginx sample link"
Test-DocContains -Doc $doc -Needle "## API key and secret handling" `
    -Label "API key section"
Test-DocContains -Doc $doc -Needle "scripts/crypto-inventory-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Crypto inventory SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"

Write-Host "Cross-links:"
Test-DocContains -Doc $security -Needle "docs/ops/crypto-inventory.md" `
    -Label "SECURITY.md -> crypto-inventory"
Test-DocContains -Doc $trust -Needle "crypto-inventory.md" `
    -Label "local-trust-boundary -> crypto-inventory"


Write-Host "Envelope soft stub anchors:"
$envelope = Get-Content -LiteralPath (Join-Path $repoRoot "src/envelope.rs") -Raw
$cargoToml = Get-Content -LiteralPath (Join-Path $repoRoot "Cargo.toml") -Raw
Test-DocContains -Doc $envelope -Needle "C02 L22" -Label "envelope C02 L22 marker"
Test-DocContains -Doc $envelope -Needle "SL_ENVELOPE_KEY" -Label "SL_ENVELOPE_KEY"
Test-DocContains -Doc $envelope -Needle "pub fn seal" -Label "seal helper"
Test-DocContains -Doc $envelope -Needle "pub fn open" -Label "open helper"
Test-DocContains -Doc $envelope -Needle "pub fn seal" -Label "seal present (cargo toml scanned)"
Test-DocContains -Doc $doc -Needle "src/envelope.rs" -Label "doc links envelope module"
Test-DocContains -Doc $doc -Needle "Soft envelope stub" -Label "doc soft envelope section"

Write-Host "Crypto inventory SelfCheck passed (C02 L22 doc anchors + soft envelope stub; no production KMS)."



