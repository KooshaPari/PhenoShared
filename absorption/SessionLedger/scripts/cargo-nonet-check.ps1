<#
.SYNOPSIS
  Machine-check the C04 L40 cargo-fetch no-net policy evidence anchors.

.DESCRIPTION
  Verifies docs/ops/sandbox-boundary.md documents cargo audit / cargo deny fetch
  paths and hermetic SelfCheck gates (done vs unpaid live runner enforcement),
  that .github/workflows/security.yml retains a blocking cargo-nonet anchor job,
  and that cargo-audit / cargo-deny jobs remain documented fetch paths.
  Hermetic: no container build, no network, no cargo.

  Does not claim maintainer 2FA (L36) or live no-net isolation on hosted runners
  (cargo install / advisory DB refresh still require network today).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/cargo-nonet-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/sandbox-boundary.md"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$testPath = Join-Path $repoRoot "tests/cargo_nonet.rs"
$rootlessCheck = Join-Path $repoRoot "scripts/rootless-nonet-check.ps1"
$selfPath = Join-Path $repoRoot "scripts/cargo-nonet-check.ps1"

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

Write-Host "Cargo-fetch no-net policy check (C04 L40)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + security.yml anchors; no build / no network)"
}

Assert-File -Path $docPath -Label "sandbox boundary doc"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $testPath -Label "cargo_nonet test wrapper"
Assert-File -Path $rootlessCheck -Label "rootless-nonet check script (cross-lane anchor)"
Assert-File -Path $selfPath -Label "cargo-nonet check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw
$testRs = Get-Content -LiteralPath $testPath -Raw

Write-Host "Cargo-fetch no-net doc anchors:"
Test-DocContains -Doc $doc -Needle "## Cargo-fetch no-net policy" `
    -Label "cargo-fetch no-net section heading"
Test-DocContains -Doc $doc -Needle "scripts/cargo-nonet-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Cargo-fetch no-net SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Blocking security.yml anchor | **done**" `
    -Label "blocking security.yml anchor marked done"
Test-DocContains -Doc $doc -Needle "tests/cargo_nonet.rs" `
    -Label "cargo test wrapper documented"
Test-DocContains -Doc $doc -Needle "cargo audit / cargo deny fetch paths documented | **done**" `
    -Label "cargo audit/deny fetch paths documented"
Test-DocContains -Doc $doc -Needle "Live no-net for cargo-fetch on runners | **unpaid**" `
    -Label "live runner no-net enforcement remains unpaid"
Test-DocContains -Doc $doc -Needle "does **not** enforce live no-net on hosted runners" `
    -Label "no false live-runner enforcement claim"

Write-Host "security.yml blocking-gate anchors:"
Test-DocContains -Doc $securityWf -Needle "cargo-nonet-check.ps1" `
    -Label "security.yml runs cargo-nonet-check.ps1" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "cargo-nonet:" `
    -Label "security.yml defines cargo-nonet job" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "cargo-audit:" `
    -Label "security.yml documents cargo-audit fetch path" -Context ".github/workflows/security.yml"
Test-DocContains -Doc $securityWf -Needle "cargo-deny:" `
    -Label "security.yml documents cargo-deny fetch path" -Context ".github/workflows/security.yml"

if ($securityWf -match '(?ms)^  cargo-nonet:(.*?)(?=^  [a-z][a-z0-9-]*:)') {
    $cargoNonetBlock = $Matches[1]
    if ($cargoNonetBlock -match 'continue-on-error:\s*true') {
        throw "security.yml cargo-nonet job must be blocking (no continue-on-error)."
    }
    if ($cargoNonetBlock -notmatch 'cargo-nonet-check\.ps1') {
        throw "security.yml cargo-nonet job must run scripts/cargo-nonet-check.ps1 -SelfCheck."
    }
} else {
    throw "security.yml must define a cargo-nonet job block."
}
[void](Write-Check -Label "cargo-nonet job is blocking when present" -Ok $true)
[void](Write-Check -Label "cargo-nonet job runs cargo-nonet-check.ps1" -Ok $true)

Write-Host "cargo test wrapper anchors:"
if ($testRs -notmatch 'cargo-nonet-check\.ps1') {
    throw "tests/cargo_nonet.rs must invoke scripts/cargo-nonet-check.ps1."
}
[void](Write-Check -Label "cargo_nonet.rs invokes SelfCheck script" -Ok $true)

if ($testRs -notmatch 'Cargo-fetch no-net SelfCheck passed') {
    throw "tests/cargo_nonet.rs must assert Cargo-fetch no-net SelfCheck passed success line."
}
[void](Write-Check -Label "cargo_nonet.rs asserts success line" -Ok $true)

$summary = @"
## Cargo-fetch no-net policy SelfCheck (C04 L40)

SelfCheck passed: ``docs/ops/sandbox-boundary.md`` cargo-fetch no-net rows,
blocking ``security.yml`` ``cargo-nonet`` anchor, and ``cargo-audit`` / ``cargo-deny`` fetch-path documentation.
Live no-net for cargo-fetch on hosted runners remains unpaid.
Does not claim maintainer 2FA.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Cargo-fetch no-net SelfCheck passed (C04 L40 policy evidence; live runner no-net unpaid)."
exit 0
