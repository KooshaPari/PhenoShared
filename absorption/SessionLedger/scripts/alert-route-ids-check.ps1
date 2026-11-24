<#
.SYNOPSIS
Validates SessionLedger Alertmanager Slack/PagerDuty route ID stubs.

.DESCRIPTION
Always checks that docs/ops/alerts/alertmanager.yaml and route-ids.stub.env
contain the expected stub receivers and placeholder tokens (no live secrets).

Without -Strict: exit 0 when stubs are present (OSS / local DX).
With -Strict: also require SL_ALERT_SLACK_WEBHOOK_URL, SL_ALERT_SLACK_CHANNEL_ID,
and SL_ALERT_PAGERDUTY_ROUTING_KEY in the process environment with non-stub values.
#>
[CmdletBinding()]
param(
    [switch]$Strict,
    [string]$AlertmanagerPath = "",
    [string]$StubEnvPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($AlertmanagerPath)) {
    $AlertmanagerPath = Join-Path $repoRoot "docs/ops/alerts/alertmanager.yaml"
}
if ([string]::IsNullOrWhiteSpace($StubEnvPath)) {
    $StubEnvPath = Join-Path $repoRoot "docs/ops/alerts/route-ids.stub.env"
}

function Write-Check {
    param([string]$Label, [bool]$Ok)
    $Mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "  [$Mark] $Label"
    return $Ok
}

function Test-IsStubValue {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $true
    }
    $v = $Value.Trim()
    if ($v -match 'REPLACE_ME') {
        return $true
    }
    if ($v -match 'hooks\.slack\.com/services/REPLACE_ME') {
        return $true
    }
    $stubExact = @(
        "REPLACE_ME_SLACK_CHANNEL_ID",
        "REPLACE_ME_PAGERDUTY_ROUTING_KEY",
        "https://hooks.slack.com/services/REPLACE_ME/SLACK/WEBHOOK"
    )
    return $stubExact -contains $v
}

$failures = New-Object System.Collections.Generic.List[string]

Write-Host "Alertmanager route ID stub check"
Write-Host "  alertmanager: $AlertmanagerPath"
Write-Host "  stub env:     $StubEnvPath"
Write-Host "  strict:       $Strict"

if (-not (Test-Path -LiteralPath $AlertmanagerPath -PathType Leaf)) {
    throw "Alertmanager config not found: $AlertmanagerPath"
}
if (-not (Test-Path -LiteralPath $StubEnvPath -PathType Leaf)) {
    throw "Stub env file not found: $StubEnvPath"
}

$am = Get-Content -LiteralPath $AlertmanagerPath -Raw
$stub = Get-Content -LiteralPath $StubEnvPath -Raw

$amChecks = @(
    @{ Label = "receiver sessionledger-slack-ops"; Ok = $am -match 'name:\s*sessionledger-slack-ops' },
    @{ Label = "receiver sessionledger-pagerduty"; Ok = $am -match 'name:\s*sessionledger-pagerduty' },
    @{ Label = "Slack api_url stub token"; Ok = $am -match 'REPLACE_ME/SLACK/WEBHOOK' },
    @{ Label = "PagerDuty routing_key stub token"; Ok = $am -match 'REPLACE_ME_PAGERDUTY_ROUTING_KEY' },
    @{ Label = "webhook placeholder retained"; Ok = $am -match 'sessionledger-webhook-placeholder' }
)

foreach ($c in $amChecks) {
    if (-not (Write-Check -Label $c.Label -Ok $c.Ok)) {
        $failures.Add($c.Label) | Out-Null
    }
}

$envKeys = @(
    "SL_ALERT_SLACK_WEBHOOK_URL",
    "SL_ALERT_SLACK_CHANNEL_ID",
    "SL_ALERT_PAGERDUTY_ROUTING_KEY"
)

foreach ($key in $envKeys) {
    $present = $stub -match "(?m)^\s*$([regex]::Escape($key))\s*="
    if (-not (Write-Check -Label "stub env documents $key" -Ok $present)) {
        $failures.Add("stub env missing $key") | Out-Null
    }
}

# Guard: stub file must not look like a live secret dump.
if ($stub -match 'xox[baprs]-|pd[a-z0-9]{20,}|hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[A-Za-z0-9]+') {
    if ($stub -notmatch 'REPLACE_ME') {
        $failures.Add("stub env appears to contain a live Slack/PagerDuty credential") | Out-Null
        Write-Check -Label "stub env has no live-looking secrets" -Ok $false | Out-Null
    }
    else {
        Write-Check -Label "stub env keeps REPLACE_ME tokens" -Ok $true | Out-Null
    }
}
else {
    Write-Check -Label "stub env keeps REPLACE_ME tokens" -Ok ($stub -match 'REPLACE_ME') | Out-Null
    if ($stub -notmatch 'REPLACE_ME') {
        $failures.Add("stub env missing REPLACE_ME tokens") | Out-Null
    }
}

if ($failures.Count -gt 0) {
    Write-Host "FAIL: stub artifacts incomplete:"
    foreach ($f in $failures) {
        Write-Host "  - $f"
    }
    exit 1
}

if (-not $Strict) {
    Write-Host "OK: route ID stubs present (non-strict; live env not required)."
    Write-Host "    Rerun with -Strict after exporting SL_ALERT_* values for go-live."
    exit 0
}

Write-Host "Strict mode: requiring live SL_ALERT_* environment values..."
$strictFailures = New-Object System.Collections.Generic.List[string]

foreach ($key in $envKeys) {
    $val = [Environment]::GetEnvironmentVariable($key)
    $ok = -not (Test-IsStubValue -Value $val)
    if (-not (Write-Check -Label "env $key is set and non-stub" -Ok $ok)) {
        if ([string]::IsNullOrWhiteSpace($val)) {
            $strictFailures.Add("$key is unset") | Out-Null
        }
        else {
            $strictFailures.Add("$key still looks like a REPLACE_ME stub") | Out-Null
        }
    }
}

if ($strictFailures.Count -gt 0) {
    Write-Host "FAIL: -Strict requires non-stub environment values:"
    foreach ($f in $strictFailures) {
        Write-Host "  - $f"
    }
    Write-Host "Export live SL_ALERT_* vars (never commit them), then rerun -Strict."
    exit 1
}

Write-Host "OK: live SL_ALERT_* route IDs present under -Strict."
exit 0
