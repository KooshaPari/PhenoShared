<#
.SYNOPSIS
  Machine-check soft Alertmanager packaging evidence (C05).

.DESCRIPTION
  Verifies packaging/alertmanager/alertmanager.yml.sample is a secrets-free
  local placeholder receiver and that docs/ops/alertmanager-soft.md documents
  soft evidence with live webhook unpaid. Hermetic: no Alertmanager process,
  no network, no cargo build required for -SelfCheck.

  Does not claim live paging or production webhook traffic.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/alertmanager-soft-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$samplePath = Join-Path $repoRoot "packaging/alertmanager/alertmanager.yml.sample"
$docPath = Join-Path $repoRoot "docs/ops/alertmanager-soft.md"
$alertsPath = Join-Path $repoRoot "docs/ops/alerts.md"
$obsPath = Join-Path $repoRoot "docs/ops/observability.md"
$selfPath = Join-Path $repoRoot "scripts/alertmanager-soft-check.ps1"
$softTestPath = Join-Path $repoRoot "tests/alertmanager_soft.rs"

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
        [string]$Context = "docs/ops/alertmanager-soft.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Soft Alertmanager packaging check (C05)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (packaging sample + docs anchors; no Alertmanager / no network)"
}

Assert-File -Path $samplePath -Label "Alertmanager packaging sample"
Assert-File -Path $docPath -Label "alertmanager-soft doc"
Assert-File -Path $alertsPath -Label "alerts.md"
Assert-File -Path $obsPath -Label "observability.md"
Assert-File -Path $selfPath -Label "alertmanager soft check script"
Assert-File -Path $softTestPath -Label "alertmanager_soft test"

$sample = Get-Content -LiteralPath $samplePath -Raw
$doc = Get-Content -LiteralPath $docPath -Raw
$alerts = Get-Content -LiteralPath $alertsPath -Raw
$obs = Get-Content -LiteralPath $obsPath -Raw

Write-Host "Packaging sample anchors:"
Test-DocContains -Doc $sample -Needle "sessionledger-webhook-placeholder" `
    -Label "placeholder receiver name" -Context "packaging/alertmanager/alertmanager.yml.sample"
Test-DocContains -Doc $sample -Needle "http://127.0.0.1:9099/sessionledger-alerts" `
    -Label "loopback webhook URL" -Context "packaging/alertmanager/alertmanager.yml.sample"
Test-DocContains -Doc $sample -Needle "must never contain secrets" `
    -Label "no-secrets comment" -Context "packaging/alertmanager/alertmanager.yml.sample"

# Reject accidental secret-shaped tokens in the packaging sample.
$forbidden = @(
    "hooks.slack.com",
    "pagerduty.com",
    "xoxb-",
    "xoxp-",
    "sk_live",
    "SL_ALERT_SLACK_WEBHOOK_URL=",
    "SL_ALERT_PAGERDUTY_ROUTING_KEY="
)
foreach ($needle in $forbidden) {
    $hit = $sample.Contains($needle)
    [void](Write-Check -Label "sample free of '$needle'" -Ok (-not $hit))
    if ($hit) {
        throw "packaging sample must not contain secrets or live webhook hosts: '$needle'"
    }
}

Write-Host "alertmanager-soft.md anchors:"
Test-DocContains -Doc $doc -Needle "Soft Alertmanager packaging evidence" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "packaging/alertmanager/alertmanager.yml.sample" `
    -Label "packaging sample reference"
Test-DocContains -Doc $doc -Needle "scripts/alertmanager-soft-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Soft Alertmanager SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Live webhook / production paging | **unpaid**" `
    -Label "live webhook unpaid gate"
Test-DocContains -Doc $doc -Needle "Local placeholder" `
    -Label "local placeholder narrative"
Test-DocContains -Doc $doc -Needle "no network" `
    -Label "hermetic / no-network note"

Write-Host "Cross-link anchors:"
Test-DocContains -Doc $alerts -Needle "alertmanager-soft.md" `
    -Label "alerts.md links soft doc" -Context "docs/ops/alerts.md"
Test-DocContains -Doc $alerts -Needle "alertmanager.yml.sample" `
    -Label "alerts.md links packaging sample" -Context "docs/ops/alerts.md"
Test-DocContains -Doc $obs -Needle "alertmanager-soft.md" `
    -Label "observability.md links soft doc" -Context "docs/ops/observability.md"

Write-Host "Soft Alertmanager SelfCheck passed"
exit 0
