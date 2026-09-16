# Launches the full HF scrape detached via PowerShell Start-Process so the
# call returns immediately and we can poll heartbeat.json for progress.
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\koosh\pheno-harness"

$python = "C:\Python314\python.exe"
$script = "scripts\hf_scrape_2026_07_03.py"
$outDir = "state\hf_scrape\2026-07-03"
$heartbeat = Join-Path $outDir "heartbeat.json"

if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

$logOut = "state\_scrape_2026-07-03.log"
$logErr = "state\_scrape_2026-07-03.err"

# -u = unbuffered. Capture both streams.
$args = @(
  "-u",
  $script,
  "--max-per-author", "80",
  "--enrich-timeout", "6",
  "--output-dir", $outDir
)

$proc = Start-Process -FilePath $python -ArgumentList $args `
   -NoNewWindow -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr

Write-Host ("started pid=" + $proc.Id + ", logs=" + $logOut + ", heartbeat=" + $heartbeat)
