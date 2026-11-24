<#
.SYNOPSIS
  Back-compat wrapper for scripts/slsa-isolation-check.ps1 (C06 L53 SSOT).

.DESCRIPTION
  Delegates to slsa-isolation-check.ps1. Prefer invoking the SLSA script directly.

.PARAMETER SelfCheck
  Forwarded to slsa-isolation-check.ps1.

.PARAMETER Strict
  Forwarded to slsa-isolation-check.ps1.

.EXAMPLE
  pwsh ./scripts/hermetic-isolation-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck,

    [switch]$Strict
)

$delegate = Join-Path $PSScriptRoot "slsa-isolation-check.ps1"
if (-not (Test-Path -LiteralPath $delegate -PathType Leaf)) {
    throw "Missing SLSA isolation SSOT at '$delegate'."
}

& $delegate @PSBoundParameters
exit $LASTEXITCODE
