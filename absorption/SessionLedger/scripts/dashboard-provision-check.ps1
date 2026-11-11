<#
.SYNOPSIS
Validates the SessionLedger Grafana RED dashboard provisioning artifact.

.DESCRIPTION
Parses docs/ops/dashboards/sessionledger-red.json and verifies the dashboard
keeps the expected identity, panels, and Prometheus target expressions needed
for operations provisioning evidence.
#>
[CmdletBinding()]
param(
    [string]$DashboardPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($DashboardPath)) {
    $DashboardPath = Join-Path $repoRoot "docs/ops/dashboards/sessionledger-red.json"
}

if (-not (Test-Path -LiteralPath $DashboardPath -PathType Leaf)) {
    throw "Dashboard JSON not found: $DashboardPath"
}

try {
    $dashboard = Get-Content -LiteralPath $DashboardPath -Raw | ConvertFrom-Json -Depth 100
}
catch {
    throw "Dashboard JSON is invalid: $($_.Exception.Message)"
}

if ($dashboard.uid -ne "sessionledger-red") {
    throw "Expected dashboard uid 'sessionledger-red', got '$($dashboard.uid)'."
}

if ($dashboard.title -ne "SessionLedger / RED") {
    throw "Expected dashboard title 'SessionLedger / RED', got '$($dashboard.title)'."
}

$panels = @($dashboard.panels)
if ($panels.Count -lt 8) {
    throw "Expected at least 8 dashboard panels, found $($panels.Count)."
}

$requiredPanels = @(
    "Scrape health",
    "Request rate",
    "HTTP error ratio",
    "Mean request duration",
    "Request and error increases",
    "Route request rate",
    "Route error ratio",
    "Route p95 latency"
)

foreach ($title in $requiredPanels) {
    $panel = @($panels | Where-Object { $_.title -eq $title })
    if ($panel.Count -ne 1) {
        throw "Expected exactly one panel titled '$title', found $($panel.Count)."
    }

    $targets = @($panel[0].targets)
    if ($targets.Count -lt 1) {
        throw "Panel '$title' must define at least one Prometheus target."
    }

    foreach ($target in $targets) {
        if ([string]::IsNullOrWhiteSpace([string]$target.expr)) {
            throw "Panel '$title' has a target without a Prometheus expr."
        }
    }
}

$allExpressions = ($panels |
    ForEach-Object { @($_.targets) } |
    Where-Object { $null -ne $_ } |
    ForEach-Object { [string]$_.expr }) -join "`n"

$requiredMetrics = @(
    "up",
    "sl_http_requests_total",
    "sl_http_errors_total",
    "sl_http_request_duration_seconds_count",
    "sl_http_request_duration_seconds_sum"
)

foreach ($metric in $requiredMetrics) {
    if ($allExpressions -notmatch [regex]::Escape($metric)) {
        throw "Dashboard targets do not reference required metric '$metric'."
    }
}

if ($allExpressions -notmatch 'route!=') {
    throw "Dashboard targets do not reference per-route label matchers."
}

if ($allExpressions -notmatch 'histogram_quantile') {
    throw "Dashboard targets do not include route-level latency rollups."
}

Write-Host "Dashboard provisioning check passed: $DashboardPath"
