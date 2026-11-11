[CmdletBinding()]
param(
    [string]$Workflow = ".github/workflows/release.yml",
    [string[]]$RequiredOs = @("ubuntu-latest", "macos-latest", "windows-latest")
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

if ([System.IO.Path]::IsPathRooted($Workflow)) {
    $WorkflowPath = $Workflow
} else {
    $WorkflowPath = Join-Path $RepoRoot $Workflow
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) {
    throw "Release workflow not found: $WorkflowPath"
}

$Lines = Get-Content -LiteralPath $WorkflowPath
$InBuildJob = $false
$ObservedOs = [System.Collections.Generic.List[string]]::new()

foreach ($Line in $Lines) {
    if (-not $InBuildJob) {
        if ($Line -match '^  build:\s*$') {
            $InBuildJob = $true
        }
        continue
    }

    if ($Line -match '^  [A-Za-z0-9_-]+:\s*$') {
        break
    }

    if ($Line -match '^\s+os:\s*["'']?([^"''#\s]+)') {
        $ObservedOs.Add($Matches[1])
    }
}

$UniqueOs = $ObservedOs | Sort-Object -Unique
$Missing = @($RequiredOs | Where-Object { $UniqueOs -notcontains $_ })

if ($Missing.Count -gt 0) {
    Write-Error ("release.yml build matrix is missing required OS entries: {0}. Found: {1}" -f ($Missing -join ", "), ($UniqueOs -join ", "))
    exit 1
}

Write-Host ("release.yml build matrix includes: {0}" -f ($UniqueOs -join ", "))
