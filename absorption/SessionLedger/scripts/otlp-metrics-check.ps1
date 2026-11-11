<#
.SYNOPSIS
  Machine-check the C05 L43/L42 OTLP metrics export anchors.

.DESCRIPTION
  Verifies docs/ops/otlp-metrics.md + otlp-metrics.json document the OTLP metrics
  export path while preserving default Prometheus GET /metrics. Also asserts the
  otel-metrics Cargo feature, MetricExporter wiring, and export env contract.
  Hermetic: no network, no collector, no cargo build required for -SelfCheck.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/otlp-metrics-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/otlp-metrics.md"
$jsonPath = Join-Path $repoRoot "docs/ops/otlp-metrics.json"
$obsPath = Join-Path $repoRoot "docs/ops/observability.md"
$cargoPath = Join-Path $repoRoot "crates/sl-daemon/Cargo.toml"
$exportPath = Join-Path $repoRoot "crates/sl-daemon/src/otel_metrics.rs"
$metricsPath = Join-Path $repoRoot "crates/sl-daemon/src/metrics.rs"
$selfPath = Join-Path $repoRoot "scripts/otlp-metrics-check.ps1"
$workflowPath = Join-Path $repoRoot ".github/workflows/ops-load.yml"

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
        [string]$Context = "docs/ops/otlp-metrics.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "OTLP metrics export check (C05 L43/L42)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + export path; no cargo / no network)"
}

Assert-File -Path $docPath -Label "OTLP metrics doc"
Assert-File -Path $jsonPath -Label "OTLP metrics JSON"
Assert-File -Path $obsPath -Label "observability.md"
Assert-File -Path $cargoPath -Label "sl-daemon Cargo.toml"
Assert-File -Path $exportPath -Label "otel_metrics export module"
Assert-File -Path $metricsPath -Label "Prometheus metrics module"
Assert-File -Path $selfPath -Label "OTLP metrics check script"
Assert-File -Path $workflowPath -Label "ops-load workflow"

$doc = Get-Content -LiteralPath $docPath -Raw
$json = Get-Content -LiteralPath $jsonPath -Raw
$obs = Get-Content -LiteralPath $obsPath -Raw
$cargo = Get-Content -LiteralPath $cargoPath -Raw
$export = Get-Content -LiteralPath $exportPath -Raw
$metrics = Get-Content -LiteralPath $metricsPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw

Write-Host "OTLP metrics doc anchors:"
Test-DocContains -Doc $doc -Needle "OTLP metrics export (L43 / L42 evidence)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "Prometheus HTTP RED" `
    -Label "Prometheus RED preserved"
Test-DocContains -Doc $doc -Needle "GET /metrics" `
    -Label "GET /metrics contract"
Test-DocContains -Doc $doc -Needle "otel-metrics" `
    -Label "otel-metrics feature named"
Test-DocContains -Doc $doc -Needle "SL_OTLP_METRICS_ENDPOINT" `
    -Label "metrics endpoint env"
Test-DocContains -Doc $doc -Needle "otlp_metrics_export" `
    -Label "export status field"
Test-DocContains -Doc $doc -Needle "scripts/otlp-metrics-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "otlp-metrics-export" `
    -Label "blocking CI job named"
Test-DocContains -Doc $doc -Needle "Unpaid gaps (explicit)" `
    -Label "unpaid gaps section"

Write-Host "OTLP metrics JSON anchors:"
Test-DocContains -Doc $json -Needle "sessionledger.otlp-metrics.v1" `
    -Label "JSON schema id" -Context "docs/ops/otlp-metrics.json"
Test-DocContains -Doc $json -Needle '"otlp_metrics_export": "otlp-grpc"' `
    -Label "export otlp-grpc" -Context "docs/ops/otlp-metrics.json"
Test-DocContains -Doc $json -Needle '"prometheus_http": "/metrics"' `
    -Label "Prometheus path pinned" -Context "docs/ops/otlp-metrics.json"
Test-DocContains -Doc $json -Needle '"cargo_feature": "otel-metrics"' `
    -Label "feature pin" -Context "docs/ops/otlp-metrics.json"
Test-DocContains -Doc $json -Needle '"SL_OTLP_METRICS_ENDPOINT"' `
    -Label "endpoint env pin" -Context "docs/ops/otlp-metrics.json"
Test-DocContains -Doc $json -Needle '"ack_env": "SL_OTLP_METRICS"' `
    -Label "ack env pin" -Context "docs/ops/otlp-metrics.json"

Write-Host "Feature + export-path evidence:"
Test-DocContains -Doc $cargo -Needle "otel-metrics" `
    -Label "Cargo feature present" -Context "crates/sl-daemon/Cargo.toml"
Test-DocContains -Doc $export -Needle "SL_OTLP_METRICS_ENDPOINT" `
    -Label "metrics endpoint constant" -Context "crates/sl-daemon/src/otel_metrics.rs"
Test-DocContains -Doc $export -Needle "MetricExporter" `
    -Label "MetricExporter wired" -Context "crates/sl-daemon/src/otel_metrics.rs"
Test-DocContains -Doc $export -Needle "SdkMeterProvider" `
    -Label "SdkMeterProvider wired" -Context "crates/sl-daemon/src/otel_metrics.rs"
Test-DocContains -Doc $export -Needle "Prometheus /metrics unchanged" `
    -Label "non-breaking export note" -Context "crates/sl-daemon/src/otel_metrics.rs"
Test-DocContains -Doc $metrics -Needle "render_prometheus" `
    -Label "Prometheus renderer intact" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "sl_http_requests_total" `
    -Label "RED counter series" -Context "crates/sl-daemon/src/metrics.rs"

Write-Host "Ops cross-links:"
Test-DocContains -Doc $obs -Needle "otlp-metrics.md" `
    -Label "observability links export doc" -Context "docs/ops/observability.md"
Test-DocContains -Doc $obs -Needle "otel-metrics" `
    -Label "observability names feature" -Context "docs/ops/observability.md"
Test-DocContains -Doc $workflow -Needle "otlp-metrics-export" `
    -Label "export job in ops-load" -Context ".github/workflows/ops-load.yml"
Test-DocContains -Doc $workflow -Needle "otlp-metrics-check.ps1" `
    -Label "workflow invokes SelfCheck" -Context ".github/workflows/ops-load.yml"

Write-Host "OTLP metrics SelfCheck passed"
exit 0
