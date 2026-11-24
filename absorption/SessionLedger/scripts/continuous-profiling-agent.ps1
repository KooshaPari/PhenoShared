<#
.SYNOPSIS
Soft continuous-profiling agent stub for sl-daemon (L45 evidence).

.DESCRIPTION
Documents and exercises a one-shot agent loop against the gated loopback pprof
surface (Wave-27 #232). Retains a local CPU protobuf sample on unix. Optional
soft HTTP push (`push_backend: http_soft`) posts the retained sample only when
SL_PROFILE_PUSH_URL is set; -DryRun logs intent without network.

Modes:
  - -SelfCheck: validate agent config + doc anchors (no daemon, no network).
  - -RunOnce: start a local daemon on unix, sample once, write under samples/.
  - -AttachOnly: probe a running daemon; skip when SL_ENABLE_PPROF is off.

Windows hosts exit 0 with an explicit skip — Windows CPU pprof is not required.
#>
[CmdletBinding()]
param(
    [string]$AgentConfig = "",

    [string]$DaemonPath = "",

    [string]$BaseUrl = "",

    [string]$SamplesDir = "",

    [string]$WorkRoot = $env:RUNNER_TEMP,

    [string]$PushUrl = "",

    [switch]$SelfCheck,

    [switch]$RunOnce,

    [switch]$AttachOnly,

    [switch]$SkipBuild,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot

if ([string]::IsNullOrWhiteSpace($AgentConfig)) {
    $AgentConfig = Join-Path $repoRoot "docs/ops/continuous-profiling.json"
}

$pprofSmoke = Join-Path $scriptRoot "pprof-smoke.ps1"
$agentDoc = Join-Path $repoRoot "docs/ops/continuous-profiling.md"

function Test-IsWindowsHost {
    return ($IsWindows -eq $true) -or ($env:OS -eq "Windows_NT")
}

function Get-ResolvedPushUrl {
    param([string]$Override)

    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        return $Override.Trim()
    }
    if (-not [string]::IsNullOrWhiteSpace($env:SL_PROFILE_PUSH_URL)) {
        return $env:SL_PROFILE_PUSH_URL.Trim()
    }
    return ""
}

function Get-AgentConfig {
    param([Parameter(Mandatory = $true)][string]$ConfigPath)

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Agent config not found at '$ConfigPath'."
    }

    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($null -eq $config.schema -or $config.schema -ne "sessionledger.continuous-profiling.v1") {
        throw "Agent config '$ConfigPath' must declare schema sessionledger.continuous-profiling.v1."
    }
    if ($null -eq $config.sample_seconds -or [int]$config.sample_seconds -lt 1) {
        throw "Agent config '$ConfigPath' must set sample_seconds >= 1."
    }

    $backend = [string]$config.push_backend
    $allowed = @("none", "http_soft")
    if ([string]::IsNullOrWhiteSpace($backend) -or ($allowed -notcontains $backend)) {
        throw "Agent config '$ConfigPath' push_backend must be one of: none, http_soft (got '$backend')."
    }

    return [pscustomobject]@{
        SampleSeconds       = [int]$config.sample_seconds
        PollIntervalSeconds = [int]$config.poll_interval_seconds
        RetainSamples       = [int]$config.retain_samples
        PushBackend         = $backend
        ConfigPath          = $ConfigPath
    }
}

function Save-AgentSample {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][byte[]]$Bytes,
        [Parameter(Mandatory = $true)][int]$SampleSeconds
    )

    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $outPath = Join-Path $Directory "cpu-$stamp-${SampleSeconds}s.pb"
    [System.IO.File]::WriteAllBytes($outPath, $Bytes)
    if ($Bytes.Length -le 0) {
        throw "Agent sample at '$outPath' is empty."
    }
    Write-Host "ok: retained agent sample -> $outPath ($($Bytes.Length) bytes)"
    return $outPath
}

function Invoke-SoftHttpProfilePush {
    param(
        [Parameter(Mandatory = $true)][string]$Backend,
        [Parameter(Mandatory = $true)][string]$SamplePath,
        [Parameter(Mandatory = $true)][byte[]]$Bytes,
        [string]$Url,
        [switch]$DryRunMode
    )

    if ($Backend -eq "none") {
        Write-Host "skip: push_backend=none (local retain only)."
        return
    }

    if ($Backend -ne "http_soft") {
        throw "Unsupported push_backend '$Backend'."
    }

    if ([string]::IsNullOrWhiteSpace($Url)) {
        Write-Host "skip: http_soft push (SL_PROFILE_PUSH_URL unset; local retain only)."
        return
    }

    if ($DryRunMode) {
        Write-Host "dry-run: would soft-POST $($Bytes.Length) bytes from '$SamplePath' to $Url (no network)."
        return
    }

    try {
        Write-Host "soft-push: POSTing $($Bytes.Length) bytes to $Url ..."
        $response = Invoke-WebRequest `
            -Uri $Url `
            -Method Post `
            -ContentType "application/octet-stream" `
            -Body $Bytes `
            -TimeoutSec 15 `
            -SkipHttpErrorCheck
        $code = [int]$response.StatusCode
        if ($code -ge 200 -and $code -lt 300) {
            Write-Host "ok: soft HTTP profile push succeeded (HTTP $code)."
        }
        else {
            Write-Host "warn: soft HTTP profile push returned HTTP $code (continue-on-error; local sample retained)."
        }
    }
    catch {
        Write-Host "warn: soft HTTP profile push failed: $($_.Exception.Message) (continue-on-error; local sample retained)."
    }
}

function Assert-AgentDocAnchors {
    if (-not (Test-Path -LiteralPath $agentDoc -PathType Leaf)) {
        throw "Missing agent doc at '$agentDoc'."
    }
    if (-not (Test-Path -LiteralPath $pprofSmoke -PathType Leaf)) {
        throw "Missing pprof smoke script at '$pprofSmoke'."
    }

    $docText = Get-Content -LiteralPath $agentDoc -Raw
    foreach ($anchor in @(
            "#232",
            "push_backend",
            "http_soft",
            "SL_PROFILE_PUSH_URL",
            "DryRun",
            "continue-on-error",
            "unpaid",
            "pprof-smoke.ps1"
        )) {
        if ($docText -notmatch [regex]::Escape($anchor)) {
            throw "continuous-profiling.md missing anchor '$anchor'."
        }
    }
}

$config = Get-AgentConfig -ConfigPath $AgentConfig
$resolvedPushUrl = Get-ResolvedPushUrl -Override $PushUrl

if ($SelfCheck) {
    Assert-AgentDocAnchors
    Write-Host "ok: agent config schema $($config.ConfigPath)"
    Write-Host "ok: sample_seconds=$($config.SampleSeconds) poll_interval_seconds=$($config.PollIntervalSeconds) retain_samples=$($config.RetainSamples)"
    Write-Host "ok: push_backend=$($config.PushBackend) (http_soft uses SL_PROFILE_PUSH_URL; unset/DryRun skips network)"
    if ($DryRun) {
        Write-Host "ok: -DryRun acknowledged (SelfCheck remains hermetic; no sockets)."
    }
    Write-Host "Self-check passed: continuous profiling agent stub is coherent."
    exit 0
}

if ($AttachOnly) {
    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        throw "-AttachOnly requires -BaseUrl pointing at a running daemon."
    }

    & $pprofSmoke -AttachOnly -BaseUrl $BaseUrl
    exit $LASTEXITCODE
}

if (-not $RunOnce) {
    throw "Specify -SelfCheck, -RunOnce, or -AttachOnly."
}

if (Test-IsWindowsHost) {
    Write-Host "skip: continuous profiling agent cycle is unix-only (Windows pprof not required)."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($SamplesDir)) {
    if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
        $WorkRoot = [System.IO.Path]::GetTempPath()
    }
    $SamplesDir = Join-Path $WorkRoot "sl-continuous-profiling-samples"
}

if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
    $WorkRoot = [System.IO.Path]::GetTempPath()
}

if (-not $SkipBuild) {
    Push-Location (Join-Path $repoRoot "crates/sl-daemon")
    try {
        cargo build --locked
    }
    finally {
        Pop-Location
    }
}

$metadata = cargo metadata `
    --format-version 1 `
    --no-deps `
    --manifest-path (Join-Path $repoRoot "crates/sl-daemon/Cargo.toml") |
    ConvertFrom-Json
$daemon = if ([string]::IsNullOrWhiteSpace($DaemonPath)) {
    Join-Path $metadata.target_directory "debug/sl-daemon"
} else {
    $DaemonPath
}

if (-not (Test-Path -LiteralPath $daemon -PathType Leaf)) {
    throw "sl-daemon binary not found at '$daemon'."
}

$runId = [Guid]::NewGuid().ToString("n")
$watchDir = Join-Path $WorkRoot "sl-cp-$runId-watch"
$outDir = Join-Path $WorkRoot "sl-cp-$runId-out"
New-Item -ItemType Directory -Force -Path $watchDir, $outDir | Out-Null

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ($listener.LocalEndpoint).Port
$listener.Stop()
$bind = "127.0.0.1:$port"
$url = "http://$bind"

$previous = $env:SL_ENABLE_PPROF
$proc = $null
try {
    $env:SL_ENABLE_PPROF = "1"
    $args = @(
        "serve",
        "--watch", $watchDir,
        "--out", $outDir,
        "--http-bind", $bind
    )
    $proc = Start-Process -FilePath $daemon -ArgumentList $args -NoNewWindow -PassThru

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        if ($proc.HasExited) {
            throw "sl-daemon exited before /readyz became healthy (exit code $($proc.ExitCode))."
        }
        try {
            $readyz = Invoke-WebRequest -Uri "$url/readyz" -Method Get -TimeoutSec 2 -SkipHttpErrorCheck
            if ([int]$readyz.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            Write-Host "readyz attempt $attempt/30 failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "sl-daemon did not become ready within 30 seconds."
    }

    & $pprofSmoke -AttachOnly -BaseUrl $url
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $seconds = $config.SampleSeconds
    $tmpSample = Join-Path $WorkRoot "sl-cp-$runId-sample.pb"
    Invoke-WebRequest `
        -Uri "$url/debug/pprof/profile?seconds=$seconds" `
        -Method Get `
        -TimeoutSec ([Math]::Max(20, $seconds + 10)) `
        -OutFile $tmpSample
    $sampleBytes = [System.IO.File]::ReadAllBytes($tmpSample)
    $savedPath = Save-AgentSample -Directory $SamplesDir -Bytes $sampleBytes -SampleSeconds $seconds
    Remove-Item -LiteralPath $tmpSample -Force -ErrorAction SilentlyContinue

    Invoke-SoftHttpProfilePush `
        -Backend $config.PushBackend `
        -SamplePath $savedPath `
        -Bytes $sampleBytes `
        -Url $resolvedPushUrl `
        -DryRunMode:$DryRun

    Write-Host "continuous profiling agent stub cycle complete (push_backend=$($config.PushBackend))."
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
        $proc.WaitForExit(5000) | Out-Null
    }
    if ($null -eq $previous) {
        Remove-Item Env:SL_ENABLE_PPROF -ErrorAction SilentlyContinue
    }
    else {
        $env:SL_ENABLE_PPROF = $previous
    }
}

exit 0
