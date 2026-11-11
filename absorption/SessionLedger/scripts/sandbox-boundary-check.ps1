<#
.SYNOPSIS
  Machine-check the C04 L40 sandbox boundary checklist anchors.

.DESCRIPTION
  Verifies docs/ops/sandbox-boundary.md documents process isolation evidence
  (non-root container USER, loopback bind, data-dir VOLUME, soft seccomp /
  no-new-privileges / cap-drop / soft no-net policy) and that
  crates/sl-daemon/Containerfile + packaging/oci seccomp profile +
  trust-boundary docs retain required anchors.
  Hermetic: no container build, no network, no cargo.

  Does not claim maintainer 2FA (L36) or hard rootless / no-net runner enforcement (SelfCheck CI is blocking).

.PARAMETER SelfCheck
  Explicit docs/path smoke (CI unit proof). Same checks as the default path.

.EXAMPLE
  pwsh ./scripts/sandbox-boundary-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/sandbox-boundary.md"
$containerPath = Join-Path $repoRoot "crates/sl-daemon/Containerfile"
$threatPath = Join-Path $repoRoot "docs/THREAT_MODEL.md"
$trustPath = Join-Path $repoRoot "docs/ops/local-trust-boundary.md"
$systemdPath = Join-Path $repoRoot "packaging/systemd/sessionledger-daemon.service"
$seccompPath = Join-Path $repoRoot "packaging/oci/sl-daemon-seccomp.json"
$composePath = Join-Path $repoRoot "packaging/oci/compose.sl-daemon.soft-hardening.yml"
$securityWorkflow = Join-Path $repoRoot ".github/workflows/security.yml"
$ciWorkflow = Join-Path $repoRoot ".github/workflows/ci.yml"
$selfPath = Join-Path $repoRoot "scripts/sandbox-boundary-check.ps1"

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
        [string]$Context = "docs/ops/sandbox-boundary.md"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

function Get-YamlJobBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Document,
        [Parameter(Mandatory = $true)][string]$JobName
    )

    $lines = $Document -split "\r?\n"
    $start = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -eq "  ${JobName}:") {
            $start = $index
            break
        }
    }
    if ($start -lt 0) {
        throw "Workflow missing '$JobName' job definition."
    }

    $end = $lines.Count
    for ($index = $start + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^  [A-Za-z0-9_-]+:\s*$') {
            $end = $index
            break
        }
    }
    return ($lines[$start..($end - 1)] -join "`n")
}

Write-Host "Sandbox boundary checklist check (C04 L40)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + Containerfile + seccomp + workflow anchors; no build / no network)"
}

Assert-File -Path $docPath -Label "sandbox boundary doc"
Assert-File -Path $containerPath -Label "sl-daemon Containerfile"
Assert-File -Path $threatPath -Label "THREAT_MODEL.md"
Assert-File -Path $trustPath -Label "local trust boundary doc"
Assert-File -Path $systemdPath -Label "systemd unit sample"
Assert-File -Path $seccompPath -Label "soft seccomp profile"
Assert-File -Path $composePath -Label "soft hardening compose sample"
Assert-File -Path $securityWorkflow -Label "security workflow"
Assert-File -Path $ciWorkflow -Label "ci workflow"
Assert-File -Path $selfPath -Label "sandbox boundary check script"

$doc = Get-Content -LiteralPath $docPath -Raw
$container = Get-Content -LiteralPath $containerPath -Raw
$threat = Get-Content -LiteralPath $threatPath -Raw
$trust = Get-Content -LiteralPath $trustPath -Raw
$systemd = Get-Content -LiteralPath $systemdPath -Raw
$seccomp = Get-Content -LiteralPath $seccompPath -Raw
$compose = Get-Content -LiteralPath $composePath -Raw
$securityWf = Get-Content -LiteralPath $securityWorkflow -Raw
$ciWf = Get-Content -LiteralPath $ciWorkflow -Raw

Write-Host "Sandbox boundary doc anchors:"
Test-DocContains -Doc $doc -Needle "Sandbox boundary checklist (process isolation)" `
    -Label "checklist heading"
Test-DocContains -Doc $doc -Needle "scripts/sandbox-boundary-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Sandbox boundary SelfCheck | **done**" `
    -Label "SelfCheck gate marked done"
Test-DocContains -Doc $doc -Needle "Non-root runtime user | **done**" `
    -Label "non-root USER gate marked done"
Test-DocContains -Doc $doc -Needle "Data-dir volume contract | **done**" `
    -Label "data VOLUME gate marked done"
Test-DocContains -Doc $doc -Needle "Loopback HTTP bind | **done**" `
    -Label "loopback bind gate marked done"
Test-DocContains -Doc $doc -Needle "Soft seccomp profile JSON | **done**" `
    -Label "soft seccomp profile gate marked done"
Test-DocContains -Doc $doc -Needle "Soft ``no-new-privileges`` + ``cap-drop ALL`` guidance | **done**" `
    -Label "no-new-privileges / cap-drop gate marked done"
Test-DocContains -Doc $doc -Needle "Soft no-net policy documented | **done**" `
    -Label "soft no-net policy gate marked done"
Test-DocContains -Doc $doc -Needle "no-new-privileges:true" `
    -Label "no-new-privileges security-opt documented"
Test-DocContains -Doc $doc -Needle "--cap-drop ALL" `
    -Label "cap-drop ALL documented"
Test-DocContains -Doc $doc -Needle "packaging/oci/sl-daemon-seccomp.json" `
    -Label "seccomp profile path documented"
Test-DocContains -Doc $doc -Needle "Hard no-network CI sandbox for security jobs | **unpaid**" `
    -Label "hard no-net CI remains unpaid"
Test-DocContains -Doc $doc -Needle "does **not** claim maintainer 2FA enforcement" `
    -Label "no 2FA claim disclaimer"
Test-DocContains -Doc $doc -Needle "docs/THREAT_MODEL.md" `
    -Label "THREAT_MODEL cross-link"
Test-DocContains -Doc $doc -Needle "local-trust-boundary.md" `
    -Label "local-trust-boundary cross-link"

Write-Host "Soft seccomp / compose anchors:"
if ($seccomp -notmatch '"defaultAction"\s*:\s*"SCMP_ACT_ALLOW"') {
    throw "seccomp profile missing defaultAction SCMP_ACT_ALLOW."
}
[void](Write-Check -Label "seccomp defaultAction SCMP_ACT_ALLOW" -Ok $true)

if ($seccomp -notmatch '"action"\s*:\s*"SCMP_ACT_ERRNO"') {
    throw "seccomp profile missing deny-list SCMP_ACT_ERRNO entries."
}
[void](Write-Check -Label "seccomp deny-list SCMP_ACT_ERRNO" -Ok $true)

foreach ($syscall in @("mount", "reboot", "bpf", "unshare", "setns")) {
    if ($seccomp -notmatch [regex]::Escape('"' + $syscall + '"')) {
        throw "seccomp profile missing deny entry for syscall '$syscall'."
    }
}
[void](Write-Check -Label "seccomp denies mount/reboot/bpf/unshare/setns" -Ok $true)

if ($compose -notmatch 'no-new-privileges:true') {
    throw "compose sample missing no-new-privileges:true."
}
[void](Write-Check -Label "compose no-new-privileges" -Ok $true)

if ($compose -notmatch 'seccomp=./packaging/oci/sl-daemon-seccomp.json') {
    throw "compose sample missing seccomp profile path."
}
[void](Write-Check -Label "compose seccomp profile path" -Ok $true)

if ($compose -notmatch '(?m)^\s*cap_drop:\s*$' -and $compose -notmatch 'cap_drop:') {
    throw "compose sample missing cap_drop."
}
if ($compose -notmatch '(?m)^\s*-\s*ALL\s*$') {
    throw "compose sample missing cap_drop ALL."
}
[void](Write-Check -Label "compose cap_drop ALL" -Ok $true)

if ($compose -notmatch 'network_mode:\s*"none"') {
    throw "compose sample missing soft no-net network_mode none guidance."
}
[void](Write-Check -Label "compose soft no-net comment/anchor" -Ok $true)

Write-Host "Containerfile isolation anchors:"
if ($container -notmatch '(?m)^USER\s+sl\s*$') {
    throw "Containerfile missing non-root USER sl directive."
}
[void](Write-Check -Label "Containerfile USER sl" -Ok $true)

if ($container -notmatch 'VOLUME\s+\["/data/sessions",\s*"/data/out"\]') {
    throw "Containerfile missing VOLUME [""/data/sessions"", ""/data/out""]."
}
[void](Write-Check -Label "Containerfile VOLUME data dirs" -Ok $true)

if ($container -notmatch '127\.0\.0\.1:8080/healthz') {
    throw "Containerfile HEALTHCHECK must probe loopback 127.0.0.1:8080/healthz."
}
[void](Write-Check -Label "Containerfile loopback HEALTHCHECK" -Ok $true)

if ($container -notmatch 'useradd.*\bsl\b') {
    throw "Containerfile missing useradd for sl system user."
}
[void](Write-Check -Label "Containerfile useradd sl" -Ok $true)

Write-Host "Trust-boundary doc anchors:"
Test-DocContains -Doc $threat -Needle "**Trust boundaries:**" `
    -Label "THREAT_MODEL trust boundaries section" -Context "docs/THREAT_MODEL.md"
Test-DocContains -Doc $threat -Needle "127.0.0.1:8080" `
    -Label "THREAT_MODEL loopback default" -Context "docs/THREAT_MODEL.md"
Test-DocContains -Doc $trust -Needle "Prefer binding HTTP to loopback" `
    -Label "local-trust-boundary loopback policy" -Context "docs/ops/local-trust-boundary.md"
Test-DocContains -Doc $trust -Needle "**Startup deny**" `
    -Label "local-trust-boundary non-loopback deny" -Context "docs/ops/local-trust-boundary.md"

if ($systemd -notmatch 'SL_HTTP_BIND=127\.0\.0\.1:8080') {
    throw "systemd unit missing SL_HTTP_BIND=127.0.0.1:8080."
}
[void](Write-Check -Label "systemd loopback bind env" -Ok $true)

Write-Host "CI least-privilege anchors:"
if ($securityWf -notmatch 'permissions:\s*\r?\n\s*contents:\s*read') {
    throw "security.yml missing permissions: contents: read."
}
[void](Write-Check -Label "security.yml contents: read" -Ok $true)

if ($securityWf -notmatch 'sandbox-boundary:') {
    throw "security.yml missing sandbox-boundary job."
}
[void](Write-Check -Label "security.yml sandbox-boundary job" -Ok $true)

# Extract the sandbox-boundary job block and require it to be blocking.
$sbBlock = Get-YamlJobBlock -Document $securityWf -JobName "sandbox-boundary"
if ($sbBlock -match 'continue-on-error:\s*true') {
    throw "sandbox-boundary job must be blocking (remove continue-on-error: true)."
}
[void](Write-Check -Label "sandbox-boundary job is blocking" -Ok $true)

$workflowDir = Join-Path $repoRoot ".github/workflows"
$privilegedHits = @()
Get-ChildItem -LiteralPath $workflowDir -Filter "*.yml" | ForEach-Object {
    $wfText = Get-Content -LiteralPath $_.FullName -Raw
    if ($wfText -match 'privileged:\s*true') {
        $privilegedHits += $_.Name
    }
}
if ($privilegedHits.Count -gt 0) {
    throw "Found privileged: true in workflow(s): $($privilegedHits -join ', ')."
}
[void](Write-Check -Label "no privileged: true in workflows" -Ok $true)

# Keep $ciWf referenced so StrictMode does not flag an unused variable.
if ([string]::IsNullOrWhiteSpace($ciWf)) {
    throw "ci.yml unexpectedly empty."
}
[void](Write-Check -Label "ci.yml present and non-empty" -Ok $true)

$summary = @"
## Sandbox boundary SelfCheck

SelfCheck passed: ``docs/ops/sandbox-boundary.md`` checklist anchors,
Containerfile ``USER``/``VOLUME``/loopback HEALTHCHECK, soft seccomp profile
(``packaging/oci/sl-daemon-seccomp.json``), ``no-new-privileges`` / ``cap-drop``,
soft no-net policy anchors, and blocking sandbox-boundary CI. Hard rootless / hard no-net runner sandbox remain unpaid.
Does not claim maintainer 2FA.
"@

if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

Write-Host "Sandbox boundary SelfCheck passed (C04 L40 process isolation + soft seccomp/no-net + blocking SelfCheck CI; hard rootless/no-net unpaid)."
exit 0

