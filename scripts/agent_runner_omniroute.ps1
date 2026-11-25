#Requires -Version 5.1
<#
.SYNOPSIS
  Run agent-runner queue jobs through OmniRoute (localhost:20128).

.DESCRIPTION
  Wraps agent-runner.exe queue with OmniRoute proxy env vars so codex-spark CI
  lane traffic routes via the Main combo.

.PARAMETER JobsFile
  JSONL jobs file (one job per line: id, prompt, model, cwd).

.PARAMETER Concurrency
  Max concurrent turns (default 3, matches ci lane in harness/lanes.yaml).

.PARAMETER DefaultModel
  Model when a job line omits "model" (default: gpt-5.3-codex-spark).

.EXAMPLE
  .\scripts\agent_runner_omniroute.ps1 "$env:USERPROFILE\.claude\forge-dispatch\codex-jobs.jsonl"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string]$JobsFile,

    [int]$Concurrency = 3,
    [string]$DefaultModel = "gpt-5.3-codex-spark",
    [string]$AgentRunner = "$env:USERPROFILE\.claude\tools\agent-runner\agent-runner.exe",
    [string]$OmniRouteConfig = "$env:USERPROFILE\.pi\agent\omniroute.json",
    [string]$ModelsJson = "$env:USERPROFILE\.pi\agent\models.json",
    [string]$Combo = "Main",
    [string]$Lane = "ci"
)

$ErrorActionPreference = "Stop"

function Get-OmniRouteBaseUrl {
    param([string]$ConfigPath)
    if ($env:OMNIROUTE_URL) { return $env:OMNIROUTE_URL.TrimEnd("/") }
    if (Test-Path $ConfigPath) {
        $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        if ($cfg.url) { return [string]$cfg.url.TrimEnd("/") }
    }
    return "http://localhost:20128"
}

function Get-OmniRouteApiKey {
    param([string]$ModelsPath)
    if ($env:OMNIROUTE_API_KEY) { return $env:OMNIROUTE_API_KEY }
    if ($env:OPENAI_API_KEY) { return $env:OPENAI_API_KEY }
    if (Test-Path $ModelsPath) {
        $models = Get-Content $ModelsPath -Raw | ConvertFrom-Json
        $key = $models.providers.omni.apiKey
        if ($key) { return [string]$key }
    }
    return "omniroute-local"
}

if (-not (Test-Path $AgentRunner)) {
    throw "agent-runner not found: $AgentRunner"
}
if (-not (Test-Path $JobsFile)) {
    throw "Jobs file not found: $JobsFile"
}

$OmniUrl = Get-OmniRouteBaseUrl -ConfigPath $OmniRouteConfig
$ApiKey = Get-OmniRouteApiKey -ModelsPath $ModelsJson

$env:OMNIROUTE_URL = $OmniUrl
$env:OMNIROUTE_COMBO = $Combo
$env:OPENAI_BASE_URL = "$OmniUrl/v1"
$env:OPENAI_API_BASE = "$OmniUrl/v1"
$env:OPENAI_API_KEY = $ApiKey
$env:PHENO_LANE = $Lane
$env:PHENO_HARNESS = "pheno-harness"

Write-Host "==> agent-runner queue via OmniRoute" -ForegroundColor Cyan
Write-Host "    url=$OmniUrl combo=$Combo lane=$Lane"
Write-Host "    jobs=$JobsFile concurrency=$Concurrency model=$DefaultModel"

& $AgentRunner queue $JobsFile `
    --concurrency $Concurrency `
    --default-model $DefaultModel

exit $LASTEXITCODE
