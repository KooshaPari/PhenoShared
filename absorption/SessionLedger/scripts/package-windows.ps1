[CmdletBinding()]
param(
    [string]$Target = "x86_64-pc-windows-msvc",
    [string]$Version,
    [string]$DistDir,
    [string]$BinaryPath,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$metadata = $null
if (-not $Version -or -not $BinaryPath) {
    $metadata = cargo metadata --manifest-path (Join-Path $ProjectRoot "Cargo.toml") --no-deps --format-version 1 |
        ConvertFrom-Json
}

if (-not $Version) {
    $viewer = $metadata.packages | Where-Object { $_.name -eq "sl-viewer" } | Select-Object -First 1
    if (-not $viewer) {
        throw "Could not determine the sl-viewer version from cargo metadata."
    }
    $Version = $viewer.version
}

if (-not $DistDir) {
    $DistDir = Join-Path $ProjectRoot "packaging\dist"
}

if (-not $SkipBuild) {
    $originalSourceDateEpoch = $env:SOURCE_DATE_EPOCH
    $originalCargoIncremental = $env:CARGO_INCREMENTAL
    try {
        if ($env:SOURCE_DATE_EPOCH -notmatch '^\d+$') {
            $epoch = (& git -C $ProjectRoot log -1 --format=%ct).Trim()
            if ($LASTEXITCODE -ne 0 -or $epoch -notmatch '^\d+$') {
                throw "Could not derive SOURCE_DATE_EPOCH for release packaging."
            }
            $env:SOURCE_DATE_EPOCH = $epoch
        }
        $env:CARGO_INCREMENTAL = "0"
        Write-Host "Building with SOURCE_DATE_EPOCH=$($env:SOURCE_DATE_EPOCH)"
        & cargo build --manifest-path (Join-Path $ProjectRoot "Cargo.toml") `
            -p sl-viewer --release --locked --target $Target
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        $env:SOURCE_DATE_EPOCH = $originalSourceDateEpoch
        $env:CARGO_INCREMENTAL = $originalCargoIncremental
    }
}

if (-not $BinaryPath) {
    $BinaryPath = Join-Path $metadata.target_directory "$Target\release\sl-viewer.exe"
}
if (-not (Test-Path -LiteralPath $BinaryPath -PathType Leaf)) {
    throw "Viewer binary not found at '$BinaryPath'. Build it first or pass -BinaryPath."
}

$tagVersion = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
$packageName = "sl-viewer-$tagVersion-$Target"
$layoutDir = Join-Path $DistDir $packageName
$archivePath = Join-Path $DistDir "$packageName.zip"
$windowsScaffold = Join-Path $ProjectRoot "packaging\windows"

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue -LiteralPath $layoutDir
Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $archivePath
New-Item -ItemType Directory -Path $layoutDir | Out-Null

Copy-Item -LiteralPath $BinaryPath -Destination (Join-Path $layoutDir "sl-viewer.exe")
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE-MIT") -Destination $layoutDir
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE-APACHE") -Destination $layoutDir
Copy-Item -LiteralPath (Join-Path $windowsScaffold "Install.ps1") -Destination $layoutDir
Copy-Item -LiteralPath (Join-Path $windowsScaffold "Uninstall.ps1") -Destination $layoutDir

@"
SessionLedger viewer $tagVersion

Portable use:
  Run sl-viewer.exe from this directory.

Per-user install:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1

The installer script copies the application to LocalAppData, creates a Start
Menu shortcut, and registers an uninstall entry. Use Uninstall.ps1 or Windows
Installed Apps to remove it.

This is an unsigned installer scaffold, not an MSI and not intended for public
distribution. Windows SmartScreen may warn before first launch. Authenticode
remains deferred; verify the release checksum/cosign provenance as documented
in docs/ops/distribution.md in the source repository.
"@ | Set-Content -LiteralPath (Join-Path $layoutDir "README.txt") -Encoding utf8

Compress-Archive -LiteralPath $layoutDir -DestinationPath $archivePath -CompressionLevel Optimal
Write-Output "Windows package: $archivePath"
