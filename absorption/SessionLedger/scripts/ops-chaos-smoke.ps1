<#
.SYNOPSIS
Short operational chaos + load smoke for sl-daemon (CI and manual).

.DESCRIPTION
Exercises liveness vs readiness separation, Prometheus/product metrics probes,
a light concurrent load burst, and process-kill recovery. Target wall time once
the daemon binary exists: under two minutes.

Readiness fault uses a unique file path for --out (so /readyz returns 503) while
SL_DATA_DIR points at a separate writable directory for the audit sink.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DaemonPath,

    [string]$HttpBind = "",

    [string]$WorkRoot = $env:RUNNER_TEMP,

    [ValidateRange(8, 500)]
    [int]$LoadRequests = 48,

    [ValidateRange(1, 32)]
    [int]$LoadConcurrency = 6,

    [ValidateRange(4, 120)]
    [int]$RecoveryRequests = 16,

    [string]$EvidencePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DaemonPath -PathType Leaf)) {
    throw "Daemon binary not found at '$DaemonPath'."
}

if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
    $WorkRoot = [System.IO.Path]::GetTempPath()
}

$scriptRoot = $PSScriptRoot
$loadSmokeScript = Join-Path $scriptRoot "load-smoke.ps1"
$script:EvidenceSteps = @()
$script:RedMetricSeries = @()
if (-not (Test-Path -LiteralPath $loadSmokeScript -PathType Leaf)) {
    throw "Missing load smoke script at '$loadSmokeScript'."
}

if ([string]::IsNullOrWhiteSpace($HttpBind)) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ($listener.LocalEndpoint).Port
    $listener.Stop()
    $HttpBind = "127.0.0.1:$port"
}

$baseUrl = "http://$HttpBind"
Write-Host "Using daemon HTTP bind $HttpBind"

$runId = [Guid]::NewGuid().ToString("n")
$watchDir = Join-Path $WorkRoot "sl-chaos-$runId-watch"
$outDir = Join-Path $WorkRoot "sl-chaos-$runId-out"
$dataDir = Join-Path $WorkRoot "sl-chaos-$runId-data"
$daemonProc = $null
$previousDataDir = $env:SL_DATA_DIR

function Remove-PathForce {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Add-EvidenceStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][ValidateSet("pass", "fail", "skip")]
        [string]$Outcome,
        [string]$Detail = ""
    )

    $script:EvidenceSteps += [ordered]@{
        name    = $Name
        outcome = $Outcome
        detail  = $Detail
        at      = (Get-Date).ToUniversalTime().ToString("o")
    }
}

function Get-RedMetricSeries {
    param([Parameter(Mandatory = $true)][string]$MetricsBody)

    $series = [ordered]@{}
    foreach ($name in @(
            "sl_http_requests_total",
            "sl_http_errors_total",
            "sl_http_request_duration_seconds_sum",
            "sl_http_request_duration_seconds_count"
        )) {
        $series[$name] = [bool]($MetricsBody -match [regex]::Escape($name))
    }

    $series["route_labels"] = [bool]($MetricsBody -match 'sl_http_requests_total\{route=')
    $series["histogram_buckets"] = [bool]($MetricsBody -match 'sl_http_request_duration_seconds_bucket\{route=')
    return $series
}

function Write-GameDayEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("pass", "fail")]
        [string]$Outcome,
        [Parameter(Mandatory = $true)][string]$HttpBind,
        [int]$LoadRequests,
        [int]$LoadConcurrency,
        [int]$RecoveryRequests
    )

    $evidence = [ordered]@{
        schema       = "sessionledger.gameday-evidence.v1"
        outcome      = $Outcome
        httpBind     = $HttpBind
        loadRequests = $LoadRequests
        loadConcurrency = $LoadConcurrency
        recoveryRequests = $RecoveryRequests
        host         = [ordered]@{
            os       = if ($IsWindows -or $env:OS -eq "Windows_NT") { "windows" } else { "linux" }
            ci       = [bool]($env:GITHUB_ACTIONS -eq "true")
            runner   = $env:RUNNER_OS
            workflow = $env:GITHUB_WORKFLOW
            run_id   = $env:GITHUB_RUN_ID
            run_url  = @($env:GITHUB_SERVER_URL, $env:GITHUB_REPOSITORY, "actions/runs", $env:GITHUB_RUN_ID) -join "/"
        }
        generatedAt  = (Get-Date).ToUniversalTime().ToString("o")
        redMetrics   = $script:RedMetricSeries
        steps        = @($script:EvidenceSteps)
        notes        = @(
            "Short chaos smoke only; does not prove multi-host steady state or live pager delivery.",
            "Prometheus job=sl-daemon and Alertmanager routing are documented in docs/ops/alerts.md."
        )
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Path -Encoding utf8
    Write-Host "ok: game-day evidence written to $Path"
}

function Start-SlDaemon {
    param(
        [Parameter(Mandatory = $true)][string]$Watch,
        [Parameter(Mandatory = $true)][string]$Out
    )

    $daemonArgs = @(
        "serve",
        "--watch", $Watch,
        "--out", $Out,
        "--http-bind", $HttpBind
    )

    return Start-Process -FilePath $DaemonPath -ArgumentList $daemonArgs -NoNewWindow -PassThru
}

function Stop-SlDaemon {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }

    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
        $Process.WaitForExit(5000) | Out-Null
    }
}

function Invoke-StatusProbe {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int]$ExpectedStatus
    )

    $response = Invoke-WebRequest `
        -Uri "$baseUrl$Path" `
        -Method Get `
        -TimeoutSec 5 `
        -SkipHttpErrorCheck

    if ([int]$response.StatusCode -ne $ExpectedStatus) {
        throw "Expected $Path to return $ExpectedStatus but got $($response.StatusCode)."
    }

    Write-Host "ok: $Path -> $ExpectedStatus"
}

function Wait-ReadyzHealthy {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [int]$MaxAttempts = 20
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        if ($Process.HasExited) {
            throw "sl-daemon exited before /readyz became healthy (exit code $($Process.ExitCode))."
        }

        try {
            $response = Invoke-WebRequest `
                -Uri "$baseUrl/readyz" `
                -Method Get `
                -TimeoutSec 2 `
                -SkipHttpErrorCheck
            if ([int]$response.StatusCode -eq 200) {
                Write-Host "ok: /readyz healthy after $attempt attempt(s)"
                return
            }
        }
        catch {
            Write-Host "readyz attempt $attempt of $MaxAttempts failed: $($_.Exception.Message)"
        }

        Start-Sleep -Seconds 1
    }

    throw "sl-daemon did not become ready within $MaxAttempts seconds."
}

function Assert-MetricsShape {
    $prometheus = Invoke-WebRequest -Uri "$baseUrl/metrics" -Method Get -TimeoutSec 5
    if ($prometheus.Content -notmatch "sl_http_requests_total") {
        throw "/metrics did not expose sl_http_requests_total."
    }
    if ($prometheus.Content -notmatch "sl_http_request_duration_seconds") {
        throw "/metrics did not expose sl_http_request_duration_seconds."
    }
    Write-Host "ok: /metrics exposes RED counters"

    $bundleMetrics = Invoke-WebRequest -Uri "$baseUrl/api/metrics" -Method Get -TimeoutSec 5
    $json = $bundleMetrics.Content | ConvertFrom-Json
    foreach ($field in @("total_bundles", "total_tokens", "avg_tokens")) {
        if ($null -eq $json.PSObject.Properties[$field]) {
            throw "/api/metrics JSON is missing '$field'."
        }
    }
    Write-Host "ok: /api/metrics JSON shape"
}

$overallOutcome = "pass"

try {
    Remove-PathForce -Path $watchDir
    Remove-PathForce -Path $outDir
    Remove-PathForce -Path $dataDir

    New-Item -ItemType Directory -Force -Path $watchDir, $dataDir | Out-Null
    $env:SL_DATA_DIR = $dataDir

    Write-Host "Phase 1: readiness fault — --out is a file (not a directory)"
    New-Item -ItemType File -Force -Path $outDir | Out-Null

    $daemonProc = Start-SlDaemon -Watch $watchDir -Out $outDir
    Start-Sleep -Seconds 2
    if ($daemonProc.HasExited) {
        throw "sl-daemon exited during readiness fault phase (exit code $($daemonProc.ExitCode))."
    }
    Invoke-StatusProbe -Path "/healthz" -ExpectedStatus 200
    Invoke-StatusProbe -Path "/readyz" -ExpectedStatus 503
    Add-EvidenceStep -Name "readiness_fault" -Outcome "pass" -Detail "/healthz=200 /readyz=503"

    Write-Host "Phase 2: recover readiness"
    Stop-SlDaemon -Process $daemonProc
    $daemonProc = $null
    Remove-PathForce -Path $outDir
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $daemonProc = Start-SlDaemon -Watch $watchDir -Out $outDir
    Wait-ReadyzHealthy -Process $daemonProc
    Assert-MetricsShape
    Add-EvidenceStep -Name "readiness_recovery" -Outcome "pass"
    $prometheusBody = (Invoke-WebRequest -Uri "$baseUrl/metrics" -Method Get -TimeoutSec 5).Content
    $script:RedMetricSeries = Get-RedMetricSeries -MetricsBody $prometheusBody
    Add-EvidenceStep -Name "red_metrics_shape" -Outcome "pass" -Detail ($script:RedMetricSeries | ConvertTo-Json -Compress)

    Write-Host "Phase 3: light load burst"
    & $loadSmokeScript `
        -BaseUrl $baseUrl `
        -Requests $LoadRequests `
        -Concurrency $LoadConcurrency `
        -MinSuccessRate 99 `
        -MaxP95Ms 500
    Add-EvidenceStep -Name "load_burst" -Outcome "pass" -Detail "requests=$LoadRequests concurrency=$LoadConcurrency"

    Write-Host "Phase 4: process-kill recovery"
    Stop-SlDaemon -Process $daemonProc
    $daemonProc = $null
    Start-Sleep -Seconds 1

    $daemonProc = Start-SlDaemon -Watch $watchDir -Out $outDir
    Wait-ReadyzHealthy -Process $daemonProc
    Invoke-StatusProbe -Path "/healthz" -ExpectedStatus 200
    Add-EvidenceStep -Name "process_kill_recovery" -Outcome "pass"

    Write-Host "Phase 5: post-recovery mini load"
    & $loadSmokeScript `
        -BaseUrl $baseUrl `
        -Requests $RecoveryRequests `
        -Concurrency 4 `
        -MinSuccessRate 99 `
        -MaxP95Ms 500
    Add-EvidenceStep -Name "post_recovery_load" -Outcome "pass" -Detail "requests=$RecoveryRequests"

    Write-Host "Ops chaos smoke passed."
}
catch {
    $overallOutcome = "fail"
    Add-EvidenceStep -Name "chaos_smoke" -Outcome "fail" -Detail $_.Exception.Message
    throw
}
finally {
    if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
        Write-GameDayEvidence `
            -Path $EvidencePath `
            -Outcome $overallOutcome `
            -HttpBind $HttpBind `
            -LoadRequests $LoadRequests `
            -LoadConcurrency $LoadConcurrency `
            -RecoveryRequests $RecoveryRequests
    }
    Stop-SlDaemon -Process $daemonProc
    if ($null -eq $previousDataDir) {
        Remove-Item Env:SL_DATA_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:SL_DATA_DIR = $previousDataDir
    }
    Remove-PathForce -Path $watchDir
    Remove-PathForce -Path $outDir
    Remove-PathForce -Path $dataDir
}
