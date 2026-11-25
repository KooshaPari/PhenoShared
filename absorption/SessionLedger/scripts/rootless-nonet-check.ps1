<#
.SYNOPSIS
  Machine-check the C04 L40 hard rootless / no-net CI evidence anchors.

.DESCRIPTION
  Verifies docs/ops/sandbox-boundary.md documents hard rootless/no-net CI gates
  (done vs unpaid), that .github/workflows/rootless-nonet.yml exists as a
  blocking PR SelfCheck workflow, and that security.yml + ci.yml retain
  cross-reference anchors. Hermetic: no container build, no network, no cargo.

  Does not claim maintainer 2FA (L36) or live rootless-only runner matrix /
  blocking no-net enforcement for cargo-fetch security jobs (those remain unpaid).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/rootless-nonet-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/sandbox-boundary.md"
$workflowPath = Join-Path $repoRoot ".github/workflows/rootless-nonet.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$ciWorkflow = Join-Path $repoRoot ".github/workflows/ci.yml"
$testPath = Join-Path $repoRoot "tests/rootless_nonet.rs"
$sandboxCheck = Join-Path $repoRoot "scripts/sandbox-boundary-check.ps1"
$selfPath = Join-Path $repoRoot "scripts/rootless-nonet-check.ps1"

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

Write-Host "Hard rootless / no-net CI evidence check (C04 L40)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + security/ci anchors; no build / no network)"
}

Assert-File -Path $docPath -Label "sandbox boundary doc"
Assert-File -Path $workflowPath -Label "rootless-nonet workflow"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $ciWorkflow -Label "ci workflow"
Assert-File -Path $testPath -Label "rootless_nonet test wrapper"
Assert-File -Path $sandboxCheck -Label "sandbox boundary check script"
Assert-File -Path $selfPath -Label "rootless-nonet check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw
$ciWf = Get-Content -LiteralPath $ciWorkflow -Raw
$testRs = Get-Content -LiteralPath $testPath -Raw

Write-Host "Hard rootless / no-net doc anchors:"
Test-DocContains -Doc $doc -Needle "## Hard rootless / no-net CI" `
    -Label "hard rootless/no-net section heading"
Test-DocContains -Doc $doc -Needle "scripts/rootless-nonet-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Rootless/no-net SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Blocking rootless-no-net CI workflow | **done**" `
    -Label "blocking workflow gate marked done"
Test-DocContains -Doc $doc -Needle ".github/workflows/rootless-nonet.yml" `
    -Label "rootless-nonet workflow path documented"
Test-DocContains -Doc $doc -Needle "tests/rootless_nonet.rs" `
    -Label "cargo test wrapper documented"
Test-DocContains -Doc $doc -Needle "Hard rootless-only runner matrix | **unpaid**" `
    -Label "hard rootless runner matrix remains unpaid"
Test-DocContains -Doc $doc -Needle "Hard no-network for cargo-fetch security jobs | **unpaid**" `
    -Label "hard no-net cargo-fetch enforcement remains unpaid"
Test-DocContains -Doc $doc -Needle "does **not** enforce rootless-only runners or blocking no-net on cargo-fetch jobs" `
    -Label "no false hard enforcement claim"

Write-Host "rootless-nonet workflow blocking-gate anchors:"
if ($workflow -match 'continue-on-error:\s*true') {
    throw "rootless-nonet.yml must not set continue-on-error (blocking SelfCheck CI)."
}
[void](Write-Check -Label "workflow has no continue-on-error" -Ok $true)

if ($workflow -notmatch 'pull_request:') {
    throw "rootless-nonet.yml must run on pull_request."
}
[void](Write-Check -Label "workflow triggers on pull_request" -Ok $true)

if ($workflow -notmatch 'rootless-nonet-check\.ps1') {
    throw "rootless-nonet.yml must run scripts/rootless-nonet-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "workflow runs rootless-nonet-check.ps1" -Ok $true)

Write-Host "security.yml / ci.yml cross-reference anchors:"
Test-DocContains -Doc $securityWf -Needle "rootless-nonet.yml" `
    -Label "security.yml references rootless-nonet workflow" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "rootless-nonet-check.ps1" `
    -Label "security.yml references rootless-nonet SelfCheck script" -Context ".github/workflows/security.yml"

Test-DocContains -Doc $ciWf -Needle "rootless-nonet.yml" `
    -Label "ci.yml references rootless-nonet workflow" -Context ".github/workflows/ci.yml"
Test-DocContains -Doc $ciWf -Needle "rootless-nonet-check.ps1" `
    -Label "ci.yml references rootless-nonet SelfCheck script" -Context ".github/workflows/ci.yml"

# Extract just the rootless-nonet-policy: block (until the next top-level
# job or end of file) so the continue-on-error check can't bleed across
# into unrelated jobs like `security:`. (?ms) = multi-line + dotall so
# `.*?` can span newlines.
$policyBlockMatch = [regex]::Match(
    $ciWf,
    '(?ms)^  rootless-nonet-policy:.*?(?=^  [A-Za-z][\w-]*:\s|\z)'
)
if (-not $policyBlockMatch.Success) {
    throw "ci.yml must define a rootless-nonet-policy job block (C04 L40 cross-reference anchor)."
}
if ($policyBlockMatch.Value -match 'continue-on-error:\s*true') {
    throw "ci.yml rootless-nonet-policy job must be blocking (no continue-on-error)."
}
[void](Write-Check -Label "ci.yml rootless-nonet-policy job is blocking when present" -Ok $true)

Write-Host "cargo test wrapper anchors:"
if ($testRs -notmatch 'rootless-nonet-check\.ps1') {
    throw "tests/rootless_nonet.rs must invoke scripts/rootless-nonet-check.ps1."
}
[void](Write-Check -Label "rootless_nonet.rs invokes SelfCheck script" -Ok $true)

if ($testRs -notmatch 'Rootless/no-net SelfCheck passed') {
    throw "tests/rootless_nonet.rs must assert Rootless/no-net SelfCheck passed success line."
}
[void](Write-Check -Label "rootless_nonet.rs asserts success line" -Ok $true)

$summary = @"
## Hard rootless / no-net CI SelfCheck (C04 L40)

SelfCheck passed: ``docs/ops/sandbox-boundary.md`` hard rootless/no-net rows,
blocking ``rootless-nonet.yml`` workflow, and ``security.yml`` / ``ci.yml`` anchors.
Hard rootless-only runner matrix and blocking no-net for cargo-fetch jobs remain unpaid.
Does not claim maintainer 2FA.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Rootless/no-net SelfCheck passed (C04 L40 hard CI evidence; runner matrix + cargo-fetch no-net unpaid)."
exit 0
