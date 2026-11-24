<#
.SYNOPSIS
Runs a concurrent, headless load smoke test against sl-daemon.

.DESCRIPTION
Distributes requests across probe and/or macro HTTP routes on sl-daemon, then
fails when the requested success-rate or p95 latency SLO is missed.

Route tiers (see docs/ops/load-macro-gate.md):
  probe — /healthz, /readyz, /api/metrics, /metrics (default)
  macro — /api/bundles, /api/search?limit=1, /api/stream
  all   — probe + macro
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8080",

    [ValidateSet("probe", "macro", "all")]
    [string]$RouteTier = "probe",

    [ValidateRange(4, 1000000)]
    [int]$Requests = 400,

    [ValidateRange(1, 10000)]
    [int]$Concurrency = 20,

    [ValidateRange(1, 3600)]
    [int]$TimeoutSeconds = 10,

    [ValidateRange(0, 100)]
    [double]$MinSuccessRate = 99,

    [ValidateRange(1, 600000)]
    [double]$MaxP95Ms = 500
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required for ForEach-Object -Parallel."
}

$normalizedBaseUrl = $BaseUrl.TrimEnd("/")
$probeEndpoints = @("/healthz", "/readyz", "/api/metrics", "/metrics")
$macroEndpoints = @("/api/bundles", "/api/search?limit=1", "/api/stream")
$endpoints = switch ($RouteTier) {
    "probe" { $probeEndpoints }
    "macro" { $macroEndpoints }
    "all" { $probeEndpoints + $macroEndpoints }
    default { throw "Unsupported RouteTier '$RouteTier'." }
}
$streamEndpoints = @($endpoints | Where-Object { $_ -match "/api/stream$" })
$parallelEndpoints = @($endpoints | Where-Object { $_ -notmatch "/api/stream$" })
if ($parallelEndpoints.Count -eq 0) {
    throw "No parallel-safe endpoints configured for RouteTier '$RouteTier'."
}

$results = [System.Collections.Generic.List[object]]::new()
foreach ($streamEndpoint in $streamEndpoints) {
    $url = "$normalizedBaseUrl$streamEndpoint"
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $statusCode = 0
    $errorMessage = $null
    $streamJob = Start-Job -ScriptBlock {
        param($ProbeUrl)
        try {
            $handler = [System.Net.Http.SocketsHttpHandler]::new()
            $client = [System.Net.Http.HttpClient]::new($handler)
            $client.Timeout = [TimeSpan]::FromSeconds(5)
            $response = $client.GetAsync(
                $ProbeUrl,
                [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
            ).GetAwaiter().GetResult()
            $statusCode = [int]$response.StatusCode
            $response.Dispose()
            $client.Dispose()
            return [pscustomobject]@{
                StatusCode = $statusCode
                Error = $null
            }
        }
        catch {
            return [pscustomobject]@{
                StatusCode = 0
                Error = $_.Exception.Message
            }
        }
    } -ArgumentList $url

    $completed = Wait-Job -Job $streamJob -Timeout 5
    if (-not $completed) {
        Stop-Job -Job $streamJob -ErrorAction SilentlyContinue
        $errorMessage = "stream probe timed out after 5s"
    }
    else {
        $probe = Receive-Job -Job $streamJob
        $statusCode = [int]$probe.StatusCode
        $errorMessage = $probe.Error
    }
    Remove-Job -Job $streamJob -Force -ErrorAction SilentlyContinue
    $stopwatch.Stop()

    $results.Add([pscustomobject]@{
        Endpoint = $streamEndpoint
        StatusCode = $statusCode
        Success = $statusCode -ge 200 -and $statusCode -lt 300
        LatencyMs = $stopwatch.Elapsed.TotalMilliseconds
        Error = $errorMessage
    })
}

$work = for ($i = 0; $i -lt $Requests; $i++) {
    [pscustomobject]@{ Endpoint = $parallelEndpoints[$i % $parallelEndpoints.Count] }
}

Write-Host "Sending $Requests parallel requests to $normalizedBaseUrl (tier: $RouteTier, concurrency: $Concurrency)..."
if ($streamEndpoints.Count -gt 0) {
    Write-Host "Probing $($streamEndpoints.Count) SSE route(s) serially with 2s connect timeout."
}

$parallelResults = @($work | ForEach-Object -Parallel {
    $endpoint = $_.Endpoint
    $url = "$using:normalizedBaseUrl$endpoint"
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $statusCode = 0
    $errorMessage = $null

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $statusCode = 0
    $errorMessage = $null

    try {
        $response = Invoke-WebRequest `
            -Uri $url `
            -Method Get `
            -TimeoutSec $using:TimeoutSeconds `
            -SkipHttpErrorCheck
        $statusCode = [int]$response.StatusCode
    }
    catch {
        $errorMessage = $_.Exception.Message
    }
    finally {
        $stopwatch.Stop()
    }

    [pscustomobject]@{
        Endpoint = $endpoint
        StatusCode = $statusCode
        Success = $statusCode -ge 200 -and $statusCode -lt 300
        LatencyMs = $stopwatch.Elapsed.TotalMilliseconds
        Error = $errorMessage
    }
} -ThrottleLimit $Concurrency)

foreach ($row in $parallelResults) {
    $results.Add($row)
}

$results = @($results)

$successful = @($results | Where-Object Success).Count
$successRate = 100.0 * $successful / $results.Count
$sortedLatencies = @($results.LatencyMs | Sort-Object)
$p95Index = [Math]::Max(0, [Math]::Ceiling(0.95 * $sortedLatencies.Count) - 1)
$p95Ms = $sortedLatencies[$p95Index]

$results |
    Group-Object Endpoint |
    ForEach-Object {
        $endpointResults = @($_.Group)
        $endpointSuccesses = @($endpointResults | Where-Object Success).Count
        [pscustomobject]@{
            Endpoint = $_.Name
            Requests = $endpointResults.Count
            SuccessRate = "{0:N2}%" -f (100.0 * $endpointSuccesses / $endpointResults.Count)
            AverageMs = "{0:N2}" -f (($endpointResults.LatencyMs | Measure-Object -Average).Average)
        }
    } |
    Sort-Object Endpoint |
    Format-Table -AutoSize

Write-Host ("Overall: {0}/{1} successful ({2:N2}%), p95={3:N2} ms" -f `
    $successful, $results.Count, $successRate, $p95Ms)
Write-Host ("SLO: success rate >= {0:N2}%, p95 <= {1:N2} ms" -f `
    $MinSuccessRate, $MaxP95Ms)

$failures = @($results | Where-Object { -not $_.Success })
if ($failures.Count -gt 0) {
    Write-Host "Sample failures:"
    $failures |
        Select-Object -First 5 Endpoint, StatusCode, Error |
        Format-Table -AutoSize
}

if ($successRate -lt $MinSuccessRate -or $p95Ms -gt $MaxP95Ms) {
    Write-Error "Load smoke SLO failed."
    exit 1
}

Write-Host "Load smoke SLO passed."
