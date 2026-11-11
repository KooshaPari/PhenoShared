#Requires -Version 7.0
<#
.SYNOPSIS
  CI-safe smoke for L30.10 feedback-loop budget docs (and optional advisory timing).

.DESCRIPTION
  Default mode verifies docs/ops/feedback-budgets.md exists and contains the
  expected command anchors. With -Measure, runs short warm timings and writes a
  JSON artifact. Timing overruns are advisory only (warning + exit 0) unless
  -Enforce is passed with documented generous thresholds.
#>
[CmdletBinding()]
param(
    [switch]$Measure,

    [string]$ArtifactPath,

    [switch]$Enforce,

    [ValidateRange(1, 3600)]
    [double]$CheckBudgetSeconds = 15,

    [ValidateRange(1, 3600)]
    [double]$TestBudgetSeconds = 30,

    [ValidateRange(1, 7200)]
    [double]$LintBudgetSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot 'docs/ops/feedback-budgets.md'
$daemonManifest = Join-Path $repoRoot 'crates/sl-daemon/Cargo.toml'
$nextestRoot = Join-Path $repoRoot '.config/nextest.toml'
$nextestDaemon = Join-Path $repoRoot 'crates/sl-daemon/.config/nextest.toml'

function Assert-File {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

Assert-File -Path $docPath -Label 'feedback budgets doc'
Assert-File -Path $PSCommandPath -Label 'feedback budget check script'
Assert-File -Path $nextestRoot -Label 'root nextest config'
Assert-File -Path $nextestDaemon -Label 'daemon nextest config'

$doc = Get-Content -LiteralPath $docPath -Raw
foreach ($needle in @(
        'cargo check --manifest-path crates/sl-daemon/Cargo.toml',
        'cargo test --manifest-path crates/sl-daemon/Cargo.toml',
        'make lint',
        'method',
        'hyperfine',
        'advisory'
    )) {
    if ($doc -notmatch [regex]::Escape($needle)) {
        throw "docs/ops/feedback-budgets.md missing required anchor: '$needle'"
    }
}

Write-Host "feedback-budget-check: doc and nextest configs OK"

if (-not $Measure) {
    if ($env:GITHUB_STEP_SUMMARY) {
        @"
## Feedback-loop budgets

Smoke passed: ``docs/ops/feedback-budgets.md`` and ``.config/nextest.toml`` present.
Wall-clock budgets remain advisory (see doc).
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
    }
    exit 0
}

Assert-File -Path $daemonManifest -Label 'sl-daemon Cargo.toml'

if (-not $ArtifactPath) {
    $ArtifactPath = Join-Path $repoRoot 'artifacts/feedback-budget.json'
}
$ArtifactPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ArtifactPath)
$artifactDir = Split-Path -Parent $ArtifactPath
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

function Invoke-Timed {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Script
    )
    Write-Host "Measuring $Name ..."
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Script
    $code = $LASTEXITCODE
    $sw.Stop()
    if ($null -eq $code) { $code = 0 }
    [pscustomobject]@{
        name           = $Name
        seconds        = [Math]::Round($sw.Elapsed.TotalSeconds, 3)
        exit_code      = [int]$code
        budget_seconds = $null
    }
}

Push-Location $repoRoot
try {
    # Warm once so -Measure reflects incremental loop cost.
    & cargo check --manifest-path $daemonManifest | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "warm cargo check failed with exit $LASTEXITCODE"
    }

    $rows = @(
        (Invoke-Timed -Name 'cargo_check_sl_daemon' -Script {
            & cargo check --manifest-path $daemonManifest | Out-Null
        }),
        (Invoke-Timed -Name 'cargo_test_sl_daemon' -Script {
            & cargo test --manifest-path $daemonManifest --quiet | Out-Null
        })
    )

    # lint is expensive; time fmt+daemon clippy as a proxy when full make is unavailable,
    # but prefer `make lint` when make exists.
    $makeCmd = Get-Command make -ErrorAction SilentlyContinue
    if ($makeCmd) {
        $lintRow = Invoke-Timed -Name 'make_lint' -Script {
            & make lint | Out-Null
        }
    }
    else {
        $lintRow = Invoke-Timed -Name 'fmt_check_plus_daemon_clippy' -Script {
            & cargo fmt --all --check | Out-Null
            & cargo fmt --manifest-path $daemonManifest --check | Out-Null
            & cargo clippy --manifest-path $daemonManifest --all-targets --quiet | Out-Null
        }
    }
    $rows += $lintRow
}
finally {
    Pop-Location
}

$budgetMap = @{
    cargo_check_sl_daemon           = $CheckBudgetSeconds
    cargo_test_sl_daemon            = $TestBudgetSeconds
    make_lint                       = $LintBudgetSeconds
    fmt_check_plus_daemon_clippy    = $LintBudgetSeconds
}

$warnings = [System.Collections.Generic.List[string]]::new()
foreach ($row in $rows) {
    $row.budget_seconds = $budgetMap[$row.name]
    if ($row.exit_code -ne 0) {
        throw "$($row.name) failed with exit $($row.exit_code) after $($row.seconds)s"
    }
    if ($row.seconds -gt $row.budget_seconds) {
        $msg = "{0}: {1}s exceeds advisory budget {2}s" -f $row.name, $row.seconds, $row.budget_seconds
        $warnings.Add($msg)
        Write-Warning $msg
    }
    else {
        Write-Host ("{0}: {1}s (budget {2}s)" -f $row.name, $row.seconds, $row.budget_seconds)
    }
}

$payload = [ordered]@{
    schema_version = 1
    measured_at_utc = [DateTime]::UtcNow.ToString('o')
    method          = 'cargo/Measure-Command'
    host            = [System.Environment]::OSVersion.VersionString
    cargo_version   = ((& cargo --version) -join ' ').Trim()
    rustc_wrapper   = if ($env:RUSTC_WRAPPER) { $env:RUSTC_WRAPPER } else { $null }
    policy          = [ordered]@{
        advisory              = $true
        enforce               = [bool]$Enforce
        check_budget_seconds  = $CheckBudgetSeconds
        test_budget_seconds   = $TestBudgetSeconds
        lint_budget_seconds   = $LintBudgetSeconds
    }
    measurements    = $rows
    warnings        = @($warnings)
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ArtifactPath -Encoding utf8
Write-Host "Wrote advisory timing artifact: $ArtifactPath"

if ($Enforce -and $warnings.Count -gt 0) {
    Write-Error "Enforce mode: $($warnings.Count) advisory budget overrun(s)."
    exit 1
}

if ($env:GITHUB_STEP_SUMMARY) {
    $lines = @(
        '## Feedback-loop budgets (measured)',
        '',
        '| Command | Seconds | Budget |',
        '|---------|--------:|-------:|'
    )
    foreach ($row in $rows) {
        $lines += ("| `{0}` | {1} | {2} |" -f $row.name, $row.seconds, $row.budget_seconds)
    }
    $lines += ''
    $lines += 'Policy: advisory (CI default does not enforce wall-clock).'
    $lines -join "`n" | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

exit 0
