<#
.SYNOPSIS
  Machine-check the C06 L57 no-MCP-server ADR anchors.

.DESCRIPTION
  Verifies ADR 0006, AGENTS.md / llms.txt cross-links, and hermetic SelfCheck
  wiring. Does not claim MCP host/server support — asserts the explicit N/A.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.EXAMPLE
  pwsh ./scripts/mcp-scope-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$adrPath = Join-Path $repoRoot "docs/adr/0006-no-mcp-server.md"
$agentsPath = Join-Path $repoRoot "AGENTS.md"
$llmsPath = Join-Path $repoRoot "llms.txt"
$checkScript = Join-Path $repoRoot "scripts/mcp-scope-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/mcp_scope.rs"

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

Write-Host "MCP scope check (C06 L57)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (ADR + AGENTS + llms anchors; no MCP / no network)"
}

Assert-File -Path $adrPath -Label "ADR 0006 no-mcp-server"
Assert-File -Path $agentsPath -Label "AGENTS.md"
Assert-File -Path $llmsPath -Label "llms.txt"
Assert-File -Path $checkScript -Label "mcp scope check script"
Assert-File -Path $rustWrapper -Label "mcp scope rust SelfCheck wrapper"

$adr = Get-Content -LiteralPath $adrPath -Raw
$agents = Get-Content -LiteralPath $agentsPath -Raw
$llms = Get-Content -LiteralPath $llmsPath -Raw

Write-Host "ADR anchors:"
Assert-Contains -Doc $adr -Needle "No MCP host / server surface" `
    -Label "ADR title" -Context "ADR 0006"
Assert-Contains -Doc $adr -Needle "Status: Accepted" `
    -Label "ADR accepted" -Context "ADR 0006"
Assert-Contains -Doc $adr -Needle "does not** ship an MCP host" `
    -Label "explicit does-not-ship decision" -Context "ADR 0006"
Assert-Contains -Doc $adr -Needle "MCP server pin list" `
    -Label "no pin-list decision" -Context "ADR 0006"
Assert-Contains -Doc $adr -Needle "C06 L57" `
    -Label "L57 cross-ref" -Context "ADR 0006"
Assert-Contains -Doc $adr -Needle "intentional" `
    -Label "absence intentional" -Context "ADR 0006"

Write-Host "AGENTS.md anchors:"
Assert-Contains -Doc $agents -Needle "0006-no-mcp-server.md" `
    -Label "AGENTS links ADR 0006" -Context "AGENTS.md"
Assert-Contains -Doc $agents -Needle "MCP" `
    -Label "MCP mention" -Context "AGENTS.md"

Write-Host "llms.txt anchors:"
Assert-Contains -Doc $llms -Needle "0006-no-mcp-server.md" `
    -Label "llms links ADR 0006" -Context "llms.txt"
Assert-Contains -Doc $llms -Needle "MCP" `
    -Label "MCP mention" -Context "llms.txt"

# Ensure we did not accidentally add MCP pin / host configs.
foreach ($forbidden in @("mcp.json", ".mcp.json", "phenoMCP.json", "phenomcp.json")) {
    $hit = Get-ChildItem -LiteralPath $repoRoot -Recurse -Filter $forbidden -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch '\\audit\\' -and
            $_.FullName -notmatch '\\target' -and
            $_.FullName -notmatch '\\.git\\'
        }
    $ok = -not $hit
    [void](Write-Check -Label "no $forbidden in tree" -Ok $ok)
    if (-not $ok) {
        throw "Unexpected $forbidden present — contradicts ADR 0006."
    }
}

Write-Host "MCP scope SelfCheck passed (C06 L57 ADR 0006 — no MCP host/server / no pin list)."
