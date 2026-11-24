param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$Config = "$PSScriptRoot\..\config\pheno_serve.yaml"
)

$ErrorActionPreference = "Stop"
Set-Location $Root

Write-Host "Starting pheno-serve-dev" -ForegroundColor Cyan
Write-Host "  Root:   $Root"
Write-Host "  Config: $Config"

python -m pheno.serve.server --config $Config
