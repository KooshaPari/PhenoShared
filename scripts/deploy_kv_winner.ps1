# Deploy KV bakeoff winner to 3090 Ti long-ctx lanes (Phase 4 stub)
param(
    [string]$WinnerState = "$PSScriptRoot\..\state\kv_winner.json",
    [string]$ConfigPath = "$PSScriptRoot\..\config\kv_bakeoff.yaml",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $WinnerState)) {
    Write-Error "Winner state not found: $WinnerState — run scripts/kv_bakeoff.py first"
}

$winner = Get-Content $WinnerState -Raw | ConvertFrom-Json
Write-Host "KV winner: $($winner.variant_id)"
Write-Host "  metric: $($winner.accepted_steps_per_sec_per_gb) accepted_steps/sec/GB"
Write-Host "  tok/s: $($winner.tok_per_s)  VRAM: $($winner.vram_gb) GB"

if ($DryRun) {
    Write-Host "[dry-run] Would patch llama-server flags for locked local aliases (ctx >= 16384)"
    exit 0
}

# TODO: merge winner ctk/ctv flags into models.yaml or env template.
# Deferred until the kv-winner promotion pipeline is shipped. See WBS task 93
# and docs/plans/2026-08-07-pheno-harness-WBS-PERT-100-v0.9.md for the trigger
# criterion (a variant must first be promoted via bench/kv_runner/.
Write-Host "STUB: copy winner flags to PHENO_KV_CTK / PHENO_KV_CTV and restart llama-server"
Write-Host "  variant_id=$($winner.variant_id)"
exit 0
