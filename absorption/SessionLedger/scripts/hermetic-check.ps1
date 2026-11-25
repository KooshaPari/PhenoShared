[CmdletBinding()]
param(
    [switch]$IncludeRootPackage
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$daemonDir = Join-Path $repoRoot "crates/sl-daemon"
$builderPinPath = Join-Path $repoRoot "docs/ops/hermetic-builder.json"

function Assert-BuilderPin {
    if (-not (Test-Path -LiteralPath $builderPinPath -PathType Leaf)) {
        throw "Hermetic builder pin not found at '$builderPinPath'."
    }

    $pin = Get-Content -LiteralPath $builderPinPath -Raw | ConvertFrom-Json
    $rustcVersion = (& rustc --version) -replace '^rustc ', ''
    $rustcSemver = ($rustcVersion -split '\s+', 2)[0]
    $msrv = [version]$pin.msrv

    if ([version]$rustcSemver -lt $msrv) {
        throw "rustc $rustcSemver is below pinned MSRV $($pin.msrv) from hermetic-builder.json."
    }

    Write-Host "Hermetic builder pin: MSRV=$($pin.msrv) image=$($pin.builder_image)@$($pin.builder_image_digest)"
}

Assert-BuilderPin

function Invoke-CargoStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,

        [switch]$Offline
    )

    Write-Host "==> $Description"
    Push-Location -LiteralPath $WorkingDirectory
    try {
        & cargo @Arguments
        if ($LASTEXITCODE -ne 0) {
            $hint = if ($Offline) {
                "Offline build failed. This usually means Cargo needed the network after fetch; check Cargo.lock, path dependencies, and feature changes."
            }
            else {
                "Cargo step failed before the offline build could be attempted."
            }
            throw "$Description exited with code $LASTEXITCODE. $hint"
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $daemonDir "Cargo.toml") -PathType Leaf)) {
    throw "Expected sl-daemon manifest at '$daemonDir/Cargo.toml'."
}

Invoke-CargoStep `
    -Description "Fetch locked sl-daemon dependencies" `
    -Arguments @("fetch", "--locked") `
    -WorkingDirectory $daemonDir

Invoke-CargoStep `
    -Description "Build sl-daemon with locked offline dependencies" `
    -Arguments @("build", "--locked", "--offline") `
    -WorkingDirectory $daemonDir `
    -Offline

if ($IncludeRootPackage) {
    Invoke-CargoStep `
        -Description "Fetch locked root workspace dependencies" `
        -Arguments @("fetch", "--locked") `
        -WorkingDirectory $repoRoot

    Invoke-CargoStep `
        -Description "Build root session-ledger package with locked offline dependencies" `
        -Arguments @("build", "--locked", "--offline", "--package", "session-ledger") `
        -WorkingDirectory $repoRoot `
        -Offline
}

Write-Host "Hermetic dependency check passed: cargo build completed with --locked --offline after fetch."
