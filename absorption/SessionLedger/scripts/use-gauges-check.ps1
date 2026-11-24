<#
.SYNOPSIS
  Machine-check the C05 L42 USE process gauges on Prometheus /metrics.

.DESCRIPTION
  Verifies docs/ops/observability.md documents USE process gauges and that
  crates/sl-daemon/src/metrics.rs exports the standard series via
  append_process_use_gauges. Hermetic: no network, no cargo build required
  for -SelfCheck.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/use-gauges-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$obsPath = Join-Path $repoRoot "docs/ops/observability.md"
$metricsPath = Join-Path $repoRoot "crates/sl-daemon/src/metrics.rs"
$selfPath = Join-Path $repoRoot "scripts/use-gauges-check.ps1"
$testPath = Join-Path $repoRoot "tests/use_gauges.rs"

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
        [string]$Context = "docs/ops/observability.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "USE process gauges check (C05 L42)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + metrics.rs anchors; no cargo / no network)"
}

Assert-File -Path $obsPath -Label "observability.md"
Assert-File -Path $metricsPath -Label "Prometheus metrics module"
Assert-File -Path $selfPath -Label "USE gauges check script"
Assert-File -Path $testPath -Label "use_gauges test wrapper"

$obs = Get-Content -LiteralPath $obsPath -Raw
$metrics = Get-Content -LiteralPath $metricsPath -Raw

Write-Host "Observability USE anchors:"
Test-DocContains -Doc $obs -Needle "USE process gauges" `
    -Label "USE gauges section heading"
Test-DocContains -Doc $obs -Needle "GET /metrics" `
    -Label "GET /metrics export path"
Test-DocContains -Doc $obs -Needle "process_cpu_seconds_total" `
    -Label "CPU gauge named"
Test-DocContains -Doc $obs -Needle "process_resident_memory_bytes" `
    -Label "RSS gauge named"
Test-DocContains -Doc $obs -Needle "process_open_fds" `
    -Label "open FD gauge named"
Test-DocContains -Doc $obs -Needle "scripts/use-gauges-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $obs -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"

Write-Host "metrics.rs USE anchors:"
Test-DocContains -Doc $metrics -Needle "append_process_use_gauges" `
    -Label "append helper present" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "process_cpu_seconds_total" `
    -Label "CPU series emitted" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "process_resident_memory_bytes" `
    -Label "RSS series emitted" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "process_open_fds" `
    -Label "open FD series emitted" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "/proc/self" `
    -Label "linux /proc/self reader" -Context "crates/sl-daemon/src/metrics.rs"
Test-DocContains -Doc $metrics -Needle "render_prometheus" `
    -Label "Prometheus renderer intact" -Context "crates/sl-daemon/src/metrics.rs"

Write-Host "USE gauges SelfCheck passed"
exit 0
