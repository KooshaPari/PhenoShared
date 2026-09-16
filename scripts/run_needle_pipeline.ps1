# Needle pipeline: export call_logs -> train router -> compile sample context
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Phase 1 Needle pipeline ==" -ForegroundColor Cyan

Write-Host "`n[1/3] Export OmniRoute training data..."
python "$Root\scripts\export_omniroute_training.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/3] Train Needle router v0..."
python "$Root\scripts\train_needle_router.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[3/3] Test compile on sample candidates..."
$Sample = "$Root\bench\fixtures\sample_candidates.json"
python "$Root\scripts\compile_context.py" --query "fix context compiler and model manager for pheno harness" --candidates $Sample --role patch
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nOptional: install context caps middleware into OmniRoute"
Write-Host "  python scripts\install_middleware.py --mode both"
Write-Host "`nDone." -ForegroundColor Green
