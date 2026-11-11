<#
.SYNOPSIS
  Machine-check the C04 L40 rootless-only OCI runner matrix scaffold anchors.

.DESCRIPTION
  Verifies docs/ops/sandbox-boundary.md documents the rootless-only runner
  capability matrix (done vs unpaid live enforcement), that
  .github/workflows/rootless-matrix.yml exists as a blocking PR SelfCheck
  workflow, and that security.yml + ci.yml retain cross-reference anchors.
  Hermetic: no container build, no network, no cargo, no podman/docker.

  Does not claim maintainer 2FA (L36) or live rootless-only runner matrix
  enforcement on GitHub-hosted runners (those remain unpaid).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/rootless-matrix-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/sandbox-boundary.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/rootless-matrix.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$ciWorkflow = Join-Path $repoRoot ".github/workflows/ci.yml"
$testPath = Join-Path $repoRoot "tests/rootless_matrix.rs"
$rootlessNonetCheck = Join-Path $repoRoot "scripts/rootless-nonet-check.ps1"
$selfPath = Join-Path $repoRoot "scripts/rootless-matrix-check.ps1"

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

function Test-DocContains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "docs/ops/sandbox-boundary.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Rootless-only OCI runner matrix scaffold check (C04 L40)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + security/ci anchors; no OCI build / no network)"
}

Assert-File -Path $docPath -Label "sandbox boundary doc"
Assert-File -Path $workflowPath -Label "rootless-matrix workflow"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $ciWorkflow -Label "ci workflow"
Assert-File -Path $testPath -Label "rootless_matrix test wrapper"
Assert-File -Path $rootlessNonetCheck -Label "rootless-nonet check script (cross-lane anchor)"
Assert-File -Path $selfPath -Label "rootless-matrix check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw
$ciWf = Get-Content -LiteralPath $ciWorkflow -Raw
$testRs = Get-Content -LiteralPath $testPath -Raw

Write-Host "Rootless-only runner matrix doc anchors:"
Test-DocContains -Doc $doc -Needle "## Rootless-only OCI runner matrix" `
    -Label "rootless-only matrix section heading"
Test-DocContains -Doc $doc -Needle "scripts/rootless-matrix-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Rootless-only matrix SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Blocking rootless-matrix CI workflow | **done**" `
    -Label "blocking workflow gate marked done"
Test-DocContains -Doc $doc -Needle ".github/workflows/rootless-matrix.yml" `
    -Label "rootless-matrix workflow path documented"
Test-DocContains -Doc $doc -Needle "tests/rootless_matrix.rs" `
    -Label "cargo test wrapper documented"
Test-DocContains -Doc $doc -Needle "Runner capability matrix documented | **done**" `
    -Label "runner capability matrix documented"
Test-DocContains -Doc $doc -Needle "Live rootless-only runners on hosted CI | **unpaid**" `
    -Label "live rootless runner matrix remains unpaid"
Test-DocContains -Doc $doc -Needle "OCI build/smoke in matrix jobs | **unpaid**" `
    -Label "OCI build/smoke in matrix remains unpaid"
Test-DocContains -Doc $doc -Needle "does **not** execute OCI builds" `
    -Label "no false OCI build claim"
Test-DocContains -Doc $doc -Needle "or claim live rootless-only matrix enforcement on GitHub-hosted runners" `
    -Label "no false live-runner enforcement claim"

Write-Host "rootless-matrix workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "rootless-matrix.yml must not set continue-on-error (blocking SelfCheck CI)."
}
[void](Write-Check -Label "workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'pull_request:') {
    throw "rootless-matrix.yml must run on pull_request."
}
[void](Write-Check -Label "workflow triggers on pull_request" -Ok $true)

if ($workflow -notmatch 'rootless-matrix-check\.ps1') {
    throw "rootless-matrix.yml must run scripts/rootless-matrix-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "workflow runs rootless-matrix-check.ps1" -Ok $true)

Write-Host "security.yml / ci.yml cross-reference anchors:"
Test-DocContains -Doc $securityWf -Needle "rootless-matrix.yml" `
    -Label "security.yml references rootless-matrix workflow" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "rootless-matrix-check.ps1" `
    -Label "security.yml references rootless-matrix SelfCheck script" -Context ".github/workflows/security.yml"

Test-DocContains -Doc $ciWf -Needle "rootless-matrix.yml" `
    -Label "ci.yml references rootless-matrix workflow" -Context ".github/workflows/ci.yml"
Test-DocContains -Doc $ciWf -Needle "rootless-matrix-check.ps1" `
    -Label "ci.yml references rootless-matrix SelfCheck script" -Context ".github/workflows/ci.yml"

if ($securityWf -match '(?ms)^  rootless-matrix:(.*?)(?=^  [a-z][a-z0-9-]*:)') {
    $rootlessMatrixBlock = $Matches[1]
    if ($rootlessMatrixBlock -match 'continue-on-error:\s*true') {
        throw "security.yml rootless-matrix job must be blocking (no continue-on-error)."
    }
    if ($rootlessMatrixBlock -notmatch 'rootless-matrix-check\.ps1') {
        throw "security.yml rootless-matrix job must run scripts/rootless-matrix-check.ps1 -SelfCheck."
    }
} else {
    throw "security.yml must define a rootless-matrix job block."
}
[void](Write-Check -Label "security.yml rootless-matrix job is blocking when present" -Ok $true)

if (-not ($ciWf -match '(?ms)^  rootless-matrix-policy:')) {
    throw "ci.yml must define a rootless-matrix-policy job block (C04 L40 cross-reference anchor)."
}
$matrixPolicyBlockMatch = [regex]::Match(
    $ciWf,
    '(?ms)^  rootless-matrix-policy:.*?(?=^  [A-Za-z][\w-]*:\s|\z)'
)
if ($matrixPolicyBlockMatch.Success -and $matrixPolicyBlockMatch.Value -match 'continue-on-error:\s*true') {
    throw "ci.yml rootless-matrix-policy job must be blocking (no continue-on-error)."
}
[void](Write-Check -Label "ci.yml rootless-matrix-policy job is blocking when present" -Ok $true)

Write-Host "cargo test wrapper anchors:"
if ($testRs -notmatch 'rootless-matrix-check\.ps1') {
    throw "tests/rootless_matrix.rs must invoke scripts/rootless-matrix-check.ps1."
}
[void](Write-Check -Label "rootless_matrix.rs invokes SelfCheck script" -Ok $true)

if ($testRs -notmatch 'Rootless-only matrix SelfCheck passed') {
    throw "tests/rootless_matrix.rs must assert Rootless-only matrix SelfCheck passed success line."
}
[void](Write-Check -Label "rootless_matrix.rs asserts success line" -Ok $true)

$summary = @"
## Rootless-only OCI runner matrix SelfCheck (C04 L40)

SelfCheck passed: ``docs/ops/sandbox-boundary.md`` rootless-only matrix rows,
blocking ``rootless-matrix.yml`` workflow, and ``security.yml`` / ``ci.yml`` anchors.
Live rootless-only runner matrix and OCI build/smoke jobs remain unpaid.
Does not claim maintainer 2FA.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Rootless-only matrix SelfCheck passed (C04 L40 scaffold evidence; live runner matrix + OCI build unpaid)."
exit 0
