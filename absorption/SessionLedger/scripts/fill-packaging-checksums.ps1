# Fill Homebrew + winget SHA-256 digests from a Release SHA256SUMS file.
#
# Does NOT publish a tap or open microsoft/winget-pkgs — it only updates the
# in-repo templates under packaging/homebrew and packaging/winget.
#
# Usage:
#   pwsh ./scripts/fill-packaging-checksums.ps1 -Sha256Sums ./SHA256SUMS -Version v0.1.0
#   pwsh ./scripts/fill-packaging-checksums.ps1 -Sha256Sums ./SHA256SUMS -Version v0.1.0 -WhatIf
#   pwsh ./scripts/fill-packaging-checksums.ps1 -DownloadFromRelease -Version v0.1.0
#
# Publish steps after fill: docs/ops/brew-winget-publish.md

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Sha256Sums = "",
    [string]$Version = "v0.1.0",
    [string]$Repo = $(if ($env:SL_REPO) { $env:SL_REPO } else { "KooshaPari/SessionLedger" }),
    [string]$RepoRoot = "",
    [switch]$DownloadFromRelease,
    [switch]$SkipVersionRewrite
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

if (-not $Version.StartsWith("v")) {
    $Version = "v$Version"
}
$VersionBare = $Version.TrimStart("v")

$HomebrewFormula = Join-Path $RepoRoot "packaging\homebrew\sessionledger.rb"
$WingetInstaller = Join-Path $RepoRoot "packaging\winget\KooshaPari.SessionLedger.installer.yaml"
$WingetVersion = Join-Path $RepoRoot "packaging\winget\KooshaPari.SessionLedger.yaml"
$WingetLocale = Join-Path $RepoRoot "packaging\winget\KooshaPari.SessionLedger.locale.en-US.yaml"

$RequiredArtifacts = @(
    "sl-viewer-$Version-aarch64-apple-darwin.tar.gz"
    "sl-viewer-$Version-x86_64-apple-darwin.tar.gz"
    "sl-viewer-$Version-x86_64-unknown-linux-gnu.tar.gz"
    "sl-viewer-$Version-x86_64-pc-windows-msvc.zip"
)

function Get-Sha256Map {
    param([string]$Path)

    $map = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.TrimStart().StartsWith("#")) { continue }
        $parts = $line -split "\s+", 2
        if ($parts.Count -lt 2) { continue }
        $hash = $parts[0].ToLowerInvariant()
        if ($hash -notmatch '^[0-9a-f]{64}$') { continue }
        $name = $parts[1].Trim().TrimStart("*", ".", "/")
        $name = Split-Path -Leaf $name
        $map[$name] = $hash
    }
    return $map
}

function Resolve-SumsPath {
    if (-not [string]::IsNullOrWhiteSpace($Sha256Sums)) {
        if (-not (Test-Path -LiteralPath $Sha256Sums -PathType Leaf)) {
            throw "SHA256SUMS not found: $Sha256Sums"
        }
        return (Resolve-Path -LiteralPath $Sha256Sums).Path
    }

    if (-not $DownloadFromRelease) {
        throw "Provide -Sha256Sums <path> or -DownloadFromRelease."
    }

    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("sl-sha256sums-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $out = Join-Path $tmp "SHA256SUMS"
    $url = "https://github.com/$Repo/releases/download/$Version/SHA256SUMS"
    Write-Host "Downloading $url ..."
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
    return $out
}

function Set-FileText {
    param(
        [string]$Path,
        [string]$Content,
        [string]$Label
    )
    if ($PSCmdlet.ShouldProcess($Path, $Label)) {
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
        Write-Host "Updated $Path"
    } else {
        Write-Host "WhatIf: would update $Path"
    }
}

foreach ($path in @($HomebrewFormula, $WingetInstaller, $WingetVersion, $WingetLocale)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing packaging template: $path"
    }
}

$sumsPath = Resolve-SumsPath
$digestMap = Get-Sha256Map -Path $sumsPath

$missing = @($RequiredArtifacts | Where-Object { -not $digestMap.ContainsKey($_) })
if ($missing.Count -gt 0) {
    $known = ($digestMap.Keys | Sort-Object) -join "`n  "
    throw ("SHA256SUMS is missing digests for:`n  {0}`nKnown entries:`n  {1}" -f ($missing -join "`n  "), $known)
}

Write-Host "Using digests from $sumsPath for $Version"
foreach ($name in $RequiredArtifacts) {
    Write-Host ("  {0}  {1}" -f $digestMap[$name], $name)
}

# --- Homebrew formula -------------------------------------------------------
$rb = Get-Content -LiteralPath $HomebrewFormula -Raw

if (-not $SkipVersionRewrite) {
    # Rewrite any prior tag/version in release URLs and Fill comments.
    $rb = [regex]::Replace(
        $rb,
        'releases/download/v[0-9]+\.[0-9]+\.[0-9]+/',
        "releases/download/$Version/"
    )
    $rb = [regex]::Replace(
        $rb,
        'sl-viewer-v[0-9]+\.[0-9]+\.[0-9]+-',
        "sl-viewer-$Version-"
    )
}

foreach ($artifact in @(
        "sl-viewer-$Version-aarch64-apple-darwin.tar.gz"
        "sl-viewer-$Version-x86_64-apple-darwin.tar.gz"
        "sl-viewer-$Version-x86_64-unknown-linux-gnu.tar.gz"
    )) {
    $hash = $digestMap[$artifact]
    # Replace the sha256 line that follows the URL (or Fill comment) for this archive.
    # Note: re-running with the same digests leaves content unchanged — detect via
    # IsMatch, not string inequality.
    $pattern = '(?ms)(url\s+"[^"]*' + [regex]::Escape($artifact) + '"\s*(?:\#[^\r\n]*\r?\n\s*)?sha256\s+")[0-9a-fA-F]{64}(")'
    $pattern2 = '(?m)(\# Fill from SHA256SUMS for ' + [regex]::Escape($artifact) + '\s*\r?\n\s*sha256\s+")[0-9a-fA-F]{64}(")'
    if ([regex]::IsMatch($rb, $pattern)) {
        $rb = [regex]::Replace($rb, $pattern, '${1}' + $hash + '${2}', 1)
    } elseif ([regex]::IsMatch($rb, $pattern2)) {
        $rb = [regex]::Replace($rb, $pattern2, '${1}' + $hash + '${2}', 1)
    } else {
        throw "Could not locate Homebrew sha256 placeholder for $artifact"
    }
}

Set-FileText -Path $HomebrewFormula -Content $rb -Label "fill Homebrew sha256 digests"

# --- winget installer -------------------------------------------------------
$installer = Get-Content -LiteralPath $WingetInstaller -Raw
$winZip = "sl-viewer-$Version-x86_64-pc-windows-msvc.zip"
$winHash = $digestMap[$winZip]

if (-not $SkipVersionRewrite) {
    $installer = [regex]::Replace($installer, '(?m)^(PackageVersion:\s*)[0-9]+\.[0-9]+\.[0-9]+', '${1}' + $VersionBare)
    $installer = [regex]::Replace(
        $installer,
        'releases/download/v[0-9]+\.[0-9]+\.[0-9]+/',
        "releases/download/$Version/"
    )
    $installer = [regex]::Replace(
        $installer,
        'sl-viewer-v[0-9]+\.[0-9]+\.[0-9]+-',
        "sl-viewer-$Version-"
    )
    $installer = [regex]::Replace(
        $installer,
        '(?m)(# Template: replace InstallerSha256 with the SHA256SUMS digest for\s*\r?\n# )sl-viewer-v[0-9]+\.[0-9]+\.[0-9]+-',
        '${1}' + "sl-viewer-$Version-"
    )
}

if ($installer -notmatch '(?m)^(\s*InstallerSha256:\s*)[0-9a-fA-F]{64}\s*$') {
    throw "Could not locate InstallerSha256 in $WingetInstaller"
}
$installer = [regex]::Replace(
    $installer,
    '(?m)^(\s*InstallerSha256:\s*)[0-9a-fA-F]{64}\s*$',
    '${1}' + $winHash,
    1
)

Set-FileText -Path $WingetInstaller -Content $installer -Label "fill winget InstallerSha256"

if (-not $SkipVersionRewrite) {
    foreach ($metaPath in @($WingetVersion, $WingetLocale)) {
        $text = Get-Content -LiteralPath $metaPath -Raw
        $text = [regex]::Replace($text, '(?m)^(PackageVersion:\s*)[0-9]+\.[0-9]+\.[0-9]+', '${1}' + $VersionBare)
        $text = [regex]::Replace($text, 'releases/tag/v[0-9]+\.[0-9]+\.[0-9]+', "releases/tag/$Version")
        Set-FileText -Path $metaPath -Content $text -Label "bump PackageVersion to $VersionBare"
    }
}

Write-Host ""
Write-Host "Done. Next: follow docs/ops/brew-winget-publish.md (templates stay in-repo until you publish)."
Write-Host "Tip: review git diff under packaging/homebrew and packaging/winget before opening external PRs."
