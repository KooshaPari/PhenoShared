<#
.SYNOPSIS
  Machine-check viewer design-token single-source anchors (C09 L81.8).

.DESCRIPTION
  Verifies assets/tokens.css remains the CSS SSOT, the Rust tokens mirror
  exists, ThemeColors / app.rs consume it (no ad-hoc --sl-accent hex in app),
  and docs/a11y/design-tokens.md documents the contract.
  Hermetic: no cargo, no network, no daemon.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/design-tokens-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tokensCss = Join-Path $repoRoot "assets/tokens.css"
$tokensRs = Join-Path $repoRoot "crates/sl-viewer/src/tokens.rs"
$themeRs = Join-Path $repoRoot "crates/sl-viewer/src/theme.rs"
$appRs = Join-Path $repoRoot "crates/sl-viewer/src/app.rs"
$docPath = Join-Path $repoRoot "docs/a11y/design-tokens.md"
$selfPath = Join-Path $repoRoot "scripts/design-tokens-check.ps1"

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
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "Missing required anchor: '$Needle' ($Label)"
    }
}

function Assert-NotContains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = -not $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "Forbidden ad-hoc token drift: '$Needle' ($Label)"
    }
}

Write-Host "Design-token single-source check (C09 L81.8)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + path anchors; no cargo / no network)"
}

Assert-File -Path $tokensCss -Label "tokens.css"
Assert-File -Path $tokensRs -Label "tokens.rs"
Assert-File -Path $themeRs -Label "theme.rs"
Assert-File -Path $appRs -Label "app.rs"
Assert-File -Path $docPath -Label "design-tokens.md"
Assert-File -Path $selfPath -Label "design-tokens-check.ps1"

$css = Get-Content -LiteralPath $tokensCss -Raw
$rsTokens = Get-Content -LiteralPath $tokensRs -Raw
$rsTheme = Get-Content -LiteralPath $themeRs -Raw
$rsApp = Get-Content -LiteralPath $appRs -Raw
$doc = Get-Content -LiteralPath $docPath -Raw

Assert-Contains -Doc $css -Needle "--lc-cobalt" -Label "tokens.css declares --lc-cobalt"
Assert-Contains -Doc $css -Needle "--lc-cobalt-on-dark" -Label "tokens.css declares --lc-cobalt-on-dark"
Assert-Contains -Doc $css -Needle "--sl-accent" -Label "tokens.css declares --sl-accent"
Assert-Contains -Doc $css -Needle "#2563eb" -Label "tokens.css keeps Lab-Coat cobalt hex"
Assert-Contains -Doc $css -Needle "#93c5fd" -Label "tokens.css keeps on-dark cobalt hex"
Assert-NotContains -Doc $css -Needle "#7c3aed" -Label "tokens.css has no legacy purple accent"

Assert-Contains -Doc $rsTokens -Needle "include_str!(" -Label "tokens.rs embeds tokens.css"
Assert-Contains -Doc $rsTokens -Needle "pub mod lab_coat" -Label "tokens.rs exports lab_coat mirror"
Assert-Contains -Doc $rsTokens -Needle "COBALT_ON_DARK" -Label "tokens.rs defines COBALT_ON_DARK"

Assert-Contains -Doc $rsTheme -Needle "tokens::lab_coat" -Label "theme.rs imports lab_coat SSOT"
Assert-Contains -Doc $rsTheme -Needle "lab_coat::COBALT" -Label "theme.rs uses lab_coat::COBALT"
Assert-NotContains -Doc $rsTheme -Needle 'accent: "#7c3aed"' -Label "theme.rs has no purple accent literal"

Assert-Contains -Doc $rsApp -Needle "TOKENS_CSS" -Label "app.rs embeds TOKENS_CSS"
Assert-NotContains -Doc $rsApp -Needle "--sl-accent: #" -Label "app.rs does not ad-hoc --sl-accent hex"
Assert-NotContains -Doc $rsApp -Needle "--sl-bg: #" -Label "app.rs does not ad-hoc --sl-bg hex"

Assert-Contains -Doc $doc -Needle "assets/tokens.css" -Label "design-tokens.md cites CSS SSOT"
Assert-Contains -Doc $doc -Needle "crates/sl-viewer/src/tokens.rs" -Label "design-tokens.md cites Rust mirror"
Assert-Contains -Doc $doc -Needle "SelfCheck" -Label "design-tokens.md documents SelfCheck"

Write-Host "Design-token SelfCheck passed"
