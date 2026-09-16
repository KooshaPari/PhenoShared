#Requires -Version 5.1
<#
.SYNOPSIS
  Terminal Bench 2.0 — honest per-model eval matrix via Harbor + OmniRoute.

.EXAMPLE
  .\harbor\run_tbench_models.ps1 -NTasks 89 -All -Resume
  .\harbor\run_tbench_models.ps1 -Model "kc/minimax/minimax-m3" -NTasks 10
  .\harbor\run_tbench_models.ps1 -ScoreboardOnly
#>
param(
    [string]$Model = "",
    [int]$NTasks = 89,
    [switch]$All,
    [switch]$Resume,
    [switch]$IncludeCombo,
    [switch]$ScoreboardOnly,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
. (Join-Path $PSScriptRoot "podman_compat_runtime.ps1")
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

if ($ScoreboardOnly) {
    python scripts/tbench_scoreboard.py --export @($(if ($IncludeCombo) { "--include-combo" }))
    exit $LASTEXITCODE
}

Assert-PodmanCompatibilityApi -TimeoutSec 30

$args = @("scripts/run_tbench_model_matrix.py", "--n-tasks", "$NTasks")
if ($Model) { $args += @("--model", $Model) }
if ($All) { $args += "--all" }
if ($Resume) { $args += "--resume" }
if ($IncludeCombo) { $args += "--include-combo" }
if ($DryRun) { $args += "--dry-run" }

python @args
