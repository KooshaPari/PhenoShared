<#
.SYNOPSIS
  Machine-check CI job timeout anchors for heavy unbounded jobs (P0 stability).

.DESCRIPTION
  Verifies .github/workflows/ci.yml sets timeout-minutes on build-test, fuzz-smoke,
  and coverage jobs so hung runners fail fast instead of burning the 6h default.
  Hermetic: no cargo, no network.

  Does not claim timeout coverage for every workflow job or security.yml scans.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/ci-timeout-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$ciPath = Join-Path $repoRoot ".github/workflows/ci.yml"
$selfPath = Join-Path $repoRoot "scripts/ci-timeout-check.ps1"

$expectedTimeouts = [ordered]@{
    "build-test" = 45
    "fuzz-smoke" = 15
    "coverage"   = 30
}

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

function Get-JobBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Workflow,
        [Parameter(Mandatory = $true)][string]$JobId
    )
    $escaped = [regex]::Escape($JobId)
    $pattern = "(?ms)^  ${escaped}:\r?\n(.*?)(?=^  [a-z][\w-]*:|\z)"
    if ($Workflow -match $pattern) {
        return $Matches[1]
    }
    throw "ci.yml missing job block '$JobId'."
}

function Test-JobTimeout {
    param(
        [Parameter(Mandatory = $true)][string]$Workflow,
        [Parameter(Mandatory = $true)][string]$JobId,
        [Parameter(Mandatory = $true)][int]$ExpectedMinutes
    )
    $block = Get-JobBlock -Workflow $Workflow -JobId $JobId
    if ($block -notmatch 'timeout-minutes:\s*(\d+)') {
        throw "ci.yml job '$JobId' must set timeout-minutes: $ExpectedMinutes."
    }
    $actual = [int]$Matches[1]
    if ($actual -ne $ExpectedMinutes) {
        throw "ci.yml job '$JobId' timeout-minutes must be $ExpectedMinutes (found $actual)."
    }
    [void](Write-Check -Label "$JobId timeout-minutes: $ExpectedMinutes" -Ok $true)
}

Write-Host "CI timeout check (P0 stability)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (ci.yml heavy-job timeout anchors; no cargo / no network)"
}

Assert-File -Path $ciPath -Label "ci workflow"
Assert-File -Path $selfPath -Label "ci timeout check script"

$ci = Get-Content -LiteralPath $ciPath -Raw

Write-Host "ci.yml heavy job timeout anchors:"
foreach ($entry in $expectedTimeouts.GetEnumerator()) {
    Test-JobTimeout -Workflow $ci -JobId $entry.Key -ExpectedMinutes $entry.Value
}

if ($ci -notmatch 'ci-timeout-check\.ps1 -SelfCheck') {
    throw "ci.yml must run scripts/ci-timeout-check.ps1 -SelfCheck (policy anchor smoke)."
}
[void](Write-Check -Label "ci.yml references ci-timeout-check.ps1 -SelfCheck" -Ok $true)

Write-Host "CI timeout SelfCheck passed"
exit 0
