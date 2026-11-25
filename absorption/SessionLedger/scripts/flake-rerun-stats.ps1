#Requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$statsPath = Join-Path $repoRoot 'docs/ops/flake-rerun-stats.json'
$repeats = if ($env:FLAKE_RERUN_REPEATS) { [int]$env:FLAKE_RERUN_REPEATS } else { 3 }
$quarantineArgs = @(& (Join-Path $PSScriptRoot 'flake-quarantine-apply.ps1'))

$runs = @()
$failures = 0

for ($run = 1; $run -le $repeats; $run++) {
    Write-Host "flake rerun ${run}/${repeats}: cargo test --test properties"
    Push-Location $repoRoot
    try {
        cargo test --test properties --locked @quarantineArgs
        $exit = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    $passed = $exit -eq 0
    if (-not $passed) {
        $failures++
    }
    $runs += [ordered]@{
        run = $run
        passed = $passed
        exit_code = $exit
    }
}

$stats = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    target = 'cargo test --test properties'
    repeats = $repeats
    failures = $failures
    runs = $runs
}

$stats | ConvertTo-Json -Depth 4 | Set-Content -Path $statsPath -Encoding utf8
Write-Host "flake rerun stats written to $statsPath (failures=$failures/$repeats)"

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Property rerun stats

| Run | Result |
|-----|--------|
$(foreach ($entry in $runs) { "| $($entry.run) | $(if ($entry.passed) { 'pass' } else { 'fail' }) |`n" })
| **failures** | **$failures / $repeats** |
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

if ($failures -gt 0) {
    throw "property tests failed in $failures of $repeats reruns — record evidence in docs/ops/flakes-records.json before quarantine"
}
