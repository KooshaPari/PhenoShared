<#
.SYNOPSIS
  Machine-check sl-viewer CLI help anchors (C01/C09 DX).

.DESCRIPTION
  Verifies docs/ops/sl-viewer-help.md + sl-viewer-help.json document expanded
  --help/--version output, SL_DAEMON_URL / FORGE_DB env vars, and blocking PR
  workflow wiring. Hermetic: -SelfCheck needs no GUI launch.

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof).

.EXAMPLE
  pwsh ./scripts/sl-viewer-help-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/sl-viewer-help.md"
$policyPath = Join-Path $repoRoot "docs/ops/sl-viewer-help.json"
$helpMdPath = Join-Path $repoRoot "docs/HELP.md"
$envExamplePath = Join-Path $repoRoot ".env.example"
$hardWorkflowPath = Join-Path $repoRoot ".github/workflows/sl-viewer-help-hard.yml"
$cliHelpPath = Join-Path $repoRoot "crates/sl-viewer/src/cli_help.rs"
$mainRsPath = Join-Path $repoRoot "crates/sl-viewer/src/main.rs"
$libRsPath = Join-Path $repoRoot "crates/sl-viewer/src/lib.rs"
$daemonUrlPath = Join-Path $repoRoot "crates/sl-viewer/src/daemon_url.rs"
$selfPath = Join-Path $repoRoot "scripts/sl-viewer-help-check.ps1"
$wrapperTest = Join-Path $repoRoot "tests/sl_viewer_help.rs"

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

function Test-DocContains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "docs/ops/sl-viewer-help.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

Write-Host "sl-viewer CLI help check (C01/C09)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + cli_help.rs anchors; no GUI launch)"
}

Assert-File -Path $docPath -Label "sl-viewer-help doc"
Assert-File -Path $policyPath -Label "sl-viewer-help policy JSON"
Assert-File -Path $helpMdPath -Label "HELP.md"
Assert-File -Path $envExamplePath -Label ".env.example"
Assert-File -Path $hardWorkflowPath -Label "sl-viewer-help-hard workflow"
Assert-File -Path $cliHelpPath -Label "cli_help.rs"
Assert-File -Path $mainRsPath -Label "sl-viewer main.rs"
Assert-File -Path $libRsPath -Label "sl-viewer lib.rs"
Assert-File -Path $daemonUrlPath -Label "daemon_url.rs"
Assert-File -Path $selfPath -Label "sl-viewer-help check script"
Assert-File -Path $wrapperTest -Label "sl_viewer_help.rs test wrapper"

$doc = Get-Content -LiteralPath $docPath -Raw
$policyRaw = Get-Content -LiteralPath $policyPath -Raw
$policy = $policyRaw | ConvertFrom-Json
$helpMd = Get-Content -LiteralPath $helpMdPath -Raw
$envExample = Get-Content -LiteralPath $envExamplePath -Raw
$hardWorkflow = Get-Content -LiteralPath $hardWorkflowPath -Raw
$cliHelp = Get-Content -LiteralPath $cliHelpPath -Raw
$mainRs = Get-Content -LiteralPath $mainRsPath -Raw
$libRs = Get-Content -LiteralPath $libRsPath -Raw
$wrapperRs = Get-Content -LiteralPath $wrapperTest -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "# sl-viewer CLI help (C01/C09 DX)" `
    -Label "doc heading"
Test-DocContains -Doc $doc -Needle "scripts/sl-viewer-help-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "SL_DAEMON_URL" `
    -Label "SL_DAEMON_URL documented"
Test-DocContains -Doc $doc -Needle "FORGE_DB" `
    -Label "FORGE_DB documented"
Test-DocContains -Doc $doc -Needle "Blocking sl-viewer-help-hard CI workflow | **done**" `
    -Label "blocking workflow marked done"
Test-DocContains -Doc $doc -Needle "Fluent i18n migration for help text | **unpaid**" `
    -Label "fluent i18n unpaid gate"
Test-DocContains -Doc $doc -Needle ".github/workflows/sl-viewer-help-hard.yml" `
    -Label "hard workflow path documented"

Write-Host "Policy JSON anchors:"
Test-DocContains -Doc $policyRaw -Needle '"schema_version"' `
    -Label "schema_version" -Context "sl-viewer-help.json"
if ($policy.environment_variables.name -notcontains "SL_DAEMON_URL") {
    throw "sl-viewer-help.json must list SL_DAEMON_URL."
}
[void](Write-Check -Label "policy SL_DAEMON_URL" -Ok $true)
if ($policy.environment_variables.name -notcontains "FORGE_DB") {
    throw "sl-viewer-help.json must list FORGE_DB."
}
[void](Write-Check -Label "policy FORGE_DB" -Ok $true)

Write-Host "HELP.md / .env.example cross-links:"
Test-DocContains -Doc $helpMd -Needle "sl-viewer-help.md" `
    -Label "HELP.md cross-link" -Context "docs/HELP.md"
Test-DocContains -Doc $envExample -Needle "FORGE_DB" `
    -Label ".env.example FORGE_DB" -Context ".env.example"
Test-DocContains -Doc $envExample -Needle "SL_DAEMON_URL" `
    -Label ".env.example SL_DAEMON_URL" -Context ".env.example"

Write-Host "cli_help.rs / main.rs anchors:"
if ($libRs -notmatch 'pub mod cli_help') {
    throw "lib.rs must export cli_help module."
}
[void](Write-Check -Label "lib.rs cli_help module" -Ok $true)
if ($cliHelp -notmatch 'SL_DAEMON_URL') {
    throw "cli_help.rs must document SL_DAEMON_URL."
}
[void](Write-Check -Label "cli_help SL_DAEMON_URL" -Ok $true)
if ($cliHelp -notmatch 'FORGE_DB') {
    throw "cli_help.rs must document FORGE_DB."
}
[void](Write-Check -Label "cli_help FORGE_DB" -Ok $true)
if ($mainRs -notmatch 'cli_help::help_text') {
    throw "main.rs must print cli_help::help_text() for --help."
}
[void](Write-Check -Label "main.rs help_text" -Ok $true)
if ($mainRs -notmatch 'cli_help::version_text') {
    throw "main.rs must print cli_help::version_text() for --version."
}
[void](Write-Check -Label "main.rs version_text" -Ok $true)

Write-Host "Hard sl-viewer-help CI blocking-gate anchors:"
if ($hardWorkflow -match 'continue-on-error:\s*true') {
    throw "sl-viewer-help-hard.yml must not set continue-on-error (blocking PR CI)."
}
[void](Write-Check -Label "hard workflow has no continue-on-error" -Ok $true)
if ($hardWorkflow -notmatch 'pull_request:') {
    throw "sl-viewer-help-hard.yml must run on pull_request."
}
[void](Write-Check -Label "hard workflow triggers on pull_request" -Ok $true)
if ($hardWorkflow -notmatch 'sl-viewer-help-check\.ps1 -SelfCheck') {
    throw "sl-viewer-help-hard.yml must run sl-viewer-help-check.ps1 -SelfCheck."
}
[void](Write-Check -Label "hard workflow runs SelfCheck" -Ok $true)
if ($hardWorkflow -notmatch 'cargo test -p sl-viewer cli_help') {
    throw "sl-viewer-help-hard.yml must run cargo test -p sl-viewer cli_help."
}
[void](Write-Check -Label "hard workflow runs cli_help unit tests" -Ok $true)
if ($wrapperRs -notmatch 'sl-viewer-help-check\.ps1') {
    throw "tests/sl_viewer_help.rs must invoke sl-viewer-help-check.ps1."
}
[void](Write-Check -Label "sl_viewer_help.rs invokes SelfCheck script" -Ok $true)

Write-Host "sl-viewer help hard CI SelfCheck passed (C01/C09 DX; fluent i18n unpaid)."

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## sl-viewer CLI help SelfCheck (C01/C09)

SelfCheck passed: ``docs/ops/sl-viewer-help.md`` policy rows, ``cli_help.rs`` env
anchors, and blocking ``sl-viewer-help-hard.yml`` workflow. Fluent i18n
migration remains unpaid.
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

exit 0
