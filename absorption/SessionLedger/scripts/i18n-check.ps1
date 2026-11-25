<#
.SYNOPSIS
  Machine-check the C01 L16 i18n scaffold anchors.

.DESCRIPTION
  Verifies locales/en.json + locales/es.json (multi-locale soft catalogs),
  src/i18n.rs lookup helper with SL_LOCALE, docs/ops/i18n.md Phase-0 decision
  + Fluent/ICU future hooks, and hermetic SelfCheck wiring. No Fluent runtime;
  no network; no cargo.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/i18n-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$enPath = Join-Path $repoRoot "locales/en.json"
$esPath = Join-Path $repoRoot "locales/es.json"
$helperPath = Join-Path $repoRoot "src/i18n.rs"
$docPath = Join-Path $repoRoot "docs/ops/i18n.md"
$checkScript = Join-Path $repoRoot "scripts/i18n-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/i18n.rs"

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

function Assert-Matches {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "document"
    )
    $ok = $Doc -match $Pattern
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required pattern: '$Pattern'"
    }
}

Write-Host "i18n scaffold check (C01 L16)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (en+es catalogs + helper + docs; no cargo / no network / no Fluent runtime)"
}

Assert-File -Path $enPath -Label "English locale catalog"
Assert-File -Path $esPath -Label "Spanish soft locale catalog"
Assert-File -Path $helperPath -Label "i18n Rust helper"
Assert-File -Path $docPath -Label "i18n ops doc"
Assert-File -Path $checkScript -Label "i18n check script"
Assert-File -Path $rustWrapper -Label "i18n rust SelfCheck wrapper"

$enCatalog = Get-Content -LiteralPath $enPath -Raw
$esCatalog = Get-Content -LiteralPath $esPath -Raw
$helper = Get-Content -LiteralPath $helperPath -Raw
$doc = Get-Content -LiteralPath $docPath -Raw

Write-Host "Catalog anchors:"
Assert-Contains -Doc $enCatalog -Needle '"locale": "en"' `
    -Label "catalog locale en" -Context "locales/en.json"
Assert-Contains -Doc $esCatalog -Needle '"locale": "es"' `
    -Label "catalog locale es" -Context "locales/es.json"
Assert-Contains -Doc $enCatalog -Needle '"messages"' `
    -Label "en messages object" -Context "locales/en.json"
Assert-Contains -Doc $esCatalog -Needle '"messages"' `
    -Label "es messages object" -Context "locales/es.json"

$requiredKeys = @(
    "cli.app_about",
    "viewer.app_title",
    "viewer.empty_state",
    "viewer.tab_sessions",
    "viewer.search_placeholder"
)
foreach ($key in $requiredKeys) {
    Assert-Contains -Doc $enCatalog -Needle ('"' + $key + '"') `
        -Label "en key $key" -Context "locales/en.json"
    Assert-Contains -Doc $esCatalog -Needle ('"' + $key + '"') `
        -Label "es key $key" -Context "locales/es.json"
}

try {
    $enParsed = $enCatalog | ConvertFrom-Json
    $esParsed = $esCatalog | ConvertFrom-Json
    $enCount = @($enParsed.messages.PSObject.Properties).Count
    $esCount = @($esParsed.messages.PSObject.Properties).Count
    $ok = ($enCount -ge 5) -and ($enCount -eq $esCount)
    [void](Write-Check -Label "en/es parse with matching key counts ($enCount)" -Ok $ok)
    if (-not $ok) {
        throw "locales/en.json and locales/es.json must parse with matching >=5 keys (en=$enCount es=$esCount)."
    }
} catch {
    throw "locale catalogs failed JSON parse / parity check: $_"
}

Write-Host "Helper anchors:"
Assert-Contains -Doc $helper -Label "DEFAULT_LOCALE" -Needle "DEFAULT_LOCALE" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "SOFT_LOCALE_ES" -Needle "SOFT_LOCALE_ES" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "include_str locales/en.json" `
    -Needle 'include_str!("../locales/en.json")' -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "include_str locales/es.json" `
    -Needle 'include_str!("../locales/es.json")' -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "pub fn t" -Needle "pub fn t(" `
    -Context "src/i18n.rs"
Assert-Matches -Doc $helper -Label "pub fn t_locale" -Pattern "pub\s+fn\s+t_locale\s*(?:<[^>]+>)?\s*\(" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "pub fn try_catalog" -Needle "pub fn try_catalog(" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "active_locale" -Needle "pub fn active_locale(" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "SL_LOCALE" -Needle "SL_LOCALE" `
    -Context "src/i18n.rs"
Assert-Contains -Doc $helper -Label "C01 L16 marker" -Needle "C01 L16" `
    -Context "src/i18n.rs"

Write-Host "Doc anchors:"
Assert-Contains -Doc $doc -Needle "## Phase-0 decision" `
    -Label "Phase-0 decision heading" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "locales/es.json" `
    -Label "Spanish catalog path" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "SL_LOCALE" `
    -Label "SL_LOCALE selection" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "src/i18n.rs" `
    -Label "helper path reference" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "## Future hooks (Fluent / ICU)" `
    -Label "Fluent/ICU future hooks heading" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "Fluent" `
    -Label "Fluent future mention" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "try_catalog" `
    -Label "try_catalog hook" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "scripts/i18n-check.ps1" `
    -Label "SelfCheck script reference" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation" -Context "docs/ops/i18n.md"
Assert-Contains -Doc $doc -Needle "i18n SelfCheck | **done**" `
    -Label "SelfCheck gate marked done" -Context "docs/ops/i18n.md"

Write-Host "i18n SelfCheck passed (C01 L16 en+es soft catalogs + SL_LOCALE helper; no Fluent runtime)."
