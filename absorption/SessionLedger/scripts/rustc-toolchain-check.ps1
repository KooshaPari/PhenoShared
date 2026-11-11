<#
.SYNOPSIS
  Machine-check the C06 L60 exact rustc toolchain pin.

.DESCRIPTION
  Verifies rust-toolchain.toml pins an exact semver channel (not floating
  stable/beta/nightly), docs/ops/rustc-toolchain-pin.json matches that channel
  and records a rustc commit-hash identity, the ops doc keeps SelfCheck anchors,
  and primary CI workflows install via dtolnay/rust-toolchain without
  toolchain: stable (which would override the pin). Hermetic: no network.

.PARAMETER SelfCheck
  Explicit pin/docs/CI smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/rustc-toolchain-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolchainPath = Join-Path $repoRoot "rust-toolchain.toml"
$pinJsonPath = Join-Path $repoRoot "docs/ops/rustc-toolchain-pin.json"
$docPath = Join-Path $repoRoot "docs/ops/rustc-toolchain-pin.md"
$checkScript = Join-Path $repoRoot "scripts/rustc-toolchain-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/rustc_toolchain.rs"
$ciWorkflow = Join-Path $repoRoot ".github/workflows/ci.yml"
$hermeticWorkflow = Join-Path $repoRoot ".github/workflows/hermetic.yml"
$releaseWorkflow = Join-Path $repoRoot ".github/workflows/release.yml"

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

function Get-TomlChannel {
    param([Parameter(Mandatory = $true)][string]$Toml)
    $match = [regex]::Match($Toml, '(?m)^\s*channel\s*=\s*"([^"]+)"\s*$')
    if (-not $match.Success) {
        throw "rust-toolchain.toml missing channel = `"...`" line."
    }
    return $match.Groups[1].Value
}

Write-Host "Exact rustc toolchain pin check (C06 L60)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (pin + docs + CI wiring; no network)"
}

Assert-File -Path $toolchainPath -Label "rust-toolchain.toml"
Assert-File -Path $pinJsonPath -Label "rustc toolchain pin JSON"
Assert-File -Path $docPath -Label "rustc toolchain pin doc"
Assert-File -Path $checkScript -Label "rustc toolchain check script"
Assert-File -Path $rustWrapper -Label "rustc toolchain rust SelfCheck wrapper"
Assert-File -Path $ciWorkflow -Label "ci.yml"
Assert-File -Path $hermeticWorkflow -Label "hermetic.yml"
Assert-File -Path $releaseWorkflow -Label "release.yml"

$toml = Get-Content -LiteralPath $toolchainPath -Raw
$doc = Get-Content -LiteralPath $docPath -Raw
$ci = Get-Content -LiteralPath $ciWorkflow -Raw
$hermetic = Get-Content -LiteralPath $hermeticWorkflow -Raw
$release = Get-Content -LiteralPath $releaseWorkflow -Raw
$pin = Get-Content -LiteralPath $pinJsonPath -Raw | ConvertFrom-Json

$channel = Get-TomlChannel -Toml $toml
Write-Host "Pin file:"
$exactOk = $channel -match '^\d+\.\d+(\.\d+)?$'
[void](Write-Check -Label "channel is exact semver (not floating)" -Ok $exactOk)
if (-not $exactOk) {
    throw "rust-toolchain.toml channel='$channel' must be exact semver (e.g. 1.96.0), not stable/beta/nightly."
}

$floating = @("stable", "beta", "nightly")
if ($floating -contains $channel.ToLowerInvariant()) {
    throw "rust-toolchain.toml channel='$channel' is floating; pin an exact rustc version."
}

[void](Write-Check -Label "components include rustfmt" -Ok ($toml -match 'rustfmt'))
if ($toml -notmatch 'rustfmt') { throw "rust-toolchain.toml must list rustfmt." }
[void](Write-Check -Label "components include clippy" -Ok ($toml -match 'clippy'))
if ($toml -notmatch 'clippy') { throw "rust-toolchain.toml must list clippy." }

Write-Host "JSON identity:"
$channelMatch = ($pin.channel -eq $channel) -and ($pin.rustc_release -eq $channel)
[void](Write-Check -Label "JSON channel/release match TOML" -Ok $channelMatch)
if (-not $channelMatch) {
    throw "docs/ops/rustc-toolchain-pin.json channel/rustc_release must equal TOML channel '$channel'."
}

$hashOk = [string]::IsNullOrWhiteSpace([string]$pin.rustc_commit_hash) -eq $false -and
    $pin.rustc_commit_hash -match '^[0-9a-f]{40}$'
[void](Write-Check -Label "JSON rustc_commit_hash is 40-char hex" -Ok $hashOk)
if (-not $hashOk) {
    throw "docs/ops/rustc-toolchain-pin.json rustc_commit_hash must be a 40-char hex commit-hash."
}

[void](Write-Check -Label "JSON records msrv" -Ok (-not [string]::IsNullOrWhiteSpace([string]$pin.msrv)))
if ([string]::IsNullOrWhiteSpace([string]$pin.msrv)) {
    throw "docs/ops/rustc-toolchain-pin.json missing msrv."
}

Write-Host "Doc anchors:"
Assert-Contains -Doc $doc -Needle "Exact rustc toolchain pin (C06 L60)" `
    -Label "doc heading" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "rust-toolchain.toml" `
    -Label "toml reference" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "rustc_commit_hash" `
    -Label "commit-hash identity" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "scripts/rustc-toolchain-check.ps1" `
    -Label "SelfCheck script reference" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "Exact rustc toolchain pin SelfCheck | **done**" `
    -Label "SelfCheck gate marked done" -Context "docs/ops/rustc-toolchain-pin.md"
Assert-Contains -Doc $doc -Needle "dtolnay/rust-toolchain" `
    -Label "CI action named" -Context "docs/ops/rustc-toolchain-pin.md"

Write-Host "CI uses pin (no toolchain: stable override):"
foreach ($pair in @(
        @{ Name = "ci.yml"; Text = $ci },
        @{ Name = "hermetic.yml"; Text = $hermetic },
        @{ Name = "release.yml"; Text = $release }
    )) {
    $hasAction = $pair.Text -match 'dtolnay/rust-toolchain@'
    [void](Write-Check -Label "$($pair.Name) uses dtolnay/rust-toolchain" -Ok $hasAction)
    if (-not $hasAction) {
        throw ".$($pair.Name) must use dtolnay/rust-toolchain so rust-toolchain.toml is installed."
    }
    $overridesStable = $pair.Text -match '(?m)^\s*toolchain:\s*stable\s*$'
    [void](Write-Check -Label "$($pair.Name) does not set toolchain: stable" -Ok (-not $overridesStable))
    if ($overridesStable) {
        throw ".$($pair.Name) sets toolchain: stable which overrides the exact pin in rust-toolchain.toml."
    }
}

$hermeticJob = $hermetic.Contains("rustc-toolchain-check.ps1") -and $hermetic.Contains("-SelfCheck")
[void](Write-Check -Label "hermetic.yml runs rustc-toolchain SelfCheck" -Ok $hermeticJob)
if (-not $hermeticJob) {
    throw "hermetic.yml must run ./scripts/rustc-toolchain-check.ps1 -SelfCheck."
}

Write-Host "Exact rustc toolchain pin SelfCheck passed (C06 L60)."
