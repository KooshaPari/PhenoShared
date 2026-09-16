#Requires -Version 5.1
<#
.SYNOPSIS
  Reserved Terminal Bench Harbor entrypoint; execution is fail-closed pending owner-issued authority.

.DESCRIPTION
  This wrapper is intentionally unavailable for execution until a canonical
  owner-issued desktop authority contract is configured. A caller-supplied
  WindowId and the legacy Harbor sidecar are run provenance, not authority.
  The retained implementation documents the future bounded local-model flow.

.PARAMETER Config
  Harbor JobConfig YAML (default: config/harbor.yaml).

.PARAMETER Model
  Harbor model alias (default: openai/local/qwen35-08b).

.PARAMETER ApiBase
  OpenAI-compatible local endpoint reachable from the container.

.PARAMETER MaxTurns
  Terminus turn bound (default: 3 for diagnostic runs).

.PARAMETER MaxTokens
  Per-request completion cap (default: 2048).

.PARAMETER Full
  After oracle sanity, run the full dataset (no --n-tasks cap).

.PARAMETER Dataset
  Override dataset slug (default: terminal-bench@2.0 — see eval/HARBOR.md for 2.1 status).

.NOTES
  Do not invoke this script to start a Harbor run while the authority contract
  is absent. It exits before endpoint, Docker, or Harbor activity.
#>
[CmdletBinding()]
param(
    [string]$Config = "",
    [switch]$Full,
    [string]$Dataset = "terminal-bench@2.0",
    [string]$DatasetPath = "D:\WSL\eval-cache\harbor-terminal-bench-2.0\terminal-bench",
    [string]$Model = "openai/local/qwen35-08b",
    [string]$ApiBase = "http://172.28.176.1:23080/v1",
    [int]$MaxTurns = 3,
    [int]$MaxTokens = 2048,
    [int]$ContextSize = 32768,
    [string[]]$IncludeTaskName = @("headless-terminal"),
    [int]$MaxOutputRetries = 2,
    [int]$ServerReadyTimeoutSec = 300,
    [string]$ServerHealthUrl = "http://127.0.0.1:23080/health",
    [string]$WindowId = "",
    [string]$ContractPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Config) { $Config = Join-Path $Root "config\harbor.yaml" }
if (-not $ContractPath) { $ContractPath = Join-Path $Root "config\desktop_nvidia_qwen35_lane.yaml" }
if ([string]::IsNullOrWhiteSpace($WindowId)) {
    throw "-WindowId is required; obtain an explicit desktop execution authorization first"
}
# A caller-provided window ID is run provenance, not execution authority.  The
# legacy sidecar below records a completed Harbor run; it cannot authorize one.
# Keep this launcher fail-closed until an owner-issued, bound authority exists.
throw "Desktop Harbor execution is blocked: no owner-issued execution authority is configured."
if (-not (Test-Path $ContractPath)) {
    throw "Desktop lane contract not found: $ContractPath"
}
$contractSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $ContractPath).Hash.ToLowerInvariant()
Set-Location $Root

# Harbor rich output on Windows cp1252 consoles can throw UnicodeEncodeError
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = $Root
$env:PHENO_DESKTOP_WINDOW_ID = $WindowId
$env:PHENO_DESKTOP_CONTRACT_SHA256 = $contractSha256
$authorizationDir = Join-Path $Root "jobs\harbor"
New-Item -ItemType Directory -Force -Path $authorizationDir | Out-Null
$authorizationId = [guid]::NewGuid().ToString("N")
$authorizationPath = Join-Path $authorizationDir ("desktop-authorization-" + $authorizationId + ".json")
$authorization = [ordered]@{
    schema_version = "pheno.desktop-harbor-authorization.v1"
    window_id = $WindowId
    contract_sha256 = $contractSha256
    canonical_model = "Qwen/Qwen3.5-0.8B"
    request_model = $Model
    base_url = $ApiBase
    authorization_id = $authorizationId
    created_at = [DateTime]::UtcNow.ToString("o")
}
$authorization | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $authorizationPath -Encoding utf8
$env:PHENO_DESKTOP_AUTHORIZATION_PATH = $authorizationPath

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-HarborExe {
    # Prefer the validated Harbor 0.18.0 environment. Older user installs do
    # not support repository-owned agent adapters or the local dataset path.
    $cacheRoot = Join-Path $env:LOCALAPPDATA "uv\cache\archive-v0"
    if (Test-Path $cacheRoot) {
        $preferred = Join-Path $cacheRoot "mLJB2gr5tr8t7aWd\Scripts\harbor.exe"
        if (Test-Path $preferred) { return $preferred }
        foreach ($archive in (Get-ChildItem $cacheRoot -Directory -ErrorAction SilentlyContinue)) {
            $cached = Join-Path $archive.FullName "Scripts\harbor.exe"
            if (Test-Path $cached) { return $cached }
        }
    }
    $candidates = @(
        (Join-Path $env:APPDATA "Python\Python313\Scripts\harbor.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\Scripts\harbor.exe"),
        (Join-Path $env:APPDATA "Python\Python314\Scripts\harbor.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\Scripts\harbor.exe"),
        "harbor"
    )
    foreach ($c in $candidates) {
        if ($c -eq "harbor") {
            $cmd = Get-Command harbor -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
            continue
        }
        if (Test-Path $c) { return $c }
    }
    $uvx = Get-Command uvx -ErrorAction SilentlyContinue
    if ($uvx) { return $uvx.Source }
    throw "Harbor CLI not found. Install Harbor or uv, then retry."
}

function Assert-Docker {
    Write-Step "Checking Docker-compatible engine (docker ps)"
    if (-not $env:DOCKER_HOST) {
        $env:DOCKER_HOST = "npipe:////./pipe/podman-machine-default"
    }
    $docker = Get-Command docker -ErrorAction Stop
    $probe = Start-Process -FilePath $docker.Source -ArgumentList @("info", "--format", "{{.ServerVersion}}") -NoNewWindow -PassThru
    if (-not $probe.WaitForExit(120000)) {
        $probe.Kill()
        $probe.WaitForExit()
        throw "Docker-compatible API did not respond within 120 seconds at $env:DOCKER_HOST."
    }
    if ($probe.ExitCode -ne 0) {
        throw "Docker info failed with exit code $($probe.ExitCode) at $env:DOCKER_HOST."
    }
}

function Assert-CanonicalModel {
    $modelsUrl = $ApiBase.TrimEnd("/") + "/models"
    try {
        $payload = Invoke-RestMethod $modelsUrl -TimeoutSec 5
    } catch {
        throw "Desktop endpoint model probe failed at $modelsUrl : $($_.Exception.Message)"
    }
    $rows = if ($null -ne $payload.data) { @($payload.data) } else { @($payload.models) }
    $ids = @($rows | ForEach-Object { [string]$_.id; [string]$_.name; [string]$_.model })
    if (($ids -notcontains "Qwen/Qwen3.5-0.8B") -and ($ids -notcontains "local/qwen35-08b")) {
        throw "Desktop endpoint does not advertise Qwen/Qwen3.5-0.8B or local/qwen35-08b: $($ids -join ', ')"
    }
    Write-Host "    model gate passed: $($ids -join ', ')" -ForegroundColor Green
}

function Wait-LocalServer {
    param(
        [Parameter(Mandatory)][int]$TimeoutSec,
        [Parameter(Mandatory)][string]$HealthUrl
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        try {
            $health = Invoke-RestMethod $HealthUrl -TimeoutSec 3
            if ($health.status -eq "ok") { return }
        } catch { }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "Local inference server did not become ready within ${TimeoutSec}s."
}

function Invoke-Harbor {
    param(
        [Parameter(Mandatory)][string[]]$HarborArgs
    )
    $exe = Resolve-HarborExe
    $runner = Join-Path (Split-Path -Parent $exe) "python.exe"
    $shim = Join-Path $Root "scripts\harbor_podman_compat.py"
    Write-Host ("    {0} {1} {2}" -f $runner, $shim, ($HarborArgs -join " "))
    & $runner $shim @HarborArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Harbor exited with code $LASTEXITCODE"
    }
}

function Resolve-LatestHarborJob {
    $jobsRoot = Join-Path $Root "jobs\harbor"
    $candidates = @(
        Get-ChildItem -LiteralPath $jobsRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName "result.json") } |
            Sort-Object LastWriteTimeUtc -Descending
    )
    if ($candidates.Count -eq 0) {
        throw "Harbor completed without a job result under $jobsRoot."
    }
    return $candidates[0].FullName
}

function Normalize-HarborJob {
    param(
        [Parameter(Mandatory)][string]$JobPath
    )
    $exe = Resolve-HarborExe
    $runner = Join-Path (Split-Path -Parent $exe) "python.exe"
    $normalizer = Join-Path $Root "scripts\normalize_harbor_trial.py"
    $normalized = Join-Path $JobPath "pheno-normalized.json"
    Write-Step "Binding Harbor result to desktop authorization"
    & $runner $normalizer $JobPath --authorization-manifest $authorizationPath --output $normalized
    if ($LASTEXITCODE -ne 0) {
        throw "Harbor result normalization failed with code $LASTEXITCODE"
    }
    Write-Host "    normalized artifact: $normalized"
}

Write-Step "pheno-harness Terminal Bench (Harbor, root: $Root)"
Write-Host "    config=$Config dataset=$Dataset model=$Model api_base=$ApiBase full=$Full window=$WindowId"

Write-Step "Waiting for local inference server"
Wait-LocalServer -TimeoutSec $ServerReadyTimeoutSec -HealthUrl $ServerHealthUrl
Assert-CanonicalModel
Assert-Docker

if (-not (Test-Path $Config)) {
    throw "Harbor config not found: $Config"
}

Write-Step "Bounded local Terminal Bench job"
$modelInfo = '{"max_input_tokens":' + $ContextSize + ',"max_output_tokens":' + $MaxTokens + '}'
$llmCallKwargs = '{"max_tokens":' + $MaxTokens + ',"temperature":0}'
$jobArgs = @(
    "run", "-c", $Config,
    "-a", "harness.harbor.terminus_safe:SafeTerminus2",
    "-m", $Model,
    "--env", "docker",
    "--n-concurrent", "1",
    "--agent-kwarg", "api_base=$ApiBase",
    "--agent-kwarg", "max_turns=$MaxTurns",
    "--agent-kwarg", "max_thinking_tokens=1024",
    "--agent-kwarg", "reasoning_effort=none",
    "--agent-kwarg", "interleaved_thinking=false",
    "--agent-kwarg", "enable_summarize=false",
    "--agent-kwarg", "record_terminal_session=false",
    "--agent-kwarg", "max_output_retries=$MaxOutputRetries",
    "--agent-kwarg", "terminal_command_timeout_sec=30",
    "--agent-kwarg", "model_info=$modelInfo",
    "--agent-kwarg", "llm_call_kwargs=$llmCallKwargs",
    "--agent-env", "OPENAI_API_KEY=local-no-key",
    "-y"
)
if (Test-Path $DatasetPath) {
    $jobArgs += @("-p", $DatasetPath)
} else {
    Write-Warning "Pinned local dataset export not found at $DatasetPath; Harbor will resolve $Dataset remotely."
    $jobArgs += @("-d", $Dataset)
}
if (-not $Full) {
    $jobArgs += @("--n-tasks", $IncludeTaskName.Count)
    foreach ($taskName in $IncludeTaskName) {
        $jobArgs += @("--include-task-name", $taskName)
    }
}
Invoke-Harbor $jobArgs

$latestJob = Resolve-LatestHarborJob
Normalize-HarborJob -JobPath $latestJob

Write-Step "Done. Results under jobs/harbor/ (see harbor.yaml jobs_dir)."
Write-Host "    authorization manifest: $authorizationPath"
