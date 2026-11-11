<#
.SYNOPSIS
  Machine-check the C07 L64 test pyramid SSOT in docs/ops/test-pyramid.md.

.DESCRIPTION
  Verifies that docs/ops/test-pyramid.md documents unit, integration,
  end-to-end, load, fuzz, and race layers with the expected key paths and CI
  workflows. Hermetic: no cargo test, no daemon, no network.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/test-pyramid-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/test-pyramid.md"
$checkScript = Join-Path $repoRoot "scripts/test-pyramid-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/test_pyramid.rs"

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
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "docs/ops/test-pyramid.md missing required anchor: '$Needle'"
    }
}

Write-Host "Test pyramid checklist check (C07 L64)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no cargo / no network)"
}

Assert-File -Path $docPath -Label "test pyramid doc"
Assert-File -Path $checkScript -Label "test pyramid check script"
Assert-File -Path $rustWrapper -Label "test pyramid rust SelfCheck wrapper"

$doc = Get-Content -LiteralPath $docPath -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "# Test pyramid (SSOT)" `
    -Label "SSOT heading"
Test-DocContains -Doc $doc -Needle "## Unit" `
    -Label "unit layer section"
Test-DocContains -Doc $doc -Needle "## Integration" `
    -Label "integration layer section"
Test-DocContains -Doc $doc -Needle "## End-to-end" `
    -Label "e2e layer section"
Test-DocContains -Doc $doc -Needle "## Load" `
    -Label "load layer section"
Test-DocContains -Doc $doc -Needle "## Fuzz" `
    -Label "fuzz layer section"
Test-DocContains -Doc $doc -Needle "## Race" `
    -Label "race layer section"
Test-DocContains -Doc $doc -Needle "scripts/test-pyramid-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Test pyramid SelfCheck | **done**" `
    -Label "SelfCheck gate row"
Test-DocContains -Doc $doc -Needle "not_applicable" `
    -Label "qgate browser e2e exclusion"
Test-DocContains -Doc $doc -Needle "tests/test_pyramid.rs" `
    -Label "rust wrapper reference"

$layerPaths = @(
    @{ Path = "src/domain/session.rs"; Layer = "unit" }
    @{ Path = "src/distill/mod.rs"; Layer = "unit" }
    @{ Path = "crates/sl-daemon/tests/integration.rs"; Layer = "integration" }
    @{ Path = "crates/sl-daemon/tests/sse_bridge.rs"; Layer = "integration" }
    @{ Path = "crates/sl-daemon/tests/completions.rs"; Layer = "integration" }
    @{ Path = "tests/schema_migrate.rs"; Layer = "integration" }
    @{ Path = "tests/merge_recovery.rs"; Layer = "integration" }
    @{ Path = "crates/sl-daemon/tests/pipeline.rs"; Layer = "e2e" }
    @{ Path = "tests/okf_roundtrip.rs"; Layer = "e2e" }
    @{ Path = "tests/okf_golden.rs"; Layer = "e2e" }
    @{ Path = "tests/fixtures/okf/golden-minimal.okf.json"; Layer = "e2e" }
    @{ Path = "scripts/load-smoke.ps1"; Layer = "load" }
    @{ Path = "scripts/ops-chaos-smoke.ps1"; Layer = "load" }
    @{ Path = ".github/workflows/ops-load.yml"; Layer = "load" }
    @{ Path = ".github/workflows/ops-chaos-smoke.yml"; Layer = "load" }
    @{ Path = "fuzz/fuzz_targets/okf_roundtrip.rs"; Layer = "fuzz" }
    @{ Path = "fuzz/fuzz_targets/jsonl_ingest.rs"; Layer = "fuzz" }
    @{ Path = "fuzz/corpus/okf_roundtrip/minimal.json"; Layer = "fuzz" }
    @{ Path = "fuzz/corpus/jsonl_ingest/two_sessions.jsonl"; Layer = "fuzz" }
    @{ Path = "tests/race_smoke.rs"; Layer = "race" }
    @{ Path = "tests/race_model.rs"; Layer = "race" }
    @{ Path = ".github/workflows/race-smoke.yml"; Layer = "race" }
    @{ Path = ".github/workflows/ci.yml"; Layer = "ci" }
    @{ Path = "tests/properties.rs"; Layer = "unit-adjacent" }
    @{ Path = "Makefile"; Layer = "task-runner" }
)

Write-Host "Key paths:"
foreach ($entry in $layerPaths) {
    $fullPath = Join-Path $repoRoot $entry.Path
    Assert-File -Path $fullPath -Label "$($entry.Layer): $($entry.Path)"
    Write-Host "  [PASS] $($entry.Layer): $($entry.Path)"
}

Write-Host "Workflow anchors:"
Test-DocContains -Doc $doc -Needle "ci.yml" `
    -Label "ci.yml reference"
Test-DocContains -Doc $doc -Needle "fuzz-smoke" `
    -Label "fuzz-smoke job reference"
Test-DocContains -Doc $doc -Needle "race-smoke.yml" `
    -Label "race-smoke workflow reference"
Test-DocContains -Doc $doc -Needle "ops-load.yml" `
    -Label "ops-load workflow reference"
Test-DocContains -Doc $doc -Needle "ops-chaos-smoke.yml" `
    -Label "ops-chaos-smoke workflow reference"
Test-DocContains -Doc $doc -Needle "build-test" `
    -Label "build-test job reference"

Write-Host "Test pyramid SelfCheck passed (C07 L64 SSOT anchors + key paths present)."
