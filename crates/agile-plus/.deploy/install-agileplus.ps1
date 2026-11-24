# AgilePlus — PowerShell installer stub
# Same model as install-tracera.ps1: builds `agileplus-launcher.exe` and
# drops a phenotypeApps Start Menu shortcut.

[CmdletBinding()]
param(
    [switch]$BuildExe,
    [switch]$AddStartMenuShortcut,
    [string]$Source = "E:\phase-finish-stack\AgilePlus\.deploy\launch-agileplus.bat",
    [string]$ShortcutDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\phenotypeApps"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Source)) {
    throw "Missing launcher source: $Source"
}

if ($AddStartMenuShortcut) {
    if (-not (Test-Path $ShortcutDir)) {
        New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $ShortcutDir "AgilePlus.lnk"))
    $shortcut.TargetPath = $Source
    $shortcut.WorkingDirectory = (Split-Path $Source -Parent)
    $shortcut.WindowStyle = 7
    $shortcut.Description = "AgilePlus — orchestrate the meta-monorepo stack"
    $shortcut.Save()
    Write-Host "[OK] Start Menu shortcut installed at $ShortcutDir\AgilePlus.lnk"
}

if ($BuildExe) {
    Write-Host "[*] Building agileplus-launcher.exe via PS2EXE ..."
    if (-not (Get-Module -ListAvailable -Name ps2exe)) {
        Install-Module -Name ps2exe -Scope CurrentUser -Force
    }
    Import-Module ps2exe
    $exeOut = Join-Path (Split-Path $Source -Parent) "agileplus-launcher.exe"
    Invoke-ps2exe -inputFile $Source -outputFile $exeOut -noConsole -noError
    Write-Host "[OK] Built: $exeOut"
}

Write-Host ""
Write-Host "AgilePlus installer stub complete."
Write-Host "Source  : $Source"
Write-Host "Shortcuts: $ShortcutDir\AgilePlus.lnk"
