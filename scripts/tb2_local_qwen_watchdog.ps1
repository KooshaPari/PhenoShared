# ****************************************************************************
# OBSOLETE — DO NOT SCHEDULE. Kept for history only.
#   * Targets DOCKER_HOST=npipe:////./pipe/docker_engine (Docker Desktop) —
#     Docker Desktop is retired (2026-08-08); the container runtime is podman
#     inside WSL (docker-compat API on tcp://<wsl-ip>:7777).
#   * Restarts llama-server on :8000 — the llama.cpp lanes were purged/banned
#     2026-08-08 (qwen :8080, lfm :19000, ornith :19095 all stood down).
#   * Kill-all-llama-server behavior would destroy the live serving stack.
#   * Last activity 2026-07-23; currently NOT registered as a scheduled task.
# ****************************************************************************
#Requires -Version 5.1
# Keep local qwen TB2 alive: restart llama if :8000 is down; resume portage if it died.
# Safe to schedule every 5–10 min (Limited run level OK — no UAC).
$ErrorActionPreference = "SilentlyContinue"
$job = "D:\WSL\eval-cache\pheno-harbor-jobs\2026-07-22__20-17-38"
$exe = "C:\Users\koosh\portage\.venv\Scripts\portage.exe"
$lock = Join-Path $env:TEMP "tb2_local_qwen_watchdog.lock"
$log = "C:\Users\koosh\pheno-harness\jobs\harbor\tbench\local-qwen35-full-20260722\watchdog_resume.log"
$llama = "D:\WSL\tools\llama.cpp-b10012-cuda12.4\llama-server.exe"
$gguf = "D:\WSL\model-cache\qwen35-08b-q4\qwen35-08b.Q4_K_M.gguf"

function Test-LlamaHealth {
    try {
        $h = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health" -TimeoutSec 3
        return ([int]$h.StatusCode -ge 200 -and [int]$h.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Start-LocalLlama {
    if (-not ((Test-Path $llama) -and (Test-Path $gguf))) { return $false }
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Start-Process -FilePath $llama -ArgumentList @(
        "-m", $gguf, "--port", "8000", "--host", "127.0.0.1",
        "-ngl", "99", "-c", "8192", "--alias", "local/qwen35-08b"
    ) -WindowStyle Hidden
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-LlamaHealth) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

try {
    $lf = [System.IO.File]::Open($lock, "OpenOrCreate", "ReadWrite", "None")
} catch {
    exit 0
}
try {
    if (-not (Test-Path "$job\result.json")) { exit 0 }
    $rj = Get-Content "$job\result.json" -Raw | ConvertFrom-Json
    if ($rj.finished_at) { exit 0 }

    # Always keep llama up while the job is unfinished (portage may still be alive).
    if (-not (Test-LlamaHealth)) {
        "WATCHDOG restart llama $(Get-Date -Format o)" | Out-File $log -Append -Encoding ascii
        if (-not (Start-LocalLlama)) { exit 0 }
    }

    if (Get-Process portage -ErrorAction SilentlyContinue) { exit 0 }

    $env:DOCKER_HOST = "npipe:////./pipe/docker_engine"
    $env:PHENO_PODMAN_PIPE = "npipe:////./pipe/docker_engine"
    $env:OPENAI_API_KEY = "local-no-key"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUNBUFFERED = "1"
    $env:PYTHONPATH = "C:\Users\koosh\pheno-harness;C:\Users\koosh\portage\src"

    Remove-Item "D:\WSL\eval-cache\pheno-harbor-local-run.lock" -Force -ErrorAction SilentlyContinue
    "WATCHDOG resume $(Get-Date -Format o)" | Out-File $log -Append -Encoding ascii
    Start-Process -FilePath $exe -ArgumentList @("job", "resume", "-p", $job, "-y") `
        -WorkingDirectory "C:\Users\koosh\pheno-harness" -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError ($log + ".err")
} finally {
    if ($lf) { $lf.Close() }
}
