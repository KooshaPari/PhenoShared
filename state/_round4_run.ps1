# Round-4 locked-pick scraper. Sets HF_TOKEN env for the duration of the run, never logs it.
# Reads token from stdin piped here-doc to keep it out of command-line history.
$ErrorActionPreference = "Stop"
$token = $args[0]
if (-not $token) {
    Write-Host "usage: _round4_run.ps1 <hf_token>"
    exit 2
}
# Set for child processes only (does not affect parent shell or any file).
$env:HF_TOKEN = $token
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:PYTHONUNBUFFERED = "1"
try {
    & C:\Python314\python.exe -X utf8 "C:\Users\koosh\pheno-harness\scripts\hf_round4_locked.py"
    $rc = $LASTEXITCODE
} finally {
    Remove-Item Env:\HF_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:\HF_HUB_DISABLE_PROGRESS_BARS -ErrorAction SilentlyContinue
}
exit $rc