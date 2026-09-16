# scripts/disk_budget_watch.ps1
# N22 — disk-budget watchdog (Forward DAG v2)
# Enforces config/disk_budget_2026-07.yaml. CHECK (default) reports footprint vs budget.
# Restored 2026-08-19 after untracked wipe (git clean). Includes parser fix (last root save) + Depth 4 removal.

[CmdletBinding()]
param(
    [switch]$Prune,
    [switch]$Check,
    [string]$ConfigPath = 'C:\Users\koosh\pheno-harness\config\disk_budget_2026-07.yaml',
    [string]$StateDir   = 'C:\Users\koosh\pheno-harness\state',
    [string[]]$DownloadGuardArgs = @()
)

$ErrorActionPreference = 'Stop'

function Read-Config([string]$Path) {
    if (-not (Test-Path $Path)) { throw "Config not found: $Path" }
    $content = Get-Content $Path -Raw
    $cfg = [ordered]@{}
    $currentSection = $null
    $currentList    = $null
    foreach ($line in ($content -split "`n")) {
        $trim = $line.TrimEnd("`r")
        if ($trim -match '^\s*#' -or $trim -match '^\s*$') { continue }
        if ($trim -match '^(?<k>[a-zA-Z_][\w_]*):\s*(?<v>.*)$') {
            $k = $Matches['k']; $v = $Matches['v']
            if ($v -match '^\[.*\]$' -or $v -eq '') {
                $currentSection = $k
                if ($v -match '^\[(.*)\]$' -and $Matches[1].Trim() -ne '') {
                    $cfg[$k] = @($Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") })
                } else { $cfg[$k] = @{} }
            } else {
                $vClean = ($v -replace '\s+#\s.*$', '').Trim().Trim('"').Trim("'")
                if ($vClean -match '^-?\d+(\.\d+)?$') {
                    if ($vClean -match '\.') { $cfg[$k] = [double]$vClean } else { $cfg[$k] = [int]$vClean }
                } else { $cfg[$k] = $vClean }
            }
        } elseif ($trim -match '^\s*-\s+(?<v>.+)$') {
            if ($null -eq $currentList) { $currentList = @() }
            $currentList += @($Matches['v'].Trim().Trim('"').Trim("'"))
            if ($null -ne $currentSection) { $cfg[$currentSection] = $currentList }
        }
    }
    return $cfg
}

function Get-DirSizeGB([string]$Path) {
    if (-not (Test-Path $Path)) { return 0.0 }
    $bytes = 0L
    foreach ($d in (Get-ChildItem -Path $Path -Directory -ErrorAction SilentlyContinue)) {
        $sub = (Get-ChildItem -Path $d.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $bytes += if ($sub) { $sub } else { 0L }
    }
    $top = (Get-ChildItem -Path $Path -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $bytes += if ($top) { $top } else { 0L }
    return [math]::Round($bytes / 1GB, 2)
}

function Emit-Status($Cfg, $Footprints, $TotalGB) {
    $budget = $Cfg['budget_gb']; $warn = $Cfg['warn_gb']
    $status = if ($TotalGB -ge $budget) { 'over_budget' } elseif ($TotalGB -ge $warn) { 'warn' } else { 'healthy' }
    $ts = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $logDir = Join-Path $StateDir 'disk_budget_log'
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
    $obj = [ordered]@{
        ts = $ts; status = $status; total_gb = $TotalGB; budget_gb = $budget; warn_gb = $warn
        headroom_gb = [math]::Round($budget - $TotalGB, 2)
        footprints = $Footprints
    }
    $json = $obj | ConvertTo-Json -Depth 4
    $json | Set-Content -Path (Join-Path $logDir "disk_budget_status_$ts.json") -Encoding utf8
    $json | Set-Content -Path (Join-Path $logDir 'disk_budget_latest.json') -Encoding utf8
    $label = if ($status -eq 'healthy') { 'HEALTHY' } elseif ($status -eq 'warn') { 'WARN' } else { 'OVER BUDGET' }
    Write-Host "Disk budget status: $label"
    Write-Host "  Total: $TotalGB GB (budget $budget GB, warn $warn GB)"
    foreach ($f in $Footprints) { Write-Host "  $($f.id.PadRight(25)) $($f.size_gb) GB  ($($f.path))" }
    Write-Host "  Status JSON: $(Join-Path $logDir "disk_budget_status_$ts.json")"
    if ($status -eq 'over_budget') { [Environment]::Exit(3) } elseif ($status -eq 'warn') { [Environment]::Exit(2) }
}

# Parse roots block separately (handles nested list under roots:)
$yamlText = Get-Content $ConfigPath -Raw
$cfg = Read-Config $ConfigPath
$roots = @(); $inRoots = $false; $cur = $null
foreach ($line in ($yamlText -split "`n")) {
    $raw = $line.TrimEnd("`r"); $trim = $raw.TrimEnd()
    if ($trim -match '^roots:\s*$') { $inRoots = $true; $cur = $null; continue }
    if (-not $inRoots) { continue }
    if ($trim -match '^\s*#' -or $trim -match '^\s*$') { continue }
    if ($trim -match '^\s+-\s+id:\s+(?<id>.+)$') {
        if ($null -ne $cur) { $roots += $cur }
        $cur = [ordered]@{ id = $Matches['id'].Trim().Trim('"').Trim("'") }
        continue
    }
    if ($null -ne $cur -and $trim -match '^\s+(?<k>path|purpose):\s+(?<v>.+)$') {
        $cur[$Matches['k']] = $Matches['v'].Trim().Trim('"').Trim("'")
        continue
    }
    if ($raw -match '^[a-zA-Z_][\w_]*:' -and $raw -notmatch '^\s') {
        if ($null -ne $cur) { $roots += $cur }
        $inRoots = $false; $cur = $null
    }
}
if ($null -ne $cur) { $roots += $cur }
$cfg['roots'] = $roots

# Main CHECK
$footprints = @(); $totalGB = 0.0
foreach ($r in $cfg['roots']) {
    $sz = Get-DirSizeGB $r.path
    $footprints += [pscustomobject]@{ id = $r.id; path = $r.path; size_gb = $sz }
    $totalGB += $sz
}
$totalGB = [math]::Round($totalGB, 2)
Emit-Status -Cfg $cfg -Footprints $footprints -TotalGB $totalGB
