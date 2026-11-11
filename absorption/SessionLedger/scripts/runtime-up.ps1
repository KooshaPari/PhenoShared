#!/usr/bin/env pwsh
# SessionLedger runtime facade — bring up daemon (+ viewer when native).
# Default: process-compose (zero hard deps beyond that CLI).
# Optional engines via SL_RUNTIME: process-compose|pheno|podman|wsl|apple|container
# See docs/ops/runtime-facade.md. ADR 0001: no tray / resident companion.

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Passthrough
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot

function Test-Cmd([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Write-Info([string]$Message) {
    Write-Host "[runtime-up] $Message"
}

function Write-Err([string]$Message) {
    [Console]::Error.WriteLine("[runtime-up] $Message")
}

function Show-EngineHints {
    $hints = @()
    if (Test-Cmd 'process-compose') { $hints += 'process-compose: available (default)' }
    else { $hints += 'process-compose: missing — install https://github.com/F1bonacc1/process-compose' }

    $pheno = @()
    if (Test-Cmd 'pheno-compose') { $pheno += 'pheno-compose' }
    if (Test-Cmd 'nvms') { $pheno += 'nvms' }
    if ($pheno.Count -gt 0) {
        $hints += "PhenoCompose/nvms: $($pheno -join ', ') on PATH (SL_RUNTIME=pheno)"
    } else {
        $hints += 'PhenoCompose/nvms: not on PATH (optional; see docs/ops/runtime-facade.md)'
    }

    if (Test-Cmd 'podman') { $hints += 'podman: available (SL_RUNTIME=podman)' }
    else { $hints += 'podman: not on PATH' }

    if (Test-Cmd 'wsl') { $hints += 'WSL: wsl.exe available (SL_RUNTIME=wsl)' }
    elseif (Test-Cmd 'wsl.exe') { $hints += 'WSL: wsl.exe available (SL_RUNTIME=wsl)' }
    else { $hints += 'WSL: wsl.exe not found' }

    $apple = $false
    foreach ($c in @('container', 'container.exe')) {
        if (Test-Cmd $c) { $apple = $true; break }
    }
    if ($apple) { $hints += 'Apple Container: container CLI available (SL_RUNTIME=apple|container)' }
    else { $hints += 'Apple Container: container CLI not found (macOS only)' }

    Write-Info 'engine probe:'
    foreach ($h in $hints) { Write-Host "  - $h" }
}

function Resolve-Runtime {
    $raw = $env:SL_RUNTIME
    if ([string]::IsNullOrWhiteSpace($raw)) { return 'process-compose' }
    switch -Regex ($raw.Trim().ToLowerInvariant()) {
        '^(process-compose|pc|default)$' { return 'process-compose' }
        '^(pheno|pheno-compose|phenocompose|nvms)$' { return 'pheno' }
        '^(podman)$' { return 'podman' }
        '^(wsl)$' { return 'wsl' }
        '^(apple|apple-container|container)$' { return 'apple' }
        default {
            Write-Err "Unknown SL_RUNTIME='$raw'. Use process-compose|pheno|podman|wsl|apple|container."
            exit 2
        }
    }
}

function Invoke-ProcessCompose {
    if (-not (Test-Cmd 'process-compose')) {
        Write-Err @'
process-compose not found on PATH.

Install: https://github.com/F1bonacc1/process-compose
  macOS:  brew install f1bonacc1/tap/process-compose
  Or run crates manually:
    cargo run -p sl-daemon -- serve
    cargo run -p sl-viewer

This facade defaults to process-compose (ADR 0001: CLI/ops stack, no tray).
'@
        exit 1
    }
    $composeFile = Join-Path $RepoRoot 'process-compose.yaml'
    Write-Info "starting process-compose -f $composeFile up"
    & process-compose -f $composeFile up @Passthrough
    exit $LASTEXITCODE
}

function Invoke-Pheno {
    $cli = $null
    foreach ($c in @('pheno-compose', 'nvms')) {
        if (Test-Cmd $c) { $cli = $c; break }
    }
    if (-not $cli) {
        Write-Err @'
SL_RUNTIME=pheno but neither pheno-compose nor nvms is on PATH.

Install (Phenotype / PhenoCompose):
  curl -fsSL https://get.nvms.dev | sh
  # or: cargo install pheno-compose --features nvms-driver
  # or: go build from https://github.com/KooshaPari/nvms

SessionLedger does not vendor PhenoCompose. Prefer process-compose for zero-dep local dev:
  $env:SL_RUNTIME = 'process-compose'; pwsh ./scripts/runtime-up.ps1

Stub compose (comment-only): compose/pheno-compose.yaml
Docs: docs/ops/runtime-facade.md
'@
        exit 1
    }

    $stub = Join-Path $RepoRoot 'compose/pheno-compose.yaml'
    $fileArgs = @()
    if (Test-Path $stub) {
        $fileArgs = @('-f', $stub)
        Write-Info "using stub/config $stub (see comments inside for Phenotype alignment)"
    }

    Write-Info "delegating to $cli $($fileArgs -join ' ') up"
    & $cli @fileArgs up @Passthrough
    if ($LASTEXITCODE -ne 0) {
        Write-Err @"
$cli exited with code $LASTEXITCODE.
If the CLI does not accept 'up' yet, use process-compose:
  `$env:SL_RUNTIME = 'process-compose'; pwsh ./scripts/runtime-up.ps1
Or follow PhenoCompose/nvms docs for the current compose subcommand.
"@
        exit $LASTEXITCODE
    }
    exit 0
}

function Invoke-Podman {
    if (-not (Test-Cmd 'podman')) {
        Write-Err @'
SL_RUNTIME=podman but podman is not on PATH.

Install Podman, then either:
  podman-compose -f compose/podman-compose.yaml up
  # or this script: podman build + run from root Containerfile

Fallback: $env:SL_RUNTIME = 'process-compose'; pwsh ./scripts/runtime-up.ps1
'@
        exit 1
    }

    $cf = Join-Path $RepoRoot 'Containerfile'
    if (-not (Test-Path $cf)) {
        $cf = Join-Path $RepoRoot 'crates/sl-daemon/Containerfile'
    }
    if (-not (Test-Path $cf)) {
        Write-Err 'No Containerfile found at repo root or crates/sl-daemon/Containerfile.'
        exit 1
    }

    if (Test-Cmd 'podman-compose') {
        $pcf = Join-Path $RepoRoot 'compose/podman-compose.yaml'
        if (Test-Path $pcf) {
            Write-Info "podman-compose -f $pcf up"
            & podman-compose -f $pcf up @Passthrough
            exit $LASTEXITCODE
        }
        Write-Info 'podman-compose on PATH but compose/podman-compose.yaml missing; using podman build/run'
    }

    $image = if ($env:SL_PODMAN_IMAGE) { $env:SL_PODMAN_IMAGE } else { 'sl-daemon:local' }
    $data = Join-Path $RepoRoot '.sl-data'
    New-Item -ItemType Directory -Force -Path $data | Out-Null
    $sessions = Join-Path $data 'sessions'
    $out = Join-Path $data 'out'
    New-Item -ItemType Directory -Force -Path $sessions, $out | Out-Null

    Write-Info "podman build -t $image -f $cf ."
    & podman build -t $image -f $cf .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $port = if ($env:SL_PORT) { $env:SL_PORT } else { '8080' }
    Write-Info "podman run --rm -p ${port}:8080 -v ${data}:/data $image"
    & podman run --rm `
        -p "${port}:8080" `
        -v "${data}:/data" `
        -e "SL_DATA_DIR=/data" `
        -e "SL_PORT=8080" `
        $image @Passthrough
    exit $LASTEXITCODE
}

function Invoke-Wsl {
    $wsl = $null
    foreach ($c in @('wsl', 'wsl.exe')) {
        if (Test-Cmd $c) { $wsl = $c; break }
    }
    if (-not $wsl) {
        Write-Err @'
SL_RUNTIME=wsl but wsl.exe was not found.

Install/enable WSL2 on Windows, then re-run, or use:
  $env:SL_RUNTIME = 'process-compose'; pwsh ./scripts/runtime-up.ps1
'@
        exit 1
    }

    $unixRoot = (& $wsl -e wslpath -a "$RepoRoot" 2>$null | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($unixRoot)) {
        $drive = $RepoRoot.Substring(0, 1).ToLowerInvariant()
        $rest = ($RepoRoot.Substring(2) -replace '\\', '/')
        $unixRoot = "/mnt/$drive$rest"
    }

    Write-Info "delegating into WSL: bash scripts/runtime-up.sh (SL_RUNTIME=process-compose inside)"
    Write-Info 'Tip: install process-compose or podman inside the distro; host Windows binaries are not used.'
    & $wsl -e bash -lc "cd '$unixRoot' && SL_RUNTIME=process-compose ./scripts/runtime-up.sh"
    exit $LASTEXITCODE
}

function Invoke-AppleContainer {
    $cli = $null
    foreach ($c in @('container', 'container.exe')) {
        if (Test-Cmd $c) { $cli = $c; break }
    }
    if (-not $cli) {
        Write-Err @'
SL_RUNTIME=apple|container but the Apple `container` CLI was not found.

Apple Container is macOS-only (OSS per-container VM). On Windows/Linux use:
  $env:SL_RUNTIME = 'process-compose'   # default
  $env:SL_RUNTIME = 'podman'            # OCI via Podman
See crates/sl-daemon/README.md for `container build/run` examples.
'@
        exit 1
    }

    $cf = Join-Path $RepoRoot 'crates/sl-daemon/Containerfile'
    if (-not (Test-Path $cf)) { $cf = Join-Path $RepoRoot 'Containerfile' }
    $image = if ($env:SL_CONTAINER_IMAGE) { $env:SL_CONTAINER_IMAGE } else { 'sl-daemon:latest' }
    $data = Join-Path $RepoRoot '.sl-data'
    $sessions = Join-Path $data 'sessions'
    $out = Join-Path $data 'out'
    New-Item -ItemType Directory -Force -Path $sessions, $out | Out-Null

    Write-Info "$cli build -t $image -f $cf ."
    & $cli build -t $image -f $cf .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Info "$cli run --rm -v sessions/out -p 8080 $image"
    & $cli run --rm `
        -v "${sessions}:/data/sessions" `
        -v "${out}:/data/out" `
        -p 8080:8080 `
        $image @Passthrough
    exit $LASTEXITCODE
}

# --- main ---
Show-EngineHints
$runtime = Resolve-Runtime
Write-Info "SL_RUNTIME -> $runtime"

switch ($runtime) {
    'process-compose' { Invoke-ProcessCompose }
    'pheno' { Invoke-Pheno }
    'podman' { Invoke-Podman }
    'wsl' { Invoke-Wsl }
    'apple' { Invoke-AppleContainer }
}
