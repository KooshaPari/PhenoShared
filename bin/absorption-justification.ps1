# absorption-justification.ps1
# ----------------------------------------------------------------------------
# PowerShell companion to bin/absorption-justification.py. Mirrors the bash
# wrapper so Windows-first CI runners (and local developers) can drive the
# orchestrator without needing bash.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File bin\absorption-justification.ps1 `
#     -Repos "<REDACTED>/foo,<REDACTED>/bar" `
#     [-RegistryRoot PATH] [-AuditsDir PATH] `
#     [-Template PATH] [-Disposition PATH] `
#     [-DryRun] [-Verbose]
# ----------------------------------------------------------------------------
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repos,
    [string]$RegistryRoot = ".",
    [string]$AuditsDir = "",
    [string]$Template = "",
    [string]$Disposition = "",
    [switch]$DryRun,
    [switch]$VerboseSwitch
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrEmpty($AuditsDir)) {
    $AuditsDir = Join-Path $RegistryRoot "audits\absorption-justifications"
}

if ([string]::IsNullOrEmpty($Template)) {
    $candidates = @(
        (Join-Path (Split-Path $RegistryRoot -Parent) "phenotype-tooling\bin\ABSORPTION_TEMPLATE.md"),
        (Join-Path $RegistryRoot "bin\ABSORPTION_TEMPLATE.md")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $Template = $c; break }
    }
}

if ([string]::IsNullOrEmpty($Disposition)) {
    $Disposition = Join-Path $RegistryRoot "registry\disposition-index.json"
}

if ([string]::IsNullOrEmpty($Template) -or -not (Test-Path $Template)) {
    Write-Error "could not locate ABSORPTION_TEMPLATE.md"
    exit 2
}

$python = $env:PYTHON
if ([string]::IsNullOrEmpty($python)) { $python = "python" }

$argsList = @(
    (Join-Path $scriptDir "absorption-justification.py"),
    "--repos", $Repos,
    "--registry-root", $RegistryRoot,
    "--template", $Template,
    "--disposition", $Disposition,
    "--audits-dir", $AuditsDir
)
if ($DryRun) { $argsList += "--dry-run" }
if ($VerboseSwitch) { $argsList += "--verbose" }

& $python @argsList
exit $LASTEXITCODE