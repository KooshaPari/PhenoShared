#Requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$schemaPath = Join-Path $repoRoot 'docs/ops/flakes.json'
$recordsPath = Join-Path $repoRoot 'docs/ops/flakes-records.json'

if (-not (Test-Path $schemaPath)) {
    throw "flake schema missing: $schemaPath"
}
if (-not (Test-Path $recordsPath)) {
    throw "flake records missing: $recordsPath"
}

$schema = Get-Content -Raw -Path $schemaPath | ConvertFrom-Json
$recordsRaw = Get-Content -Raw -Path $recordsPath
if ($recordsRaw.Trim() -eq '[]') {
    $records = @()
} else {
    $records = $recordsRaw | ConvertFrom-Json
}

if ($null -eq $records) {
    $records = @()
}

if ($records -is [string]) {
    throw 'flakes-records.json must be a JSON array'
}

$today = [DateTime]::UtcNow.Date
$open = 0
$quarantined = 0
$resolved = 0

foreach ($entry in $records) {
    foreach ($required in $schema.items.required) {
        if (-not ($entry.PSObject.Properties.Name -contains $required)) {
            throw "flake record '$($entry.id)' missing required field '$required'"
        }
    }

    switch ($entry.status) {
        'open' { $open++ }
        'quarantined' {
            $quarantined++
            if ($null -eq $entry.quarantine) {
                throw "quarantined flake '$($entry.id)' must include quarantine metadata"
            }
            $deadline = [DateTime]::Parse($entry.deadline)
            if ($deadline -lt $today) {
                throw "quarantined flake '$($entry.id)' passed deadline $($entry.deadline)"
            }
        }
        'resolved' { $resolved++ }
        default { throw "flake '$($entry.id)' has invalid status '$($entry.status)'" }
    }
}

Write-Host "flake tracker: open=$open quarantined=$quarantined resolved=$resolved total=$($records.Count)"

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Flake tracker

| Status | Count |
|--------|------:|
| open | $open |
| quarantined | $quarantined |
| resolved | $resolved |
| total | $($records.Count) |
"@ | Out-File -FilePath $env:GITHUB_STEP_SUMMARY -Append -Encoding utf8
}
