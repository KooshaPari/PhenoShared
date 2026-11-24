# SessionLedger installer (Windows)
#
# Downloads a checksum-verified sl-viewer ZIP from GitHub Releases and installs
# it under %LOCALAPPDATA%\Programs\SessionLedger by default.
#
# Usage (recommended):
#   irm https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.ps1 | iex
#
# Pin a release / override destination via environment variables before piping:
#   $env:SL_VERSION = 'v0.1.0'
#   $env:SL_INSTALL_DIR = "$env:LOCALAPPDATA\Programs\SessionLedger"
#   irm ... | iex
#
# Direct invocation:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Version v0.1.0

[CmdletBinding()]
param(
    [string]$Repo = $(if ($env:SL_REPO) { $env:SL_REPO } else { "KooshaPari/SessionLedger" }),
    [string]$Version = $(if ($env:SL_VERSION) { $env:SL_VERSION } else { "" }),
    [string]$InstallDir = $(if ($env:SL_INSTALL_DIR) {
            $env:SL_INSTALL_DIR
        } else {
            Join-Path $env:LOCALAPPDATA "Programs\SessionLedger"
        }),
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"

if ($env:SL_SKIP_VERIFY -eq "1") {
    $SkipVerify = $true
}

$Target = "x86_64-pc-windows-msvc"

function Get-LatestReleaseTag {
    param([string]$Repository)

    $headers = @{
        Accept                 = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent"           = "SessionLedger-install.ps1"
    }
    try {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/releases/latest" -Headers $headers
        if ($release.tag_name) {
            return [string]$release.tag_name
        }
    } catch {
        # Fall through to redirect probe.
    }

    $resp = Invoke-WebRequest -Uri "https://github.com/$Repository/releases/latest" -MaximumRedirection 0 -ErrorAction SilentlyContinue
    if ($resp.Headers.Location) {
        return ([string]$resp.Headers.Location).TrimEnd("/").Split("/")[-1]
    }
    # Some hosts follow redirects; parse the final URI.
    $followed = Invoke-WebRequest -Uri "https://github.com/$Repository/releases/latest" -MaximumRedirection 5
    return ([string]$followed.BaseResponse.ResponseUri.AbsoluteUri).TrimEnd("/").Split("/")[-1]
}

function Get-Sha256Hex {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    Write-Host "Resolving latest GitHub Release for $Repo ..."
    $Version = Get-LatestReleaseTag -Repository $Repo
}

if ([string]::IsNullOrWhiteSpace($Version) -or $Version -eq "latest") {
    throw "Could not resolve a release tag for $Repo. Publish a v* Release or set -Version / `$env:SL_VERSION."
}

if (-not $Version.StartsWith("v")) {
    $Version = "v$Version"
}

# Release archives historically used the tag verbatim (sl-viewer-v0.1.1-...)
# and later dropped the leading `v` (sl-viewer-0.1.1-...). Probe both spellings
# so the installer works against every published release.
$assetVersion = $Version.TrimStart("v")
$archive = $null
foreach ($candidate in @("sl-viewer-$Version-$Target.zip", "sl-viewer-$assetVersion-$Target.zip")) {
    try {
        Invoke-WebRequest -Uri "$baseUrl/$candidate" -Method Head -UseBasicParsing -ErrorAction Stop | Out-Null
        $archive = $candidate
        break
    } catch {
        # Not this spelling; try the next one.
    }
}
if (-not $archive) {
    throw "No sl-viewer archive found for $Version ($Target). Tried: sl-viewer-$Version-$Target.zip, sl-viewer-$assetVersion-$Target.zip"
}
$baseUrl = "https://github.com/$Repo/releases/download/$Version"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sessionledger-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null

try {
    $archivePath = Join-Path $tmpRoot $archive
    $sumsPath = Join-Path $tmpRoot "SHA256SUMS"

    Write-Host "Installing SessionLedger sl-viewer $Version ($Target)"
    Write-Host "  archive: $archive"
    Write-Host "  dest:    $InstallDir"

    Invoke-WebRequest -Uri "$baseUrl/$archive" -OutFile $archivePath -UseBasicParsing
    Invoke-WebRequest -Uri "$baseUrl/SHA256SUMS" -OutFile $sumsPath -UseBasicParsing

    if (-not $SkipVerify) {
        $expected = $null
        foreach ($line in Get-Content -LiteralPath $sumsPath) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $parts = $line -split "\s+"
            if ($parts.Count -lt 2) { continue }
            $hash = $parts[0].ToLowerInvariant()
            $name = $parts[1].TrimStart("*", ".", "/")
            if ($name -eq $archive) {
                $expected = $hash
                break
            }
        }
        if (-not $expected) {
            throw "No checksum found for $archive in SHA256SUMS."
        }
        $actual = Get-Sha256Hex -Path $archivePath
        if ($actual -ne $expected) {
            throw "Checksum mismatch for $archive.`n  expected: $expected`n  actual:   $actual"
        }
        Write-Host "Checksum OK ($actual)"
    } else {
        Write-Warning "SkipVerify set — skipping SHA-256 verification."
    }

    $extractDir = Join-Path $tmpRoot "extracted"
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir -Force

    $binary = Get-ChildItem -Path $extractDir -Recurse -Filter "sl-viewer.exe" -File |
        Select-Object -First 1
    if (-not $binary) {
        throw "sl-viewer.exe not found inside $archive."
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -LiteralPath $binary.FullName -Destination (Join-Path $InstallDir "sl-viewer.exe") -Force

    # Best-effort Start Menu shortcut (matches packaging/windows/Install.ps1 UX).
    try {
        $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
        $shortcutPath = Join-Path $startMenuDir "SessionLedger.lnk"
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = Join-Path $InstallDir "sl-viewer.exe"
        $shortcut.WorkingDirectory = $InstallDir
        $shortcut.Description = "SessionLedger Viewer"
        $shortcut.Save()
        Write-Host "Start Menu shortcut: $shortcutPath"
    } catch {
        Write-Warning "Could not create Start Menu shortcut: $($_.Exception.Message)"
    }

    $installed = Join-Path $InstallDir "sl-viewer.exe"
    Write-Host "Installed sl-viewer $Version to $installed"
    try {
        & $installed --version
    } catch {
        # Binary may still work when launched interactively (SmartScreen, etc.).
    }

    Write-Host ""
    Write-Host "Add the install directory to PATH if you want 'sl-viewer' on the command line:"
    Write-Host "  $InstallDir"
    Write-Host ""
    Write-Host "Daemon (optional, from source):"
    Write-Host "  cargo install --git https://github.com/$Repo --locked --path crates/sl-daemon"
    Write-Host "Releases: https://github.com/$Repo/releases"
} finally {
    Remove-Item -Recurse -Force -LiteralPath $tmpRoot -ErrorAction SilentlyContinue
}
