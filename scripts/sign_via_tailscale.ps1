# sign_via_tailscale.ps1 — Windows PowerShell wrapper for sign_via_tailscale.sh
#
# Run the macOS signing scripts (cosign keyless, GHCR push, Apple codesign)
# remotely on your MacBook, secured by Tailscale mesh + OpenSSH.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\sign_via_tailscale.ps1
#   powershell ... -Mac "macos@100.x.y.z" -Tag v0.38
#   powershell ... -Steps "sign"            # only sign tarball
#   powershell ... -Steps "publish"         # only docker push
#   powershell ... -Steps "kernel"          # only sign macOS kernel
#
# Requires:
#   - OpenSSH client (built into Windows 10+)
#   - Tailscale on both Windows + MacBook (https://tailscale.com/download)
#   - macOS with 'Remote Login' enabled (System Settings -> General -> Sharing)
#
# Or just run the .sh equivalent directly in WSL / Git Bash:
#   bash scripts/sign_via_tailscale.sh

[CmdletBinding()]
param(
    [string]$Mac = "",
    [string]$Tag = "v0.37",
    [ValidateSet("sign","publish","kernel")]
    [string[]]$Steps = @("sign","publish","kernel"),
    [string]$ExtraArgs = ""
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Msg)
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Msg" -ForegroundColor Blue
}

function Write-Err {
    param([string]$Msg)
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Msg" -ForegroundColor Red
}

# --- Discover MacBook host ---
if (-not $Mac) {
    Write-Log "Auto-discovering MacBook via Tailscale..."

    # Try `tailscale status --json` first
    $ts = Get-Command tailscale -ErrorAction SilentlyContinue
    if ($ts) {
        try {
            $json = & tailscale status --json 2>$null | ConvertFrom-Json
            $peer = $json.Peer.PSObject.Properties.Value | Where-Object {
                $_.TailscaleIPs -and ($_.TailscaleIPs[0] -like "100.*") -and $_.Online
            } | Select-Object -First 1
            if ($peer) {
                $user = $env:USERNAME
                if (-not $user) { $user = "macos" }
                $Mac = "$user@$($peer.TailscaleIPs[0])"
                Write-Log "  found: $Mac"
            }
        } catch {
            # fall through
        }
    }

    # Try ~/.ssh/config
    if (-not $Mac -and (Test-Path "$HOME\.ssh\config")) {
        $sshHost = Select-String -Path "$HOME\.ssh\config" -Pattern "^Host\s+.*tailscale" -CaseSensitive:$false |
            Select-Object -First 1
        if ($sshHost) {
            $hostName = ($sshHost -split "\s+")[1]
            $Mac = $hostName
            Write-Log "  from SSH config: $Mac"
        }
    }

    if (-not $Mac) {
        Write-Err "Could not auto-discover MacBook. Pass -Mac macos@100.x.y.z"
        Write-Err "On the MacBook run 'tailscale ip -4' to find the IP."
        exit 1
    }
}

# --- Build SSH options ---
$sshOpts = @(
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-o", "ConnectTimeout=15",
    "-o", "StrictHostKeyChecking=accept-new"
)

# --- Probe reachability ---
Write-Log "Probing $Mac ..."
$probe = & ssh @sshOpts $Mac "uname -s" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Cannot reach $Mac. Check Tailscale + Remote Login on MacBook."
    exit 1
}
Write-Log "  reachable ($probe)"

# --- Sync repo ---
$remoteDir = "~/work/pheno-harness-remote"
Write-Log "Syncing repo to ${Mac}:${remoteDir}"
& ssh @sshOpts $Mac "bash -s" @"
set -e
mkdir -p ~/work
if [[ ! -d $remoteDir/.git ]]; then
    git clone https://github.com/<REDACTED>/pheno-harness.git $remoteDir
fi
cd $remoteDir
git fetch --tags origin
git checkout $Tag 2>/dev/null || git checkout main
git pull --rebase origin main 2>/dev/null || true
echo 'On commit:' `$(git rev-parse --short HEAD)
"@

# --- Run steps ---
foreach ($step in $Steps) {
    Write-Host ""
    Write-Host "=== STEP: $step ===" -ForegroundColor Cyan
    switch ($step) {
        "kernel" {
            & ssh @sshOpts -t $Mac "cd $remoteDir && bash scripts/sign_macos.sh $ExtraArgs"
        }
        "sign" {
            & ssh @sshOpts -t $Mac "cd $remoteDir && TAG=$Tag bash scripts/sign_release.sh $Tag $ExtraArgs"
        }
        "publish" {
            & ssh @sshOpts -t $Mac "cd $remoteDir && TAG=$Tag bash scripts/publish_docker.sh"
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Step '$step' failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Log "All steps complete."
Write-Log "View release: https://github.com/<REDACTED>/pheno-harness/releases/tag/${Tag}-pheno-harness-summit"
Write-Log "View package: https://github.com/<REDACTED>/pheno-harness/pkgs/container/pheno-harness"
