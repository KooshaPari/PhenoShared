#Requires -Version 5.1
# Run local TB2 full matrix sequentially: LFM then Ornith (one GPU).
[CmdletBinding()]
param(
    [ValidateSet("lfm", "ornith", "both")]
    [string]$Which = "both",
    [int]$ContextSize = 16384,
    [int]$MaxTokens = 4096,
    [int]$MaxTurns = 8
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$startLlama = Join-Path $PSScriptRoot "start_llama_local.ps1"
$runLocal = Join-Path $PSScriptRoot "run_tbench_local.ps1"
$models = @()
if ($Which -eq "both" -or $Which -eq "lfm") {
    $models += @{ Key = "lfm"; Harbor = "openai/local/lfm25-8b-a1b"; Job = ("local-lfm25-full-" + (Get-Date -Format "yyyyMMdd")) }
}
if ($Which -eq "both" -or $Which -eq "ornith") {
    $models += @{ Key = "ornith"; Harbor = "openai/local/ornith-8b"; Job = ("local-ornith-full-" + (Get-Date -Format "yyyyMMdd")) }
}
foreach ($m in $models) {
    Write-Host ""
    Write-Host ("==== " + $m.Key + " full TB2 ====") -ForegroundColor Cyan
    & $startLlama -Model $m.Key -ContextSize $ContextSize -ParallelSlots 1
    $logDir = Join-Path $Root ("jobs\harbor\tbench\" + $m.Job)
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $out = Join-Path $logDir "run.log"
    $env:OPENAI_API_KEY = "local-no-key"
    $env:DOCKER_HOST = "npipe:////./pipe/docker_engine"
    $env:PHENO_PODMAN_PIPE = "npipe:////./pipe/docker_engine"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONPATH = $Root
    $code = 0
    try {
        & $runLocal -Full -Model $m.Harbor `
            -ApiBase "http://127.0.0.1:8000/v1" `
            -ContainerApiBase "http://127.0.0.1:8000/v1" `
            -ServerHealthUrl "http://127.0.0.1:8000/health" `
            -UpstreamHealthUrl "http://127.0.0.1:8000/health" `
            -MaxTokens $MaxTokens -MaxTurns $MaxTurns -ContextSize $ContextSize `
            2>&1 | Tee-Object -FilePath $out
        $code = $LASTEXITCODE
    } catch {
        $_ | Out-File -FilePath $out -Append -Encoding ascii
        $code = 1
    }
    ("EXIT=" + $code + " " + (Get-Date -Format o)) | Out-File -Append $out -Encoding ascii
    if ($code -ne 0) {
        Write-Warning ($m.Key + " exited " + $code + " see " + $out)
    }
}
Write-Host "Matrix complete." -ForegroundColor Green
