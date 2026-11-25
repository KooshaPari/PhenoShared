$ErrorActionPreference = 'Stop'

# BytePort launcher: ensure deps, then start the Go backend + SvelteKit/Tauri frontend.
# Does NOT recreate its own Start-Menu shortcut (that overwrote the glass icon).

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backendDir = Join-Path $repoRoot 'backend\byteport'
$frontendDir = Join-Path $repoRoot 'frontend\web'

# First-run deps (idempotent)
if (Test-Path $backendDir) {
  Start-Process -FilePath 'go' -ArgumentList @('mod','download') -WorkingDirectory $backendDir -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
}
if ((Test-Path $frontendDir) -and -not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
  $npm = (Get-Command bun -ErrorAction SilentlyContinue) ; $inst = if ($npm) { 'bun' } else { 'npm' }
  Start-Process -FilePath $inst -ArgumentList @('install') -WorkingDirectory $frontendDir -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
}

# Launch backend + frontend
if (Test-Path $backendDir) {
  Start-Process -FilePath 'go' -ArgumentList @('run', '.') -WorkingDirectory $backendDir -WindowStyle Hidden -ErrorAction SilentlyContinue
}
if (Test-Path $frontendDir) {
  $runner = if (Get-Command bun -ErrorAction SilentlyContinue) { 'bun' } else { 'npm' }
  Start-Process -FilePath $runner -ArgumentList @('run', 'tauri', 'dev') -WorkingDirectory $frontendDir -WindowStyle Hidden -ErrorAction SilentlyContinue
}

Write-Host "BytePort: backend + frontend launching (first run installs deps; Tauri toolchain required)."
