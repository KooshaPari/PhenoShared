<#
.SYNOPSIS
  Install a GitHub Actions self-hosted runner on Windows 11 (AMD64) as a
  dedicated service, registered at the KooshaPari organization scope.

.DESCRIPTION
  Provisions a `gh-runner` local user, downloads the latest actions/runner
  release from github.com, and installs it as a Windows service running
  under the dedicated service account. Registers the runner at the
  organization scope (https://github.com/KooshaPari) with labels
  "self-hosted,Windows,X64,desktop-kooshapari-desk" so workflows can
  target this GPU/desktop box directly.

  Forgejo deployment is blocked on OCI capacity; this runner stands in
  for that mesh node until Forgejo lands. Infrastructure (dedicated user,
  sc.exe crash-recovery ladder, Parsec-aware pause task, Tailscale
  prereq check) is identical to the Forgejo variant — only the
  registration target changes.

  A "gaming-mode" scheduled task pauses the service whenever a sentinel
  file exists (%USERPROFILE%\.phenotype\runner-paused) or when Parsec
  (parsecd.exe) is running, so the runner never steals cycles from a
  remote-desktop / game-streaming session.

.PARAMETER RegToken
  GitHub Actions registration token. If omitted, the script will try to
  fetch one via `gh api -X POST orgs/KooshaPari/actions/runners/registration-token`.
  The invoking user must have `gh` CLI authenticated with an org-admin
  scope (`admin:org`) for that fetch to succeed.

.PARAMETER InstallDir
  Install root. Default: C:\actions-runner

.PARAMETER OrgUrl
  Organization URL to register against. Default: https://github.com/KooshaPari

.PARAMETER Labels
  Runner labels. Default: self-hosted,Windows,X64,desktop-kooshapari-desk

.PARAMETER RunnerName
  Runner name shown in GitHub. Default: desktop-kooshapari-desk

.NOTES
  Run in an ELEVATED PowerShell session on kooshapari-desk.tail2b570.ts.net.
  Requires: Tailscale installed + connected, Windows 11 AMD64, admin rights,
  and either `gh auth login` with org-admin scope OR a pre-fetched -RegToken.

.EXAMPLE
  # Option A — let the script fetch the token via gh
  PS> Set-ExecutionPolicy -Scope Process Bypass -Force
  PS> .\install-windows-runner.ps1

.EXAMPLE
  # Option B — paste a pre-fetched token
  PS> $t = gh api -X POST orgs/KooshaPari/actions/runners/registration-token --jq .token
  PS> .\install-windows-runner.ps1 -RegToken $t
#>

[CmdletBinding()]
param(
  [string]$RegToken    = $null,
  [string]$InstallDir  = 'C:\actions-runner',
  [string]$OrgUrl      = 'https://github.com/KooshaPari',
  [string]$Labels      = 'self-hosted,Windows,X64,desktop-kooshapari-desk',
  [string]$RunnerName  = 'desktop-kooshapari-desk',
  [string]$RunnerUser  = 'gh-runner',
  [string]$ServiceName = 'GitHubActionsRunner'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step { param($msg) Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "  ok  $msg" -ForegroundColor Green }
function Write-Warn2{ param($msg) Write-Host "  !!  $msg" -ForegroundColor Yellow }
function Fail       { param($msg) Write-Host "  xx  $msg" -ForegroundColor Red; throw $msg }

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
Write-Step 'Checking prerequisites'

# Admin check
$principal = New-Object Security.Principal.WindowsPrincipal(
  [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Fail 'Must run in an elevated (Administrator) PowerShell session.'
}
Write-Ok 'Running as Administrator'

# OS + arch
$os = Get-CimInstance Win32_OperatingSystem
if ($os.Caption -notmatch 'Windows 11') {
  Write-Warn2 "OS caption: $($os.Caption) — expected Windows 11; continuing anyway"
} else { Write-Ok "OS: $($os.Caption)" }

if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
  Fail "Unsupported arch: $($env:PROCESSOR_ARCHITECTURE). This script targets AMD64."
}
Write-Ok 'Architecture: AMD64'

# Tailscale installed + up
$tailscaleExe = 'C:\Program Files\Tailscale\tailscale.exe'
if (-not (Test-Path $tailscaleExe)) {
  Fail "Tailscale not found at $tailscaleExe. Install from https://tailscale.com/download/windows first."
}
try {
  $tsStatus = & $tailscaleExe status --json 2>$null | ConvertFrom-Json
  if ($tsStatus.BackendState -ne 'Running') {
    Fail "Tailscale BackendState=$($tsStatus.BackendState); run 'tailscale up' first."
  }
  Write-Ok "Tailscale up (Self=$($tsStatus.Self.HostName))"
} catch {
  Fail "Tailscale status check failed: $_"
}

# Registration token — either provided or fetched via gh
if ([string]::IsNullOrWhiteSpace($RegToken)) {
  Write-Step 'No -RegToken supplied; attempting to fetch via gh CLI'
  $ghExe = Get-Command gh -ErrorAction SilentlyContinue
  if (-not $ghExe) {
    Fail 'gh CLI not found. Install GitHub CLI and run `gh auth login` with admin:org scope, or pass -RegToken <token>.'
  }
  try {
    $RegToken = & gh api -X POST 'orgs/KooshaPari/actions/runners/registration-token' --jq .token
  } catch {
    Fail "gh api call failed: $_. Ensure `gh auth login` completed with admin:org scope."
  }
  if ([string]::IsNullOrWhiteSpace($RegToken)) {
    Fail 'gh returned an empty registration token; re-authenticate with admin:org scope.'
  }
  Write-Ok 'Fetched registration token via gh'
} else {
  Write-Ok 'Registration token supplied via -RegToken'
}

# ---------------------------------------------------------------------------
# 2. Dedicated local user
# ---------------------------------------------------------------------------
Write-Step "Provisioning local user '$RunnerUser'"

$existing = Get-LocalUser -Name $RunnerUser -ErrorAction SilentlyContinue
if ($null -ne $existing) {
  Write-Warn2 "User '$RunnerUser' already exists — reusing (password must be supplied out-of-band for re-install)"
  $generatedPassword = $null
} else {
  # Generate a 32-char password from a broad character pool.
  Add-Type -AssemblyName System.Web
  # Alphanumeric-only to avoid cmd.exe shell metachar issues when passed to config.cmd
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  $bytes = New-Object byte[] 32
  $rng.GetBytes($bytes)
  $generatedPassword = -join (0..31 | ForEach-Object { $chars[$bytes[$_] % $chars.Length] })
  $secure = ConvertTo-SecureString $generatedPassword -AsPlainText -Force

  New-LocalUser -Name $RunnerUser `
                -Password $secure `
                -FullName 'GitHub Actions Runner Service Account' `
                -Description 'GH Actions runner (Phenotype infra)' `
                -PasswordNeverExpires `
                -UserMayNotChangePassword | Out-Null
  Add-LocalGroupMember -Group 'Users' -Member $RunnerUser -ErrorAction SilentlyContinue
  Write-Ok "Created user '$RunnerUser'"
}

if (-not $generatedPassword) {
  Fail "User '$RunnerUser' pre-existed and no password is available. Either delete the user and rerun, or supply a password via Set-LocalUser and rerun with the user already configured."
}

# ---------------------------------------------------------------------------
# 3. Download latest actions/runner (Windows x64)
# ---------------------------------------------------------------------------
Write-Step 'Resolving latest actions/runner release from github.com'

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$apiUrl = 'https://api.github.com/repos/actions/runner/releases/latest'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$headers = @{ 'User-Agent' = 'phenotype-installer'; 'Accept' = 'application/vnd.github+json' }
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers
if (-not $release) { Fail 'Could not query actions/runner releases.' }

$asset = $release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' } | Select-Object -First 1
if (-not $asset) {
  # Fallback: construct predictable URL. tag looks like v2.321.0 -> version 2.321.0.
  $version = $release.tag_name.TrimStart('v')
  $dlUrl   = "https://github.com/actions/runner/releases/download/$($release.tag_name)/actions-runner-win-x64-$version.zip"
  Write-Warn2 "No asset match in API; falling back to $dlUrl"
} else {
  $dlUrl = $asset.browser_download_url
}

$zipPath = Join-Path $InstallDir 'actions-runner.zip'
Write-Step "Downloading $dlUrl"
Invoke-WebRequest -Uri $dlUrl -OutFile $zipPath -UseBasicParsing
if (-not (Test-Path $zipPath)) { Fail 'Download failed.' }
Unblock-File -Path $zipPath

Write-Step "Extracting to $InstallDir"
# Remove previous runner binaries if reinstalling (but keep _work and .credentials)
Get-ChildItem -Path $InstallDir -Exclude '_work','_diag','.credentials','.runner','actions-runner.zip','logs' |
  Where-Object { $_.Name -ne 'config.cmd' -or -not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) } |
  ForEach-Object {
    if ($_.PSIsContainer -and $_.Name -in @('bin','externals')) {
      Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
    }
  }
Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
Remove-Item $zipPath -Force
Write-Ok "Runner extracted to $InstallDir"

$configCmd = Join-Path $InstallDir 'config.cmd'
if (-not (Test-Path $configCmd)) { Fail "config.cmd not found at $configCmd after extract." }

# ---------------------------------------------------------------------------
# 4. ACL: grant runner user access to install dir
# ---------------------------------------------------------------------------
Write-Step 'Setting ACLs on install dir'
$acl = Get-Acl $InstallDir
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
  $RunnerUser, 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$acl.SetAccessRule($rule)
Set-Acl -Path $InstallDir -AclObject $acl
Write-Ok "Granted Modify to $RunnerUser on $InstallDir"

# Ensure log dir exists for the pause hook
$logDir = Join-Path $InstallDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ---------------------------------------------------------------------------
# 5. Stop + remove existing service (clean reinstall path)
# ---------------------------------------------------------------------------
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
  Write-Warn2 "Service '$ServiceName' already exists — stopping + removing to reinstall"
  Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
  sc.exe delete $ServiceName | Out-Null
  Start-Sleep -Seconds 2

  # If we're re-registering, we should remove the old runner first; config.cmd
  # provides `remove`, but it needs a PAT, not a registration token. Skip here
  # and document in the README as a manual step if the user is replacing a
  # previous runner with the same name.
  Write-Warn2 "Note: a previous runner with name '$RunnerName' may still be registered at the org. Remove it via the GitHub UI or `config.cmd remove` if re-registration fails."
}

# ---------------------------------------------------------------------------
# 6. Register + install service via config.cmd
# ---------------------------------------------------------------------------
Write-Step "Registering runner '$RunnerName' against $OrgUrl (service-mode install)"

$logonAccount = ".\$RunnerUser"
$configArgs = @(
  '--url', $OrgUrl,
  '--token', $RegToken,
  '--name', $RunnerName,
  '--labels', $Labels,
  '--work', '_work',
  '--runasservice',
  '--windowslogonaccount', $logonAccount,
  '--windowslogonpassword', $generatedPassword,
  '--unattended',
  '--replace'
)

Push-Location $InstallDir
try {
  & $configCmd @configArgs
  if ($LASTEXITCODE -ne 0) {
    Fail "config.cmd exited with code $LASTEXITCODE. Check $InstallDir\_diag for details."
  }
} finally {
  Pop-Location
}
Write-Ok "Runner registered + service installed by config.cmd"

# config.cmd installs the service with its own canonical name; detect it so we
# can tune crash-recovery + link the pause task to the real name.
$actualService = Get-Service | Where-Object { $_.Name -match '^actions\.runner\..*KooshaPari.*' -or $_.DisplayName -match $RunnerName } |
  Select-Object -First 1
if (-not $actualService) {
  Write-Warn2 "Could not detect the installed actions.runner.* service automatically. Assuming name '$ServiceName'; verify with Get-Service."
  $resolvedServiceName = $ServiceName
} else {
  $resolvedServiceName = $actualService.Name
  Write-Ok "Detected service '$resolvedServiceName'"
}

# Crash-recovery ladder: 5s / 15s / 60s, reset window 24h.
sc.exe failure $resolvedServiceName reset= 86400 actions= restart/5000/restart/15000/restart/60000 | Out-Null
sc.exe description $resolvedServiceName 'GitHub Actions self-hosted runner (Phenotype desktop runner, Parsec-aware).' | Out-Null
Write-Ok "Crash-recovery ladder applied to '$resolvedServiceName'"

# ---------------------------------------------------------------------------
# 7. Gaming-mode pause hook (scheduled task)
# ---------------------------------------------------------------------------
Write-Step 'Installing gaming-mode pause scheduled task'

$pauseScript = Join-Path $InstallDir 'gaming-mode-pause.ps1'
$sentinelDir = Join-Path $env:USERPROFILE '.phenotype'
$sentinel    = Join-Path $sentinelDir 'runner-paused'
New-Item -ItemType Directory -Force -Path $sentinelDir | Out-Null

$pauseBody = @"
# Auto-generated pause hook — pauses '$resolvedServiceName' when Parsec is running
# or when sentinel '$sentinel' exists. Resumes otherwise.
`$svc = Get-Service -Name '$resolvedServiceName' -ErrorAction SilentlyContinue
if (-not `$svc) { exit 0 }

`$parsecRunning = [bool](Get-Process -Name parsecd -ErrorAction SilentlyContinue)
`$sentinelHit   = Test-Path '$sentinel'
`$shouldPause   = `$parsecRunning -or `$sentinelHit

if (`$shouldPause -and `$svc.Status -eq 'Running') {
  Stop-Service -Name '$resolvedServiceName' -Force
  Add-Content -Path '$logDir\gaming-mode.log' -Value "`$(Get-Date -Format o) paused (parsec=`$parsecRunning sentinel=`$sentinelHit)"
} elseif (-not `$shouldPause -and `$svc.Status -ne 'Running') {
  try {
    Start-Service -Name '$resolvedServiceName'
    Add-Content -Path '$logDir\gaming-mode.log' -Value "`$(Get-Date -Format o) resumed"
  } catch {
    Add-Content -Path '$logDir\gaming-mode.log' -Value "`$(Get-Date -Format o) resume-failed: `$_"
  }
}
"@
Set-Content -Path $pauseScript -Value $pauseBody -Encoding UTF8

$taskName = 'GitHubActionsRunner-GamingModePause'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$pauseScript`""
$trigger1 = New-ScheduledTaskTrigger -AtStartup
$trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal2 = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action `
  -Trigger @($trigger1, $trigger2) -Principal $principal2 -Settings $settings | Out-Null
Write-Ok "Scheduled task '$taskName' installed (runs every 60s)"

# ---------------------------------------------------------------------------
# 8. Final report
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '============================================================' -ForegroundColor Magenta
Write-Host ' GitHub Actions runner install complete' -ForegroundColor Magenta
Write-Host '============================================================' -ForegroundColor Magenta

if ($generatedPassword) {
  Write-Host ''
  Write-Host 'Service account password (shown ONCE — stash in Vaultwarden):' -ForegroundColor Yellow
  Write-Host "  user: $RunnerUser" -ForegroundColor Yellow
  Write-Host "  pass: $generatedPassword" -ForegroundColor Yellow
  Write-Host ''
}

Write-Host 'Verify:' -ForegroundColor Cyan
Write-Host "  Get-Service '$resolvedServiceName'           # expect Running"
Write-Host "  gh api orgs/KooshaPari/actions/runners --jq '.runners[] | select(.name == \"$RunnerName\") | {name, status, busy, labels: [.labels[].name]}'"
Write-Host ''
Write-Host 'Target this runner from a workflow:' -ForegroundColor Cyan
Write-Host "  runs-on: [self-hosted, Windows, X64, desktop-kooshapari-desk]"
Write-Host ''
Write-Host "Install dir : $InstallDir" -ForegroundColor DarkGray
Write-Host "Logs        : $logDir + $InstallDir\_diag" -ForegroundColor DarkGray
Write-Host "Pause sentinel: $sentinel (touch to force-pause)" -ForegroundColor DarkGray
Write-Host "Pause task  : $taskName (runs every 60s)" -ForegroundColor DarkGray
