param(
    [string]$CliPath = "E:\agileplus-target\release\agileplus-cli.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$databasePath = Join-Path $repoRoot "agileplus.db"

if (-not (Test-Path -LiteralPath $CliPath -PathType Leaf)) {
    throw "AgilePlus CLI not found at '$CliPath'. Pass -CliPath to override it."
}

& $CliPath seed-requirements --db $databasePath
if ($LASTEXITCODE -ne 0) {
    throw "AgilePlus requirement seeding failed with exit code $LASTEXITCODE."
}

Write-Host "AgilePlus bootstrap database is available at $databasePath"
