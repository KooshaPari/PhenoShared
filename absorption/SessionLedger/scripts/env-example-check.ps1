[CmdletBinding()]
param(
    [string]$EnvExamplePath = ".env.example"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$fullPath = if ([IO.Path]::IsPathRooted($EnvExamplePath)) {
    $EnvExamplePath
}
else {
    Join-Path $repoRoot $EnvExamplePath
}

# Secrets-adjacent and core local-runtime keys that must be documented.
$RequiredKeys = @(
    "SL_API_KEY",
    "SL_PORT",
    "SL_DATA_DIR",
    "SL_WATCH_DIR",
    "SL_OUT_DIR",
    "SL_INGEST_MAX_BODY_BYTES",
    "SL_INGEST_MAX_CONCURRENCY",
    "SL_API_RATE_LIMIT",
    "SL_API_RATE_WINDOW_MS",
    "SL_DAEMON_URL"
)

# Placeholder tokens allowed as SL_API_KEY values (never real secrets).
$AllowedApiKeyPlaceholders = @(
    "",
    "changeme",
    "replace-me",
    "your-api-key-here",
    "<sl-api-key>",
    "local-dev-only"
)

function Get-AssignmentLines {
    param([string]$Path)
    $lines = Get-Content -LiteralPath $Path
    $parsed = New-Object System.Collections.Generic.List[object]
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $raw = $lines[$i]
        $trimmed = $raw.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        $commented = $false
        $body = $trimmed
        if ($trimmed.StartsWith("#")) {
            $commented = $true
            $body = $trimmed.TrimStart("#").Trim()
        }
        if ($body -notmatch '^(?<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<value>.*)$') {
            continue
        }
        $key = $Matches["key"]
        $value = $Matches["value"].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $parsed.Add([pscustomobject]@{
                LineNumber = $i + 1
                Key        = $key
                Value      = $value
                Commented  = $commented
                Raw        = $raw
            })
    }
    return $parsed
}

function Test-HighEntropySecretPattern {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    # PEM / OpenSSH private key material
    if ($Value -match 'BEGIN\s+(RSA|OPENSSH|EC|DSA|PRIVATE)\s+KEY') {
        return $true
    }
    # AWS access key id
    if ($Value -match '\bAKIA[0-9A-Z]{16}\b') {
        return $true
    }
    # GitHub classic / fine-grained / PAT-looking tokens
    if ($Value -match '\bgh[pousr]_[A-Za-z0-9_]{20,}\b') {
        return $true
    }
    # JWT-shaped triple (header.payload.sig)
    if ($Value -match '^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') {
        return $true
    }
    # Long high-entropy hex or base64-ish blobs (likely pasted secrets)
    if ($Value.Length -ge 32 -and $Value -match '^[A-Fa-f0-9]{32,}$') {
        return $true
    }
    if ($Value.Length -ge 40 -and $Value -match '^[A-Za-z0-9+/=_-]{40,}$' -and $Value -notmatch '^[./\\]') {
        return $true
    }
    return $false
}

if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
    throw ".env.example missing at '$fullPath'."
}

$assignments = @(Get-AssignmentLines -Path $fullPath)
if ($assignments.Count -eq 0) {
    throw ".env.example at '$fullPath' has no KEY=VALUE assignments."
}

$presentKeys = [System.Collections.Generic.HashSet[string]]::new(
    [StringComparer]::Ordinal
)
foreach ($row in $assignments) {
    [void]$presentKeys.Add($row.Key)
}

$findings = New-Object System.Collections.Generic.List[string]

foreach ($key in $RequiredKeys) {
    if (-not $presentKeys.Contains($key)) {
        $findings.Add("missing required key documentation: $key")
    }
}

foreach ($row in $assignments) {
    if (Test-HighEntropySecretPattern -Value $row.Value) {
        $findings.Add(
            ("line {0}: high-entropy secret pattern on {1}" -f $row.LineNumber, $row.Key)
        )
    }

    if ($row.Key -eq "SL_API_KEY") {
        $normalized = $row.Value.Trim().ToLowerInvariant()
        if ($AllowedApiKeyPlaceholders -notcontains $normalized) {
            $findings.Add(
                ("line {0}: SL_API_KEY must stay empty or use an explicit placeholder, not a real key" -f $row.LineNumber)
            )
        }
    }
}

$relative = [IO.Path]::GetRelativePath($repoRoot, $fullPath)
Write-Host "env-example check: $relative ($($assignments.Count) assignments, $($presentKeys.Count) keys)"

if ($findings.Count -gt 0) {
    Write-Host "env-example check failed with $($findings.Count) finding(s):"
    foreach ($finding in $findings) {
        Write-Host "  - $finding"
    }
    exit 1
}

Write-Host "env-example check passed (required keys present; no high-entropy secret patterns)."
exit 0
