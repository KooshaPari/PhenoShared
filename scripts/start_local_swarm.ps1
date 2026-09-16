# Start local swarm: locked ADR 0005 aliases via model manager
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Phase 2 Local swarm ==" -ForegroundColor Cyan

if (-not $env:PHENO_LLAMA_SERVER) {
    Write-Host "PHENO_LLAMA_SERVER not set — using 'llama-server' from PATH" -ForegroundColor Yellow
}
foreach ($var in @("PHENO_QWEN35_08B", "PHENO_LFM25_8B_A1B", "PHENO_ORNITH_8B")) {
    if (-not (Get-Item "Env:$var" -ErrorAction SilentlyContinue)) {
        Write-Host "$var not set — always-on start may skip missing GGUF" -ForegroundColor Yellow
    }
}

Write-Host "`n[1/2] Ensure always-on models (dry-run preview)..."
python "$Root\scripts\model_manager.py" ensure-always-on --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Start = Read-Host "`nStart llama-server processes now? [y/N]"
if ($Start -match '^[Yy]') {
    Write-Host "`n[2/2] Starting always-on stack..."
    python "$Root\scripts\model_manager.py" ensure-always-on
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Skipped live start. Use:" -ForegroundColor Yellow
    Write-Host "  python scripts\model_manager.py ensure-always-on"
}

Write-Host "`nStatus:"
python "$Root\scripts\model_manager.py" status

Write-Host "`nOn-demand swap examples:"
Write-Host "  python scripts\model_manager.py swap --name local.lfm25_8b_a1b"
Write-Host "  python scripts\model_manager.py swap --name local.ornith_8b"
Write-Host "`nEndpoints (config/local_swarm.yaml):"
Write-Host "  Qwen3.5 0.8B -> http://127.0.0.1:8080/v1"
Write-Host "  LFM2.5 8B-A1B -> http://127.0.0.1:8081/v1"
Write-Host "  Ornith 8B -> http://127.0.0.1:8082/v1"
Write-Host "`nDone." -ForegroundColor Green
