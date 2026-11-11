<#
.SYNOPSIS
RSS / working-set budget smoke for sl-daemon POST /api/ingest.

.DESCRIPTION
Starts a local sl-daemon (or attaches to an already-running one), drives a small
ingest burst, samples process RSS / working-set, and fails only when the peak
exceeds the documented ceiling in docs/ops/memory-budget.json (or an explicit
-CeilingBytes override) or when RSS sampling itself fails unexpectedly.

Hermetic and intended to finish in well under two minutes once the daemon binary
exists. Use -SelfCheck to validate args + ceiling config without starting a
daemon (CI unit/integration proof).
#>
[CmdletBinding()]
param(
    [string]$DaemonPath = "",

    [string]$BaseUrl = "",

    [string]$HttpBind = "",

    [string]$BudgetConfig = "",

    [ValidateRange(0, 9223372036854775807)]
    [long]$CeilingBytes = 0,

    [ValidateRange(1, 256)]
    [int]$IngestCount = 8,

    [string]$WorkRoot = $env:RUNNER_TEMP,

    [switch]$AttachOnly,

    [switch]$SelfCheck,

    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot

if ([string]::IsNullOrWhiteSpace($BudgetConfig)) {
    $BudgetConfig = Join-Path $repoRoot "docs/ops/memory-budget.json"
}

function Get-BudgetCeilingBytes {
    param(
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [long]$OverrideBytes
    )

    if ($OverrideBytes -gt 0) {
        return $OverrideBytes
    }

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Memory budget config not found at '$ConfigPath'."
    }

    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($null -eq $config.ingest_rss_ceiling_bytes) {
        throw "Budget config '$ConfigPath' is missing ingest_rss_ceiling_bytes."
    }

    $ceiling = [long]$config.ingest_rss_ceiling_bytes
    if ($ceiling -le 0) {
        throw "ingest_rss_ceiling_bytes must be a positive integer (got $ceiling)."
    }

    return $ceiling
}

function Get-ProcessRssBytes {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    $proc = Get-Process -Id $ProcessId -ErrorAction Stop

    # WorkingSet64 is available on Windows and Linux under PowerShell 7.
    # On Linux it maps to resident set; on Windows it is the working set.
    $rss = [long]$proc.WorkingSet64
    if ($rss -le 0) {
        throw "RSS sample for PID $ProcessId returned non-positive WorkingSet64 ($rss)."
    }

    # Prefer /proc VmRSS on Linux when present (more explicit RSS wording).
    $statusPath = "/proc/$ProcessId/status"
    if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
        $line = Select-String -Path $statusPath -Pattern '^VmRSS:\s+(\d+)\s+kB' | Select-Object -First 1
        if ($null -eq $line) {
            throw "Found $statusPath but could not parse VmRSS for PID $ProcessId."
        }
        $kb = [long]$line.Matches[0].Groups[1].Value
        if ($kb -le 0) {
            throw "VmRSS for PID $ProcessId was non-positive ($kb kB)."
        }
        return ($kb * 1024)
    }

    return $rss
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

    if (-not $env:CARGO_TARGET_DIR) {
        $env:CARGO_TARGET_DIR = Join-Path $repoRoot "target-w23-c00-rss"
        Write-Host "Using worktree-local CARGO_TARGET_DIR=$($env:CARGO_TARGET_DIR)"
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

function Invoke-IngestBurst {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][int]$Count
    )

    $accepted = 0
    for ($i = 0; $i -lt $Count; $i++) {
        $body = @"
{
  "bundle_id": "rss-budget-$i",
  "created_at": "2026-07-13T21:40:00Z",
  "messages": [{"role": "user", "content": "rss budget smoke $i"}],
  "token_count": 1
}
"@
        $response = Invoke-WebRequest `
            -Uri "$Url/api/ingest" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 10 `
            -SkipHttpErrorCheck

        $status = [int]$response.StatusCode
        if ($status -lt 200 -or $status -ge 300) {
            throw "POST /api/ingest returned $status for burst index $i."
        }
        $accepted++
    }

    Write-Host "ok: accepted $accepted/$Count ingest posts"
}

# --- Self-check (no daemon) -------------------------------------------------

$ceiling = Get-BudgetCeilingBytes -ConfigPath $BudgetConfig -OverrideBytes $CeilingBytes
Write-Host ("Ceiling: {0:N0} bytes ({1:N1} MiB) from {2}" -f `
    $ceiling, ($ceiling / 1MB), $BudgetConfig)

if ($SelfCheck) {
    if ($CeilingBytes -lt 0) {
        throw "CeilingBytes must be >= 0."
    }
    if ($IngestCount -lt 1) {
        throw "IngestCount must be >= 1."
    }
    Write-Host "Self-check passed: budget config parses and ceiling is positive."
    exit 0
}

# --- Live smoke --------------------------------------------------------------

if ([string]::IsNullOrWhiteSpace($WorkRoot)) {
    $WorkRoot = [System.IO.Path]::GetTempPath()
}

$daemonProc = $null
$startedByUs = $false
$peakRss = [long]0

try {
    if ($AttachOnly) {
        if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
            throw "-AttachOnly requires -BaseUrl pointing at a running daemon."
        }
        $normalizedBaseUrl = $BaseUrl.TrimEnd("/")
        Wait-ReadyzHealthy -Url $normalizedBaseUrl

        # Best-effort: locate a running sl-daemon for RSS sampling.
        $candidates = @(Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -match '^(sl-daemon|sl_daemon)$' })
        if ($candidates.Count -eq 0) {
            throw "AttachOnly: could not find a running sl-daemon process to sample RSS."
        }
        $daemonProc = $candidates[0]
        Write-Host "Attached to PID $($daemonProc.Id) at $normalizedBaseUrl"
    }
    else {
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
        $watchDir = Join-Path $WorkRoot "sl-rss-$runId-watch"
        $outDir = Join-Path $WorkRoot "sl-rss-$runId-out"
        New-Item -ItemType Directory -Force -Path $watchDir, $outDir | Out-Null

        $daemonArgs = @(
            "serve",
            "--watch", $watchDir,
            "--out", $outDir,
            "--http-bind", $HttpBind
        )

        Write-Host "Starting $resolvedDaemon on $HttpBind"
        $daemonProc = Start-Process -FilePath $resolvedDaemon -ArgumentList $daemonArgs -NoNewWindow -PassThru
        $startedByUs = $true
        Wait-ReadyzHealthy -Url $normalizedBaseUrl -Process $daemonProc
    }

    $before = Get-ProcessRssBytes -ProcessId $daemonProc.Id
    Write-Host ("RSS before ingest: {0:N0} bytes ({1:N1} MiB)" -f $before, ($before / 1MB))
    $peakRss = $before

    Invoke-IngestBurst -Url $normalizedBaseUrl -Count $IngestCount

    # Sample a few times after ingest; keep the peak.
    for ($sample = 0; $sample -lt 5; $sample++) {
        $rss = Get-ProcessRssBytes -ProcessId $daemonProc.Id
        if ($rss -gt $peakRss) {
            $peakRss = $rss
        }
        Start-Sleep -Milliseconds 200
    }

    Write-Host ("RSS peak after ingest: {0:N0} bytes ({1:N1} MiB)" -f $peakRss, ($peakRss / 1MB))
    Write-Host ("Budget ceiling: {0:N0} bytes ({1:N1} MiB)" -f $ceiling, ($ceiling / 1MB))

    if ($peakRss -gt $ceiling) {
        Write-Error ("RSS budget failed: peak {0:N0} exceeds ceiling {1:N0}." -f $peakRss, $ceiling)
        exit 1
    }

    Write-Host "RSS budget smoke passed."
}
finally {
    if ($startedByUs -and $null -ne $daemonProc -and -not $daemonProc.HasExited) {
        Stop-Process -Id $daemonProc.Id -Force -ErrorAction SilentlyContinue
        $daemonProc.WaitForExit(5000) | Out-Null
    }
}
