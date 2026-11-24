# Round-4 followup probe wrapper. Token-only env, never logged.
$ErrorActionPreference = "Stop"
$token = $args[0]
if (-not $token) {
    Write-Host "usage: _round4_followup.ps1 <hf_token>"
    exit 2
}
$env:HF_TOKEN = $token
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:PYTHONUNBUFFERED = "1"
try {
    & C:\Python314\python.exe -X utf8 "C:\Users\koosh\pheno-harness\scripts\hf_round4_followups.py"
    $rc = $LASTEXITCODE
} finally {
    Remove-Item Env:\HF_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:\HF_HUB_DISABLE_PROGRESS_BARS -ErrorAction SilentlyContinue
}
exit $rc
