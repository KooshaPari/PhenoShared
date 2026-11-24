[CmdletBinding()]
param(
    [string]$BaselinePath,

    [ValidateRange(10, 1000000)]
    [int]$SampleSize = 10,

    [ValidateRange(0.1, 3600)]
    [double]$WarmUpSeconds = 1,

    [ValidateRange(0.1, 3600)]
    [double]$MeasurementSeconds = 2,

    [double]$ThresholdPercent = -1,

    [string]$ArtifactPath,

    [switch]$UpdateBaseline,

    [switch]$SelfCheck,

    # C00 L6 latency SelfCheck only (no cargo bench). Validates schema; enforcement is in the full gate.
    [switch]$SoftLatencyCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $BaselinePath) {
    $BaselinePath = Join-Path $repoRoot "docs/ops/perf-baseline.json"
}
$BaselinePath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($BaselinePath)

if (-not $ArtifactPath) {
    $ArtifactPath = Join-Path $repoRoot "artifacts/pipeline-perf-gate.json"
}

if ($env:CARGO_TARGET_DIR) {
    if ([System.IO.Path]::IsPathRooted($env:CARGO_TARGET_DIR)) {
        $targetDir = $env:CARGO_TARGET_DIR
    }
    else {
        $targetDir = Join-Path $repoRoot $env:CARGO_TARGET_DIR
    }
}
else {
    $targetDir = Join-Path $repoRoot "target"
}
$criterionDir = Join-Path $targetDir "criterion"

$benchmarkNames = @(
    "distill_compile_200_messages",
    "okf_export_200_messages",
    "inject_render_200_messages"
)

function Get-BenchmarkKey {
    param([Parameter(Mandatory = $true)][string]$BenchmarkName)
    "pipeline/$BenchmarkName"
}

function Get-BaselineBenchmarkEntry {
    param(
        [Parameter(Mandatory = $true)]$Benchmarks,
        [Parameter(Mandatory = $true)][string]$Key
    )

    $prop = $Benchmarks.PSObject.Properties[$Key]
    if ($null -eq $prop) {
        throw "Baseline is missing required benchmark '$Key'."
    }
    $prop.Value
}

function Assert-BaselinePolicy {
    param(
        [Parameter(Mandatory = $true)]$Baseline,
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Baseline not found at '$Path'."
    }

    if ($null -eq $Baseline.policy) {
        throw "Baseline '$Path' is missing policy."
    }

    $enforced = $false
    if ($Baseline.policy.PSObject.Properties.Name -contains "enforced") {
        $enforced = [bool]$Baseline.policy.enforced
    }
    if (-not $enforced) {
        throw "Baseline policy.enforced must be true — pipeline perf budgets are a blocking CI gate."
    }

    $threshold = [double]$Baseline.policy.threshold_percent
    if ($threshold -le 0 -or $threshold -gt 500) {
        throw "Baseline policy.threshold_percent must be in (0, 500]; got $threshold."
    }

    $props = @($Baseline.benchmarks.PSObject.Properties)
    if ($props.Count -eq 0) {
        throw "Baseline benchmarks object is empty."
    }

    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        $entry = Get-BaselineBenchmarkEntry -Benchmarks $Baseline.benchmarks -Key $key

        $meanNs = [double]$entry.mean_ns
        if ($meanNs -le 0) {
            throw "Baseline '$key'.mean_ns must be > 0."
        }

        if ($entry.PSObject.Properties.Name -contains "budget_mean_ns") {
            $budgetNs = [double]$entry.budget_mean_ns
        }
        else {
            $budgetNs = $meanNs * (1.0 + ($threshold / 100.0))
        }

        $expectedMin = $meanNs * (1.0 + ($threshold / 100.0))
        if ($budgetNs + 0.001 -lt $expectedMin) {
            throw ("Baseline '{0}'.budget_mean_ns ({1}) is tighter than mean_ns + {2}% ({3})." -f `
                $key, $budgetNs, $threshold, $expectedMin)
        }
        if ($budgetNs -lt $meanNs) {
            throw "Baseline '$key'.budget_mean_ns must be >= mean_ns."
        }
    }

    return $threshold
}

function Assert-LatencyPolicy {
    param(
        [Parameter(Mandatory = $true)]$Baseline,
        [Parameter(Mandatory = $true)][string]$Path
    )

    if ($null -eq $Baseline.latency) {
        throw "Baseline '$Path' is missing latency (C00 L6 checked-in p95 budgets)."
    }

    $latency = $Baseline.latency
    if ($null -eq $latency.threshold_percent) {
        throw "Baseline latency.threshold_percent is required."
    }

    $threshold = [double]$latency.threshold_percent
    if ($threshold -le 0 -or $threshold -gt 500) {
        throw "Baseline latency.threshold_percent must be in (0, 500]; got $threshold."
    }

    $enforced = $false
    if ($latency.PSObject.Properties.Name -contains "enforced") {
        $enforced = [bool]$latency.enforced
    }

    if ($null -eq $latency.benchmarks) {
        throw "Baseline latency.benchmarks object is missing."
    }

    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        $entry = Get-BaselineBenchmarkEntry -Benchmarks $latency.benchmarks -Key $key

        $p95Ns = [double]$entry.p95_ns
        if ($p95Ns -le 0) {
            throw "Baseline latency '$key'.p95_ns must be > 0."
        }

        if ($entry.PSObject.Properties.Name -notcontains "p95_source") {
            throw "Baseline latency '$key' must include p95_source (criterion_sample_json or synthetic_mean_x1_15)."
        }

        if ($entry.PSObject.Properties.Name -contains "budget_p95_ns") {
            $budgetNs = [double]$entry.budget_p95_ns
        }
        else {
            $budgetNs = $p95Ns * (1.0 + ($threshold / 100.0))
        }

        $expectedMin = $p95Ns * (1.0 + ($threshold / 100.0))
        if ($budgetNs + 0.001 -lt $expectedMin) {
            throw ("Baseline latency '{0}'.budget_p95_ns ({1}) is tighter than p95_ns + {2}% ({3})." -f `
                $key, $budgetNs, $threshold, $expectedMin)
        }
        if ($budgetNs -lt $p95Ns) {
            throw "Baseline latency '$key'.budget_p95_ns must be >= p95_ns."
        }
    }

    if ($null -eq $latency.http_load_smoke) {
        throw "Baseline latency.http_load_smoke is required (documents load-smoke p95 SLO)."
    }
    $httpMax = [double]$latency.http_load_smoke.max_p95_ms
    if ($httpMax -le 0) {
        throw "Baseline latency.http_load_smoke.max_p95_ms must be > 0."
    }

    return @{
        ThresholdPercent = $threshold
        Enforced         = $enforced
        HttpMaxP95Ms     = $httpMax
    }
}

function Get-CriterionP95Ns {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BenchmarkName
    )

    $samplePath = Join-Path $criterionDir "pipeline/$BenchmarkName/current/sample.json"
    if (-not (Test-Path -LiteralPath $samplePath -PathType Leaf)) {
        return $null
    }

    $sample = Get-Content -LiteralPath $samplePath -Raw | ConvertFrom-Json
    if ($null -eq $sample.times -or $null -eq $sample.iters) {
        return $null
    }

    $times = @($sample.times)
    $iters = @($sample.iters)
    if ($times.Count -eq 0 -or $times.Count -ne $iters.Count) {
        return $null
    }

    $perIter = New-Object System.Collections.Generic.List[double]
    for ($i = 0; $i -lt $times.Count; $i++) {
        $n = [double]$iters[$i]
        if ($n -le 0) {
            continue
        }
        $perIter.Add([double]$times[$i] / $n)
    }

    if ($perIter.Count -eq 0) {
        return $null
    }

    $sorted = @($perIter | Sort-Object)
    $p95Index = [Math]::Max(0, [Math]::Ceiling(0.95 * $sorted.Count) - 1)
    return [double]$sorted[$p95Index]
}

function Get-CriterionEstimate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BenchmarkName
    )

    $estimatePath = Join-Path $criterionDir "pipeline/$BenchmarkName/current/estimates.json"
    if (-not (Test-Path -LiteralPath $estimatePath -PathType Leaf)) {
        throw "Criterion estimate not found at '$estimatePath'."
    }

    $estimate = Get-Content -LiteralPath $estimatePath -Raw | ConvertFrom-Json
    [double]$estimate.mean.point_estimate
}

function Get-CurrentMeasurements {
    $measurements = [ordered]@{}
    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        $measurements[$key] = Get-CriterionEstimate -BenchmarkName $name
    }
    $measurements
}

function Write-GateSummary {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Body
    )

    if ($env:GITHUB_STEP_SUMMARY) {
        @"
## $Title

$Body
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
    }
}

if ($SoftLatencyCheck -or $SelfCheck) {
    if (-not (Test-Path -LiteralPath $BaselinePath -PathType Leaf)) {
        throw "Baseline not found at '$BaselinePath'."
    }
    if (-not (Test-Path -LiteralPath $PSCommandPath -PathType Leaf)) {
        throw "bench-gate script missing at '$PSCommandPath'."
    }

    $baseline = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json

    if ($SoftLatencyCheck -and -not $SelfCheck) {
        $latencyInfo = Assert-LatencyPolicy -Baseline $baseline -Path $BaselinePath
        $threshold = $latencyInfo.ThresholdPercent
        $enforcedLabel = if ($latencyInfo.Enforced) { "true" } else { "false" }

        $rows = New-Object System.Collections.Generic.List[string]
        $rows.Add("| Benchmark | Baseline p95 (ns) | Budget ceiling (ns) | Threshold |")
        $rows.Add("|---|---:|---:|---:|")
        foreach ($name in $benchmarkNames) {
            $key = Get-BenchmarkKey -BenchmarkName $name
            $entry = Get-BaselineBenchmarkEntry -Benchmarks $baseline.latency.benchmarks -Key $key
            $p95Ns = [double]$entry.p95_ns
            if ($entry.PSObject.Properties.Name -contains "budget_p95_ns") {
                $budgetNs = [double]$entry.budget_p95_ns
            }
            else {
                $budgetNs = $p95Ns * (1.0 + ($threshold / 100.0))
            }
            $rows.Add(("| `{0}` | {1:N3} | {2:N3} | {3:N1}% |" -f $key, $p95Ns, $budgetNs, $threshold))
        }

        Write-Host "bench-gate SoftLatencyCheck passed (latency.enforced=$enforcedLabel, threshold=${threshold}%)."
        Write-Host ("HTTP load-smoke max p95: {0} ms" -f $latencyInfo.HttpMaxP95Ms)
        Write-Host ("Documented latency budgets: {0}" -f ($benchmarkNames -join ", "))
        $enforcementNote = if ($latencyInfo.Enforced) {
            "Full gate fails when any Criterion sample p95 exceeds ``budget_p95_ns``."
        }
        else {
            "Soft CI: p95 overruns warn only until ``latency.enforced`` is promoted to ``true``."
        }
        Write-GateSummary -Title "Pipeline latency baseline check (C00 L6)" -Body @"
Latency policy OK (``latency.enforced=$enforcedLabel``).

Threshold: **${threshold}%** slower than checked-in ``p95_ns``.

HTTP load-smoke ``max_p95_ms``: **$($latencyInfo.HttpMaxP95Ms)**.

$($rows -join "`n")

$enforcementNote
"@
        exit 0
    }

    $threshold = Assert-BaselinePolicy -Baseline $baseline -Path $BaselinePath
    $latencyInfo = Assert-LatencyPolicy -Baseline $baseline -Path $BaselinePath

    $rows = New-Object System.Collections.Generic.List[string]
    $rows.Add("| Benchmark | Baseline mean (ns) | Budget ceiling (ns) | Threshold |")
    $rows.Add("|---|---:|---:|---:|")
    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        $entry = Get-BaselineBenchmarkEntry -Benchmarks $baseline.benchmarks -Key $key
        $meanNs = [double]$entry.mean_ns
        if ($entry.PSObject.Properties.Name -contains "budget_mean_ns") {
            $budgetNs = [double]$entry.budget_mean_ns
        }
        else {
            $budgetNs = $meanNs * (1.0 + ($threshold / 100.0))
        }
        $rows.Add(("| `{0}` | {1:N3} | {2:N3} | {3:N1}% |" -f $key, $meanNs, $budgetNs, $threshold))
    }

    $latRows = New-Object System.Collections.Generic.List[string]
    $latRows.Add("| Benchmark | Baseline p95 (ns) | Budget ceiling (ns) | Threshold |")
    $latRows.Add("|---|---:|---:|---:|")
    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        $entry = Get-BaselineBenchmarkEntry -Benchmarks $baseline.latency.benchmarks -Key $key
        $p95Ns = [double]$entry.p95_ns
        if ($entry.PSObject.Properties.Name -contains "budget_p95_ns") {
            $budgetNs = [double]$entry.budget_p95_ns
        }
        else {
            $budgetNs = $p95Ns * (1.0 + ($latencyInfo.ThresholdPercent / 100.0))
        }
        $latRows.Add(("| `{0}` | {1:N3} | {2:N3} | {3:N1}% |" -f $key, $p95Ns, $budgetNs, $latencyInfo.ThresholdPercent))
    }

    $latEnforced = if ($latencyInfo.Enforced) { "true" } else { "false" }
    Write-Host "bench-gate SelfCheck passed (enforced=true, threshold=${threshold}%)."
    Write-Host ("Latency budgets present (latency.enforced={0}, threshold={1}%)." -f $latEnforced, $latencyInfo.ThresholdPercent)
    Write-Host ("Documented budgets: {0}" -f ($benchmarkNames -join ", "))
    $latFailureNote = if ($latencyInfo.Enforced) {
        "CI fails when any Criterion sample p95 exceeds ``budget_p95_ns``."
    }
    else {
        "Soft p95 overruns warn only until ``latency.enforced`` is promoted to ``true``."
    }
    Write-GateSummary -Title "Pipeline perf-budget SelfCheck" -Body @"
Enforced blocking gate policy OK (``policy.enforced=true``).

Threshold: **${threshold}%** slower than checked-in ``mean_ns``.

$($rows -join "`n")

### Latency (C00 L6)

``latency.enforced=$latEnforced`` · threshold **$($latencyInfo.ThresholdPercent)%** · HTTP load-smoke max p95 **$($latencyInfo.HttpMaxP95Ms) ms**.

$($latRows -join "`n")

CI fails when any Criterion mean exceeds ``budget_mean_ns``. $latFailureNote
"@
    exit 0
}

$oldSampleSize = $env:SESSION_LEDGER_BENCH_SAMPLE_SIZE
$oldWarmUp = $env:SESSION_LEDGER_BENCH_WARM_UP_SECONDS
$oldMeasurement = $env:SESSION_LEDGER_BENCH_MEASUREMENT_SECONDS

try {
    $env:SESSION_LEDGER_BENCH_SAMPLE_SIZE = [string]$SampleSize
    $env:SESSION_LEDGER_BENCH_WARM_UP_SECONDS = [string]$WarmUpSeconds
    $env:SESSION_LEDGER_BENCH_MEASUREMENT_SECONDS = [string]$MeasurementSeconds

    Push-Location $repoRoot
    try {
        Write-Host "Running pipeline Criterion suite with sample_size=$SampleSize, warm_up=${WarmUpSeconds}s, measurement=${MeasurementSeconds}s..."
        & cargo bench --locked --bench pipeline -- --save-baseline current
        if ($LASTEXITCODE -ne 0) {
            throw "cargo bench failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    $current = Get-CurrentMeasurements

    if ($UpdateBaseline) {
        if ($ThresholdPercent -lt 0) {
            if (Test-Path -LiteralPath $BaselinePath -PathType Leaf) {
                $existing = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
                $ThresholdPercent = [double]$existing.policy.threshold_percent
            }
            else {
                $ThresholdPercent = 25.0
            }
        }

        $latencyThreshold = $ThresholdPercent
        $httpMaxP95Ms = 500.0
        $httpMinSuccess = 99.0
        $latencyEnforced = $true
        if (Test-Path -LiteralPath $BaselinePath -PathType Leaf) {
            $existing = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
            if ($null -ne $existing.latency -and $null -ne $existing.latency.threshold_percent) {
                $latencyThreshold = [double]$existing.latency.threshold_percent
            }
            if ($null -ne $existing.latency -and $existing.latency.PSObject.Properties.Name -contains "enforced") {
                $latencyEnforced = [bool]$existing.latency.enforced
            }
            if ($null -ne $existing.latency -and $null -ne $existing.latency.http_load_smoke) {
                if ($null -ne $existing.latency.http_load_smoke.max_p95_ms) {
                    $httpMaxP95Ms = [double]$existing.latency.http_load_smoke.max_p95_ms
                }
                if ($null -ne $existing.latency.http_load_smoke.min_success_rate_percent) {
                    $httpMinSuccess = [double]$existing.latency.http_load_smoke.min_success_rate_percent
                }
            }
        }

        $benchmarkBaselines = [ordered]@{}
        $latencyBaselines = [ordered]@{}
        foreach ($entry in $current.GetEnumerator()) {
            $meanNs = [Math]::Round([double]$entry.Value, 3)
            $budgetNs = [Math]::Ceiling($meanNs * (1.0 + ($ThresholdPercent / 100.0)) * 1000.0) / 1000.0
            $benchmarkBaselines[$entry.Key] = [ordered]@{
                mean_ns        = $meanNs
                budget_mean_ns = $budgetNs
            }

            $benchName = $entry.Key -replace '^pipeline/', ''
            $p95Raw = Get-CriterionP95Ns -BenchmarkName $benchName
            $p95Source = "criterion_sample_json"
            if ($null -eq $p95Raw) {
                $p95Raw = $meanNs * 1.15
                $p95Source = "synthetic_mean_x1_15"
            }
            $p95Ns = [Math]::Round([double]$p95Raw, 3)
            $budgetP95 = [Math]::Ceiling($p95Ns * (1.0 + ($latencyThreshold / 100.0)) * 1000.0) / 1000.0
            $latencyBaselines[$entry.Key] = [ordered]@{
                p95_ns        = $p95Ns
                budget_p95_ns = $budgetP95
                p95_source    = $p95Source
            }
        }

        $baseline = [ordered]@{
            schema_version      = 2
            suite               = "benches/pipeline.rs"
            criterion_baseline  = "current"
            units               = "nanoseconds"
            policy              = [ordered]@{
                enforced             = $true
                threshold_percent    = [double]$ThresholdPercent
                sample_size          = $SampleSize
                warm_up_seconds      = $WarmUpSeconds
                measurement_seconds  = $MeasurementSeconds
                update_command       = "./scripts/bench-gate.ps1 -UpdateBaseline"
                self_check_command   = "./scripts/bench-gate.ps1 -SelfCheck"
                notes                = @(
                    "CI job 'pipeline perf regression gate' is blocking (no continue-on-error).",
                    "A run fails when any current mean exceeds budget_mean_ns (baseline mean + threshold_percent)."
                )
            }
            latency             = [ordered]@{
                enforced            = $latencyEnforced
                threshold_percent   = [double]$latencyThreshold
                units               = "nanoseconds"
                metric              = "criterion_sample_p95"
                notes               = @(
                    "C00 L6 latency budgets: checked-in p95 baselines with the same regression threshold as mean budgets.",
                    "When latency.enforced=true, p95 overruns fail the blocking pipeline perf gate.",
                    "Refresh via ./scripts/bench-gate.ps1 -UpdateBaseline (writes p95_source per benchmark).",
                    "HTTP load-smoke p95 SLO (ms) is recorded under http_load_smoke for ops alignment with scripts/load-smoke.ps1."
                )
                p95_refresh         = [ordered]@{
                    source  = "criterion_sample_json"
                    command = "./scripts/bench-gate.ps1 -UpdateBaseline"
                }
                http_load_smoke     = [ordered]@{
                    max_p95_ms                 = $httpMaxP95Ms
                    min_success_rate_percent   = $httpMinSuccess
                    script                     = "scripts/load-smoke.ps1"
                    workflow                   = ".github/workflows/ops-load.yml"
                }
                benchmarks          = $latencyBaselines
            }
            benchmarks          = $benchmarkBaselines
        }

        $baselineDir = Split-Path -Parent $BaselinePath
        New-Item -ItemType Directory -Force -Path $baselineDir | Out-Null
        $baseline | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $BaselinePath -Encoding utf8
        Write-Host "Updated performance baseline at $BaselinePath."
        return
    }

    if (-not (Test-Path -LiteralPath $BaselinePath -PathType Leaf)) {
        throw "Baseline not found at '$BaselinePath'. Run ./scripts/bench-gate.ps1 -UpdateBaseline after reviewing local measurements."
    }

    $baseline = Get-Content -LiteralPath $BaselinePath -Raw | ConvertFrom-Json
    $policyThreshold = Assert-BaselinePolicy -Baseline $baseline -Path $BaselinePath
    $latencyInfo = Assert-LatencyPolicy -Baseline $baseline -Path $BaselinePath
    if ($ThresholdPercent -lt 0) {
        $ThresholdPercent = $policyThreshold
    }

    Write-Host ("Gate threshold: fail when current mean exceeds budget_mean_ns (>{0:N1}% slower than baseline)." -f $ThresholdPercent)
    Write-Host "Enforcement: blocking (policy.enforced=true)."
    Write-Host ("Latency: compare Criterion sample p95 vs budget_p95_ns (latency.enforced={0}, threshold={1:N1}%)." -f `
        $(if ($latencyInfo.Enforced) { "true" } else { "false" }), $latencyInfo.ThresholdPercent)

    $failures = [System.Collections.Generic.List[string]]::new()
    $latencyWarnings = [System.Collections.Generic.List[string]]::new()
    $resultRows = [System.Collections.Generic.List[object]]::new()
    $latencyRows = [System.Collections.Generic.List[object]]::new()
    $summaryRows = New-Object System.Collections.Generic.List[string]
    $summaryRows.Add("| Benchmark | Baseline | Current | Budget | Delta | Result |")
    $summaryRows.Add("|---|---:|---:|---:|---:|:---:|")
    $latencySummaryRows = New-Object System.Collections.Generic.List[string]
    $latencySummaryRows.Add("| Benchmark | Baseline p95 | Current p95 | Budget p95 | Delta | Result |")
    $latencySummaryRows.Add("|---|---:|---:|---:|---:|:---:|")

    foreach ($name in $benchmarkNames) {
        $key = Get-BenchmarkKey -BenchmarkName $name
        if (-not $current.Contains($key)) {
            throw "Current Criterion output is missing '$key'."
        }

        $entry = Get-BaselineBenchmarkEntry -Benchmarks $baseline.benchmarks -Key $key
        $baselineMean = [double]$entry.mean_ns
        $currentMean = [double]$current[$key]
        if ($entry.PSObject.Properties.Name -contains "budget_mean_ns") {
            $budgetMean = [double]$entry.budget_mean_ns
        }
        else {
            $budgetMean = $baselineMean * (1.0 + ($ThresholdPercent / 100.0))
        }
        $deltaPercent = (($currentMean - $baselineMean) / $baselineMean) * 100.0
        $passed = $currentMean -le $budgetMean

        Write-Host ("{0}: baseline={1:N0} ns current={2:N0} ns delta={3:N1}% budget={4:N0} ns => {5}" -f `
            $key, $baselineMean, $currentMean, $deltaPercent, $budgetMean, $(if ($passed) { "PASS" } else { "FAIL" }))

        $summaryRows.Add(("| `{0}` | {1:N0} | {2:N0} | {3:N0} | {4:N1}% | {5} |" -f `
            $key, $baselineMean, $currentMean, $budgetMean, $deltaPercent, $(if ($passed) { "PASS" } else { "FAIL" })))

        $resultRows.Add([ordered]@{
                benchmark      = $key
                baseline_ns    = [Math]::Round($baselineMean, 3)
                current_ns     = [Math]::Round($currentMean, 3)
                budget_ns      = [Math]::Round($budgetMean, 3)
                delta_percent  = [Math]::Round($deltaPercent, 3)
                passed         = $passed
            })

        if (-not $passed) {
            $failures.Add(("{0} exceeded budget: current {1:N0} ns > budget {2:N0} ns ({3:N1}% vs allowed {4:N1}%)." -f `
                $key, $currentMean, $budgetMean, $deltaPercent, $ThresholdPercent))
        }

        # C00 L6 p95 latency comparison (blocking when latency.enforced=true).
        $latEntry = Get-BaselineBenchmarkEntry -Benchmarks $baseline.latency.benchmarks -Key $key
        $baselineP95 = [double]$latEntry.p95_ns
        if ($latEntry.PSObject.Properties.Name -contains "budget_p95_ns") {
            $budgetP95 = [double]$latEntry.budget_p95_ns
        }
        else {
            $budgetP95 = $baselineP95 * (1.0 + ($latencyInfo.ThresholdPercent / 100.0))
        }
        $currentP95 = Get-CriterionP95Ns -BenchmarkName $name
        if ($null -eq $currentP95) {
            $latencySummaryRows.Add(("| `{0}` | {1:N0} | n/a | {2:N0} | n/a | SKIP |" -f `
                $key, $baselineP95, $budgetP95))
            $latencyRows.Add([ordered]@{
                    benchmark      = $key
                    baseline_p95_ns = [Math]::Round($baselineP95, 3)
                    current_p95_ns  = $null
                    budget_p95_ns   = [Math]::Round($budgetP95, 3)
                    delta_percent   = $null
                    passed          = $null
                    skipped         = $true
                })
            Write-Host ("{0} latency: sample.json missing — SKIP p95 check." -f $key) -ForegroundColor Yellow
        }
        else {
            $latDelta = (($currentP95 - $baselineP95) / $baselineP95) * 100.0
            $latPassed = $currentP95 -le $budgetP95
            $latLabel = if ($latPassed) { "PASS" } else { $(if ($latencyInfo.Enforced) { "FAIL" } else { "WARN" }) }

            Write-Host ("{0} latency: baseline_p95={1:N0} ns current_p95={2:N0} ns delta={3:N1}% budget={4:N0} ns => {5}" -f `
                $key, $baselineP95, $currentP95, $latDelta, $budgetP95, $latLabel)

            $latencySummaryRows.Add(("| `{0}` | {1:N0} | {2:N0} | {3:N0} | {4:N1}% | {5} |" -f `
                $key, $baselineP95, $currentP95, $budgetP95, $latDelta, $latLabel))

            $latencyRows.Add([ordered]@{
                    benchmark       = $key
                    baseline_p95_ns = [Math]::Round($baselineP95, 3)
                    current_p95_ns  = [Math]::Round($currentP95, 3)
                    budget_p95_ns   = [Math]::Round($budgetP95, 3)
                    delta_percent   = [Math]::Round($latDelta, 3)
                    passed          = $latPassed
                    skipped         = $false
                })

            if (-not $latPassed) {
                $msg = ("{0} exceeded p95 budget: current {1:N0} ns > budget {2:N0} ns ({3:N1}% vs allowed {4:N1}%)." -f `
                    $key, $currentP95, $budgetP95, $latDelta, $latencyInfo.ThresholdPercent)
                if ($latencyInfo.Enforced) {
                    $failures.Add($msg)
                }
                else {
                    $latencyWarnings.Add($msg)
                    Write-Host "WARN: $msg" -ForegroundColor Yellow
                }
            }
        }
    }

    $artifactDir = Split-Path -Parent $ArtifactPath
    if ($artifactDir) {
        New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
    }
    $latencyPassed = ($latencyWarnings.Count -eq 0) -and `
        (@($latencyRows | Where-Object { $null -ne $_.passed -and $_.passed -eq $false }).Count -eq 0)
    $artifact = [ordered]@{
        schema_version     = 1
        enforced           = $true
        threshold_percent  = $ThresholdPercent
        baseline_path      = $BaselinePath
        passed             = ($failures.Count -eq 0)
        results            = @($resultRows)
        latency            = [ordered]@{
            enforced           = [bool]$latencyInfo.Enforced
            threshold_percent  = $latencyInfo.ThresholdPercent
            soft               = -not [bool]$latencyInfo.Enforced
            passed             = $latencyPassed
            warnings           = @($latencyWarnings)
            results            = @($latencyRows)
            http_load_smoke_max_p95_ms = $latencyInfo.HttpMaxP95Ms
        }
    }
    $artifact | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ArtifactPath -Encoding utf8
    Write-Host "Wrote gate artifact: $ArtifactPath"

    if ($failures.Count -gt 0) {
        Write-GateSummary -Title "Pipeline perf-budget gate FAILED" -Body @"
Blocking gate failed (``policy.enforced=true``). Threshold: **${ThresholdPercent}%**.

$($summaryRows -join "`n")

### Latency (C00 L6)

$($latencySummaryRows -join "`n")

Failures:
$($failures | ForEach-Object { "- $_" } | Out-String)
"@
        foreach ($failure in $failures) {
            Write-Host "ERROR: $failure" -ForegroundColor Red
        }
        exit 1
    }

    $latencyNote = ""
    if ($latencyWarnings.Count -gt 0) {
        $latencyNote = @"

Latency warnings (non-blocking while ``latency.enforced=false``):
$($latencyWarnings | ForEach-Object { "- $_" } | Out-String)
"@
    }

    Write-GateSummary -Title "Pipeline perf-budget gate passed" -Body @"
Blocking gate passed (``policy.enforced=true``). Threshold: **${ThresholdPercent}%**.

$($summaryRows -join "`n")

### Latency (C00 L6)

``latency.enforced=$(if ($latencyInfo.Enforced) { "true" } else { "false" })`` · threshold **$($latencyInfo.ThresholdPercent)%**.

$($latencySummaryRows -join "`n")
$latencyNote
"@
    Write-Host "Pipeline performance gate passed."
    if ($latencyWarnings.Count -gt 0) {
        Write-Host ("Latency warnings: {0} (non-blocking)." -f $latencyWarnings.Count) -ForegroundColor Yellow
    }
}
finally {
    $env:SESSION_LEDGER_BENCH_SAMPLE_SIZE = $oldSampleSize
    $env:SESSION_LEDGER_BENCH_WARM_UP_SECONDS = $oldWarmUp
    $env:SESSION_LEDGER_BENCH_MEASUREMENT_SECONDS = $oldMeasurement
}
