# One-shot launcher for last-modified probe.
# Pass token as args[0]; it is set in this process's $env:HF_TOKEN, used, then removed.
# Token is never written to a file or echoed.
$ErrorActionPreference = "Continue"
$TOKEN = $args[0]
if (-not $TOKEN) { Write-Error "Token arg missing"; exit 2 }

# Save old value (if any) so we can restore it.
$prev = $env:HF_TOKEN
$env:HF_TOKEN = $TOKEN
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
try {
    & C:\Python314\python.exe -X utf8 "C:\Users\koosh\pheno-harness\scripts\hf_round4_last_modified.py" 2>&1
} finally {
    if ($null -eq $prev) { Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue }
    else { $env:HF_TOKEN = $prev }
}