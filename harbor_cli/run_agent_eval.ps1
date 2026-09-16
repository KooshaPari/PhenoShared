#Requires -Version 5.1
<#
.SYNOPSIS
  Harbor agent eval matrix — forge/codex/claude via native configs + OmniRoute.

.DESCRIPTION
  Runs Repo2RL reference dataset with oracle (sanity) then optional agent harnesses.
  terminus-2 uses OmniRoute Main model for local-first eval.
#>
param(
    [string]$DatasetDir = "",
    [ValidateSet("oracle", "terminus-2")]
    [string[]]$Agents = @("oracle"),
    [int]$NTasks = 1
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"

if (-not $DatasetDir) {
    $DatasetDir = Join-Path $Root "datasets\ref-pr-diff"
}

Write-Host "==> Harbor agent eval" -ForegroundColor Cyan
Write-Host "    dataset=$DatasetDir agents=$($Agents -join ',')"

python scripts/repo2rl_setup.py --skip-install 2>&1 | Out-Null

foreach ($agent in $Agents) {
    Write-Host "`n--- agent: $agent ---" -ForegroundColor Yellow
    $args = @("scripts/repo2rl_eval.py", "--agent", $agent, "--n-tasks", "$NTasks")
    if ($agent -eq "terminus-2") { $args += @("--model", "Main") }
    python @args
    if ($LASTEXITCODE -ne 0) { Write-Warning "Agent $agent exited $LASTEXITCODE" }
}
