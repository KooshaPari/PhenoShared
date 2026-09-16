# Run TB2 route matrix (non-firepass cloud + local + Main router)
param(
    [string]$RouteKind = "",
    [string]$Model = "",
    [switch]$Pilot,
    [switch]$All,
    [switch]$Resume,
    [switch]$IncludeCombo,
    [switch]$Force,
    [switch]$ProbeOnly,
    [switch]$Scoreboard
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if ($ProbeOnly) {
    python scripts/probe_tbench_routes.py --force
    exit $LASTEXITCODE
}

if ($Scoreboard) {
    python scripts/tbench_route_scoreboard.py --export
    exit $LASTEXITCODE
}

$args = @()
if ($Model) { $args += @("--model", $Model) }
if ($RouteKind) { $args += @("--route-kind", $RouteKind) }
if ($Pilot) { $args += "--pilot" }
if ($All) { $args += "--all" }
if ($Resume) { $args += "--resume" }
if ($IncludeCombo) { $args += "--include-combo" }
if ($Force) { $args += "--force" }

python scripts/run_tbench_route_matrix.py @args
exit $LASTEXITCODE
