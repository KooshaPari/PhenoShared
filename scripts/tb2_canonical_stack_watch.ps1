#Requires -Version 5.1
# Canonical-stack watchdog: NEVER start llama-server.
# Only reports whether pheno-serve + admitted upstream are healthy.
$ErrorActionPreference = "SilentlyContinue"
$log = "C:\Users\koosh\pheno-harness\jobs\harbor\tbench\canonical_stack_watch.log"
$line = "WATCH $(Get-Date -Format o)"
try {
    $h = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:21080/healthz" -TimeoutSec 3
    $line += " pheno_health=$([int]$h.StatusCode)"
} catch { $line += " pheno_health=down" }
try {
    $m = (Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:21080/v1/models" -TimeoutSec 3).Content
    $n = ([regex]::Matches($m, '"id"')).Count
    $line += " pheno_models=$n"
} catch { $line += " pheno_models=down" }
try {
    $u = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health" -TimeoutSec 3
    $line += " sglang_health=$([int]$u.StatusCode)"
} catch { $line += " sglang_health=down" }
if (Get-Process llama-server -ErrorAction SilentlyContinue) {
    $line += " WARN_interim_llama_server_running"
}
$line | Out-File $log -Append -Encoding ascii
