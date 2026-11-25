<#
.SYNOPSIS
  Machine-check the C11 L114 no-serverless/edge deploy ADR anchors.

.DESCRIPTION
  Verifies ADR 0005, distribution.md cross-link, and hermetic SelfCheck wiring.
  Does not claim Workers/Vercel support — asserts the explicit non-goal.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.EXAMPLE
  pwsh ./scripts/edge-deploy-scope-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$adrPath = Join-Path $repoRoot "docs/adr/0005-no-serverless-edge.md"
$distPath = Join-Path $repoRoot "docs/ops/distribution.md"
$checkScript = Join-Path $repoRoot "scripts/edge-deploy-scope-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/edge_deploy_scope.rs"

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

function Write-Check {
    param([string]$Label, [bool]$Ok)
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "  [$mark] $Label"
    return $Ok
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "document"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "Edge/serverless deploy scope check (C11 L114)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (ADR + distribution anchors; no Workers / no network)"
}

Assert-File -Path $adrPath -Label "ADR 0005 no-serverless-edge"
Assert-File -Path $distPath -Label "distribution ops doc"
Assert-File -Path $checkScript -Label "edge deploy scope check script"
Assert-File -Path $rustWrapper -Label "edge deploy scope rust SelfCheck wrapper"

$adr = Get-Content -LiteralPath $adrPath -Raw
$dist = Get-Content -LiteralPath $distPath -Raw

Write-Host "ADR anchors:"
Assert-Contains -Doc $adr -Needle "No serverless / edge deploy target" `
    -Label "ADR title" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "Status: Accepted" `
    -Label "ADR accepted" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "Cloudflare Workers" `
    -Label "Workers non-goal" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "Vercel" `
    -Label "Vercel non-goal" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "does not** target" `
    -Label "explicit does-not-target decision" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "wrangler.toml" `
    -Label "wrangler absence intentional" -Context "ADR 0005"
Assert-Contains -Doc $adr -Needle "C11 L114" `
    -Label "L114 cross-ref" -Context "ADR 0005"

Write-Host "Distribution anchors:"
Assert-Contains -Doc $dist -Needle "0005-no-serverless-edge.md" `
    -Label "distribution links ADR 0005" -Context "distribution.md"
Assert-Contains -Doc $dist -Needle "serverless" `
    -Label "serverless mention" -Context "distribution.md"
Assert-Contains -Doc $dist -Needle "Workers" `
    -Label "Workers mention" -Context "distribution.md"

# Ensure we did not accidentally add edge deploy configs.
foreach ($forbidden in @("wrangler.toml", "vercel.json")) {
    $hit = Get-ChildItem -LiteralPath $repoRoot -Recurse -Filter $forbidden -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\audit\\' -and $_.FullName -notmatch '\\target' }
    $ok = -not $hit
    [void](Write-Check -Label "no $forbidden in tree" -Ok $ok)
    if (-not $ok) {
        throw "Unexpected $forbidden present — contradicts ADR 0005."
    }
}

Write-Host "Edge deploy scope SelfCheck passed (C11 L114 ADR 0005 — no Workers/Vercel target)."
