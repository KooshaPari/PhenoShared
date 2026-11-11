<#
.SYNOPSIS
  Machine-check live tokio daemon-graph hard gate anchors (C00 L7).

.DESCRIPTION
  Verifies docs/ops/daemon-graph-hard.md + daemon-graph-hard.json document live
  tokio mpsc/broadcast/SSE graph ports for sl-daemon, cross-checks
  tests/daemon_graph_tokio.rs and blocking PR workflow wiring.
  Hermetic: -SelfCheck needs no loom / no daemon process.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.EXAMPLE
  pwsh ./scripts/daemon-graph-hard-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/daemon-graph-hard.md"
$policyPath = Join-Path $repoRoot "docs/ops/daemon-graph-hard.json"
$concurrencyDoc = Join-Path $repoRoot "docs/ops/concurrency-safety.md"
$hardWorkflowPath = Join-Path $repoRoot ".github/workflows/daemon-graph-hard.yml"
$loomWorkflowPath = Join-Path $repoRoot ".github/workflows/loom-permutation.yml"
$tokioTestPath = Join-Path $repoRoot "tests/daemon_graph_tokio.rs"
$selfPath = Join-Path $repoRoot "scripts/daemon-graph-hard-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/daemon_graph_hard.rs"
$cargoToml = Join-Path $repoRoot "Cargo.toml"
$daemonMain = Join-Path $repoRoot "crates/sl-daemon/src/main.rs"

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
        [string]$Context = "docs/ops/daemon-graph-hard.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Daemon-graph hard check (C00 L7)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + tokio graph anchors; no loom / no daemon process)"
}

Assert-File -Path $docPath -Label "daemon-graph-hard doc"
Assert-File -Path $policyPath -Label "daemon-graph-hard policy JSON"
Assert-File -Path $concurrencyDoc -Label "concurrency-safety doc"
Assert-File -Path $hardWorkflowPath -Label "daemon-graph-hard workflow"
Assert-File -Path $loomWorkflowPath -Label "loom-permutation workflow"
Assert-File -Path $tokioTestPath -Label "daemon_graph_tokio.rs"
Assert-File -Path $selfPath -Label "daemon-graph-hard check script"
Assert-File -Path $wrapperTest -Label "daemon_graph_hard.rs test wrapper"
Assert-File -Path $cargoToml -Label "workspace Cargo.toml"
Assert-File -Path $daemonMain -Label "sl-daemon main.rs"

$doc = Get-Content -LiteralPath $docPath -Raw
$policyRaw = Get-Content -LiteralPath $policyPath -Raw
$policy = $policyRaw | ConvertFrom-Json
$concurrency = Get-Content -LiteralPath $concurrencyDoc -Raw
$hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
$tokioTest = Get-Content -LiteralPath $tokioTestPath -Raw
$wrapperRs = Get-Content -LiteralPath $wrapperTest -Raw
$cargo = Get-Content -LiteralPath $cargoToml -Raw
$mainRs = Get-Content -LiteralPath $daemonMain -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "# Daemon-graph hard (C00 L7 live tokio ports)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "scripts/daemon-graph-hard-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "Live tokio mpsc/broadcast/SSE daemon graph ports | **done**" `
    -Label "live tokio ports marked done"
Test-DocContains -Doc $doc -Needle "Blocking daemon-graph-hard CI workflow | **done**" `
    -Label "blocking workflow marked done"
Test-DocContains -Doc $doc -Needle "Process-level HTTP SSE soak under loom | **unpaid**" `
    -Label "process-level soak unpaid gate"
Test-DocContains -Doc $doc -Needle ".github/workflows/daemon-graph-hard.yml" `
    -Label "hard workflow path documented"

Write-Host "Policy JSON anchors:"
Test-DocContains -Doc $policyRaw -Needle '"schema_version"' `
    -Label "schema_version" -Context "daemon-graph-hard.json"
if ($policy.tokio_tests.Count -lt 3) {
    throw "daemon-graph-hard.json must list at least three tokio_tests."
}
[void](Write-Check -Label "tokio_tests count" -Ok $true)

Write-Host "concurrency-safety.md cross-link anchors:"
Test-DocContains -Doc $concurrency -Needle "daemon-graph-hard.md" `
    -Label "cross-link to daemon-graph-hard" -Context "docs/ops/concurrency-safety.md"
Test-DocContains -Doc $concurrency -Needle "Live tokio mpsc/broadcast/SSE daemon graph ports | **done**" `
    -Label "live tokio ports done in concurrency-safety" -Context "docs/ops/concurrency-safety.md"

Write-Host "daemon_graph_tokio.rs / Cargo / main anchors:"
if ($tokioTest -notmatch 'daemon_tokio_mpsc_broadcast_sse_pipeline_conserves') {
    throw "daemon_graph_tokio.rs must include pipeline conservation test."
}
[void](Write-Check -Label "pipeline conservation test" -Ok $true)
if ($tokioTest -notmatch 'daemon_tokio_broadcast_lagged_subscriber_recovers') {
    throw "daemon_graph_tokio.rs must include lagged subscriber test."
}
[void](Write-Check -Label "lagged subscriber test" -Ok $true)
if ($tokioTest -notmatch 'daemon_tokio_shutdown_stops_mpsc_enqueue') {
    throw "daemon_graph_tokio.rs must include shutdown enqueue stop test."
}
[void](Write-Check -Label "shutdown enqueue stop test" -Ok $true)
if ($tokioTest -notmatch 'use tokio::sync::\{broadcast, mpsc\}') {
    throw "daemon_graph_tokio.rs must use tokio::sync::{broadcast, mpsc}."
}
[void](Write-Check -Label "tokio sync imports" -Ok $true)
if ($cargo -notmatch '(?m)^tokio\s*=') {
    throw "Cargo.toml must declare tokio as a (dev) dependency for daemon_graph_tokio."
}
[void](Write-Check -Label "Cargo.toml tokio dep" -Ok $true)
if ($mainRs -notmatch 'BROADCAST_CAPACITY' -or $mainRs -notmatch 'CHANNEL_CAPACITY') {
    throw "sl-daemon main.rs must declare CHANNEL_CAPACITY and BROADCAST_CAPACITY."
}
[void](Write-Check -Label "sl-daemon capacity constants" -Ok $true)

Write-Host "Hard daemon-graph CI blocking-gate anchors:"
if ($hardWorkflow -match 'continue-on-error:\s*true') {
    throw "daemon-graph-hard.yml must not set continue-on-error (blocking PR CI)."
}
[void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)
if ($hardWorkflow -notmatch 'pull_request:') {
    throw "daemon-graph-hard.yml must run on pull_request."
}
[void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)
if ($hardWorkflow -notmatch 'daemon-graph-hard-check\.ps1 -SelfCheck') {
    throw "daemon-graph-hard.yml must run daemon-graph-hard-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hard workflow runs SelfCheck" -Ok $true)
if ($hardWorkflow -notmatch 'daemon_graph_tokio') {
    throw "daemon-graph-hard.yml must run cargo test --test daemon_graph_tokio."
}
[void](Write-Check -Label "hard workflow runs tokio graph suite" -Ok $true)
if ($wrapperRs -notmatch 'daemon-graph-hard-check\.ps1') {
    throw "tests/daemon_graph_hard.rs must invoke daemon-graph-hard-check.ps1."
}
[void](Write-Check -Label "daemon_graph_hard.rs invokes SelfCheck script" -Ok $true)

Write-Host "Daemon graph hard CI SelfCheck passed (C00 L7; loom-permutation retained; process-level SSE soak unpaid)."

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Daemon-graph hard SelfCheck (C00 L7)

SelfCheck passed: ``docs/ops/daemon-graph-hard.md`` policy rows, live tokio
``daemon_graph_tokio`` suite anchors, and blocking ``daemon-graph-hard.yml``.
Loom permutation retained. Process-level HTTP SSE soak remains unpaid.
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

exit 0
