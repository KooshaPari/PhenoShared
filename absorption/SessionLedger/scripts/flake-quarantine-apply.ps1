#Requires -Version 7.0
<#
.SYNOPSIS
Emit cargo test skip arguments for quarantined flakes.

.DESCRIPTION
Reads docs/ops/flakes-records.json and prints one `--skip <test_name>` pair per
quarantined entry whose `test` field ends with a Rust test function name.
Downstream CI steps can append the output to `cargo test` invocations.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$recordsPath = Join-Path $repoRoot 'docs/ops/flakes-records.json'
$recordsRaw = Get-Content -Raw -Path $recordsPath

if ($recordsRaw.Trim() -eq '[]') {
    return
}

$records = @($recordsRaw | ConvertFrom-Json)
if ($records.Count -eq 0) {
    return
}

foreach ($entry in $records) {
    if ($entry.status -ne 'quarantined') {
        continue
    }

    $test = [string]$entry.test
    if ($test -match '(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*$') {
        $skipName = $Matches[1]
        Write-Output '--skip'
        Write-Output $skipName
        Write-Warning "flake quarantine: skipping '$skipName' from $($entry.id)"
    } else {
        throw "quarantined flake '$($entry.id)' test field must end with a Rust test name: $test"
    }
}
