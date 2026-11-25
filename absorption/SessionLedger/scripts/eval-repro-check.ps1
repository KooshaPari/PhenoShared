<#
.SYNOPSIS
  Verify eval reproducibility manifest anchors (C08 L79).

.DESCRIPTION
  Asserts Cargo.lock SHA-256, MSRV, OKF fixture count/anchors, and bench policy
  wiring match docs/ops/eval-manifest.json. Hermetic: no network.

.PARAMETER SelfCheck
  Explicit manifest/docs/CI smoke (same checks as default; also validates wiring).

.EXAMPLE
  pwsh ./scripts/eval-repro-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [string]$ManifestPath,

    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $repoRoot "docs/ops/eval-manifest.json"
}
$ManifestPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ManifestPath)

$docPath = Join-Path $repoRoot "docs/ops/eval-reproducibility.md"
$rustWrapper = Join-Path $repoRoot "tests/eval_repro.rs"
$ciWorkflow = Join-Path $repoRoot ".github/workflows/ci.yml"

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

if ($SelfCheck) {
    Write-Host "Eval reproducibility manifest check (C08 L79)"
    Write-Host "Mode: SelfCheck (manifest + docs + CI wiring; no network)"
    Assert-File -Path $ManifestPath -Label "eval manifest JSON"
    Assert-File -Path $docPath -Label "eval reproducibility doc"
    Assert-File -Path $rustWrapper -Label "eval repro rust SelfCheck wrapper"
    Assert-File -Path $PSCommandPath -Label "eval repro check script"
    Assert-File -Path $ciWorkflow -Label "ci.yml"

    $doc = Get-Content -LiteralPath $docPath -Raw
    $ci = Get-Content -LiteralPath $ciWorkflow -Raw
    foreach ($pair in @(
            @{ Text = $doc; Needle = "eval-manifest.json"; Label = "doc references eval-manifest.json" },
            @{ Text = $doc; Needle = "eval-repro-check.ps1"; Label = "doc references eval-repro-check.ps1" },
            @{ Text = $doc; Needle = "-SelfCheck"; Label = "doc references SelfCheck" },
            @{ Text = $ci; Needle = "eval-repro-check.ps1"; Label = "ci.yml runs eval-repro-check.ps1" }
        )) {
        if (-not $pair.Text.Contains($pair.Needle)) {
            throw "$($pair.Label) missing required anchor: '$($pair.Needle)'."
        }
    }
}

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Eval manifest not found at '$ManifestPath'."
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$cargoLockPath = Join-Path $repoRoot "Cargo.lock"
$fixtureRoot = Join-Path $repoRoot "docs/reference/conformance/fixtures"
$benchPolicyPath = Join-Path $repoRoot ([string]$manifest.bench_policy_path)
$benchGatePath = Join-Path $repoRoot ([string]$manifest.bench_gate_script)

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][string]$Path)
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

if (-not (Test-Path -LiteralPath $cargoLockPath -PathType Leaf)) {
    throw "Cargo.lock missing at '$cargoLockPath'."
}

$lockHash = Get-Sha256Hex -Path $cargoLockPath
if ($lockHash -ne [string]$manifest.cargo_lock_sha256) {
    throw "Cargo.lock SHA-256 mismatch. Expected $($manifest.cargo_lock_sha256); got $lockHash. Update docs/ops/eval-manifest.json when lockfile changes intentionally."
}

$rustcVersion = (& rustc --version) -replace '^rustc ', ''
$rustcSemver = ($rustcVersion -split '\s+', 2)[0]
if ([version]$rustcSemver -lt [version][string]$manifest.rust_msrv) {
    throw "rustc $rustcSemver is below eval manifest MSRV $($manifest.rust_msrv)."
}

$fixtureFiles = @(Get-ChildItem -LiteralPath $fixtureRoot -Filter *.okf.json -File | Sort-Object Name)
$fixtureCount = $fixtureFiles.Count
if ($fixtureCount -ne [int]$manifest.fixture_count) {
    throw "Fixture count mismatch. Expected $($manifest.fixture_count); found $fixtureCount under '$fixtureRoot'."
}

$anchors = @()
if ($manifest.PSObject.Properties.Name -contains "fixture_anchors") {
    $anchors = @($manifest.fixture_anchors | ForEach-Object { [string]$_ })
}
if ($anchors.Count -gt 0) {
    if ($anchors.Count -ne [int]$manifest.fixture_count) {
        throw "fixture_anchors length ($($anchors.Count)) must match fixture_count ($($manifest.fixture_count))."
    }

    $onDisk = @($fixtureFiles | ForEach-Object { $_.Name })
    foreach ($anchor in $anchors) {
        if ($anchor -notin $onDisk) {
            throw "Missing anchored fixture '$anchor' under '$fixtureRoot'."
        }
    }

    foreach ($name in $onDisk) {
        if ($name -notin $anchors) {
            throw "Unexpected fixture '$name' not listed in eval-manifest.json fixture_anchors."
        }
    }
}

foreach ($required in @($benchPolicyPath, $benchGatePath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required eval artifact missing: '$required'."
    }
}

$benchPolicy = Get-Content -LiteralPath $benchPolicyPath -Raw | ConvertFrom-Json
if (-not [bool]$benchPolicy.policy.enforced) {
    throw "Bench policy at '$benchPolicyPath' must set policy.enforced=true for the blocking perf-budget gate."
}
$threshold = [double]$benchPolicy.policy.threshold_percent
if ($threshold -le 0) {
    throw "Bench policy threshold_percent must be > 0 (got $threshold)."
}

$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($SelfCheck) {
    Write-Host "Eval reproducibility manifest SelfCheck passed (C08 L79)."
}
else {
    Write-Host "Eval reproducibility check passed."
}
Write-Host "  commit=$commit"
Write-Host "  fixture_seed=$($manifest.fixture_seed) fixture_count=$fixtureCount anchor_count=$($anchors.Count)"
Write-Host "  cargo_lock_sha256=$lockHash"
Write-Host "  rustc=$rustcSemver bench_policy=$($manifest.bench_policy_path) enforced=true threshold=${threshold}%"
