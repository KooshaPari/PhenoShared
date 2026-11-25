#Requires -Version 5.1
<#
.SYNOPSIS
  Run forge -p on the architecture lane.

.DESCRIPTION
  Forge already routes via OmniRoute through its native session config:
    C:\Users\koosh\forge\.forge.toml  -> [session] provider_id=openai_compatible, model_id=Main
    C:\Users\koosh\forge\.credentials.json -> OPENAI_URL=http://127.0.0.1:20128/v1

  Do NOT override OPENAI_* / ANTHROPIC_* here — that bypasses forge's provider store and
  can desync from what works in interactive `forge` TUI sessions.

  Optional: pass -Combo to set x-omniroute-combo on requests via forge env hook only.

.EXAMPLE
  .\scripts\forge_lane.ps1 -Prompt "Audit module boundaries in pheno-harness"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Prompt,

    [Alias("C")]
    [string]$Directory = (Get-Location).Path,

    [string]$Forge = "forge",
    [string]$Combo = "Main",
    [string]$Lane = "architecture"
)

$ErrorActionPreference = "Stop"

# Lane tags for pheno analytics only — forge session comes from ~/.forge.toml
$env:PHENO_LANE = $Lane
$env:PHENO_HARNESS = "pheno-harness"
if ($Combo) { $env:PHENO_OMNIROUTE_COMBO = $Combo }

Write-Host "==> forge -p (native session from ~/forge/.forge.toml)" -ForegroundColor Cyan
Write-Host "    lane=$Lane combo=$Combo dir=$Directory"
Write-Host "    config=$env:USERPROFILE\forge\.forge.toml"

& $Forge -p $Prompt -C $Directory
exit $LASTEXITCODE
