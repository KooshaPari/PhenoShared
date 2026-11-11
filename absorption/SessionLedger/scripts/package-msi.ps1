[CmdletBinding()]
param(
    [string]$Target = "x86_64-pc-windows-msvc",
    [string]$Version,
    [string]$SourceDir,
    [string]$DistDir,
    [string]$BinaryPath,
    [string]$WxsPath,
    [string]$OutputPath,
    [switch]$SkipBuild,
    [switch]$SkipLayout
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Get-DotNetToolsPath {
    if ($env:DOTNET_TOOLS_PATH -and (Test-Path -LiteralPath $env:DOTNET_TOOLS_PATH)) {
        return $env:DOTNET_TOOLS_PATH
    }
    $candidate = Join-Path $env:USERPROFILE ".dotnet\tools"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    return $null
}

function Resolve-WixCommand {
    $cmd = Get-Command wix -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $tools = Get-DotNetToolsPath
    if ($tools) {
        $wixCmd = Join-Path $tools "wix.exe"
        if (Test-Path -LiteralPath $wixCmd -PathType Leaf) {
            return $wixCmd
        }
    }
    throw "WiX v4 CLI ('wix') not found. Install with: dotnet tool install --global wix"
}

$metadata = $null
if (-not $Version) {
    $metadata = cargo metadata --manifest-path (Join-Path $ProjectRoot "Cargo.toml") --no-deps --format-version 1 |
        ConvertFrom-Json
    $viewer = $metadata.packages | Where-Object { $_.name -eq "sl-viewer" } | Select-Object -First 1
    if (-not $viewer) {
        throw "Could not determine the sl-viewer version from cargo metadata."
    }
    $Version = $viewer.version
}

$Version = $Version.TrimStart("v")
if ($Version -notmatch '^\d+\.\d+\.\d+') {
    throw "Version '$Version' is not a WiX-compatible Major.Minor.Patch value."
}

if (-not $DistDir) {
    $DistDir = Join-Path $ProjectRoot "packaging\dist"
}
if (-not $WxsPath) {
    $WxsPath = Join-Path $ProjectRoot "packaging\windows\Product.wxs"
}
if (-not (Test-Path -LiteralPath $WxsPath -PathType Leaf)) {
    throw "WiX source not found at '$WxsPath'."
}

if (-not $SkipLayout) {
    if (-not $SourceDir) {
        $layoutScript = Join-Path $PSScriptRoot "package-windows.ps1"
        $layoutArgs = @{
            Target  = $Target
            Version = $Version
            DistDir = $DistDir
        }
        if ($SkipBuild) {
            $layoutArgs["SkipBuild"] = $true
        }
        if ($BinaryPath) {
            $layoutArgs["BinaryPath"] = $BinaryPath
        }
        & $layoutScript @layoutArgs
        if ($LASTEXITCODE -ne 0) {
            throw "package-windows.ps1 failed with exit code $LASTEXITCODE."
        }
        $tagVersion = "v$Version"
        $SourceDir = Join-Path $DistDir "sl-viewer-$tagVersion-$Target"
    }
}

if (-not $SourceDir) {
    throw "SourceDir is required when -SkipLayout is set."
}
if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "MSI source layout not found at '$SourceDir'."
}

$viewerExe = Join-Path $SourceDir "sl-viewer.exe"
if (-not (Test-Path -LiteralPath $viewerExe -PathType Leaf)) {
    throw "Expected sl-viewer.exe in MSI source layout at '$viewerExe'."
}
foreach ($license in @("LICENSE-MIT", "LICENSE-APACHE")) {
    $licensePath = Join-Path $SourceDir $license
    if (-not (Test-Path -LiteralPath $licensePath -PathType Leaf)) {
        throw "Expected $license in MSI source layout at '$licensePath'."
    }
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
if (-not $OutputPath) {
    $OutputPath = Join-Path $DistDir "SessionLedger-$Version-x64.msi"
}
Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $OutputPath

$wix = Resolve-WixCommand
$sourceDirResolved = (Resolve-Path -LiteralPath $SourceDir).Path
$wxsResolved = (Resolve-Path -LiteralPath $WxsPath).Path

Write-Host "Building unsigned MSI with WiX: $wix"
Write-Host "  Version=$Version"
Write-Host "  SourceDir=$sourceDirResolved"
Write-Host "  Output=$OutputPath"

& $wix build $wxsResolved `
    -d "Version=$Version" `
    -d "SourceDir=$sourceDirResolved" `
    -o $OutputPath
if ($LASTEXITCODE -ne 0) {
    throw "wix build failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
    throw "WiX reported success but MSI was not written to '$OutputPath'."
}

Write-Output "Windows MSI (unsigned): $OutputPath"
