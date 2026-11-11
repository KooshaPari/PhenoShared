<#
.SYNOPSIS
Tail, filter, or export the local durable audit sink for compliance review.

.DESCRIPTION
Reads the append-only audit store under <data_dir>/audit/. This script touches
local files only; it does not call sl-daemon HTTP endpoints and preserves the
loopback-only trust boundary.

JSONL is the default backend. When SL_AUDIT_BACKEND=sqlite (or -Backend sqlite),
events are exported with the sqlite3 CLI if present.

.EXAMPLE
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Tail 20

.EXAMPLE
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Since "2026-07-01" -Export ./review/audit-export.jsonl
#>
[CmdletBinding()]
param(
    [string]$DataDir = $env:SL_DATA_DIR,

    [ValidateSet("jsonl", "sqlite")]
    [string]$Backend = "",

    [ValidateRange(1, 1000000)]
    [int]$Tail = 0,

    [string]$Since = "",

    [string]$Until = "",

    [string]$Export = "",

    [switch]$PassThru
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-AuditBackend {
    param([string]$Requested)

    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return $Requested.ToLowerInvariant()
    }

    $fromEnv = $env:SL_AUDIT_BACKEND
    if ([string]::IsNullOrWhiteSpace($fromEnv)) {
        return "jsonl"
    }

    return $fromEnv.Trim().ToLowerInvariant()
}

function Resolve-DataDir {
    param([string]$Requested)

    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path -LiteralPath $Requested).Path
    }

    throw "Set -DataDir or SL_DATA_DIR to the daemon data root (for example ./.sl-data)."
}

function ConvertToUnixMs {
    param([Parameter(Mandatory = $true)][datetime]$Value)

    return [int64]([DateTimeOffset]$Value.ToUniversalTime()).ToUnixTimeMilliseconds()
}

function Get-AuditJsonlPath {
    param([Parameter(Mandatory = $true)][string]$Root)

    return Join-Path $Root "audit/events.jsonl"
}

function Get-AuditSqlitePath {
    param([Parameter(Mandatory = $true)][string]$Root)

    return Join-Path $Root "audit/events.db"
}

function Read-AuditJsonlLines {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Audit JSONL file not found at '$Path'. Start sl-daemon or run a mutating command first."
    }

    return @(Get-Content -LiteralPath $Path -Encoding utf8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Export-AuditSqliteJsonl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Sqlite3 = "sqlite3"
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Audit SQLite database not found at '$Path'. Build sl-daemon with --features sqlite and set SL_AUDIT_BACKEND=sqlite."
    }

    if (-not (Get-Command $Sqlite3 -ErrorAction SilentlyContinue)) {
        throw "sqlite3 is required to read the audit SQLite backend. Install sqlite3 or switch SL_AUDIT_BACKEND=jsonl."
    }

    $escaped = $Path.Replace("'", "''")
    $query = @"
.mode json
SELECT json_object(
  'timestamp', timestamp,
  'actor', actor,
  'action', action,
  'outcome', outcome,
  'request_id', request_id,
  'reason', reason,
  'resource', resource
) AS line
FROM audit_events
ORDER BY id;
"@

    $raw = & $Sqlite3 $Path $query 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "sqlite3 failed: $raw"
    }

    return @($raw | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
}

function Filter-AuditLines {
    param(
        [Parameter(Mandatory = $true)][string[]]$Lines,
        $SinceMs,
        $UntilMs
    )

    if ($null -eq $SinceMs -and $null -eq $UntilMs) {
        return $Lines
    }

    $filtered = New-Object System.Collections.Generic.List[string]
    foreach ($line in $Lines) {
        $record = $line | ConvertFrom-Json
        $timestamp = [int64]$record.timestamp
        if ($null -ne $SinceMs -and $timestamp -lt $SinceMs) {
            continue
        }
        if ($null -ne $UntilMs -and $timestamp -gt $UntilMs) {
            continue
        }
        $filtered.Add($line)
    }

    return @($filtered)
}

$resolvedBackend = Resolve-AuditBackend -Requested $Backend
$resolvedDataDir = Resolve-DataDir -Requested $DataDir

$sinceMs = $null
if (-not [string]::IsNullOrWhiteSpace($Since)) {
    $sinceMs = ConvertToUnixMs -Value ([datetime]$Since)
}

$untilMs = $null
if (-not [string]::IsNullOrWhiteSpace($Until)) {
    $untilMs = ConvertToUnixMs -Value ([datetime]$Until)
}

$lines = switch ($resolvedBackend) {
    "jsonl" { Read-AuditJsonlLines -Path (Get-AuditJsonlPath -Root $resolvedDataDir) }
    "sqlite" { Export-AuditSqliteJsonl -Path (Get-AuditSqlitePath -Root $resolvedDataDir) }
    default { throw "Unsupported backend '$resolvedBackend'. Use jsonl or sqlite." }
}

$lines = Filter-AuditLines -Lines $lines -SinceMs $sinceMs -UntilMs $untilMs

if ($Tail -gt 0 -and $lines.Count -gt $Tail) {
    $lines = $lines[-$Tail..($lines.Count - 1)]
}

if (-not [string]::IsNullOrWhiteSpace($Export)) {
    $exportDir = Split-Path -Parent $Export
    if (-not [string]::IsNullOrWhiteSpace($exportDir) -and -not (Test-Path -LiteralPath $exportDir)) {
        New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
    }

    if ($lines.Count -eq 0) {
        New-Item -ItemType File -Path $Export -Force | Out-Null
    }
    else {
        Set-Content -LiteralPath $Export -Value $lines -Encoding utf8
    }

    Write-Host "Exported $($lines.Count) audit record(s) to $Export"
}

if ($PassThru) {
    return $lines
}

foreach ($line in $lines) {
    Write-Output $line
}

if ($lines.Count -eq 0) {
    Write-Host "No audit records matched the requested filters."
}
