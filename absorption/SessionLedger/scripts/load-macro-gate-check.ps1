<#
.SYNOPSIS
  Machine-check macro-tier load-smoke PR gate anchors (C08 L73).

.DESCRIPTION
  Verifies docs/ops/load-macro-gate.md + load-macro-gate.json document the macro
  route tier (/api/bundles, /api/search, /api/stream) blocking PR gate alongside
  the soft probe-tier ops-load.yml schedule.
  Hermetic: -SelfCheck needs no daemon. -RunSmoke builds sl-daemon, seeds ingest,
  and runs load-smoke.ps1 -RouteTier macro.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.PARAMETER RunSmoke
  Live macro-tier load smoke against a local sl-daemon (blocking PR job).

.EXAMPLE
  pwsh ./scripts/load-macro-gate-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,
    [switch]$RunSmoke,
    [string]$DaemonPath = "",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/load-macro-gate.md"
$policyPath = Join-Path $repoRoot "docs/ops/load-macro-gate.json"
$loadSmokeScript = Join-Path $repoRoot "scripts/load-smoke.ps1"
$softWorkflow = Join-Path $repoRoot ".github/workflows/ops-load.yml"
$hardWorkflow = Join-Path $repoRoot ".github/workflows/load-macro-gate-hard.yml"
$selfPath = Join-Path $repoRoot "scripts/load-macro-gate-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/load_macro_gate.rs"
$perfBaseline = Join-Path $repoRoot "docs/ops/perf-baseline.json"

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
        [string]$Context = "docs/ops/load-macro-gate.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

function Get-LoadMacroPolicy {
    Assert-File -Path $policyPath -Label "load-macro-gate policy JSON"
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($null -eq $policy.schema_version) {
        throw "load-macro-gate.json must declare schema_version."
    }
    if ($null -eq $policy.pr_smoke) {
        throw "load-macro-gate.json must declare pr_smoke."
    }
    return $policy
}

function Invoke-MacroSeedIngest {
    param([Parameter(Mandatory = $true)][string]$BaseUrl)

    $body = @"
{
  "bundle_id": "load-macro-gate-seed",
  "created_at": "2026-07-21T00:00:00Z",
  "messages": [{"role": "user", "content": "load macro gate seed"}],
  "token_count": 1
}
"@
    $response = Invoke-WebRequest `
        -Uri "$BaseUrl/api/ingest" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 10 `
        -SkipHttpErrorCheck

    $status = [int]$response.StatusCode
    if ($status -lt 200 -or $status -ge 300) {
        throw "POST /api/ingest seed returned $status."
    }
    Write-Host "ok: seeded macro ingest bundle"
}

function Wait-Readyz {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [int]$MaxAttempts = 30
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $response = Invoke-WebRequest `
                -Uri "$BaseUrl/readyz" `
                -Method Get `
                -TimeoutSec 2 `
                -SkipHttpErrorCheck
            if ($response.StatusCode -eq 200) {
                Write-Host "ok: /readyz healthy after $attempt attempt(s)"
                return
            }
        }
        catch {
            Write-Host "readyz attempt $attempt/$MaxAttempts failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds 1
    }

    throw "sl-daemon did not become ready within $MaxAttempts seconds at $BaseUrl."
}

Write-Host "Load-macro gate check (C08 L73)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + evidence paths; no daemon / no network)"
}

if ($SelfCheck) {
    Assert-File -Path $docPath -Label "load-macro-gate doc"
    Assert-File -Path $loadSmokeScript -Label "load-smoke script"
    Assert-File -Path $softWorkflow -Label "ops-load workflow"
    Assert-File -Path $hardWorkflow -Label "load-macro-gate-hard workflow"
    Assert-File -Path $selfPath -Label "load-macro-gate check script"
    Assert-File -Path $wrapperTest -Label "load_macro_gate.rs test wrapper"
    Assert-File -Path $perfBaseline -Label "perf-baseline.json"

    $doc = Get-Content -LiteralPath $docPath -Raw
    $policyRaw = Get-Content -LiteralPath $policyPath -Raw
    $policy = $policyRaw | ConvertFrom-Json
    $softYaml = Get-Content -LiteralPath $softWorkflow -Raw
    $hardYaml = Get-Content -LiteralPath $hardWorkflow -Raw
    $loadSmoke = Get-Content -LiteralPath $loadSmokeScript -Raw
    $wrapperRs = Get-Content -LiteralPath $wrapperTest -Raw

    Write-Host "Doc anchors:"
    Test-DocContains -Doc $doc -Needle "# Load-macro gate (C08 L73 macro route tier)" `
        -Label "doc heading"
    Test-DocContains -Doc $doc -Needle "C08 L73" `
        -Label "C08 L73 status"
    Test-DocContains -Doc $doc -Needle "## Route tiers" `
        -Label "route tiers heading"
    Test-DocContains -Doc $doc -Needle "/api/bundles" `
        -Label "bundles route"
    Test-DocContains -Doc $doc -Needle "/api/search" `
        -Label "search route"
    Test-DocContains -Doc $doc -Needle "/api/stream" `
        -Label "stream route"
    Test-DocContains -Doc $doc -Needle "macro routes smoke" `
        -Label "expected PR smoke check name"
    Test-DocContains -Doc $doc -Needle "scripts/load-macro-gate-check.ps1" `
        -Label "SelfCheck script reference"
    Test-DocContains -Doc $doc -Needle "Blocking load-macro-gate-hard CI workflow | **done**" `
        -Label "blocking gate marked done"
    Test-DocContains -Doc $doc -Needle "-RouteTier macro" `
        -Label "RouteTier macro reference"

    Write-Host "Policy JSON anchors:"
    Test-DocContains -Doc $policyRaw -Needle '"schema_version"' `
        -Label "schema_version" -Context "load-macro-gate.json"
    if ($policy.route_tiers.macro.Count -lt 3) {
        throw "load-macro-gate.json must list at least three macro routes."
    }
    [void](Write-Check -Label "macro route tier count" -Ok $true)
    if ($policy.pr_smoke.route_tier -ne "macro") {
        throw "load-macro-gate.json pr_smoke.route_tier must be macro."
    }
    [void](Write-Check -Label "pr_smoke.route_tier macro" -Ok $true)

    Write-Host "load-smoke.ps1 anchors:"
    if ($loadSmoke -notmatch 'RouteTier') {
        throw "load-smoke.ps1 must declare RouteTier parameter."
    }
    [void](Write-Check -Label "RouteTier parameter" -Ok $true)
    if ($loadSmoke -notmatch '/api/bundles') {
        throw "load-smoke.ps1 must include /api/bundles in macro tier."
    }
    [void](Write-Check -Label "macro /api/bundles route" -Ok $true)

    Write-Host "ops-load soft-gate anchors:"
    if ($softYaml -notmatch 'load-smoke:') {
        throw "ops-load.yml must declare load-smoke job."
    }
    [void](Write-Check -Label "ops-load load-smoke job" -Ok $true)
    if ($softYaml -notmatch 'load-smoke\.ps1') {
        throw "ops-load.yml must invoke scripts/load-smoke.ps1."
    }
    [void](Write-Check -Label "ops-load invokes load-smoke.ps1" -Ok $true)

    Write-Host "Hard load-macro CI blocking-gate anchors:"
    if ($hardYaml -match 'continue-on-error:\s*true') {
        throw "load-macro-gate-hard.yml must not set continue-on-error (blocking PR CI)."
    }
    [void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)
    if ($hardYaml -notmatch 'pull_request:') {
        throw "load-macro-gate-hard.yml must run on pull_request."
    }
    [void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)
    if ($hardYaml -notmatch 'load-macro-gate-check\.ps1 -SelfCheck') {
        throw "load-macro-gate-hard.yml must run load-macro-gate-check.ps1 -SelfCheck."
    }
    [void](Write-Check -Label "hard workflow runs SelfCheck" -Ok $true)
    if ($hardYaml -notmatch 'load-macro-gate-check\.ps1 -RunSmoke') {
        throw "load-macro-gate-hard.yml must run load-macro-gate-check.ps1 -RunSmoke."
    }
    [void](Write-Check -Label "hard workflow runs RunSmoke" -Ok $true)
    if ($hardYaml -notmatch 'cargo build --locked') {
        throw "load-macro-gate-hard.yml must run cargo build --locked before RunSmoke."
    }
    [void](Write-Check -Label "hard workflow pre-builds sl-daemon" -Ok $true)
    if ($wrapperRs -notmatch 'load-macro-gate-check\.ps1') {
        throw "tests/load_macro_gate.rs must invoke load-macro-gate-check.ps1."
    }
    [void](Write-Check -Label "load_macro_gate.rs invokes SelfCheck script" -Ok $true)

    Write-Host "Load macro gate hard CI SelfCheck passed (C08 L73 blocking PR gate; soft ops-load probe tier retained)."
    if (-not $RunSmoke) {
        exit 0
    }
}

function Resolve-DaemonPath {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (-not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw "Daemon binary not found at '$ExplicitPath'."
        }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }

    $manifest = Join-Path $repoRoot "crates/sl-daemon/Cargo.toml"
    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        throw "sl-daemon manifest not found at '$manifest'."
    }

    if (-not $SkipBuild) {
        Write-Host "Building sl-daemon (locked)..."
        Push-Location (Join-Path $repoRoot "crates/sl-daemon")
        try {
            & cargo build --locked
            if ($LASTEXITCODE -ne 0) {
                throw "cargo build --locked failed with exit code $LASTEXITCODE."
            }
        }
        finally {
            Pop-Location
        }
    }

    $metadataJson = & cargo metadata `
        --format-version 1 `
        --no-deps `
        --manifest-path $manifest
    if ($LASTEXITCODE -ne 0) {
        throw "cargo metadata failed with exit code $LASTEXITCODE."
    }

    $metadata = $metadataJson | ConvertFrom-Json
    $candidate = Join-Path $metadata.target_directory "debug/sl-daemon"
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $candidate = "$candidate.exe"
    }

    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Built daemon not found at '$candidate'. Pass -DaemonPath or build first."
    }

    return (Resolve-Path -LiteralPath $candidate).Path
}

if ($RunSmoke) {
    $policy = Get-LoadMacroPolicy
    $baseUrl = "http://127.0.0.1:8080"
    $watchDir = Join-Path ([System.IO.Path]::GetTempPath()) "sl-watch-load-macro"
    $outDir = Join-Path ([System.IO.Path]::GetTempPath()) "sl-out-load-macro"
    New-Item -ItemType Directory -Force -Path $watchDir, $outDir | Out-Null

    $daemon = Resolve-DaemonPath -ExplicitPath $DaemonPath

    $proc = Start-Process -FilePath $daemon -ArgumentList @(
        "serve", "--watch", $watchDir, "--out", $outDir, "--http-bind", "127.0.0.1:8080"
    ) -NoNewWindow -PassThru
    try {
        Wait-Readyz -BaseUrl $baseUrl
        Invoke-MacroSeedIngest -BaseUrl $baseUrl
        & $loadSmokeScript `
            -BaseUrl $baseUrl `
            -RouteTier $policy.pr_smoke.route_tier `
            -Requests $policy.pr_smoke.requests `
            -Concurrency $policy.pr_smoke.concurrency `
            -MinSuccessRate $policy.pr_smoke.min_success_rate_percent `
            -MaxP95Ms $policy.pr_smoke.max_p95_ms
        if ($LASTEXITCODE -ne 0) {
            throw "load-smoke.ps1 macro tier failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force
            $proc.WaitForExit(5000) | Out-Null
        }
    }

    Write-Host "Load macro gate macro-route smoke passed."
    exit 0
}

if (-not $SelfCheck) {
    throw "Specify -SelfCheck and/or -RunSmoke."
}
