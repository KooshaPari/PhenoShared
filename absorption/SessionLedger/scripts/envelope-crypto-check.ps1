<#
.SYNOPSIS
  Machine-check the C02 L22 hard envelope-crypto CI evidence anchors.

.DESCRIPTION
  Verifies docs/ops/crypto-inventory.md documents the soft envelope helper,
  explicit non-KMS / non-sealed-secret scope, done vs unpaid envelope gates,
  that .github/workflows/envelope-crypto.yml exists as a blocking PR SelfCheck
  workflow, and that security.yml retains cross-reference anchors. Hermetic: no
  container build, no network, no cargo.

  Does not claim in-tree KMS, sealed-secret clients, KEK wrap, AES-GCM
  revision, or automatic OKF/audit at-rest encryption (those remain unpaid).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/envelope-crypto-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/crypto-inventory.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/envelope-crypto.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$envelopePath = Join-Path $repoRoot "src/envelope.rs"
$cargoToml = Join-Path $repoRoot "Cargo.toml"
$testPath = Join-Path $repoRoot "tests/envelope_crypto.rs"
$cryptoInventoryCheck = Join-Path $repoRoot "scripts/crypto-inventory-check.ps1"
$selfPath = Join-Path $repoRoot "scripts/envelope-crypto-check.ps1"

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
        [string]$Context = "docs/ops/crypto-inventory.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Hard envelope-crypto CI evidence check (C02 L22)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + security anchors; no build / no network / no KMS)"
}

Assert-File -Path $docPath -Label "crypto inventory doc"
Assert-File -Path $workflowPath -Label "envelope-crypto workflow"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $envelopePath -Label "envelope soft helper"
Assert-File -Path $cargoToml -Label "Cargo.toml"
Assert-File -Path $testPath -Label "envelope_crypto test wrapper"
Assert-File -Path $cryptoInventoryCheck -Label "crypto inventory check script"
Assert-File -Path $selfPath -Label "envelope-crypto check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw
$envelope = Get-Content -LiteralPath $envelopePath -Raw
$cargo = Get-Content -LiteralPath $cargoToml -Raw
$testRs = Get-Content -LiteralPath $testPath -Raw

Write-Host "Hard envelope-crypto doc anchors:"
Test-DocContains -Doc $doc -Needle "## Hard envelope-crypto CI evidence (C02 L22)" `
    -Label "hard envelope-crypto section heading"
Test-DocContains -Doc $doc -Needle "scripts/envelope-crypto-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Envelope-crypto SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Blocking envelope-crypto CI workflow | **done**" `
    -Label "blocking workflow gate marked done"
Test-DocContains -Doc $doc -Needle ".github/workflows/envelope-crypto.yml" `
    -Label "envelope-crypto workflow path documented"
Test-DocContains -Doc $doc -Needle "tests/envelope_crypto.rs" `
    -Label "cargo test wrapper documented"
Test-DocContains -Doc $doc -Needle "In-tree KMS / sealed-secret client | **unpaid**" `
    -Label "KMS/sealed-secret remains unpaid"
Test-DocContains -Doc $doc -Needle "KEK wrap / cloud KMS for envelope DEK | **unpaid**" `
    -Label "KEK/KMS wrap remains unpaid"
Test-DocContains -Doc $doc -Needle "does **not** claim in-tree KMS" `
    -Label "no false KMS claim"
Test-DocContains -Doc $doc -Needle "envelope-crypto" `
    -Label "envelope-crypto feature reference"

Write-Host "Envelope helper anchors:"
Test-DocContains -Doc $envelope -Needle "C02 L22" `
    -Label "envelope C02 L22 marker" -Context "src/envelope.rs"
Test-DocContains -Doc $envelope -Needle "SL_ENVELOPE_KEY" `
    -Label "SL_ENVELOPE_KEY env var" -Context "src/envelope.rs"
Test-DocContains -Doc $envelope -Needle "pub fn seal" `
    -Label "seal helper" -Context "src/envelope.rs"
Test-DocContains -Doc $envelope -Needle "pub fn open" `
    -Label "open helper" -Context "src/envelope.rs"
Test-DocContains -Doc $envelope -Needle "not** a KMS" `
    -Label "no KMS disclaimer in module" -Context "src/envelope.rs"

if ($cargo -notmatch 'envelope-crypto\s*=') {
    throw "Cargo.toml must declare the envelope-crypto feature."
}
[void](Write-Check -Label "Cargo.toml declares envelope-crypto feature" -Ok $true)

Write-Host "envelope-crypto workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "envelope-crypto.yml must not set continue-on-error (blocking SelfCheck CI)."
}
[void](Write-Check -Label "workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'pull_request:') {
    throw "envelope-crypto.yml must run on pull_request."
}
[void](Write-Check -Label "workflow triggers on pull_request" -Ok $true)

if ($workflow -notmatch 'envelope-crypto-check\.ps1') {
    throw "envelope-crypto.yml must run scripts/envelope-crypto-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "workflow runs envelope-crypto-check.ps1" -Ok $true)

Write-Host "security.yml cross-reference anchors:"
Test-DocContains -Doc $securityWf -Needle "envelope-crypto.yml" `
    -Label "security.yml references envelope-crypto workflow" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "envelope-crypto-check.ps1" `
    -Label "security.yml references envelope-crypto SelfCheck script" -Context ".github/workflows/security.yml"

Write-Host "cargo test wrapper anchors:"
if ($testRs -notmatch 'envelope-crypto-check\.ps1') {
    throw "tests/envelope_crypto.rs must invoke scripts/envelope-crypto-check.ps1."
}
[void](Write-Check -Label "envelope_crypto.rs invokes SelfCheck script" -Ok $true)

if ($testRs -notmatch 'Envelope-crypto SelfCheck passed') {
    throw "tests/envelope_crypto.rs must assert Envelope-crypto SelfCheck passed success line."
}
[void](Write-Check -Label "envelope_crypto.rs asserts success line" -Ok $true)

$summary = @"
## Hard envelope-crypto CI SelfCheck (C02 L22)

SelfCheck passed: ``docs/ops/crypto-inventory.md`` envelope hard-evidence rows,
blocking ``envelope-crypto.yml`` workflow, and ``security.yml`` anchors.
In-tree KMS, sealed secrets, KEK wrap, and OKF/audit at-rest encryption remain unpaid.
Does not claim production envelope encryption or cloud KMS integration.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Envelope-crypto SelfCheck passed (C02 L22 hard CI evidence; KMS/sealed-secrets/KEK wrap unpaid)."
exit 0
