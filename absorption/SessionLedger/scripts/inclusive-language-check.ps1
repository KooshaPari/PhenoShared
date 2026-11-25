[CmdletBinding()]
param(
    [string[]]$Paths = @("docs", "CONTRIBUTING.md"),
    [string[]]$CopyFiles = @(
        "crates/sl-viewer/src/help_overlay.rs",
        "crates/sl-viewer/src/async_states.rs"
    )
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

$terms = @(
    @{ Pattern = "\bblacklist(?:ed|ing)?\b"; Suggestion = "denylist or blocklist" },
    @{ Pattern = "\bwhitelist(?:ed|ing)?\b"; Suggestion = "allowlist" },
    @{ Pattern = "\bmaster\b"; Suggestion = "main, primary, or source" },
    @{ Pattern = "\bslave\b"; Suggestion = "replica, secondary, or worker" }
)

$files = New-Object System.Collections.Generic.List[string]
foreach ($path in $Paths) {
    $fullPath = Join-Path $repoRoot $path
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Inclusive language check path not found: $path"
    }

    if (Test-Path -LiteralPath $fullPath -PathType Container) {
        Get-ChildItem -LiteralPath $fullPath -Recurse -File -Filter "*.md" |
            ForEach-Object { $files.Add($_.FullName) }
    }
    elseif ($fullPath -like "*.md") {
        $files.Add((Resolve-Path -LiteralPath $fullPath).Path)
    }
}

foreach ($relative in $CopyFiles) {
    $fullPath = Join-Path $repoRoot $relative
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Inclusive language copy file not found: $relative"
    }
    $files.Add((Resolve-Path -LiteralPath $fullPath).Path)
}

$findings = New-Object System.Collections.Generic.List[string]
foreach ($file in $files) {
    foreach ($term in $terms) {
        $matches = Select-String -LiteralPath $file -Pattern $term.Pattern -AllMatches
        foreach ($match in $matches) {
            $relativePath = [IO.Path]::GetRelativePath($repoRoot, $match.Path)
            $findings.Add("$($relativePath):$($match.LineNumber): $($term.Suggestion) -> $($match.Line.Trim())")
        }
    }
}

if ($findings.Count -gt 0) {
    Write-Host "Inclusive language seed check found $($findings.Count) issue(s):"
    $findings | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "Inclusive language seed check passed for docs/, CONTRIBUTING.md, and viewer user-copy sources."
