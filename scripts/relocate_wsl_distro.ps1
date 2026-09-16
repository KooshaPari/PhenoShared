<#
.SYNOPSIS
    Plan or explicitly relocate one WSL2 distro to D: or E:.

.DESCRIPTION
    Plan mode is read-only. Execute mode performs export, verifies the tar
    exists and has a SHA256, then requires -ConfirmUnregister before the
    destructive unregister/import step. It never touches other distros.
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$Distro = "Ubuntu-22.04",
    [string]$TargetRoot = "D:\WSL\Ubuntu-22.04",
    [switch]$Execute,
    [switch]$ConfirmUnregister
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$target = [System.IO.DirectoryInfo](Resolve-Path -LiteralPath $TargetRoot -ErrorAction SilentlyContinue)
if ($null -eq $target) {
    $targetPath = [System.IO.Path]::GetFullPath($TargetRoot)
} else {
    $targetPath = $target.FullName
}

$drive = [System.IO.Path]::GetPathRoot($targetPath).TrimEnd('\').ToUpperInvariant()
if ($drive -notin @("D:", "E:")) {
    throw "TargetRoot must be on D: or E:, got $targetPath"
}

$entries = @(Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss" -ErrorAction Stop |
    ForEach-Object { Get-ItemProperty $_.PSPath } |
    Where-Object { $_.DistributionName -eq $Distro })
if ($entries.Count -ne 1) {
    throw "Expected exactly one registered distro named '$Distro'; found $($entries.Count)"
}
$basePath = [string]$entries[0].BasePath
$vhdx = Join-Path $basePath "ext4.vhdx"
$vhdxExists = Test-Path -LiteralPath $vhdx
$vhdxBytes = if ($vhdxExists) { (Get-Item -LiteralPath $vhdx).Length } else { 0 }
$freeBytes = (Get-PSDrive -Name $drive.TrimEnd(':')).Free
$minimumFreeBytes = 50GB
$plan = [ordered]@{
    schema_version = "phenolm.wsl_relocation.v1"
    distro = $Distro
    source_base_path = $basePath
    source_vhdx = $vhdx
    source_vhdx_exists = $vhdxExists
    source_vhdx_bytes = $vhdxBytes
    target_root = $targetPath
    target_drive = $drive
    target_free_bytes = $freeBytes
    minimum_target_free_bytes = $minimumFreeBytes
    disk_admission = if ($freeBytes -ge $minimumFreeBytes) { "pass" } else { "reject_low_disk" }
    mode = if ($Execute) { "execute" } else { "plan" }
    destructive_step_requires_confirm_unregister = $true
    other_distros_touched = @()
    export_before_unregister = $true
}

$planPath = Join-Path $repoRoot "state\wsl_relocation_plan.json"
$plan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $planPath -Encoding UTF8
Write-Output ($plan | ConvertTo-Json -Depth 5)

if (-not $Execute) { exit 0 }
if (-not $vhdxExists) { throw "Source VHDX is missing: $vhdx" }
if ($freeBytes -lt $minimumFreeBytes) { throw "Target has less than 50 GB free" }
if (-not $ConfirmUnregister) { throw "Execute mode requires -ConfirmUnregister" }

$targetDir = [System.IO.DirectoryInfo]$targetPath
if ($targetDir.Exists -and $targetDir.EnumerateFileSystemInfos().Count -gt 0) {
    throw "TargetRoot must be empty before import: $targetPath"
}
$exportPath = Join-Path $targetPath "$Distro.export.tar"
if (-not $PSCmdlet.ShouldProcess("$Distro -> $targetPath", "export, unregister, and import this single distro")) {
    Write-Output "WhatIf: no export, unregister, or import performed"
    exit 0
}
$targetDir.Create()
wsl --terminate $Distro | Out-Null
wsl --export $Distro $exportPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exportPath)) {
    throw "WSL export failed"
}
$hash = (Get-FileHash -LiteralPath $exportPath -Algorithm SHA256).Hash
if ((Get-Item -LiteralPath $exportPath).Length -lt 1MB) { throw "Export is unexpectedly small" }
$plan.export_path = $exportPath
$plan.export_sha256 = $hash
$plan.export_bytes = (Get-Item -LiteralPath $exportPath).Length
$plan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $planPath -Encoding UTF8
wsl --unregister $Distro
if ($LASTEXITCODE -ne 0) { throw "WSL unregister failed after verified export" }
wsl --import $Distro $targetPath $exportPath --version 2
if ($LASTEXITCODE -ne 0) { throw "WSL import failed; verified export remains at $exportPath" }
$plan.completed = $true
$plan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $planPath -Encoding UTF8
Write-Output "Relocation completed. Export SHA256: $hash"
