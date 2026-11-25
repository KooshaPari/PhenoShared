[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\SessionLedger")
)

$ErrorActionPreference = "Stop"
$SourceDir = $PSScriptRoot
$Binary = Join-Path $SourceDir "sl-viewer.exe"

if (-not (Test-Path -LiteralPath $Binary -PathType Leaf)) {
    throw "sl-viewer.exe must be next to Install.ps1."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -LiteralPath $Binary -Destination $InstallDir -Force
Copy-Item -LiteralPath (Join-Path $SourceDir "Uninstall.ps1") -Destination $InstallDir -Force

foreach ($license in @("LICENSE-MIT", "LICENSE-APACHE")) {
    $source = Join-Path $SourceDir $license
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Copy-Item -LiteralPath $source -Destination $InstallDir -Force
    }
}

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenuDir "SessionLedger.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $InstallDir "sl-viewer.exe"
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Description = "SessionLedger Viewer"
$shortcut.Save()

$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SessionLedger"
New-Item -Path $uninstallKey -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name DisplayName -Value "SessionLedger Viewer" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name Publisher -Value "SessionLedger" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $InstallDir -PropertyType String -Force | Out-Null
$uninstallCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\Uninstall.ps1`""
New-ItemProperty -Path $uninstallKey -Name UninstallString -Value $uninstallCommand -PropertyType String -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null

Write-Output "SessionLedger installed to $InstallDir"
Write-Output "Start Menu shortcut created: $shortcutPath"
