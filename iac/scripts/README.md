# Phenotype infra — runner install scripts

Helper scripts for provisioning self-hosted Forgejo runners across the
Phenotype fleet. These are operator-run; they do not get invoked by CI.

## Files

| Script | Target | Purpose |
|--------|--------|---------|
| `bootstrap-oci.sh` | Oracle Cloud ARM VM | Stand up Forgejo + Woodpecker backbone. |
| `register-home-runner.sh` | macOS / Linux | Register a home act_runner against Forgejo. |
| `health-check.sh` | Any | Probe runner + Forgejo liveness. |
| `install-windows-runner.ps1` | **Windows 11 AMD64 desktop** | Dedicated Forgejo runner on `kooshapari-desk.tail2b570.ts.net`. |

---

## `install-windows-runner.ps1`

### What it does

1. **Prereq checks** — elevated shell, Windows 11, AMD64, Tailscale installed and `BackendState=Running`.
2. **Creates local user `forgejo-runner`** with a 32-char generated password (displayed **once** at the end of the run — stash it in Vaultwarden after OCI is live).
3. **Downloads the latest `act_runner.exe`** (Windows AMD64) from `https://gitea.com/api/v1/repos/gitea/act_runner/releases` to `C:\forgejo-runner\act_runner.exe`.
4. **Writes `C:\forgejo-runner\config.yaml`** wired for `http://forgejo.ts.internal:3000` via Tailscale MagicDNS (assumes Forgejo lives on the OCI tailnet node).
5. **Installs the `ForgejoRunner` Windows service** via `sc.exe` in `daemon --config` mode, running as `.\forgejo-runner` with autostart + crash-recovery policy (restart after 5s / 15s / 60s).
6. **Skips registration** — Forgejo is not yet up. The script prints the exact `act_runner register` command to run once the OCI instance is live.
7. **Installs `ForgejoRunner-GamingModePause` scheduled task** — runs every 60s as SYSTEM, pauses the service when `parsecd.exe` is running OR when `%USERPROFILE%\.phenotype\runner-paused` exists; resumes otherwise.

### Prerequisites on the desktop

- Windows 11 (AMD64).
- Tailscale installed (`C:\Program Files\Tailscale\tailscale.exe`) and up (`tailscale up`).
- Elevated PowerShell (Run as Administrator).
- Machine reachable at `kooshapari-desk.tail2b570.ts.net` on the tailnet.
- Outbound HTTPS to `gitea.com` (for the initial binary download only).

### Run it

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
cd C:\path\to\phenotype-infra\iac\scripts
.\install-windows-runner.ps1
```

Optional overrides:

```powershell
.\install-windows-runner.ps1 `
  -ForgejoUrl 'http://forgejo.ts.internal:3000' `
  -Labels     'self-hosted,windows,amd64,desktop,gpu' `
  -InstallDir 'C:\forgejo-runner'
```

### Post-OCI registration (manual follow-up)

Once Forgejo is live on OCI and you have a runner registration token:

```powershell
cd C:\forgejo-runner
.\act_runner.exe register `
  --instance 'http://forgejo.ts.internal:3000' `
  --token    '<RUNNER_TOKEN>' `
  --labels   'self-hosted,windows,amd64,desktop' `
  --no-interactive

Start-Service -Name ForgejoRunner
Get-Service  -Name ForgejoRunner        # expect Running
Get-Content  C:\forgejo-runner\logs\gaming-mode.log -Tail 20
```

### Gaming-mode controls

- **Force-pause the runner during a Parsec session or game stream:**
  ```powershell
  New-Item -ItemType File -Force "$env:USERPROFILE\.phenotype\runner-paused" | Out-Null
  ```
- **Release the hold:**
  ```powershell
  Remove-Item "$env:USERPROFILE\.phenotype\runner-paused" -Force
  ```
- The scheduled task reconciles state within ~60s.
- Auto-pause also triggers whenever `parsecd.exe` is detected running.

### Paths

| Purpose | Path |
|---------|------|
| Install root | `C:\forgejo-runner` |
| Binary | `C:\forgejo-runner\act_runner.exe` |
| Config | `C:\forgejo-runner\config.yaml` |
| Cache | `C:\forgejo-runner\cache` |
| Logs | `C:\forgejo-runner\logs` |
| Pause sentinel | `%USERPROFILE%\.phenotype\runner-paused` |
| Gaming-mode log | `C:\forgejo-runner\logs\gaming-mode.log` |

### Uninstall

```powershell
Stop-Service ForgejoRunner -Force
sc.exe delete ForgejoRunner
Unregister-ScheduledTask -TaskName ForgejoRunner-GamingModePause -Confirm:$false
Remove-LocalUser -Name forgejo-runner
Remove-Item -Recurse -Force C:\forgejo-runner
```

### Scripting-policy note

PowerShell is the right tool here — this is platform glue for Windows
service + scheduled-task APIs that have no clean cross-platform Rust/Go
equivalent (LocalUser provisioning, `sc.exe`, `Register-ScheduledTask`).
Migrating to Rust would require wrapping `advapi32`/`taskschd` COM and
would be a net loss versus a single `.ps1` the operator runs once.
