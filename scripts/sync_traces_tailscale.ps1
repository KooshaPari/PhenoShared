#Requires -Version 5.1
<#
.SYNOPSIS
  Sync trace logs from MacBook (Tailscale) into unified ingest path.

.DESCRIPTION
  Pulls ~/.omniroute/training and agent transcripts from a Tailscale peer.
  Set $env:PHENO_MAC_HOST to the Mac's Tailscale hostname or IP.

.EXAMPLE
  $env:PHENO_MAC_HOST = "macbook.tail1234.ts.net"
  .\scripts\sync_traces_tailscale.ps1
#>
param(
    [string]$MacHost = $env:PHENO_MAC_HOST,
    [string]$RemoteUser = $env:PHENO_MAC_USER,
    [string]$LocalTraining = "$env:USERPROFILE\.omniroute\training\mac_sync"
)

if (-not $MacHost) {
    Write-Warning "Set PHENO_MAC_HOST (Tailscale hostname) to enable Mac trace sync."
    exit 0
}
if (-not $RemoteUser) { $RemoteUser = $env:USERNAME }

New-Item -ItemType Directory -Force -Path $LocalTraining | Out-Null
$remote = "${RemoteUser}@${MacHost}:.omniroute/training/"
Write-Host "Syncing $remote -> $LocalTraining"
scp -r $remote $LocalTraining
Write-Host "Run: python scripts/collect_traces.py"
