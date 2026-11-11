<#
.SYNOPSIS
  Machine-check fuzz cadence SSOT anchors (C07 L67).

.DESCRIPTION
  Verifies docs/ops/fuzz-cadence.md documents blocking vs soft sustained fuzz,
  and that the fuzz-blocking / fuzz-cadence workflows, fuzz targets/corpus,
  and this script stay wired. Hermetic: no cargo-fuzz, no network.

  Does not claim automatic corpus promotion or multi-hour corpus triage.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/fuzz-cadence-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/fuzz-cadence.md"
$blockingWorkflowPath = Join-Path $repoRoot ".github/workflows/fuzz-blocking.yml"
$workflowPath = Join-Path $repoRoot ".github/workflows/fuzz-cadence.yml"
$ciPath = Join-Path $repoRoot ".github/workflows/ci.yml"
$selfPath = Join-Path $repoRoot "scripts/fuzz-cadence-check.ps1"
$okfTarget = Join-Path $repoRoot "fuzz/fuzz_targets/okf_roundtrip.rs"
$jsonlTarget = Join-Path $repoRoot "fuzz/fuzz_targets/jsonl_ingest.rs"
$okfCorpus = Join-Path $repoRoot "fuzz/corpus/okf_roundtrip/minimal.json"
$jsonlCorpus = Join-Path $repoRoot "fuzz/corpus/jsonl_ingest/two_sessions.jsonl"

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
        [string]$Context = "docs/ops/fuzz-cadence.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Fuzz cadence check (C07 L67)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + workflow + corpus anchors; no cargo-fuzz / no network)"
}

Assert-File -Path $docPath -Label "fuzz cadence doc"
Assert-File -Path $blockingWorkflowPath -Label "fuzz-blocking workflow"
Assert-File -Path $workflowPath -Label "fuzz-cadence workflow"
Assert-File -Path $ciPath -Label "ci.yml"
Assert-File -Path $selfPath -Label "fuzz cadence check script"
Assert-File -Path $okfTarget -Label "okf_roundtrip fuzz target"
Assert-File -Path $jsonlTarget -Label "jsonl_ingest fuzz target"
Assert-File -Path $okfCorpus -Label "okf_roundtrip corpus seed"
Assert-File -Path $jsonlCorpus -Label "jsonl_ingest corpus seed"

$doc = Get-Content -LiteralPath $docPath -Raw
$blockingWorkflow = Get-Content -LiteralPath $blockingWorkflowPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$ci = Get-Content -LiteralPath $ciPath -Raw

Write-Host "Fuzz cadence doc anchors (blocking vs soft):"
Test-DocContains -Doc $doc -Needle "Fuzz cadence (C07 L67)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "Cadence map (blocking vs soft)" `
    -Label "blocking vs soft cadence map heading"
Test-DocContains -Doc $doc -Needle "scripts/fuzz-cadence-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Fuzz cadence SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Blocking sustained fuzz CI | **done**" `
    -Label "blocking sustained fuzz CI gate marked done"
Test-DocContains -Doc $doc -Needle "fuzz-blocking.yml" `
    -Label "fuzz-blocking workflow reference"
Test-DocContains -Doc $doc -Needle "max_total_time=30" `
    -Label "blocking 30s budget"
Test-DocContains -Doc $doc -Needle "fuzz-cadence.yml" `
    -Label "fuzz-cadence workflow reference"
Test-DocContains -Doc $doc -Needle "continue-on-error" `
    -Label "soft continue-on-error note"
Test-DocContains -Doc $doc -Needle "max_total_time=120" `
    -Label "sustained 120s budget"
Test-DocContains -Doc $doc -Needle "fuzz-smoke" `
    -Label "PR fuzz-smoke reference"
Test-DocContains -Doc $doc -Needle "## Crash corpus triage" `
    -Label "crash corpus triage section"
Test-DocContains -Doc $doc -Needle "fuzz/artifacts/" `
    -Label "crash artifacts path"
Test-DocContains -Doc $doc -Needle "Auto corpus promotion from CI crashes | **unpaid**" `
    -Label "auto corpus promotion unpaid gate"
Test-DocContains -Doc $doc -Needle "okf_roundtrip" `
    -Label "okf_roundtrip target"
Test-DocContains -Doc $doc -Needle "jsonl_ingest" `
    -Label "jsonl_ingest target"

Write-Host "Blocking workflow gate anchors:"
if ($blockingWorkflow -match 'continue-on-error:\s*true') {
    throw "fuzz-blocking.yml must not set continue-on-error (blocking sustained fuzz CI)."
}
[void](Write-Check -Label "fuzz-blocking workflow has no continue-on-error" -Ok $true)

if ($blockingWorkflow -notmatch 'fuzz-cadence-check\.ps1') {
    throw "fuzz-blocking.yml must exercise scripts/fuzz-cadence-check.ps1."
}
[void](Write-Check -Label "blocking workflow references fuzz-cadence-check.ps1" -Ok $true)

if ($blockingWorkflow -notmatch 'max_total_time=30') {
    throw "fuzz-blocking.yml must run bounded sustained fuzz with -max_total_time=30."
}
[void](Write-Check -Label "blocking workflow max_total_time=30" -Ok $true)

if ($blockingWorkflow -notmatch 'okf_roundtrip' -or $blockingWorkflow -notmatch 'jsonl_ingest') {
    throw "fuzz-blocking.yml must exercise okf_roundtrip and jsonl_ingest."
}
[void](Write-Check -Label "blocking workflow exercises both fuzz targets" -Ok $true)

Write-Host "Soft workflow gate anchors:"
if ($workflow -notmatch 'continue-on-error:\s*true') {
    throw "fuzz-cadence.yml must set continue-on-error: true (soft gate)."
}
[void](Write-Check -Label "workflow continue-on-error: true" -Ok $true)

if ($workflow -notmatch 'max_total_time=120') {
    throw "fuzz-cadence.yml must run sustained fuzz with -max_total_time=120."
}
[void](Write-Check -Label "workflow max_total_time=120" -Ok $true)

if ($workflow -notmatch 'github\.event_name != ''pull_request''') {
    throw "fuzz-cadence.yml must skip sustained job on pull_request (keep PR CI fast)."
}
[void](Write-Check -Label "sustained job skips pull_request" -Ok $true)

if ($workflow -notmatch 'fuzz-crash-artifacts') {
    throw "fuzz-cadence.yml must upload fuzz-crash-artifacts on failure."
}
[void](Write-Check -Label "workflow crash artifact upload" -Ok $true)

if ($workflow -notmatch 'okf_roundtrip' -or $workflow -notmatch 'jsonl_ingest') {
    throw "fuzz-cadence.yml must exercise okf_roundtrip and jsonl_ingest."
}
[void](Write-Check -Label "workflow exercises both fuzz targets" -Ok $true)

Write-Host "PR smoke stays short:"
# The PR smoke contract was consolidated into fuzz-blocking.yml (C07 L67
# follow-up). The 10 s `ci.yml` `fuzz-smoke` job no longer exists; the
# blocking sustained PR budget is now `fuzz-blocking.yml` at 30 s / target.
# Enforce that here so PR CI doesn't silently lose its bounded PR fuzz.
if ($blockingWorkflow -notmatch 'max_total_time=30') {
    throw "fuzz-blocking.yml must keep -max_total_time=30 for the PR fuzz budget (do not slow PR CI here)."
}
[void](Write-Check -Label "fuzz-blocking.yml PR fuzz max_total_time=30" -Ok $true)

Write-Host "Fuzz cadence SelfCheck passed"
exit 0
