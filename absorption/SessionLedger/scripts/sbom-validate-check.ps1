<#
.SYNOPSIS
  Validate CycloneDX SBOM policy anchors and optional SBOM JSON files.

.DESCRIPTION
  SelfCheck verifies docs/ops/sbom-policy.json, pinned cargo-cyclonedx install
  lines in qgate.yml + release.yml, and classification fixtures. -Path mode
  validates bomFormat/specVersion/metadata anchors on a generated .cdx.json.

.PARAMETER SelfCheck
  Hermetic policy + fixture smoke (no cargo-cyclonedx required).

.PARAMETER Path
  CycloneDX JSON file to validate (post-generation in CI).

.EXAMPLE
  pwsh ./scripts/sbom-validate-check.ps1 -SelfCheck
  pwsh ./scripts/sbom-validate-check.ps1 -Path target/sbom.cdx.json
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,
    [string]$Path = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$policyPath = Join-Path $repoRoot "docs/ops/sbom-policy.json"
$validFixture = Join-Path $repoRoot "docs/ops/fixtures/sbom-valid-minimal.cdx.json"
$qgateWorkflow = Join-Path $repoRoot ".github/workflows/qgate.yml"
$releaseWorkflow = Join-Path $repoRoot ".github/workflows/release.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$securityDoc = Join-Path $repoRoot "SECURITY.md"
$selfPath = Join-Path $repoRoot "scripts/sbom-validate-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/sbom_validate.rs"

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
        throw "Missing $Label at '$FilePath'."
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

function Test-CycloneDxSbom {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath
    )

    Assert-File -FilePath $FilePath -Label "CycloneDX SBOM"
    $raw = Get-Content -LiteralPath $FilePath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "SBOM at '$FilePath' is empty."
    }

    try {
        $bom = $raw | ConvertFrom-Json
    }
    catch {
        throw "SBOM at '$FilePath' is not valid JSON: $($_.Exception.Message)"
    }

    if ($bom.bomFormat -ne "CycloneDX") {
        throw "SBOM at '$FilePath' bomFormat must be CycloneDX (got '$($bom.bomFormat)')."
    }
    if ($bom.specVersion -notmatch '^1\.[0-9]+$') {
        throw "SBOM at '$FilePath' specVersion must be CycloneDX 1.x (got '$($bom.specVersion)')."
    }
    if ($null -eq $bom.version -or [int]$bom.version -lt 1) {
        throw "SBOM at '$FilePath' version must be a positive integer."
    }
    if ($null -eq $bom.metadata) {
        throw "SBOM at '$FilePath' missing metadata object."
    }
    if ($null -eq $bom.metadata.component -or [string]::IsNullOrWhiteSpace([string]$bom.metadata.component.name)) {
        throw "SBOM at '$FilePath' missing metadata.component.name."
    }
    if ($null -eq $bom.components) {
        throw "SBOM at '$FilePath' missing components array."
    }
    if ($bom.components -isnot [System.Array]) {
        throw "SBOM at '$FilePath' components must be an array."
    }

    return $true
}

function Invoke-SelfCheck {
    Write-Host "SBOM policy check (C04 L32)"
    Write-Host "Mode: SelfCheck (policy JSON + workflow pins + fixtures; no cargo-cyclonedx)"

    Assert-File -FilePath $policyPath -Label "sbom policy JSON"
    Assert-File -FilePath $validFixture -Label "valid SBOM fixture"
    Assert-File -FilePath $qgateWorkflow -Label "qgate workflow"
    Assert-File -FilePath $releaseWorkflow -Label "release workflow"
    Assert-File -FilePath $securityWorkflow -Label "security workflow"
    Assert-File -FilePath $securityDoc -Label "SECURITY.md"
    Assert-File -FilePath $selfPath -Label "sbom validate script"
    Assert-File -FilePath $wrapperTest -Label "sbom_validate.rs wrapper"

    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    $version = [string]$policy.cargo_cyclonedx_version
    if ([string]::IsNullOrWhiteSpace($version)) {
        throw "sbom-policy.json missing cargo_cyclonedx_version."
    }
    [void](Write-Check -Label "sbom-policy cargo_cyclonedx_version present" -Ok $true)

    $installNeedle = "cargo install cargo-cyclonedx --version $version --locked"
    $qgate = Get-Content -LiteralPath $qgateWorkflow -Raw
    $release = Get-Content -LiteralPath $releaseWorkflow -Raw
    $security = Get-Content -LiteralPath $securityWorkflow -Raw
    $secDoc = Get-Content -LiteralPath $securityDoc -Raw

    Assert-Contains -Doc $qgate -Needle $installNeedle -Label "qgate pinned cargo-cyclonedx install" -Context ".github/workflows/qgate.yml"
    Assert-Contains -Doc $release -Needle $installNeedle -Label "release pinned cargo-cyclonedx install" -Context ".github/workflows/release.yml"
    Assert-Contains -Doc $qgate -Needle "sbom-validate-check.ps1" -Label "qgate SBOM validate step" -Context ".github/workflows/qgate.yml"
    Assert-Contains -Doc $security -Needle "sbom-validate-check.ps1 -SelfCheck" -Label "security.yml SBOM SelfCheck job" -Context ".github/workflows/security.yml"
    Assert-Contains -Doc $secDoc -Needle "sbom-policy.json" -Label "SECURITY.md sbom policy cross-link" -Context "SECURITY.md"

    Write-Host "Fixture validation:"
    [void](Test-CycloneDxSbom -FilePath $validFixture)
    [void](Write-Check -Label "valid minimal fixture passes schema anchors" -Ok $true)

    $invalid = Join-Path ([System.IO.Path]::GetTempPath()) "sbom-invalid-selfcheck.cdx.json"
    '{"version":1}' | Set-Content -LiteralPath $invalid -Encoding utf8
    $failed = $false
    try {
        [void](Test-CycloneDxSbom -FilePath $invalid)
    }
    catch {
        $failed = $true
    }
    finally {
        Remove-Item -LiteralPath $invalid -ErrorAction SilentlyContinue
    }
    if (-not $failed) {
        throw "Expected invalid SBOM fixture to fail validation."
    }
    [void](Write-Check -Label "invalid fixture rejected" -Ok $true)

    Write-Host "SBOM validate SelfCheck passed (C04 L32 pinned cargo-cyclonedx + schema anchors)."
    exit 0
}

if ($SelfCheck) {
    Invoke-SelfCheck
}

if ([string]::IsNullOrWhiteSpace($Path)) {
    throw "Specify -Path <file.cdx.json> or -SelfCheck."
}

$resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
[void](Test-CycloneDxSbom -FilePath $resolved)
Write-Host "CycloneDX SBOM validation passed for $resolved."
exit 0
