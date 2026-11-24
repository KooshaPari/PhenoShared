param(
    [string]$CliPath = "E:\agileplus-target\release\agileplus-cli.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$databasePath = Join-Path $repoRoot "agileplus.db"

if (-not (Test-Path -LiteralPath $CliPath -PathType Leaf)) {
    throw "AgilePlus CLI not found at '$CliPath'. Pass -CliPath to override it."
}

Push-Location $repoRoot
try {
    if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
        Write-Host "Creating AgilePlus bootstrap database at $databasePath"
        & $CliPath seed-requirements --db $databasePath
        if ($LASTEXITCODE -ne 0) {
            throw "AgilePlus requirement seeding failed with exit code $LASTEXITCODE."
        }
    }

    Write-Host "`nProjects"
    & $CliPath list-projects
    if ($LASTEXITCODE -ne 0) { throw "list-projects failed with exit code $LASTEXITCODE." }

    Write-Host "`nEpics"
    & $CliPath list-epics
    if ($LASTEXITCODE -ne 0) { throw "list-epics failed with exit code $LASTEXITCODE." }

    Write-Host "`nStories"
    & $CliPath list-stories
    if ($LASTEXITCODE -ne 0) { throw "list-stories failed with exit code $LASTEXITCODE." }

    $syncValues = @(
        $env:GITHUB_TOKEN,
        $env:AGILEPLUS_PROJECT_ID,
        $env:AGILEPLUS_EPIC_ID
    )
    $configuredValues = @($syncValues | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

    if ($configuredValues.Count -ne $syncValues.Count) {
        Write-Host "`nSync skipped. Set GITHUB_TOKEN, AGILEPLUS_PROJECT_ID, and AGILEPLUS_EPIC_ID to enable it."
    }
    else {
        Write-Host "`nSyncing KooshaPari/SessionLedger"
        & $CliPath sync "KooshaPari/SessionLedger" `
            --project $env:AGILEPLUS_PROJECT_ID `
            --epic $env:AGILEPLUS_EPIC_ID `
            --token $env:GITHUB_TOKEN
        if ($LASTEXITCODE -ne 0) {
            throw "AgilePlus sync failed with exit code $LASTEXITCODE."
        }
    }
}
finally {
    Pop-Location
}
