<#
.SYNOPSIS
  Machine-check the C01 L16 Fluent catalog stub anchors (Phase-1).

.DESCRIPTION
  Verifies locales/en.ftl + locales/es.ftl exist, key parity with locales/en.json,
  src/i18n_fluent.rs helper with optional fluent-catalog feature, docs/ops/i18n.md
  Phase-1 section, and hermetic SelfCheck wiring. No cargo; no network.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/fluent-i18n-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$enJsonPath = Join-Path $repoRoot "locales/en.json"
$esJsonPath = Join-Path $repoRoot "locales/es.json"
$enFtlPath = Join-Path $repoRoot "locales/en.ftl"
$esFtlPath = Join-Path $repoRoot "locales/es.ftl"
$helperPath = Join-Path $repoRoot "src/i18n_fluent.rs"
$cargoPath = Join-Path $repoRoot "Cargo.toml"
$docPath = Join-Path $repoRoot "docs/ops/i18n.md"
$checkScript = Join-Path $repoRoot "scripts/fluent-i18n-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/fluent_i18n.rs"

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

function JsonKeyToFluentId {
    param([Parameter(Mandatory = $true)][string]$Key)
    return ($Key -replace '\.', '-')
}

Write-Host "Fluent i18n catalog check (C01 L16 Phase-1)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (en+es .ftl + JSON parity + helper + docs; no cargo / no network)"
}

Assert-File -Path $enJsonPath -Label "English JSON catalog"
Assert-File -Path $esJsonPath -Label "Spanish JSON catalog"
Assert-File -Path $enFtlPath -Label "English Fluent catalog"
Assert-File -Path $esFtlPath -Label "Spanish Fluent catalog"
Assert-File -Path $helperPath -Label "i18n_fluent Rust helper"
Assert-File -Path $cargoPath -Label "root Cargo.toml"
Assert-File -Path $docPath -Label "i18n ops doc"
Assert-File -Path $checkScript -Label "fluent i18n check script"
Assert-File -Path $rustWrapper -Label "fluent i18n rust SelfCheck wrapper"

$enJson = Get-Content -LiteralPath $enJsonPath -Raw
$esJson = Get-Content -LiteralPath $esJsonPath -Raw
$enFtl = Get-Content -LiteralPath $enFtlPath -Raw
$esFtl = Get-Content -LiteralPath $esFtlPath -Raw
$helper = Get-Content -LiteralPath $helperPath -Raw
$cargo = Get-Content -LiteralPath $cargoPath -Raw
$doc = Get-Content -LiteralPath $docPath -Raw

Write-Host "FTL catalog anchors:"
Assert-Contains -Doc $enFtl -Needle "viewer-app_title" `
    -Label "en.ftl viewer-app_title" -Context "locales/en.ftl"
Assert-Contains -Doc $esFtl -Needle "viewer-app_title" `
    -Label "es.ftl viewer-app_title" -Context "locales/es.ftl"

try {
    $enParsed = $enJson | ConvertFrom-Json
    $esParsed = $esJson | ConvertFrom-Json
    $enKeys = @($enParsed.messages.PSObject.Properties | ForEach-Object { $_.Name })
    $esKeys = @($esParsed.messages.PSObject.Properties | ForEach-Object { $_.Name })

    foreach ($key in $enKeys) {
        $fluentId = JsonKeyToFluentId -Key $key
        Assert-Contains -Doc $enFtl -Needle ($fluentId + " =") `
            -Label "en.ftl maps JSON key $key" -Context "locales/en.ftl"
        Assert-Contains -Doc $esFtl -Needle ($fluentId + " =") `
            -Label "es.ftl maps JSON key $key" -Context "locales/es.ftl"
    }

    $ok = ($enKeys.Count -ge 5) -and ($enKeys.Count -eq $esKeys.Count)
    [void](Write-Check -Label "JSON key parity ($($enKeys.Count) keys)" -Ok $ok)
    if (-not $ok) {
        throw "locales/en.json and locales/es.json must share the same key count."
    }
} catch {
    throw "JSON/FTL parity check failed: $_"
}

Write-Host "Helper anchors:"
Assert-Contains -Doc $helper -Label "pub fn t_fluent" -Needle "pub fn t_fluent(" `
    -Context "src/i18n_fluent.rs"
Assert-Contains -Doc $helper -Label "json_key_to_fluent_id" -Needle "json_key_to_fluent_id" `
    -Context "src/i18n_fluent.rs"
Assert-Contains -Doc $helper -Label "include_str en.ftl" `
    -Needle 'include_str!("../locales/en.ftl")' -Context "src/i18n_fluent.rs"
Assert-Contains -Doc $helper -Label "include_str es.ftl" `
    -Needle 'include_str!("../locales/es.ftl")' -Context "src/i18n_fluent.rs"
Assert-Contains -Doc $helper -Label "C01 L16 Phase-1 marker" -Needle "Phase-1" `
    -Context "src/i18n_fluent.rs"

Write-Host "Cargo feature anchors:"
Assert-Contains -Doc $cargo -Label "fluent-catalog feature" -Needle "fluent-catalog" `
    -Context "Cargo.toml"
Assert-Contains -Doc $cargo -Label "fluent-bundle dep" -Needle "fluent-bundle" `
    -Context "Cargo.toml"
Assert-Contains -Doc $cargo -Label "unic-langid dep" -Needle "unic-langid" `
    -Context "Cargo.toml"

Write-Host "Doc anchors:"
Assert-Contains -Doc $doc -Needle "## Phase-1 (Fluent catalog stub)" `
    -Label "Phase-1 Fluent heading" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "locales/en.ftl" `
    -Label "en.ftl path" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "locales/es.ftl" `
    -Label "es.ftl path" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "fluent-catalog" `
    -Label "fluent-catalog feature" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "src/i18n_fluent.rs" `
    -Label "i18n_fluent helper path" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "scripts/fluent-i18n-check.ps1" `
    -Label "Fluent SelfCheck script reference" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "fluent i18n SelfCheck | **done**" `
    -Label "Fluent SelfCheck gate marked done" -Context "docs/ops/i18n.md"

Write-Host "fluent i18n SelfCheck passed (C01 L16 Phase-1 .ftl stub + JSON parity; optional fluent-catalog feature)."
