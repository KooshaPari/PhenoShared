<#
.SYNOPSIS
  Machine-check the C06 L53 reusable-workflow provenance pin for hermetic builds.

.DESCRIPTION
  Verifies docs/ops/reusable-hermetic-pin.md + reusable-hermetic-pin.json,
  the reusable-hermetic-build.yml workflow_call contract, and that
  hermetic.yml calls the reusable workflow at the documented commit SHA with a
  builder_image_digest input matching hermetic-builder.json.

  Hermetic: no cargo build, no network, no gh API.

.PARAMETER SelfCheck
  Explicit docs/pin smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/reusable-provenance-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pinDocPath = Join-Path $repoRoot "docs/ops/reusable-hermetic-pin.md"
$pinJsonPath = Join-Path $repoRoot "docs/ops/reusable-hermetic-pin.json"
$hermeticDocPath = Join-Path $repoRoot "docs/ops/hermetic-builds.md"
$reproDocPath = Join-Path $repoRoot "docs/ops/reproducible-builds.md"
$builderPinPath = Join-Path $repoRoot "docs/ops/hermetic-builder.json"
$reusableWorkflow = Join-Path $repoRoot ".github/workflows/reusable-hermetic-build.yml"
$hermeticWorkflow = Join-Path $repoRoot ".github/workflows/hermetic.yml"
$checkScript = Join-Path $repoRoot "scripts/reusable-provenance-check.ps1"

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

function Test-FullSha {
    param([Parameter(Mandatory = $true)][string]$Sha)
    return $Sha -match '^[0-9a-f]{40}$'
}

Write-Host "Reusable hermetic build provenance check (C06 L53)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + pin + caller wiring; no cargo / no network)"
}

Assert-File -Path $pinDocPath -Label "reusable hermetic pin doc"
Assert-File -Path $pinJsonPath -Label "reusable hermetic pin JSON"
Assert-File -Path $hermeticDocPath -Label "hermetic builds doc"
Assert-File -Path $reproDocPath -Label "reproducible builds doc"
Assert-File -Path $builderPinPath -Label "hermetic builder pin"
Assert-File -Path $reusableWorkflow -Label "reusable hermetic build workflow"
Assert-File -Path $hermeticWorkflow -Label "hermetic caller workflow"
Assert-File -Path $checkScript -Label "reusable provenance check script"

$pinDoc = Get-Content -LiteralPath $pinDocPath -Raw
$pinJson = Get-Content -LiteralPath $pinJsonPath -Raw | ConvertFrom-Json
$hermeticDoc = Get-Content -LiteralPath $hermeticDocPath -Raw
$reproDoc = Get-Content -LiteralPath $reproDocPath -Raw
$builderPin = Get-Content -LiteralPath $builderPinPath -Raw | ConvertFrom-Json
$reusable = Get-Content -LiteralPath $reusableWorkflow -Raw
$hermetic = Get-Content -LiteralPath $hermeticWorkflow -Raw

$expectedSha = [string]$pinJson.workflow_commit_sha
if (-not (Test-FullSha -Sha $expectedSha)) {
    throw "reusable-hermetic-pin.json workflow_commit_sha must be a full 40-char commit SHA (got '$expectedSha')."
}
[void](Write-Check -Label "pin JSON records full workflow commit SHA" -Ok $true)

$expectedDigest = [string]$pinJson.builder_image_digest
if ($expectedDigest -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "reusable-hermetic-pin.json builder_image_digest is not a sha256 digest."
}
if ([string]$builderPin.builder_image_digest -ne $expectedDigest) {
    throw "reusable-hermetic-pin.json builder_image_digest must match hermetic-builder.json."
}
[void](Write-Check -Label "pin JSON builder digest matches hermetic-builder.json" -Ok $true)

Write-Host "Pin doc anchors:"
Assert-Contains -Doc $pinDoc -Needle "reusable-hermetic-build.yml" `
    -Label "pin doc names reusable workflow" -Context "reusable-hermetic-pin.md"
Assert-Contains -Doc $pinDoc -Needle $expectedSha `
    -Label "pin doc records workflow commit SHA" -Context "reusable-hermetic-pin.md"
Assert-Contains -Doc $pinDoc -Needle $expectedDigest `
    -Label "pin doc records builder digest" -Context "reusable-hermetic-pin.md"
Assert-Contains -Doc $pinDoc -Needle "reusable-provenance-check.ps1" `
    -Label "pin doc references SelfCheck script" -Context "reusable-hermetic-pin.md"

Write-Host "Hermetic builds doc anchors:"
Assert-Contains -Doc $hermeticDoc -Needle "Reusable hermetic build workflow" `
    -Label "hermetic-builds reusable workflow section" -Context "hermetic-builds.md"
Assert-Contains -Doc $hermeticDoc -Needle "reusable-provenance-check.ps1" `
    -Label "hermetic-builds references reusable provenance SelfCheck" -Context "hermetic-builds.md"
Assert-Contains -Doc $hermeticDoc -Needle "Reusable-workflow caller SHA pin | **done**" `
    -Label "checklist row marks reusable caller pin done" -Context "hermetic-builds.md"

Write-Host "Reproducible-builds cross-links:"
Assert-Contains -Doc $reproDoc -Needle "reusable-provenance-check.ps1" `
    -Label "reproducible-builds references reusable provenance SelfCheck" -Context "reproducible-builds.md"
if ($reproDoc -notmatch 'reusable-hermetic-pin\.md|reusable hermetic build') {
    throw "docs/ops/reproducible-builds.md must cross-link reusable hermetic workflow provenance."
}
[void](Write-Check -Label "reproducible-builds.md links reusable hermetic provenance" -Ok $true)

Write-Host "Reusable workflow contract:"
if ($reusable -notmatch '(?m)^on:\s*$') {
    throw "reusable-hermetic-build.yml must declare on: workflow_call."
}
Assert-Contains -Doc $reusable -Needle "workflow_call:" `
    -Label "reusable workflow exposes workflow_call" -Context "reusable-hermetic-build.yml"
Assert-Contains -Doc $reusable -Needle "builder_image_digest:" `
    -Label "reusable workflow accepts builder_image_digest input" -Context "reusable-hermetic-build.yml"
Assert-Contains -Doc $reusable -Needle "cargo build --locked --offline" `
    -Label "reusable workflow runs locked offline cargo build" -Context "reusable-hermetic-build.yml"
Assert-Contains -Doc $reusable -Needle "ca-certificates.crt" `
    -Label "reusable workflow proves CA-root checkout prerequisite" -Context "reusable-hermetic-build.yml"
Assert-Contains -Doc $reusable -Needle "git --version" `
    -Label "reusable workflow proves Git checkout prerequisite" -Context "reusable-hermetic-build.yml"

Write-Host "Caller workflow wiring:"
$usesNeedle = "KooshaPari/SessionLedger/.github/workflows/reusable-hermetic-build.yml@$expectedSha"
Assert-Contains -Doc $hermetic -Needle $usesNeedle `
    -Label "hermetic.yml pins reusable workflow to documented SHA" -Context "hermetic.yml"
if ($hermetic -notmatch '(?m)^\s*sl-daemon-offline-container:\s*$') {
    throw "hermetic.yml must keep sl-daemon-offline-container caller job."
}
[void](Write-Check -Label "hermetic.yml retains sl-daemon-offline-container job" -Ok $true)
if ($hermetic -notmatch 'builder_image_digest:\s*' + [regex]::Escape($expectedDigest)) {
    throw "hermetic.yml must pass builder_image_digest matching the pin JSON."
}
[void](Write-Check -Label "hermetic.yml passes pinned builder_image_digest input" -Ok $true)

if ($hermetic -notmatch 'reusable-provenance-check\.ps1') {
    throw "hermetic.yml must run scripts/reusable-provenance-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hermetic.yml runs reusable-provenance SelfCheck" -Ok $true)

$summary = @"
## Reusable hermetic build provenance (C06 L53)

SelfCheck passed: reusable workflow at ``$expectedSha``, caller ``hermetic.yml``
``sl-daemon-offline-container`` job, builder digest ``$expectedDigest``.

Partial evidence only — **not** full SLSA Build L3 reusable-workflow signing.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Reusable provenance SelfCheck passed (workflow pin $expectedSha)."
exit 0
