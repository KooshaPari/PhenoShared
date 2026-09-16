# Quick dual-GPU llama.cpp smoke for pheno-harness placement policy.
# CUDA order (llama.cpp): CUDA0 = RTX 3090 Ti, CUDA1 = GTX 1080 Ti
# Use CUDA_VISIBLE_DEVICES to isolate each card.

param(
    [switch]$Execute,
    [string]$WindowId = "",
    [ValidateRange(1, 24564)]
    [int]$MinimumFreeMiB = 4096
)

$ErrorActionPreference = "Stop"
$ContractPath = Join-Path $PSScriptRoot "..\config\desktop_nvidia_qwen35_lane.yaml"
$Bench = "D:\WSL\tools\llama.cpp-b10012-cuda12.4\llama-bench.exe"
$Model = "D:\WSL\model-cache\qwen35-08b-q4\qwen35-08b.Q4_K_M.gguf"

function Assert-DesktopExecutionAuthority {
    # A window identifier is traceability data, not an authorization credential.
    # No owner-issued, bound, expiring authorization contract exists yet, so a
    # direct entry point must never convert a caller-provided string into a run.
    throw "Direct dual-GPU smoke is disabled: no owner-issued desktop execution authorization contract exists"
}

function Assert-DesktopExecutionPolicy {
    if (-not $Execute) {
        throw "-Execute is required; direct smoke is disabled by default"
    }
    if ([string]::IsNullOrWhiteSpace($WindowId)) {
        throw "-WindowId is required; obtain an explicit desktop execution authorization first"
    }
    if (-not (Test-Path $ContractPath -PathType Leaf)) {
        throw "desktop lane contract is missing: $ContractPath"
    }
    $contract = Get-Content -Raw -Path $ContractPath
    $required = @(
        "(?m)^status:\s*active\s*$",
        "(?m)^\s*allow_model_inference:\s*true\s*$",
        "(?m)^\s*allow_benchmark_execution:\s*true\s*$"
    )
    foreach ($pattern in $required) {
        if ($contract -notmatch $pattern) {
            throw "desktop execution policy is not active for direct smoke"
        }
    }
}

function Assert-DualGpuHeadroom {
    $rows = @(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>$null)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -eq 0) {
        throw "nvidia-smi headroom preflight failed; refusing direct smoke"
    }
    $freeByIndex = @{}
    foreach ($row in $rows) {
        $parts = $row -split ","
        if ($parts.Count -lt 2) {
            throw "nvidia-smi headroom preflight returned an invalid row: $row"
        }
        $freeByIndex[[int]$parts[0].Trim()] = [int]$parts[1].Trim()
    }
    foreach ($required in @(@{ role = "helper"; index = 0 }, @{ role = "primary"; index = 1 })) {
        if (-not $freeByIndex.ContainsKey($required.index) -or $freeByIndex[$required.index] -lt $MinimumFreeMiB) {
            throw "$($required.role) physical GPU index $($required.index) needs ${MinimumFreeMiB} MiB free"
        }
    }
}

Assert-DesktopExecutionAuthority
Assert-DesktopExecutionPolicy
Assert-DualGpuHeadroom

if (-not (Test-Path $Bench)) { throw "Missing llama-bench: $Bench" }
if (-not (Test-Path $Model)) { throw "Missing model: $Model" }

function Invoke-GpuSmoke {
    param([string]$Label, [string]$CudaVisible)
    Write-Host "`n=== $Label (CUDA_VISIBLE_DEVICES=$CudaVisible) ===" -ForegroundColor Cyan
    $env:CUDA_VISIBLE_DEVICES = $CudaVisible
    & $Bench -m $Model -ngl 99 -dev CUDA0 -mg 0 -p 128 -n 64 -r 1 -b 512 -ub 512
}

Invoke-GpuSmoke -Label "RTX 3090 Ti (primary)" -CudaVisible "0"
Invoke-GpuSmoke -Label "GTX 1080 Ti (helper)" -CudaVisible "1"

# nvidia-smi index 0=1080, 1=3090; llama.cpp CUDA0=3090 when both visible.
# Isolate with CUDA_VISIBLE_DEVICES: 0→3090, 1→1080.

Write-Host "`nDone. Record tg64 tok/s for hardware_aware_placement.yaml updates." -ForegroundColor Green
