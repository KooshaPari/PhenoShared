# Dual-GPU serving stack for pheno-harness heterogeneous host.
# GTX 1080 Ti (helper): llama-server on Windows, port 8082.
# RTX 3090 Ti (primary): vLLM in WSL by default, port 8000.
# pheno-serve-dev proxy: port 21080 (config/pheno_serve.yaml).
#
# CUDA isolation (llama.cpp / Windows):
# CUDA index maps differ by runtime (critical):
#   nvidia-smi / WSL PyTorch/SGLang/vLLM: 0=1080 Ti, 1=3090 Ti  → use CVD=1 for 3090
#   Windows llama.cpp (this host's smoke): 0=3090 Ti, 1=1080 Ti → helper uses CVD=1
#
# Usage:
#   powershell -File scripts\start_dual_gpu_stack.ps1
#   powershell -File scripts\start_dual_gpu_stack.ps1 -SmokeOnly
#   powershell -File scripts\start_dual_gpu_stack.ps1 -PreflightOnly -PreflightOutput preflight.json

param(
    [switch]$SmokeOnly,
    [switch]$PreflightOnly,
    [switch]$HelperOnly,
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Distro = "Ubuntu-22.04",
    [string]$PhenoConfig = (Join-Path $PSScriptRoot "..\config\pheno_serve.yaml"),
    [string]$WindowId = "",
    [string]$PreflightOutput = "",
    [ValidateSet("vllm", "sglang")]
    [string]$PrimaryRuntime = "vllm",
    [int]$HelperPort = 8082,
    [int]$PrimaryPort = 8000,
    [int]$PhenoPort = 21080,
    [int]$ReadinessTimeoutSeconds = 30,
    [ValidateRange(0, 900)]
    [int]$HoldOpenSeconds = 0,
    [int]$MinimumFreeMiB = 4096
)

$ErrorActionPreference = "Stop"

if (-not $PreflightOnly -and [string]::IsNullOrWhiteSpace($WindowId)) {
    throw "-WindowId is required; obtain an explicit desktop execution authorization first"
}
if (-not $PreflightOnly) {
    # A free-form window ID is run provenance, not an authorization credential.
    # Keep every launch path disabled until an owner-issued, bound authority
    # contract exists; -PreflightOnly remains the safe capability-record path.
    throw "Desktop launch is disabled: no owner-issued desktop execution authorization contract exists"
}

function ConvertTo-WslPath([string]$WindowsPath) {
    if (-not $WindowsPath) { return $null }
    $resolved = (Resolve-Path $WindowsPath -ErrorAction SilentlyContinue).Path
    if (-not $resolved) { $resolved = $WindowsPath }
    $drive = $resolved.Substring(0, 1).ToLower()
    $rest = ($resolved -replace '\\', '/').Substring(2)
    return "/mnt/$drive$rest"
}

function Test-PhenoServeModule {
    param([string]$RepoRoot)
    $serverPy = Join-Path $RepoRoot "pheno\serve\server.py"
    if (-not (Test-Path $serverPy)) {
        return $false
    }
    try {
        Push-Location $RepoRoot
        python -c "import pheno.serve.server" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        Pop-Location
    }
}

function Test-PortAvailable([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -eq $listener
}

function Get-ContractSha256([string]$Path) {
    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "desktop lane contract is missing: $Path"
    }
    $source = [System.IO.File]::ReadAllBytes($Path)
    $normalized = New-Object System.IO.MemoryStream
    for ($index = 0; $index -lt $source.Length; $index++) {
        if ($source[$index] -eq 13) {
            if (($index + 1) -lt $source.Length -and $source[$index + 1] -eq 10) {
                $index++
            }
            $normalized.WriteByte(10)
        } else {
            $normalized.WriteByte($source[$index])
        }
    }
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($normalized.ToArray()))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha256.Dispose()
        $normalized.Dispose()
    }
}

function Get-DesktopGpuInventory {
    $rows = @(nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.free,driver_version --format=csv,noheader,nounits 2>$null)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -eq 0) {
        throw "nvidia-smi preflight failed; refusing to record an unproven topology"
    }
    $inventory = @()
    foreach ($row in $rows) {
        $parts = $row -split ","
        if ($parts.Count -lt 6) {
            throw "nvidia-smi preflight returned an invalid row: $row"
        }
        $inventory += [PSCustomObject]@{
            index = [int]$parts[0].Trim()
            uuid = $parts[1].Trim()
            name = $parts[2].Trim()
            total_mib = [int]$parts[3].Trim()
            free_mib = [int]$parts[4].Trim()
            driver_version = $parts[5].Trim()
        }
    }
    return $inventory
}

function Write-PreflightRecord([string]$OutputPath, [object]$Record) {
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        throw "-PreflightOutput is required with -PreflightOnly"
    }
    if (Test-Path $OutputPath) {
        throw "preflight output already exists: $OutputPath"
    }
    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path $parent -PathType Container)) {
        throw "preflight output parent does not exist: $parent"
    }
    $json = $Record | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
}

function Assert-GpuMemoryBudget([int]$MinimumFree, [array]$Devices) {
    $rows = @(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits 2>$null)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -eq 0) {
        throw "nvidia-smi memory preflight failed; refusing to launch without GPU headroom evidence"
    }
    $freeByIndex = @{}
    foreach ($row in $rows) {
        $parts = $row -split ","
        if ($parts.Count -lt 2) {
            throw "nvidia-smi memory preflight returned an invalid row: $row"
        }
        $freeByIndex[[int]$parts[0].Trim()] = [int]$parts[1].Trim()
    }
    foreach ($device in $Devices) {
        if (-not $freeByIndex.ContainsKey($device.index)) {
            throw "nvidia-smi memory preflight did not report physical GPU index $($device.index)"
        }
        $free = $freeByIndex[$device.index]
        if ($free -lt $MinimumFree) {
            throw "$($device.role) GPU index $($device.index) has only ${free} MiB free; need ${MinimumFree} MiB"
        }
        Write-Host "  Memory: $($device.role) GPU index $($device.index) has ${free} MiB free" -ForegroundColor DarkGray
    }
}

if ($PreflightOnly) {
    $inventory = Get-DesktopGpuInventory
    $byIndex = @{}
    foreach ($gpu in $inventory) { $byIndex[$gpu.index] = $gpu }
    foreach ($required in @(@{ role = "helper"; index = 0 }, @{ role = "primary"; index = 1 })) {
        if (-not $byIndex.ContainsKey($required.index)) {
            throw "nvidia-smi preflight did not report $($required.role) physical GPU index $($required.index)"
        }
        if ($byIndex[$required.index].free_mib -lt $MinimumFreeMiB) {
            throw "$($required.role) physical GPU index $($required.index) has insufficient free memory"
        }
    }
    $contractPath = Join-Path $Root "config\desktop_nvidia_qwen35_lane.yaml"
    $record = [ordered]@{
        schema_version = "pheno.desktop-preflight.v1"
        created_at = [DateTime]::UtcNow.ToString("o")
        no_launch = $true
        contract = [ordered]@{
            path = "config/desktop_nvidia_qwen35_lane.yaml"
            sha256 = Get-ContractSha256 $contractPath
        }
        devices = @(
            [ordered]@{ role = "helper"; physical_index = 0; uuid = $byIndex[0].uuid; name = $byIndex[0].name; total_mib = $byIndex[0].total_mib; free_mib = $byIndex[0].free_mib; driver_version = $byIndex[0].driver_version },
            [ordered]@{ role = "primary"; physical_index = 1; uuid = $byIndex[1].uuid; name = $byIndex[1].name; total_mib = $byIndex[1].total_mib; free_mib = $byIndex[1].free_mib; driver_version = $byIndex[1].driver_version }
        )
        ports = @(
            [ordered]@{ port = $HelperPort; available = (Test-PortAvailable $HelperPort) },
            [ordered]@{ port = $PrimaryPort; available = (Test-PortAvailable $PrimaryPort) },
            [ordered]@{ port = $PhenoPort; available = (Test-PortAvailable $PhenoPort) }
        )
        runtime = [ordered]@{
            primary_runtime = $PrimaryRuntime
            distro = $Distro
            helper_port = $HelperPort
            primary_port = $PrimaryPort
            pheno_port = $PhenoPort
        }
    }
    Write-PreflightRecord -OutputPath $PreflightOutput -Record $record
    Write-Host "Preflight passed; no process was launched or stopped." -ForegroundColor Green
    exit 0
}

if ($SmokeOnly) {
    Write-Host "=== Dual-GPU smoke only ===" -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "run_dual_gpu_smoke.ps1")
    exit $LASTEXITCODE
}

Set-Location $Root

$helperPortAvailable = Test-PortAvailable $HelperPort
$primaryPortAvailable = Test-PortAvailable $PrimaryPort

$LlamaBinary = "D:\WSL\tools\llama.cpp-b10012-cuda12.4\llama-server.exe"
$HelperModel = "D:\WSL\model-cache\qwen35-08b-q4\qwen35-08b.Q4_K_M.gguf"
$SglangModel = if ($env:PHENO_QWEN35_08B_HF) { $env:PHENO_QWEN35_08B_HF } else { "Qwen/Qwen3.5-0.8B" }
$WslModel = if ($env:PHENO_QWEN35_08B_HF) { $env:PHENO_QWEN35_08B_HF } else { "/home/<REDACTED>/.cache/huggingface/hub/models--Qwen--Qwen3.5-0.8B/snapshots/2fc06364715b967f1860aea9cf38778875588b17" }
$WslVllmPython = if ($env:PHENO_VLLM_PYTHON) { $env:PHENO_VLLM_PYTHON } else { "/home/<REDACTED>/mambaforge/envs/vllm/bin/python" }
$WslVenv = "~/.pheno-serve-venv"
$CanonicalModel = "Qwen/Qwen3.5-0.8B"
$ModelAlias = "local/qwen35-08b"

function Wait-EndpointModel([int]$Port, [string]$RuntimeName) {
    $deadline = (Get-Date).AddSeconds($ReadinessTimeoutSeconds)
    $endpoint = "http://127.0.0.1:$Port/v1/models"
    do {
        try {
            $response = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 2
            $rows = if ($null -ne $response.data) { @($response.data) } else { @($response.models) }
            $ids = @($rows | ForEach-Object { [string]$_.id; [string]$_.name; [string]$_.model })
            if (($ids -contains $CanonicalModel) -or ($ids -contains $ModelAlias)) {
                Write-Host "  Ready: $RuntimeName advertises $($ids -join ', ')" -ForegroundColor Green
                return
            }
        } catch {
            # Startup is asynchronous; keep polling until the bounded deadline.
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "$RuntimeName on port $Port did not advertise $CanonicalModel or $ModelAlias within $ReadinessTimeoutSeconds seconds"
}

if ($HelperOnly) {
    Write-Host "=== pheno-harness helper-only stack ===" -ForegroundColor Cyan
    Write-Host "Window: $WindowId"
    Write-Host "[1080 Ti] llama-server helper on port $HelperPort" -ForegroundColor Yellow

    if (-not $helperPortAvailable) {
        Write-Host "  SKIP: port $HelperPort is already listening; no process will be stopped" -ForegroundColor Red
    } else {
        Assert-GpuMemoryBudget -MinimumFree $MinimumFreeMiB -Devices @(@{ role = "helper"; index = 0 })
        if (-not (Test-Path $LlamaBinary)) {
            throw "missing helper binary $LlamaBinary"
        }
        if (-not (Test-Path $HelperModel)) {
            throw "missing helper model $HelperModel"
        }
        $llamaArgs = @(
            "-m", $HelperModel,
            "--port", "$HelperPort",
            "--host", "127.0.0.1",
            "-ngl", "99",
            "-dev", "CUDA0",
            "-c", "8192",
            "--alias", $ModelAlias
        )
        $prevCuda = $env:CUDA_VISIBLE_DEVICES
        $env:CUDA_VISIBLE_DEVICES = "1"
        try {
            $llamaProc = Start-Process -FilePath $LlamaBinary `
                -ArgumentList $llamaArgs `
                -WorkingDirectory $Root `
                -PassThru `
                -WindowStyle Minimized
            Write-Host "  Started llama-server PID $($llamaProc.Id)" -ForegroundColor Green
        } finally {
            if ($null -eq $prevCuda) {
                Remove-Item Env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue
            } else {
                $env:CUDA_VISIBLE_DEVICES = $prevCuda
            }
        }
    }
    Wait-EndpointModel -Port $HelperPort -RuntimeName "llama.cpp helper"
    if ($HoldOpenSeconds -gt 0) {
        Write-Host "  Holding helper session for $HoldOpenSeconds seconds" -ForegroundColor DarkGray
        Start-Sleep -Seconds $HoldOpenSeconds
    }
    exit $LASTEXITCODE
}

if ($helperPortAvailable -or $primaryPortAvailable) {
    Assert-GpuMemoryBudget -MinimumFree $MinimumFreeMiB -Devices @(
        @{ role = "helper"; index = 0 },
        @{ role = "primary"; index = 1 }
    )
}

Write-Host "=== pheno-harness dual-GPU stack ===" -ForegroundColor Cyan
Write-Host "Root:   $Root"
Write-Host "Distro: $Distro"
Write-Host "Window: $WindowId"
Write-Host ""

# --- GTX 1080 Ti: llama-server (Windows) ---
Write-Host "[1080 Ti] llama-server helper on port $HelperPort" -ForegroundColor Yellow

if (-not $helperPortAvailable) {
    Write-Host "  SKIP: port $HelperPort is already listening; no process will be stopped" -ForegroundColor Red
} elseif (-not (Test-Path $LlamaBinary)) {
    Write-Host "  SKIP: missing binary $LlamaBinary" -ForegroundColor Red
} elseif (-not (Test-Path $HelperModel)) {
    Write-Host "  SKIP: missing model $HelperModel" -ForegroundColor Red
} else {
    $llamaArgs = @(
        "-m", $HelperModel,
        "--port", "$HelperPort",
        "--host", "127.0.0.1",
        "-ngl", "99",
        "-dev", "CUDA0",
        "-c", "8192",
        "--alias", $ModelAlias
    )
    $llamaCmd = "$LlamaBinary $($llamaArgs -join ' ')"
    Write-Host "  CUDA_VISIBLE_DEVICES=1"
    Write-Host "  $llamaCmd"

    $prevCuda = $env:CUDA_VISIBLE_DEVICES
    $env:CUDA_VISIBLE_DEVICES = "1"
    try {
        $llamaProc = Start-Process -FilePath $LlamaBinary `
            -ArgumentList $llamaArgs `
            -WorkingDirectory $Root `
            -PassThru `
            -WindowStyle Minimized
        Write-Host "  Started llama-server PID $($llamaProc.Id)" -ForegroundColor Green
    } finally {
        if ($null -eq $prevCuda) {
            Remove-Item Env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue
        } else {
            $env:CUDA_VISIBLE_DEVICES = $prevCuda
        }
    }
}
Wait-EndpointModel -Port $HelperPort -RuntimeName "llama.cpp helper"

Write-Host ""

# --- RTX 3090 Ti: primary runtime (WSL) ---
Write-Host "[3090 Ti] $PrimaryRuntime primary on port $PrimaryPort (WSL)" -ForegroundColor Yellow

if (-not $primaryPortAvailable) {
    Write-Host "  SKIP: port $PrimaryPort is already listening; no process will be stopped" -ForegroundColor Red
} elseif ($PrimaryRuntime -eq "vllm") {
    $vllmInner = @(
        "export CUDA_VISIBLE_DEVICES=1",
        "test -x '$WslVllmPython'",
        "test -d '$WslModel'",
        "exec '$WslVllmPython' -m vllm.entrypoints.openai.api_server",
        "--model '$WslModel'",
        "--host 127.0.0.1",
        "--port $PrimaryPort",
        "--served-model-name '$CanonicalModel'",
        "--gpu-memory-utilization 0.80",
        "--max-model-len 4096"
    ) -join " && "
    Write-Host "  CUDA_VISIBLE_DEVICES=1"
    Write-Host "  vLLM model: $WslModel"
    Start-Process -FilePath "wsl" -ArgumentList @("-d", $Distro, "--", "bash", "-lc", $vllmInner) -PassThru -WindowStyle Minimized | Out-Null
} else {
    $sglangInner = @(
        "source $WslVenv/bin/activate",
        "export CUDA_VISIBLE_DEVICES=1",
        "python -m sglang.launch_server",
        "--model-path '$WslModel'",
        "--port $PrimaryPort",
        "--host 127.0.0.1",
        "--served-model-name '$CanonicalModel'",
        "--dtype auto",
        "--mem-fraction-static 0.85"
    ) -join " && "
    Write-Host "  Command: wsl -d $Distro -- bash -lc `"$sglangInner`"" -ForegroundColor DarkGray
    Start-Process -FilePath "wsl" -ArgumentList @("-d", $Distro, "--", "bash", "-lc", $sglangInner) -PassThru -WindowStyle Minimized | Out-Null
}
Wait-EndpointModel -Port $PrimaryPort -RuntimeName "$PrimaryRuntime primary"

Write-Host ""

# --- pheno-serve-dev proxy ---
Write-Host "[pheno-serve] OpenAI proxy on port $PhenoPort" -ForegroundColor Yellow

if (-not (Test-PortAvailable $PhenoPort)) {
    Write-Host "  SKIP: port $PhenoPort is already listening; no process will be stopped" -ForegroundColor Red
} elseif (-not (Test-Path $PhenoConfig)) {
    Write-Host "  SKIP: missing config $PhenoConfig" -ForegroundColor Red
} elseif (-not (Test-PhenoServeModule -RepoRoot $Root)) {
    Write-Host "  SKIP: pheno.serve.server module not importable from $Root" -ForegroundColor Red
} else {
    $phenoArgs = @("-m", "pheno.serve.server", "--config", $PhenoConfig)
    Write-Host "  python $($phenoArgs -join ' ')"
    $phenoProc = Start-Process -FilePath "python" `
        -ArgumentList $phenoArgs `
        -WorkingDirectory $Root `
        -PassThru `
        -WindowStyle Minimized
    Write-Host "  Started pheno-serve PID $($phenoProc.Id)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Endpoints:" -ForegroundColor Cyan
Write-Host "  1080 helper:  http://127.0.0.1:$HelperPort/v1"
Write-Host "  3090 ${PrimaryRuntime}: http://127.0.0.1:$PrimaryPort/v1"
Write-Host "  pheno-serve:  http://127.0.0.1:$PhenoPort/v1"
Write-Host ""
Write-Host "Smoke GPUs only: powershell -File scripts\start_dual_gpu_stack.ps1 -SmokeOnly"
Write-Host "Done." -ForegroundColor Green
