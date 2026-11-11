[CmdletBinding()]
param(
    [string]$DataDir = $(if ($env:SL_DATA_DIR) { $env:SL_DATA_DIR } else { ".sl-data" }),
    [string]$Fixture = "docs/reference/conformance/fixtures/minimal-session-042.okf.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

if ([System.IO.Path]::IsPathRooted($Fixture)) {
    $FixturePath = $Fixture
} else {
    $FixturePath = Join-Path $RepoRoot $Fixture
}

if ([System.IO.Path]::IsPathRooted($DataDir)) {
    $DataPath = $DataDir
} else {
    $DataPath = Join-Path $RepoRoot $DataDir
}

if (-not (Test-Path -LiteralPath $FixturePath -PathType Leaf)) {
    throw "Sample fixture not found: $FixturePath"
}

Get-Content -LiteralPath $FixturePath -Raw | ConvertFrom-Json | Out-Null
New-Item -ItemType Directory -Force -Path $DataPath | Out-Null

$Destination = Join-Path $DataPath (Split-Path -Leaf $FixturePath)
Copy-Item -LiteralPath $FixturePath -Destination $Destination -Force

Write-Host "Seeded SessionLedger sample fixture:"
Write-Host "  $Destination"
