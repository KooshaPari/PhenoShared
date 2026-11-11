<#
.SYNOPSIS
Smoke-test the loopback pprof debug surface on sl-daemon.

.DESCRIPTION
Operator contract (see docs/ops/observability.md):
  - Routes exist only when SL_ENABLE_PPROF=1 (exact trim).
  - GET /debug/pprof/cmdline -> 200 octet-stream (null-delimited argv).
  - GET /debug/pprof/profile?seconds=1 -> 200 octet-stream CPU protobuf on unix;
    501 text on Windows (SIGPROF sampler is unix-only).
  - Without the gate, both paths return 404.

Modes:
  - Default: start a local daemon with SL_ENABLE_PPROF=1 and assert the contract.
  - -AttachOnly: probe an already-running daemon; if the surface is off (404),
    exit 0 with an explicit skip (feature off is not a failure).
  - -SelfCheck: validate args without starting a daemon.
#>
[CmdletBinding()]
param(
    [string]$DaemonPath = "",

    [string]$BaseUrl = "",

    [string]$HttpBind = "",

    [string]$WorkRoot = $env:RUNNER_TEMP,

    [switch]$AttachOnly,

    [switch]$SelfCheck,

    [switch]$SkipBuild,

    # When starting a daemon, also assert the off-by-default 404 path.
    [switch]$AlsoAssertDisabled
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot

function Test-IsWindowsHost {
    return ($IsWindows -eq $true) -or ($env:OS -eq "Windows_NT")
}

function Resolve-DaemonPath {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (-not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw "Daemon binary not found at '$ExplicitPath'."
        }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }

    $desiredTarget = Join-Path $repoRoot "target-w27-c05"
    if (
        [string]::IsNullOrWhiteSpace($env:CARGO_TARGET_DIR) -or
        -not $env:CARGO_TARGET_DIR.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        $env:CARGO_TARGET_DIR = $desiredTarget
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
    }

    $manifest = Join-Path $repoRoot "crates/sl-daemon/Cargo.toml"
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
    if (Test-IsWindowsHost) {
        $candidate = "$candidate.exe"
    }

    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Built daemon not found at '$candidate'. Pass -DaemonPath or build first."
    }

    return (Resolve-Path -LiteralPath $candidate).Path
}

function Wait-ReadyzHealthy {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [System.Diagnostics.Process]$Process = $null,
        [int]$MaxAttempts = 30
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        if ($null -ne $Process -and $Process.HasExited) {
            throw "sl-daemon exited before /readyz became healthy (exit code $($Process.ExitCode))."
        }

        try {
            $response = Invoke-WebRequest `
                -Uri "$Url/readyz" `
                -Method Get `
                -TimeoutSec 2 `
                -SkipHttpErrorCheck
            if ([int]$response.StatusCode -eq 200) {
                Write-Host "ok: /readyz healthy after $attempt attempt(s)"
                return
            }
        }
        catch {
            Write-Host "readyz attempt $attempt/$MaxAttempts failed: $($_.Exception.Message)"
        }

        Start-Sleep -Seconds 1
    }

    throw "sl-daemon did not become ready within $MaxAttempts seconds at $Url."
}

function Invoke-PprofProbe {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSec = 5
    )

    return Invoke-WebRequest `
        -Uri "$Url$Path" `
        -Method Get `
        -TimeoutSec $TimeoutSec `
        -SkipHttpErrorCheck
}

function Assert-PprofEnabledContract {
    param([Parameter(Mandatory = $true)][string]$Url)

    $cmdline = Invoke-PprofProbe -Url $Url -Path "/debug/pprof/cmdline"
    if ([int]$cmdline.StatusCode -ne 200) {
        throw "Expected /debug/pprof/cmdline -> 200, got $($cmdline.StatusCode)."
    }
    $cmdlineLen = 0
    if ($null -ne $cmdline.RawContentLength) {
        $cmdlineLen = [int]$cmdline.RawContentLength
    }
    elseif ($null -ne $cmdline.Content) {
        $cmdlineLen = ([string]$cmdline.Content).Length
    }
    if ($cmdlineLen -lt 1) {
        throw "/debug/pprof/cmdline returned an empty body."
    }
    Write-Host "ok: /debug/pprof/cmdline -> 200 ($cmdlineLen bytes)"

    # Default sample window is 1s; allow headroom beyond the sleep.
    $profile = Invoke-PprofProbe -Url $Url -Path "/debug/pprof/profile?seconds=1" -TimeoutSec 20
    $profileStatus = [int]$profile.StatusCode
    $profileLen = 0
    if ($null -ne $profile.RawContentLength) {
        $profileLen = [int]$profile.RawContentLength
    }
    elseif ($null -ne $profile.Content) {
        if ($profile.Content -is [byte[]]) {
            $profileLen = $profile.Content.Length
        }
        else {
            $profileLen = ([string]$profile.Content).Length
        }
    }

    if (Test-IsWindowsHost) {
        if ($profileStatus -ne 501) {
            throw "Expected /debug/pprof/profile -> 501 on Windows (unix sampler), got $profileStatus."
        }
        $profileText = [string]$profile.Content
        if ($profileText -notmatch "not supported|unix|platform") {
            throw "/debug/pprof/profile Windows stub body missing platform explanation."
        }
        Write-Host "ok: /debug/pprof/profile -> 501 (Windows: unix-only sampler)"
    }
    else {
        if ($profileStatus -eq 501) {
            throw "Expected /debug/pprof/profile -> non-501 CPU protobuf when enabled, got 501 stub."
        }
        if ($profileStatus -ne 200) {
            throw "Expected /debug/pprof/profile -> 200, got $profileStatus."
        }
        if ($profileLen -lt 1) {
            throw "/debug/pprof/profile returned an empty body."
        }
        Write-Host "ok: /debug/pprof/profile -> 200 ($profileLen bytes CPU protobuf)"
    }
}

function Assert-PprofDisabled {
    param([Parameter(Mandatory = $true)][string]$Url)

    foreach ($path in @("/debug/pprof/cmdline", "/debug/pprof/profile")) {
        $response = Invoke-PprofProbe -Url $Url -Path $path
        if ([int]$response.StatusCode -ne 404) {
            throw "Expected $path -> 404 when pprof disabled, got $($response.StatusCode)."
        }
        Write-Host "ok: $path -> 404 (disabled)"
    }
}

function Start-SlDaemonServe {
    param(
        [Parameter(Mandatory = $true)][string]$Daemon,
        [Parameter(Mandatory = $true)][string]$Bind,
        [Parameter(Mandatory = $true)][string]$Watch,
        [Parameter(Mandatory = $true)][string]$Out,
        [bool]$EnablePprof
    )

    $previous = $env:SL_ENABLE_PPROF
    try {
        if ($EnablePprof) {
            $env:SL_ENABLE_PPROF = "1"
        }
        elseif ($null -ne $env:SL_ENABLE_PPROF) {
            Remove-Item Env:SL_ENABLE_PPROF -ErrorAction SilentlyContinue
        }

        $daemonArgs = @(
            "serve",
            "--watch", $Watch,
            "--out", $Out,
            "--http-bind", $Bind
        )
        Write-Host ("Starting {0} on {1} (SL_ENABLE_PPROF={2})" -f `
            $Daemon, $Bind, $(if ($EnablePprof) { "1" } else { "<unset>" }))
        return Start-Process -FilePath $Daemon -ArgumentList $daemonArgs -NoNewWindow -PassThru
    }
    finally {
        if ($null -eq $previous) {
            Remove-Item Env:SL_ENABLE_PPROF -ErrorAction SilentlyContinue
        }
        else {
            $env:SL_ENABLE_PPROF = $previous
        }
    }
}

function Stop-SlDaemon {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $Process.WaitForExit(5000) | Out-Null
    }
}

# --- Self-check --------------------------------------------------------------

if ($SelfCheck) {
    if ($AttachOnly -and [string]::IsNullOrWhiteSpace($BaseUrl)) {
        throw "-AttachOnly requires -BaseUrl (self-check of attach mode args)."
    }
    Write-Host "Self-check passed: pprof smoke args and operator contract are coherent."
    Write-Host "Contract: SL_ENABLE_PPROF=1 registers /debug/pprof/{cmdline,profile}; else 404."
    Write-Host "Contract: enabled profile returns 200 protobuf on unix (non-501); 501 on Windows."
    exit 0
}

# --- Attach-only: hit or skip ------------------------------------------------

if ($AttachOnly) {
    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        throw "-AttachOnly requires -BaseUrl pointing at a running daemon."
    }
    $normalizedBaseUrl = $BaseUrl.TrimEnd("/")
    Wait-ReadyzHealthy -Url $normalizedBaseUrl

    $probe = Invoke-PprofProbe -Url $normalizedBaseUrl -Path "/debug/pprof/profile?seconds=1" -TimeoutSec 20
    $status = [int]$probe.StatusCode
    if ($status -eq 404) {
        Write-Host "skip: pprof surface disabled (set SL_ENABLE_PPROF=1 to enable)."
        exit 0
    }

    Assert-PprofEnabledContract -Url $normalizedBaseUrl
    Write-Host "pprof attach smoke passed."
    exit 0
}

# --- Start daemon and assert enabled contract --------------------------------

if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
    $WorkRoot = [System.IO.Path]::GetTempPath()
}

$resolvedDaemon = Resolve-DaemonPath -ExplicitPath $DaemonPath

if ([string]::IsNullOrWhiteSpace($HttpBind)) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ($listener.LocalEndpoint).Port
    $listener.Stop()
    $HttpBind = "127.0.0.1:$port"
}

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://$HttpBind"
}
$normalizedBaseUrl = $BaseUrl.TrimEnd("/")

$runId = [Guid]::NewGuid().ToString("n")
$watchDir = Join-Path $WorkRoot "sl-pprof-$runId-watch"
$outDir = Join-Path $WorkRoot "sl-pprof-$runId-out"
New-Item -ItemType Directory -Force -Path $watchDir, $outDir | Out-Null

$daemonProc = $null
try {
    $daemonProc = Start-SlDaemonServe `
        -Daemon $resolvedDaemon `
        -Bind $HttpBind `
        -Watch $watchDir `
        -Out $outDir `
        -EnablePprof $true
    Wait-ReadyzHealthy -Url $normalizedBaseUrl -Process $daemonProc
    Assert-PprofEnabledContract -Url $normalizedBaseUrl
    Write-Host "pprof enabled smoke passed."
}
finally {
    Stop-SlDaemon -Process $daemonProc
    $daemonProc = $null
}

if ($AlsoAssertDisabled) {
    # Fresh bind so the prior listener is fully released.
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ($listener.LocalEndpoint).Port
    $listener.Stop()
    $HttpBindOff = "127.0.0.1:$port"
    $urlOff = "http://$HttpBindOff"
    $watchOff = Join-Path $WorkRoot "sl-pprof-$runId-watch-off"
    $outOff = Join-Path $WorkRoot "sl-pprof-$runId-out-off"
    New-Item -ItemType Directory -Force -Path $watchOff, $outOff | Out-Null

    try {
        $daemonProc = Start-SlDaemonServe `
            -Daemon $resolvedDaemon `
            -Bind $HttpBindOff `
            -Watch $watchOff `
            -Out $outOff `
            -EnablePprof $false
        Wait-ReadyzHealthy -Url $urlOff -Process $daemonProc
        Assert-PprofDisabled -Url $urlOff
        Write-Host "pprof disabled (404) smoke passed."
    }
    finally {
        Stop-SlDaemon -Process $daemonProc
    }
}

Write-Host "pprof smoke complete."
