<#
.SYNOPSIS
  Machine-check the Homebrew + winget publish readiness checklist (C11).

.DESCRIPTION
  Verifies that docs/ops/brew-winget-publish.md documents in-repo template +
  checksum-fill readiness, that packaging/homebrew and packaging/winget
  formula/manifest anchors exist, and that live tap / winget-pkgs publish
  remains explicitly unpaid. Does not run brew, winget, or network calls, and
  does not claim a live publish.

  -SelfCheck: docs + formula/manifest + fill-script anchors only
  (no cargo / no network / no package managers).

.PARAMETER SelfCheck
  Explicit docs/template smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/brew-winget-publish-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checklistPath = Join-Path $repoRoot "docs/ops/brew-winget-publish.md"
$channelsPath = Join-Path $repoRoot "packaging/channels.md"
$distributionPath = Join-Path $repoRoot "docs/ops/distribution.md"
$fillScriptPath = Join-Path $repoRoot "scripts/fill-packaging-checksums.ps1"
$selfPath = Join-Path $repoRoot "scripts/brew-winget-publish-check.ps1"
$formulaPath = Join-Path $repoRoot "packaging/homebrew/sessionledger.rb"
$wingetInstallerPath = Join-Path $repoRoot "packaging/winget/KooshaPari.SessionLedger.installer.yaml"
$wingetVersionPath = Join-Path $repoRoot "packaging/winget/KooshaPari.SessionLedger.yaml"
$wingetLocalePath = Join-Path $repoRoot "packaging/winget/KooshaPari.SessionLedger.locale.en-US.yaml"

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
        throw "Missing required anchor: '$Needle' ($Label)"
    }
}

Write-Host "Homebrew + winget publish readiness check (C11)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (checklist + formula/manifest anchors; no brew / no winget / no network)"
}

Assert-File -Path $checklistPath -Label "brew/winget publish checklist"
Assert-File -Path $channelsPath -Label "packaging channels"
Assert-File -Path $distributionPath -Label "distribution guide"
Assert-File -Path $fillScriptPath -Label "fill-packaging-checksums script"
Assert-File -Path $selfPath -Label "brew-winget publish check script"
Assert-File -Path $formulaPath -Label "Homebrew formula template"
Assert-File -Path $wingetInstallerPath -Label "winget installer manifest"
Assert-File -Path $wingetVersionPath -Label "winget version manifest"
Assert-File -Path $wingetLocalePath -Label "winget locale manifest"

$checklist = Get-Content -LiteralPath $checklistPath -Raw
$channels = Get-Content -LiteralPath $channelsPath -Raw
$distribution = Get-Content -LiteralPath $distributionPath -Raw
$fillScript = Get-Content -LiteralPath $fillScriptPath -Raw
$formula = Get-Content -LiteralPath $formulaPath -Raw
$wingetInstaller = Get-Content -LiteralPath $wingetInstallerPath -Raw
$wingetVersion = Get-Content -LiteralPath $wingetVersionPath -Raw
$wingetLocale = Get-Content -LiteralPath $wingetLocalePath -Raw

Write-Host "Publish readiness checklist anchors:"
Test-DocContains -Doc $checklist -Needle "Publish readiness checklist" `
    -Label "checklist heading"
Test-DocContains -Doc $checklist -Needle "Brew/winget publish readiness SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $checklist -Needle "brew-winget-publish-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $checklist -Needle "Public Homebrew tap" `
    -Label "unpaid live Homebrew tap gate"
Test-DocContains -Doc $checklist -Needle "Merged ``microsoft/winget-pkgs`` PR" `
    -Label "unpaid live winget-pkgs gate"
Test-DocContains -Doc $checklist -Needle "| **unpaid** |" `
    -Label "explicit unpaid status markers"
Test-DocContains -Doc $checklist -Needle "fill-packaging-checksums.ps1" `
    -Label "checksum fill script reference"
Test-DocContains -Doc $checklist -Needle "Does not claim live" `
    -Label "no live publish claim"
Test-DocContains -Doc $checklist -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"

Write-Host "Checksum fill script anchors:"
Test-DocContains -Doc $fillScript -Needle "Does NOT publish a tap" `
    -Label "fill script refuses live tap claim"
Test-DocContains -Doc $fillScript -Needle "packaging\homebrew\sessionledger.rb" `
    -Label "fill script Homebrew path"
Test-DocContains -Doc $fillScript -Needle "InstallerSha256" `
    -Label "fill script winget InstallerSha256"
Test-DocContains -Doc $fillScript -Needle "SHA256SUMS" `
    -Label "fill script SHA256SUMS source"
Test-DocContains -Doc $fillScript -Needle "RequiredArtifacts" `
    -Label "fill script required artifact list"

Write-Host "Homebrew formula anchors:"
Test-DocContains -Doc $formula -Needle "class Sessionledger < Formula" `
    -Label "formula class"
Test-DocContains -Doc $formula -Needle "in-repo template" `
    -Label "formula template status comment"
Test-DocContains -Doc $formula -Needle "sha256" `
    -Label "formula sha256 field"
Test-DocContains -Doc $formula -Needle "aarch64-apple-darwin" `
    -Label "formula macOS arm archive"
Test-DocContains -Doc $formula -Needle "x86_64-apple-darwin" `
    -Label "formula macOS intel archive"
Test-DocContains -Doc $formula -Needle "x86_64-unknown-linux-gnu" `
    -Label "formula Linux archive"
Test-DocContains -Doc $formula -Needle "Fill from SHA256SUMS" `
    -Label "formula checksum fill comment"
if ($formula -notmatch 'sha256\s+"[0-9a-fA-F]{64}"') {
    throw "Homebrew formula missing sha256 hex digest lines."
}
[void](Write-Check -Label "formula sha256 hex digest lines present" -Ok $true)

Write-Host "winget manifest anchors:"
Test-DocContains -Doc $wingetInstaller -Needle "PackageIdentifier: KooshaPari.SessionLedger" `
    -Label "installer PackageIdentifier"
Test-DocContains -Doc $wingetInstaller -Needle "InstallerSha256:" `
    -Label "installer InstallerSha256 field"
Test-DocContains -Doc $wingetInstaller -Needle "InstallerType: zip" `
    -Label "installer zip type"
Test-DocContains -Doc $wingetInstaller -Needle "NestedInstallerType: portable" `
    -Label "installer nested portable"
Test-DocContains -Doc $wingetInstaller -Needle "x86_64-pc-windows-msvc" `
    -Label "installer Windows archive triple"
Test-DocContains -Doc $wingetVersion -Needle "ManifestType: version" `
    -Label "version ManifestType"
Test-DocContains -Doc $wingetLocale -Needle "ManifestType: defaultLocale" `
    -Label "locale ManifestType"
Test-DocContains -Doc $wingetLocale -Needle "PackageName: SessionLedger" `
    -Label "locale PackageName"
if ($wingetInstaller -notmatch '(?m)^\s*InstallerSha256:\s*[0-9a-fA-F]{64}\s*$') {
    throw "winget installer missing InstallerSha256 hex digest."
}
[void](Write-Check -Label "InstallerSha256 hex digest present" -Ok $true)

Write-Host "Channel / distribution 'not live' anchors:"
Test-DocContains -Doc $channels -Needle "Manifests in-repo (not a live tap)" `
    -Label "channels Homebrew not-live status"
Test-DocContains -Doc $channels -Needle "Manifests in-repo (not on winget yet)" `
    -Label "channels winget not-live status"
Test-DocContains -Doc $channels -Needle "brew-winget-publish.md" `
    -Label "channels publish doc link"
Test-DocContains -Doc $distribution -Needle "Manifests in-repo (not live)" `
    -Label "distribution Homebrew/winget not-live status"
Test-DocContains -Doc $distribution -Needle "brew-winget-publish.md" `
    -Label "distribution publish doc link"
Test-DocContains -Doc $distribution -Needle "fill-packaging-checksums.ps1" `
    -Label "distribution fill script link"

$summary = @"
## Brew/winget publish readiness SelfCheck

SelfCheck passed: ``docs/ops/brew-winget-publish.md`` checklist + Homebrew
formula / winget manifest anchors + ``fill-packaging-checksums.ps1``.

Live Homebrew tap and ``microsoft/winget-pkgs`` merge remain **unpaid** — no
live ``brew install`` / ``winget install`` claim was made.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Brew/winget publish readiness SelfCheck passed (templates + checksums; live tap/winget unpaid)."
exit 0
