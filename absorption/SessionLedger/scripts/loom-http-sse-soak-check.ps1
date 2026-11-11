#!/usr/bin/env pwsh
# loom-http-sse-soak-check.ps1 — hermetic SelfCheck for W44-B1 (C00 L7 process-level HTTP SSE soak).
#
# Validates:
#   1. tests/loom_http_sse_soak.rs exists on disk
#   2. The 3 loom tests are wired (cargo test discovery)
#   3. RUSTFLAGS=--cfg loom cargo test --test loom_http_sse_soak runs to completion
#   4. docs/ops/loom-http-sse-soak.md exists and references C00 L7 + Wave-44
#
# Usage:
#   pwsh ./scripts/loom-http-sse-soak-check.ps1 -SelfCheck

[CmdletBinding()]
param(
    [switch]$SelfCheck
)

$ErrorActionPreference = "Stop"

function Write-Section($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Pass($msg)  { Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Fail($msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }
function Note($msg)  { Write-Host "  [NOTE] $msg" -ForegroundColor Yellow }

if (-not $SelfCheck) {
    Write-Host "Use -SelfCheck to run the hermetic gate."
    exit 0
}

$repoRoot = (Resolve-Path "$PSScriptRoot/..").Path

# --- 1. test file present
Write-Section "1. loom_http_sse_soak.rs presence"
$testPath = Join-Path $repoRoot "tests/loom_http_sse_soak.rs"
if (Test-Path $testPath) { Pass "$testPath" } else { Fail "missing: $testPath" }

# --- 2. test discovery (without --cfg loom, soft-lane must show)
Write-Section "2. soft-lane discovery (default cargo test)"
$countSoft = (Select-String -Path $testPath -Pattern "fn loom_cfg_not_enabled_documents_soft_lane" -SimpleMatch).Count
if ($countSoft -ge 1) { Pass "soft-lane test fn present" } else { Fail "soft-lane test fn missing" }

# Count the three cfg(loom) tests
$expectedLoomTests = @(
    "process_level_http_sse_soak_conserves_under_cancel",
    "http_sse_soak_lagged_recovery_no_panic",
    "http_sse_soak_shutdown_propagates_to_clients"
)
foreach ($name in $expectedLoomTests) {
    $hits = (Select-String -Path $testPath -Pattern "fn $name" -SimpleMatch).Count
    if ($hits -ge 1) { Pass "loom test wired: $name" }
    else { Fail "loom test missing: $name" }
}

# --- 3. run the suite under RUSTFLAGS='--cfg loom'
Write-Section "3. cargo test --test loom_http_sse_soak (RUSTFLAGS='--cfg loom')"
$env:RUSTFLAGS = "--cfg loom"
try {
    $output = cargo test --test loom_http_sse_soak -- --nocapture 2>&1
    $last = $output | Select-Object -Last 40
    if ($LASTEXITCODE -ne 0) {
        Note "cargo output (tail):"
        $last | ForEach-Object { Write-Host "    $_" }
        Fail "cargo test failed with exit code $LASTEXITCODE"
    }
    Pass "cargo test --test loom_http_sse_soak green"
} catch {
    Fail "cargo test errored: $_"
} finally {
    Remove-Item Env:RUSTFLAGS -ErrorAction SilentlyContinue
}

# --- 4. doc presence
Write-Section "4. docs/ops/loom-http-sse-soak.md presence + content"
$docPath = Join-Path $repoRoot "docs/ops/loom-http-sse-soak.md"
if (Test-Path $docPath) { Pass "$docPath" } else { Fail "missing: $docPath" }
$doc = Get-Content $docPath -Raw
if ($doc -match "C00 L7") { Pass "doc references C00 L7" } else { Fail "doc missing C00 L7 reference" }
if ($doc -match "Wave-44") { Pass "doc references Wave-44" } else { Fail "doc missing Wave-44 reference" }

# --- 5. workflow presence (soft nightly)
Write-Section "5. soft-nightly workflow presence"
$wfPath = Join-Path $repoRoot ".github/workflows/loom-http-sse-soak-soft.yml"
if (Test-Path $wfPath) { Pass "$wfPath" } else { Fail "missing: $wfPath" }

Write-Host ""
Write-Host "==> Loom HTTP SSE soak hard CI SelfCheck passed" -ForegroundColor Green
