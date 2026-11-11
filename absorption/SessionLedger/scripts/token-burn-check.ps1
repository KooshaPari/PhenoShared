#Requires -Version 7.0
<#
.SYNOPSIS
  Per-eval/fixture token-burn ledger smoke (not Harbor).

.DESCRIPTION
  Validates docs/ops/token-burn.json against compression/token OKF fixtures:
  intent token_estimate fields must sum to gate total_token_estimate. Also checks
  that the ops metrics surface docs still expose total_tokens / avg_tokens and
  that Harbor per-eval ledgers remain N/A.

  Use -SelfCheck for hermetic CI (no cargo). With -RunEval, also runs the
  compression_eval integration test.
#>
[CmdletBinding()]
param(
    [string]$LedgerConfig = "",

    [switch]$SelfCheck,

    [switch]$RunEval
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot 'docs/ops/token-burn.md'
$evalCompressionDoc = Join-Path $repoRoot 'docs/ops/eval-compression.md'

if ([string]::IsNullOrWhiteSpace($LedgerConfig)) {
    $LedgerConfig = Join-Path $repoRoot 'docs/ops/token-burn.json'
}

function Assert-File {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

function Get-OkfTokenLedger {
    param([Parameter(Mandatory = $true)][string]$FixturePath)

    $raw = Get-Content -LiteralPath $FixturePath -Raw
    $okf = $raw | ConvertFrom-Json
    if ($null -eq $okf.entities) {
        throw "Fixture '$FixturePath' is missing entities."
    }

    $intentEstimates = [System.Collections.Generic.List[int]]::new()
    $gateTotal = $null

    foreach ($entity in @($okf.entities)) {
        $type = [string]$entity.type
        if ($type -eq 'intent') {
            $props = $entity.properties
            if ($null -ne $props -and $null -ne $props.token_estimate) {
                $intentEstimates.Add([int]$props.token_estimate)
            }
        }
        elseif ($type -eq 'gate') {
            $props = $entity.properties
            if ($null -ne $props -and $null -ne $props.total_token_estimate) {
                $gateTotal = [int]$props.total_token_estimate
            }
        }
    }

    $intentSum = 0
    foreach ($value in $intentEstimates) {
        $intentSum += $value
    }

    return [pscustomobject]@{
        IntentEstimates = @($intentEstimates)
        IntentSum       = $intentSum
        GateTotal       = $gateTotal
    }
}

Assert-File -Path $LedgerConfig -Label 'token-burn ledger config'
Assert-File -Path $docPath -Label 'token-burn doc'
Assert-File -Path $evalCompressionDoc -Label 'eval-compression doc'
Assert-File -Path $PSCommandPath -Label 'token-burn check script'

$config = Get-Content -LiteralPath $LedgerConfig -Raw | ConvertFrom-Json
if ($null -eq $config.schema -or [string]$config.schema -ne 'sessionledger.token-burn.v1') {
    throw "Ledger config must declare schema sessionledger.token-burn.v1."
}
if ([string]$config.harbor_per_eval_ledger -ne 'N/A') {
    throw "harbor_per_eval_ledger must remain N/A (got '$($config.harbor_per_eval_ledger)')."
}

$ledgerRows = [System.Collections.Generic.List[object]]::new()
foreach ($entry in @($config.fixtures)) {
    $rel = [string]$entry.path
    $fixturePath = Join-Path $repoRoot $rel
    Assert-File -Path $fixturePath -Label "fixture '$rel'"

    $ledgerKind = if ($entry.PSObject.Properties.Name -contains 'ledger') {
        [string]$entry.ledger
    }
    else {
        'intent_gate'
    }
    if ($ledgerKind -eq 'compression_only') {
        $ledgerRows.Add([pscustomobject]@{
                path    = $rel
                ledger  = 'compression_only'
                status  = 'ok'
            })
        continue
    }

    $parsed = Get-OkfTokenLedger -FixturePath $fixturePath
    if ($null -eq $parsed.GateTotal) {
        throw "Fixture '$rel' is missing gate.properties.total_token_estimate."
    }
    if ($parsed.IntentEstimates.Count -eq 0) {
        throw "Fixture '$rel' is missing intent.properties.token_estimate fields."
    }

    $expectedTotal = [int]$entry.expected_total_token_estimate
    $expectedIntents = @($entry.intent_token_estimates | ForEach-Object { [int]$_ })
    $expectedSum = 0
    foreach ($value in $expectedIntents) {
        $expectedSum += $value
    }

    if ($expectedTotal -ne $expectedSum) {
        throw "Config ledger mismatch for '$rel': expected_total_token_estimate=$expectedTotal but intent_token_estimates sum to $expectedSum."
    }
    if ($parsed.IntentSum -ne $expectedSum) {
        throw "Fixture '$rel' intent token_estimate sum is $($parsed.IntentSum); config expects $expectedSum."
    }
    if ($parsed.GateTotal -ne $expectedTotal) {
        throw "Fixture '$rel' gate total_token_estimate is $($parsed.GateTotal); config expects $expectedTotal."
    }
    $obsKey = [string]::Join(
        ',',
        @(
            $parsed.IntentEstimates |
                ForEach-Object { [int]$_ } |
                Sort-Object
        )
    )
    $expKey = [string]::Join(
        ',',
        @(
            $expectedIntents |
                ForEach-Object { [int]$_ } |
                Sort-Object
        )
    )
    if ($obsKey -cne $expKey) {
        throw "Fixture '$rel' intent token_estimate list [$obsKey] does not match config [$expKey]."
    }

    $ledgerRows.Add([pscustomobject]@{
            path                 = $rel
            ledger               = 'intent_gate'
            intent_sum           = $parsed.IntentSum
            gate_total           = $parsed.GateTotal
            intent_token_estimates = @($parsed.IntentEstimates)
            status               = 'ok'
        })
}

foreach ($watch in @($config.metrics_surface.watch_files)) {
    $watchPath = Join-Path $repoRoot ([string]$watch)
    Assert-File -Path $watchPath -Label "metrics surface watch file '$watch'"
}

$doc = Get-Content -LiteralPath $docPath -Raw
foreach ($needle in @($config.metrics_surface.doc_anchors | ForEach-Object { [string]$_ })) {
    if ($doc -notmatch [regex]::Escape($needle)) {
        throw "docs/ops/token-burn.md missing required anchor: '$needle'"
    }
}

$evalDoc = Get-Content -LiteralPath $evalCompressionDoc -Raw
foreach ($needle in @(
        'token-burn-check.ps1',
        'token-burn.md',
        'rough_tokens_saved'
    )) {
    if ($evalDoc -notmatch [regex]::Escape($needle)) {
        throw "docs/ops/eval-compression.md missing required anchor: '$needle'"
    }
}

Write-Host "token-burn-check: $($ledgerRows.Count) fixture ledger row(s) OK; Harbor ledger remains N/A."
foreach ($row in $ledgerRows) {
    if ($row.ledger -eq 'compression_only') {
        Write-Host ("  {0}: compression_only" -f $row.path)
    }
    else {
        Write-Host ("  {0}: intent_sum={1} gate_total={2}" -f $row.path, $row.intent_sum, $row.gate_total)
    }
}

if ($env:GITHUB_STEP_SUMMARY) {
    $lines = @(
        '## Token-burn ledger smoke',
        '',
        'Harbor per-eval ledger: **N/A** (ops/fixture ledgers only).',
        '',
        '| Fixture | Ledger | Intent sum | Gate total |',
        '|---------|--------|----------:|----------:|'
    )
    foreach ($row in $ledgerRows) {
        if ($row.ledger -eq 'compression_only') {
            $lines += ("| `{0}` | compression_only | — | — |" -f $row.path)
        }
        else {
            $lines += ("| `{0}` | intent_gate | {1} | {2} |" -f $row.path, $row.intent_sum, $row.gate_total)
        }
    }
    $lines -join "`n" | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}

if ($SelfCheck -and -not $RunEval) {
    exit 0
}

if ($RunEval -or (-not $SelfCheck)) {
    $cmd = [string]$config.compression_eval_command
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        throw 'compression_eval_command missing from token-burn.json.'
    }
    Write-Host "Running compression eval: $cmd"
    Push-Location $repoRoot
    try {
        Invoke-Expression $cmd
        if ($LASTEXITCODE -ne 0) {
            throw "compression eval failed with exit $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

exit 0
