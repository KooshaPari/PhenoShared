#Requires -Version 5.1
<#
.SYNOPSIS
  Start/restart llama-server on :8000 for local TB2 (one GPU slot).

.EXAMPLE
  .\harbor\start_llama_local.ps1 -Model qwen
  .\harbor\start_llama_local.ps1 -Model lfm -ContextSize 16384
#>
[CmdletBinding()]
param(
    [ValidateSet("qwen", "lfm", "ornith")]
    [string]$Model = "qwen",
    [int]$Port = 8000,
    [int]$ContextSize = 16384,
    [int]$GpuLayers = 99,
    [int]$ParallelSlots = 1,
    [string]$LlamaServer = "D:\WSL\tools\llama.cpp-b10012-cuda12.4\llama-server.exe",
    [switch]$StopOnly
)
$ErrorActionPreference = "Stop"
$weights = @{
    qwen   = @{ Path = "D:\WSL\model-cache\qwen35-08b-q4\qwen35-08b.Q4_K_M.gguf"; Alias = "local/qwen35-08b" }
    lfm    = @{ Path = "D:\WSL\model-cache\lfm25-8b-a1b-q4\lfm25-8b-a1b.Q4_K_M.gguf"; Alias = "local/lfm25-8b-a1b" }
    ornith = @{ Path = "D:\WSL\model-cache\ornith-mtp-q4\Ornith-1.0-9B-MTP-Q4_K_M.gguf"; Alias = "local/ornith-8b" }
}
# Resolve actual gguf paths (cache layout may vary)
function Find-Gguf([string]$HintDir, [string]$Pattern) {
    if (Test-Path $HintDir) {
        $hit = Get-ChildItem $HintDir -Filter $Pattern -Recurse -File -EA SilentlyContinue | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}
Get-Process llama-server -EA SilentlyContinue | Stop-Process -Force
if ($StopOnly) { Write-Host "Stopped llama-server"; return }
if (-not (Test-Path $LlamaServer)) { throw "llama-server not found: $LlamaServer" }
$spec = $weights[$Model]
$gguf = $spec.Path
if (-not (Test-Path $gguf)) {
    $root = Split-Path $gguf -Parent
    $gguf = Find-Gguf (Split-Path $root -Parent) "*.Q4_K_M.gguf"
    if (-not $gguf) { throw "Weights not found for $Model (expected $($spec.Path))" }
}
$alias = $spec.Alias
Write-Host "==> llama-server model=$Model alias=$alias -c $ContextSize -np $ParallelSlots port=$Port"
$args = @("-m", $gguf, "--port", "$Port", "--host", "127.0.0.1", "-ngl", "$GpuLayers", "-c", "$ContextSize", "-np", "$ParallelSlots", "--alias", $alias)
Start-Process -FilePath $LlamaServer -ArgumentList $args -WindowStyle Hidden
$end = (Get-Date).AddSeconds(300)
do {
    try {
        $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/health" -TimeoutSec 2
        if ([int]$r.StatusCode -lt 300) { Write-Host "ready http://127.0.0.1:$Port (alias $alias)"; return }
    } catch {}
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $end)
throw "llama-server did not become ready on :$Port"
