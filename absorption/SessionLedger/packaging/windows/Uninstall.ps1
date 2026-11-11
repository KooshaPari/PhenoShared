[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\SessionLedger")
)

$ErrorActionPreference = "Stop"
$shortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\SessionLedger.lnk"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SessionLedger"

Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue
Remove-Item -Path $uninstallKey -Recurse -Force -ErrorAction SilentlyContinue

# Run deletion in a detached process so this script can remove its own folder.
$escapedInstallDir = $InstallDir.Replace("'", "''")
$cleanup = "Start-Sleep -Seconds 1; Remove-Item -LiteralPath '$escapedInstallDir' -Recurse -Force"
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $cleanup
)

Write-Output "SessionLedger uninstalled from $InstallDir"
Write-Output "User data was not removed."
