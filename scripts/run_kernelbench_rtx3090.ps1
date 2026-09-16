#Requires -Version 5.1
<#
.SYNOPSIS
  KernelBench RTX3090Bench driver scaffold (dry-run by default).

.DESCRIPTION
  Reads config/kernelbench_rtx3090.yaml and prints the upstream bench.py command.
  Pass -Execute to run against the pinned Infatoshi/KernelBench-v3 checkout.
  Does not install packages or clone the upstream repo.

.PARAMETER Execute
  Run bench.py instead of printing the planned command.

.EXAMPLE
  .\scripts\run_kernelbench_rtx3090.ps1
  .\scripts\run_kernelbench_rtx3090.ps1 -Execute -Levels "1,2"
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$ConfigPath,
    [string]$KernelBenchRoot = $env:PHENO_KERNELBENCH_ROOT,
    [string]$Levels = "1,2,3,4",
    [int]$Workers = 4,
    [int]$ProblemsPerLevel = 1
)

$ErrorActionPreference = "Stop"
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$Root = Split-Path -Parent $ScriptDir
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $Root "config\kernelbench_rtx3090.yaml"
}

function Resolve-PythonRunner {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        return @{ Kind = "uv"; Uv = (Get-Command uv).Source }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Kind = "python"; Python = (Get-Command python).Source }
    }
    throw "Neither uv nor python found on PATH. Install uv or Python before running KernelBench."
}

function Get-DefaultKernelBenchRoot {
    param([string]$ConfiguredDefault)
    if ($ConfiguredDefault) {
        $expanded = $ConfiguredDefault -replace '\$\{PHENO_ROOT\}', $Root
        return $expanded
    }
    return Join-Path $Root "vendor\KernelBench-v3"
}

function Read-KernelBenchConfig {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Missing config: $Path"
    }
    $text = Get-Content $Path -Raw
    $cfg = [ordered]@{
        RootEnv = "PHENO_KERNELBENCH_ROOT"
        DefaultRoot = (Join-Path $Root "vendor\KernelBench-v3")
        CudaVisibleDevices = "1"
        DryRunTemplate = "uv run python bench.py run rtx3090 --levels {levels} --problems-per-level {problems_per_level} --dry-run"
        ExecuteTemplate = "uv run python bench.py run rtx3090 --levels {levels} --workers {workers}"
    }

    if ($text -match 'root_env:\s*(\S+)') { $cfg.RootEnv = $Matches[1] }
    if ($text -match 'default_root:\s*"?\$\{PHENO_ROOT\}/vendor/KernelBench-v3"?') {
        $cfg.DefaultRoot = Join-Path $Root "vendor\KernelBench-v3"
    }
    if ($text -match 'CUDA_VISIBLE_DEVICES:\s*"(\d+)"') { $cfg.CudaVisibleDevices = $Matches[1] }
    if ($text -match 'levels:\s*"([^"]+)"') { $cfg.DefaultLevels = $Matches[1] }
    if ($text -match 'workers:\s*(\d+)') { $cfg.DefaultWorkers = [int]$Matches[1] }

    return $cfg
}

function Format-BenchCommand {
    param(
        [hashtable]$Runner,
        [string]$Template,
        [string]$LevelsArg,
        [int]$WorkersArg,
        [int]$ProblemsPerLevelArg
    )

    $body = $Template `
        -replace '\{levels\}', $LevelsArg `
        -replace '\{workers\}', "$WorkersArg" `
        -replace '\{problems_per_level\}', "$ProblemsPerLevelArg"

    if ($Runner.Kind -eq "uv") {
        return $body
    }

    # Fallback when uv is unavailable: substitute the runner prefix.
    return ($body -replace '^uv run ', "python ")
}

$runner = Resolve-PythonRunner
$config = Read-KernelBenchConfig -Path $ConfigPath

if (-not $KernelBenchRoot) {
    $KernelBenchRoot = Get-DefaultKernelBenchRoot -ConfiguredDefault $config.DefaultRoot
}

if ($config.DefaultLevels -and $Levels -eq "1,2,3,4") {
    $Levels = $config.DefaultLevels
}
if ($config.DefaultWorkers -and $Workers -eq 4) {
    $Workers = $config.DefaultWorkers
}

$template = if ($Execute) { $config.ExecuteTemplate } else { $config.DryRunTemplate }
$benchCommand = Format-BenchCommand -Runner $runner -Template $template -LevelsArg $Levels -WorkersArg $Workers -ProblemsPerLevelArg $ProblemsPerLevel

Write-Host "== KernelBench RTX3090Bench ==" -ForegroundColor Cyan
Write-Host "  config:      $ConfigPath"
Write-Host "  repo root:   $KernelBenchRoot"
Write-Host "  runner:      $($runner.Kind)"
Write-Host "  mode:        $(if ($Execute) { 'execute' } else { 'dry-run' })"
Write-Host "  CUDA policy: CUDA_VISIBLE_DEVICES=$($config.CudaVisibleDevices) (3090 Ti -> PyTorch cuda:0)"
Write-Host ""

if (-not (Test-Path $KernelBenchRoot)) {
    Write-Host "WARNING: KernelBench checkout not found at $KernelBenchRoot" -ForegroundColor Yellow
    Write-Host "         Set $($config.RootEnv) or clone Infatoshi/KernelBench-v3 before -Execute." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "bench.py command:" -ForegroundColor Green
Write-Host "  cd `"$KernelBenchRoot`""
Write-Host "  `$env:CUDA_VISIBLE_DEVICES = `"$($config.CudaVisibleDevices)`""
Write-Host "  $benchCommand"
Write-Host ""

if (-not $Execute) {
    Write-Host "Dry-run only. Re-run with -Execute to invoke bench.py." -ForegroundColor DarkGray
    exit 0
}

if (-not (Test-Path (Join-Path $KernelBenchRoot "bench.py"))) {
    throw "bench.py not found under $KernelBenchRoot"
}

Push-Location $KernelBenchRoot
try {
    $env:CUDA_VISIBLE_DEVICES = $config.CudaVisibleDevices
    if ($runner.Kind -eq "uv") {
        if ($benchCommand -match '^uv run python bench\.py (.+)$') {
            & uv run python bench.py @($Matches[1].Split(' ') | Where-Object { $_ })
        } else {
            Invoke-Expression $benchCommand
        }
    } else {
        if ($benchCommand -match '^python bench\.py (.+)$') {
            & python bench.py @($Matches[1].Split(' ') | Where-Object { $_ })
        } else {
            Invoke-Expression $benchCommand
        }
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
