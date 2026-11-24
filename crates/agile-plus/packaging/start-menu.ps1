# Creates a Phenotype-Apps Start Menu shortcut to the installed agileplus binary.
param(
    [Parameter(HelpMessage = "Path to agileplus.exe or agileplus binary")]
    [string]$BinaryPath = "$env:USERPROFILE\.cargo\bin\agileplus.exe",

    [Parameter(HelpMessage = "Path to the shortcut icon (.ico)")]
    [string]$IconPath = "$PSScriptRoot\agileplus.ico",

    [Parameter(HelpMessage = "Start Menu folder for Phenotype apps")]
    [string]$StartMenuFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Phenotype-Apps",

    [Parameter(HelpMessage = "Shortcut display name")]
    [string]$ShortcutName = "AgilePlus"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BinaryPath)) {
    throw "Binary not found: $BinaryPath"
}

New-Item -ItemType Directory -Force -Path $StartMenuFolder | Out-Null

$shortcutPath = Join-Path $StartMenuFolder "$ShortcutName.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $BinaryPath
$shortcut.WorkingDirectory = Split-Path -Parent $BinaryPath

if (Test-Path -LiteralPath $IconPath) {
    $shortcut.IconLocation = $IconPath
} else {
    Write-Warning "Icon not found at $IconPath — shortcut will use the binary default icon."
}

$shortcut.Description = "AgilePlus — spec-driven development CLI (Phenotype)"
$shortcut.Save()

Write-Host "Created Start Menu shortcut:"
Write-Host "  $shortcutPath"
Write-Host "Target: $BinaryPath"
if (Test-Path -LiteralPath $IconPath) {
    Write-Host "Icon:   $IconPath"
}
