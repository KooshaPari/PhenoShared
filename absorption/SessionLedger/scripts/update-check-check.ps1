<#
.SYNOPSIS
  Machine-check C11 L111 user-initiated update check anchors.

.DESCRIPTION
  Verifies docs/ops/update-check.md, ADR 0001 manual-update posture,
  sl-daemon check-update wiring, and hermetic SelfCheck paths.
  Does not call GitHub or download release artifacts.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.EXAMPLE
  pwsh ./scripts/update-check-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/update-check.md"
$adrPath = Join-Path $repoRoot "docs/adr/0001-desktop-companion-scope.md"
$distPath = Join-Path $repoRoot "docs/ops/distribution.md"
$mainPath = Join-Path $repoRoot "crates/sl-daemon/src/main.rs"
$modulePath = Join-Path $repoRoot "crates/sl-daemon/src/update_check.rs"
$checkScript = Join-Path $repoRoot "scripts/update-check-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/update_check.rs"
$cliTest = Join-Path $repoRoot "crates/sl-daemon/tests/check_update.rs"
$softWorkflow = Join-Path $repoRoot ".github/workflows/update-check-soft.yml"
$hardWorkflow = Join-Path $repoRoot ".github/workflows/update-check-hard.yml"

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

Write-Host "Update check scope (C11 L111)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + sl-daemon wiring; no network)"
}

Assert-File -Path $docPath -Label "update-check ops doc"
Assert-File -Path $adrPath -Label "ADR 0001"
Assert-File -Path $distPath -Label "distribution ops doc"
Assert-File -Path $mainPath -Label "sl-daemon main.rs"
Assert-File -Path $modulePath -Label "update_check module"
Assert-File -Path $checkScript -Label "update-check-check.ps1"
Assert-File -Path $rustWrapper -Label "update_check rust SelfCheck wrapper"
Assert-File -Path $cliTest -Label "check_update CLI integration test"
Assert-File -Path $softWorkflow -Label "update-check-soft workflow"
Assert-File -Path $hardWorkflow -Label "update-check-hard workflow"

$doc = Get-Content -LiteralPath $docPath -Raw
$adr = Get-Content -LiteralPath $adrPath -Raw
$dist = Get-Content -LiteralPath $distPath -Raw
$main = Get-Content -LiteralPath $mainPath -Raw
$module = Get-Content -LiteralPath $modulePath -Raw

Write-Host "Update-check doc anchors:"
Assert-Contains -Doc $doc -Needle "C11 L111" -Label "L111 marker" -Context "update-check.md"
Assert-Contains -Doc $doc -Needle "sl-daemon check-update" -Label "CLI command" -Context "update-check.md"
Assert-Contains -Doc $doc -Needle "0001-desktop-companion-scope.md" -Label "ADR 0001 link" -Context "update-check.md"
Assert-Contains -Doc $doc -Needle "does not download" -Label "no auto-install" -Context "update-check.md"
Assert-Contains -Doc $doc -Needle "scripts/update-check-check.ps1" -Label "SelfCheck script ref" -Context "update-check.md"
Assert-Contains -Doc $doc -Needle "--latest" -Label "offline latest flag" -Context "update-check.md"

Write-Host "ADR 0001 anchors:"
Assert-Contains -Doc $adr -Needle "user-initiated" -Label "user-initiated updates" -Context "ADR 0001"
Assert-Contains -Doc $adr -Needle "C11 L111" -Label "L111 cross-ref" -Context "ADR 0001"
Assert-Contains -Doc $adr -Needle "check-update" -Label "check-update command ref" -Context "ADR 0001"

Write-Host "Distribution anchors:"
Assert-Contains -Doc $dist -Needle "update-check.md" -Label "distribution links update-check doc" -Context "distribution.md"
Assert-Contains -Doc $dist -Needle "sl-daemon check-update" -Label "distribution CLI ref" -Context "distribution.md"

Write-Host "sl-daemon wiring:"
Assert-Contains -Doc $main -Needle "CheckUpdate" -Label "CheckUpdate subcommand" -Context "main.rs"
Assert-Contains -Doc $main -Needle "mod update_check" -Label "update_check module import" -Context "main.rs"
Assert-Contains -Doc $module -Needle "fetch_latest_release_tag" -Label "GitHub fetch helper" -Context "update_check.rs"
Assert-Contains -Doc $module -Needle "compare_versions" -Label "version compare helper" -Context "update_check.rs"

Write-Host "Update check SelfCheck passed (C11 L111 user-initiated check — no auto-install)."
