# Windows GitHub Actions Runner (`install-windows-runner.ps1`)

Installs a **self-hosted GitHub Actions runner** on the Windows 11 desktop
(`kooshapari-desk.tail2b570.ts.net`), registered at the
[`KooshaPari`](https://github.com/KooshaPari) organization scope.

Forgejo was the original target for this script; it is blocked waiting on
OCI capacity, so GitHub Actions is standing in. The dedicated-user +
`sc.exe` crash-recovery + Parsec-pause infrastructure carries over
unchanged — only the registration target differs.

## What it installs

- Dedicated `gh-runner` Windows local user (service account, 32-char
  generated password, never expires).
- `actions/runner` latest release (Windows x64) unpacked to
  `C:\actions-runner` by default.
- Runner registered at **org scope** (`https://github.com/KooshaPari`)
  with labels `self-hosted, Windows, X64, desktop-kooshapari-desk` and
  name `desktop-kooshapari-desk`.
- Windows service installed by `config.cmd --runasservice` running as
  `.\gh-runner`, with `sc.exe failure` crash-recovery ladder
  (5s → 15s → 60s, 24h reset window).
- Scheduled task `GitHubActionsRunner-GamingModePause` (runs every 60s
  as SYSTEM) that stops the runner service while Parsec (`parsecd.exe`)
  is running or while `~/.phenotype/runner-paused` exists, and resumes
  otherwise.

## Prerequisites

1. **Windows 11 AMD64**, elevated PowerShell session, admin rights.
2. **Tailscale** installed + `tailscale up` (the script refuses to
   proceed if `BackendState != Running`).
3. **GitHub CLI** authenticated with `admin:org` scope **or** a
   pre-fetched registration token:
   ```powershell
   gh auth login --scopes admin:org
   # or, paste a token manually:
   $t = gh api -X POST orgs/KooshaPari/actions/runners/registration-token --jq .token
   ```

## Invocation

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

# Option A — let the script fetch the token via gh (requires admin:org scope)
.\install-windows-runner.ps1

# Option B — paste a pre-fetched registration token
.\install-windows-runner.ps1 -RegToken '<token-from-gh-api>'
```

Optional parameters:

| Param | Default | Notes |
|-------|---------|-------|
| `-InstallDir` | `C:\actions-runner` | Extraction + service working dir |
| `-OrgUrl` | `https://github.com/KooshaPari` | Org-scope registration URL |
| `-Labels` | `self-hosted,Windows,X64,desktop-kooshapari-desk` | Workflow targeting |
| `-RunnerName` | `desktop-kooshapari-desk` | Name shown in GitHub UI |
| `-RunnerUser` | `gh-runner` | Local service account |
| `-ServiceName` | `GitHubActionsRunner` | Fallback name if auto-detect fails |

> The `actions/runner` installer chooses its own service name
> (`actions.runner.KooshaPari.desktop-kooshapari-desk`). The script
> detects the real name after `config.cmd` runs and applies the
> crash-recovery ladder + pause hook against it.

## Verification

```powershell
# Service is up
Get-Service | Where-Object Name -match '^actions\.runner\.'

# Runner shows as online at org scope
gh api orgs/KooshaPari/actions/runners `
  --jq '.runners[] | select(.name == "desktop-kooshapari-desk") | {name, status, busy, labels: [.labels[].name]}'

# Pause task registered
Get-ScheduledTask -TaskName GitHubActionsRunner-GamingModePause
```

Target the runner from a workflow:

```yaml
jobs:
  gpu-build:
    runs-on: [self-hosted, Windows, X64, desktop-kooshapari-desk]
    steps:
      - uses: actions/checkout@v4
      - run: echo "running on the desktop box"
```

## Parsec coexistence

The pause hook (`gaming-mode-pause.ps1`, invoked every 60s by a SYSTEM
scheduled task) performs two checks:

1. Is `parsecd.exe` running? (Parsec host agent)
2. Does `%USERPROFILE%\.phenotype\runner-paused` exist? (manual override)

If **either** is true and the runner service is `Running`, it calls
`Stop-Service` and logs to `C:\actions-runner\logs\gaming-mode.log`.
When both clear, it calls `Start-Service` on the next tick. Jobs that
were queued wait in GitHub's side; the runner simply stops polling.

To force-pause for maintenance:

```powershell
New-Item -ItemType File -Path "$env:USERPROFILE\.phenotype\runner-paused" -Force
# …do work…
Remove-Item "$env:USERPROFILE\.phenotype\runner-paused"
```

## Re-install / replace

Running the script again on the same host stops the existing service,
deletes it, and re-runs `config.cmd --replace`, which re-uses the same
runner name at the org scope. If the previous runner has a different
name (e.g. after a rename), remove it from the org first via the
GitHub UI or:

```powershell
cd C:\actions-runner
.\config.cmd remove --token <removal-token-from-gh-api>
```

## Uninstall

```powershell
cd C:\actions-runner
.\config.cmd remove --token <removal-token>
Unregister-ScheduledTask -TaskName GitHubActionsRunner-GamingModePause -Confirm:$false
Remove-LocalUser -Name gh-runner
Remove-Item -Recurse -Force C:\actions-runner
```
