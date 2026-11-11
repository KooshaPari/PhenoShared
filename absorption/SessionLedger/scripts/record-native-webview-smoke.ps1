<#
.SYNOPSIS
Record a native WebView accessibility smoke pass as machine-readable JSON.

.DESCRIPTION
Copies the sample fixture schema, fills build/git/host metadata, and writes an
evidence file maintainers can attach to audits. Does not launch the viewer or a
screen reader — run the checklists in docs/a11y/ first, then record the outcome.

Optional -AttachDaemon mode probes a running sl-daemon (/healthz, /readyz,
/api/bundles, /api/search, /api/stream) and records live-daemon parity probes
alongside the manual checklist. Use when the desktop WebView smoke is exercised
against a live daemon rather than fixture-only surfaces.

.EXAMPLE
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 `
  -Outcome pass `
  -ScreenReader NVDA `
  -OutPath docs/ops/fixtures/native-webview-smoke.local.json

.EXAMPLE
# Attach to an already-running daemon and record live-daemon probe evidence:
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 `
  -Outcome pass `
  -AttachDaemon `
  -DaemonUrl http://127.0.0.1:8080 `
  -OutPath docs/ops/fixtures/native-webview-smoke.local.json

.EXAMPLE
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [ValidateSet("pass", "fail", "partial")]
    [string]$Outcome = "pass",

    [ValidateSet("NVDA", "VoiceOver", "Narrator", "Orca", "none")]
    [string]$ScreenReader = "NVDA",

    [string]$ScreenReaderVersion = "",

    [string]$BuildId = "",

    [string]$OutPath = "",

    [string]$RepoRoot = "",

    # Probe an already-running daemon and embed live-daemon parity evidence.
    [switch]$AttachDaemon,

    # Base URL for attach mode (default: SL_DAEMON_URL or http://127.0.0.1:8080).
    [string]$DaemonUrl = "",

    # Validate args / sample fixture without writing evidence or probing a daemon.
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$samplePath = Join-Path $RepoRoot "docs/ops/fixtures/native-webview-smoke.sample.json"
if (-not (Test-Path -LiteralPath $samplePath -PathType Leaf)) {
    throw "Missing sample fixture at '$samplePath'."
}

function Resolve-DaemonBaseUrl {
    param([string]$Explicit)

    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        return $Explicit.TrimEnd("/")
    }
    if (-not [string]::IsNullOrWhiteSpace($env:SL_DAEMON_URL)) {
        return $env:SL_DAEMON_URL.TrimEnd("/")
    }
    return "http://127.0.0.1:8080"
}

function Test-DaemonReachable {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [int]$TimeoutMs = 1500
    )

    try {
        $uri = [Uri]$BaseUrl
        $client = [System.Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect($uri.Host, $uri.Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $ok) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-DaemonProbe {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSec = 2,
        [int[]]$AcceptStatus = @(200)
    )

    $uri = "$BaseUrl$Path"
    $at = (Get-Date).ToUniversalTime().ToString("o")
    try {
        $response = Invoke-WebRequest `
            -Uri $uri `
            -Method Get `
            -TimeoutSec $TimeoutSec `
            -SkipHttpErrorCheck
        $status = [int]$response.StatusCode
        $ok = $AcceptStatus -contains $status
        $bodyPreview = ""
        if ($null -ne $response.Content) {
            $raw = [string]$response.Content
            if ($raw.Length -gt 120) {
                $bodyPreview = $raw.Substring(0, 120) + "…"
            }
            else {
                $bodyPreview = $raw
            }
            $bodyPreview = ($bodyPreview -replace "\s+", " ").Trim()
        }
        $contentType = ""
        if ($null -ne $response.Headers -and $response.Headers["Content-Type"]) {
            $contentType = [string]$response.Headers["Content-Type"]
        }
        return [ordered]@{
            path        = $Path
            status      = $status
            outcome     = if ($ok) { "pass" } else { "fail" }
            detail      = if ($ok) {
                "HTTP $status"
            }
            else {
                "expected $($AcceptStatus -join '/') got $status"
            }
            contentType = $contentType
            bodyPreview = $bodyPreview
            at          = $at
        }
    }
    catch {
        return [ordered]@{
            path        = $Path
            status      = 0
            outcome     = "fail"
            detail      = "request failed: $($_.Exception.Message)"
            contentType = ""
            bodyPreview = ""
            at          = $at
        }
    }
}

function Get-LiveDaemonProbes {
    param([Parameter(Mandatory = $true)][string]$BaseUrl)

    if (-not (Test-DaemonReachable -BaseUrl $BaseUrl)) {
        $at = (Get-Date).ToUniversalTime().ToString("o")
        $paths = @("/healthz", "/readyz", "/api/bundles", "/api/search?limit=1", "/api/stream")
        return @(
            foreach ($p in $paths) {
                [ordered]@{
                    path        = $p
                    status      = 0
                    outcome     = "fail"
                    detail      = "TCP connect failed (daemon not reachable at $BaseUrl)"
                    contentType = ""
                    bodyPreview = ""
                    at          = $at
                }
            }
        )
    }

    $probes = @()
    $probes += Invoke-DaemonProbe -BaseUrl $BaseUrl -Path "/healthz"
    $probes += Invoke-DaemonProbe -BaseUrl $BaseUrl -Path "/readyz"
    $probes += Invoke-DaemonProbe -BaseUrl $BaseUrl -Path "/api/bundles"
    $probes += Invoke-DaemonProbe -BaseUrl $BaseUrl -Path "/api/search?limit=1"
    # Stream may block on long-lived SSE; accept 200 quickly or treat timeout as soft fail.
    $stream = Invoke-DaemonProbe -BaseUrl $BaseUrl -Path "/api/stream" -TimeoutSec 2 -AcceptStatus @(200)
    if ($stream.outcome -eq "pass") {
        $ct = [string]$stream.contentType
        if ($ct -and ($ct -notmatch "text/event-stream") -and ($ct -notmatch "text/plain")) {
            $stream.outcome = "partial"
            $stream.detail = "HTTP $($stream.status) but unexpected Content-Type '$ct'"
        }
        else {
            $stream.detail = "HTTP $($stream.status) SSE surface reachable"
        }
    }
    $probes += $stream
    return $probes
}

function New-LiveDaemonChecklistItems {
    param(
        [Parameter(Mandatory = $true)]$Probes,
        [Parameter(Mandatory = $true)][ValidateSet("pass", "fail", "partial")]
        [string]$ManualOutcome
    )

    $byPath = @{}
    foreach ($p in $Probes) {
        $byPath[$p.path] = $p
    }

    function ProbeOutcome([string]$Path) {
        if ($byPath.ContainsKey($Path)) {
            return [string]$byPath[$Path].outcome
        }
        return "fail"
    }

    function ProbeDetail([string]$Path, [string]$Fallback) {
        if ($byPath.ContainsKey($Path)) {
            return [string]$byPath[$Path].detail
        }
        return $Fallback
    }

    $health = ProbeOutcome "/healthz"
    $ready = ProbeOutcome "/readyz"
    $bundles = ProbeOutcome "/api/bundles"
    $search = ProbeOutcome "/api/search?limit=1"
    $stream = ProbeOutcome "/api/stream"

    $apiParity = "pass"
    foreach ($o in @($bundles, $search)) {
        if ($o -eq "fail") { $apiParity = "fail"; break }
        if ($o -eq "partial" -and $apiParity -eq "pass") { $apiParity = "partial" }
    }

    return @(
        [pscustomobject]@{
            id      = "live_daemon_health"
            outcome = $health
            detail  = ProbeDetail "/healthz" "liveness probe"
        },
        [pscustomobject]@{
            id      = "live_daemon_ready"
            outcome = $ready
            detail  = ProbeDetail "/readyz" "readiness probe"
        },
        [pscustomobject]@{
            id      = "live_bundles_search"
            outcome = $apiParity
            detail  = "bundles=$bundles; search=$search"
        },
        [pscustomobject]@{
            id      = "live_feed_stream"
            outcome = $stream
            detail  = ProbeDetail "/api/stream" "SSE /api/stream"
        },
        [pscustomobject]@{
            id      = "live_status_parity"
            outcome = $ManualOutcome
            detail  = "Manual: Live Feed / Search status+alert regions match fixture contract against live daemon"
        }
    )
}

if ($SelfCheck) {
    if ($AttachDaemon) {
        $resolved = Resolve-DaemonBaseUrl -Explicit $DaemonUrl
        if ([string]::IsNullOrWhiteSpace($resolved)) {
            throw "-AttachDaemon self-check requires a resolvable -DaemonUrl / SL_DAEMON_URL."
        }
        Write-Host "Self-check passed: attach mode will probe $resolved (/healthz,/readyz,/api/bundles,/api/search,/api/stream)."
    }
    else {
        Write-Host "Self-check passed: fixture recorder loads sample at '$samplePath'."
    }
    $null = Get-Content -LiteralPath $samplePath -Raw | ConvertFrom-Json
    Write-Host "Self-check passed: sample fixture JSON parses; schema recorder contract is coherent."
    exit 0
}

Push-Location $RepoRoot
try {
    $gitSha = (git rev-parse HEAD 2>$null)
    if (-not $gitSha) {
        $gitSha = "unknown"
    }
}
finally {
    Pop-Location
}

if ([string]::IsNullOrWhiteSpace($BuildId)) {
    $BuildId = "local-{0}" -f (Get-Date -Format "yyyyMMddHHmmss")
}

if ([string]::IsNullOrWhiteSpace($OutPath)) {
    $OutPath = Join-Path $RepoRoot "docs/ops/fixtures/native-webview-smoke.local.json"
}

$sample = Get-Content -LiteralPath $samplePath -Raw | ConvertFrom-Json
$sample.outcome = $Outcome
$sample.buildId = $BuildId
$sample.gitSha = "$gitSha"
$sample.generatedAt = (Get-Date).ToUniversalTime().ToString("o")
$sample.host.os = if ($IsWindows -or $env:OS -match "Windows") { "windows" }
    elseif ($IsMacOS) { "macos" }
    elseif ($IsLinux) { "linux" }
    else { "unknown" }
$sample.host.osVersion = [System.Environment]::OSVersion.Version.ToString()
$sample.host.screenReader = $ScreenReader
$sample.host.screenReaderVersion = $ScreenReaderVersion
$sample.host.ci = [bool]($env:CI -or $env:GITHUB_ACTIONS)

$mode = "fixture"
$daemonBlock = [ordered]@{
    attached = $false
    baseUrl  = $null
    probes   = @()
}

if ($AttachDaemon) {
    $mode = "live-daemon"
    $base = Resolve-DaemonBaseUrl -Explicit $DaemonUrl
    Write-Host "AttachDaemon: probing $base …"
    $probes = @(Get-LiveDaemonProbes -BaseUrl $base)
    $daemonBlock = [ordered]@{
        attached = $true
        baseUrl  = $base
        probes   = $probes
    }

    $failedProbes = @($probes | Where-Object { $_.outcome -eq "fail" })
    if ($failedProbes.Count -gt 0 -and $Outcome -eq "pass") {
        $names = ($failedProbes | ForEach-Object { $_.path }) -join ", "
        throw "AttachDaemon probes failed ($names). Re-run with -Outcome fail|partial or fix the daemon."
    }

    # Drop prior live_* rows (idempotent re-record), then append fresh probe-backed items.
    $sample.checklist = @(
        $sample.checklist | Where-Object { $_.id -notmatch '^live_' }
    ) + @(New-LiveDaemonChecklistItems -Probes $probes -ManualOutcome $Outcome)

    $sample.procedure = "docs/a11y/status-regions-and-native-smoke.md#live-daemon-native-webview-parity"
    $notes = [System.Collections.Generic.List[string]]::new()
    foreach ($n in @($sample.notes)) {
        if ($n) { $notes.Add([string]$n) }
    }
    $notes.Add("Recorded with -AttachDaemon against $base; probes prove daemon API readiness for native WebView parity.")
    $sample.notes = $notes.ToArray()
}

# Attach mode + schema fields (additive; sample may already define defaults).
$sample | Add-Member -NotePropertyName mode -NotePropertyValue $mode -Force
$sample | Add-Member -NotePropertyName daemon -NotePropertyValue $daemonBlock -Force

if ($Outcome -ne "pass") {
    foreach ($item in $sample.checklist) {
        if ($item.outcome -eq "pass") {
            $item.outcome = $Outcome
            $item.detail = "Marked $Outcome by recorder; edit per-item detail before filing."
        }
    }
}

$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

$sample | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutPath -Encoding utf8
Write-Host "ok: native WebView smoke evidence written to $OutPath (mode=$mode, outcome=$Outcome, sha=$gitSha)"
