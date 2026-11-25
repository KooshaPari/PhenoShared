# Runbook: Windows Desktop GitHub Actions Runner

**Node:** `desktop-kooshapari-desk` (home Mac mini under Windows partition / Boot Camp; `[self-hosted, heavy, home]`)
**Status:** Operational as of 2026-04-24
**Service name:** `actions.runner.KooshaPari-phenotype-tooling.desktop-kooshapari-desk`
**Install script:** `iac/scripts/install-windows-runner.ps1`

This runbook captures the procedure that was actually used to bring the Windows desktop runner online, and the gotchas that surfaced during the install. Use this when re-provisioning, replacing the host, or onboarding a similar Windows-class heavy runner.

---

## 1. Prerequisites

- Windows 10/11 host on the Phenotype Tailnet.
- Local admin shell (PowerShell 5.1 or 7).
- GitHub PAT with `repo` + `admin:org` scopes (for org-level runner registration), OR a runner registration token from `https://github.com/organizations/KooshaPari/settings/actions/runners/new`.
- ≥10 GB free on `C:\` for the `actions-runner` work directory.
- (Optional) Parsec installed for remote desktop. Parsec gaming-mode and the runner coexist because the runner service starts in `Manual` start mode and only runs while a job is dispatched.

---

## 2. Install Procedure

```powershell
# From an elevated PowerShell session on the target Windows host:
cd C:\
iex (irm https://raw.githubusercontent.com/KooshaPari/phenotype-infra/main/iac/scripts/install-windows-runner.ps1)
```

The script:

1. Creates `C:\actions-runner\` and downloads the latest `actions-runner-win-x64-*.zip`.
2. Verifies the SHA-256 against the published checksum.
3. Creates the local service account `runneruser` with an alphanumeric password (see Gotcha §3.2).
4. Registers the runner against `https://github.com/KooshaPari` (org-level, no quoting — see §3.4).
5. Installs the runner as a Windows service in `Manual` start mode.
6. Adds firewall rule for inbound port 22 on the **Private** profile only (see §3.5).

After the script completes, verify:

```powershell
Get-Service "actions.runner.KooshaPari-phenotype-tooling.desktop-kooshapari-desk"
# Status should be: Stopped (Manual). It will be started by GH on dispatch.
```

And from any controller host on the Tailnet:

```bash
ssh runneruser@desktop-kooshapari-desk.tail-scale-name.ts.net "Get-Service actions.runner.* | Format-List"
```

---

## 3. Gotchas (Each Patched in Commit `51e5ee2`)

### 3.1 Em-dash → ASCII hyphen

PowerShell 5.1 (the default on Windows 10/11 LTSC) silently mangles the UTF-8 em-dash (`—`, U+2014) when a script is invoked via `iex (irm ...)`. The byte sequence is reinterpreted as CP-1252 and the script aborts with a parser error several lines after the actual offending character.

**Fix:** every em-dash in `install-windows-runner.ps1` was replaced with an ASCII hyphen `-`. Lint rule for this repo: no non-ASCII glyphs in `.ps1` files.

### 3.2 Alphanumeric password

The Windows local-account creation API (`New-LocalUser`) accepts special characters in the password parameter at the .NET layer but the underlying `NetUserAdd` call rejects passwords containing certain shell metacharacters when the password is forwarded to `sc.exe config <svc> obj=<acct> password=<pw>`. The failure is silent — the service is created with no credential and fails to start with `1069 (logon failure)`.

**Fix:** the script now generates a 24-char alphanumeric password (`[A-Za-z0-9]{24}`) and stores it to Vaultwarden under `windows-runner/desktop-kooshapari-desk/runneruser`. Do not use `!@#$%^&*()` in this password.

### 3.3 `Description` 48-char cap

The Windows service `Description` field has an undocumented 48-character truncation when set via `sc.exe description`. Longer values are truncated silently and leave the description in an inconsistent state across `services.msc` vs `Get-CimInstance`.

**Fix:** description is now exactly `"GH Actions runner - desktop-kooshapari-desk"` (43 chars).

### 3.4 `-OrgUrl` without quotes

When `config.cmd` is invoked via PowerShell with a quoted URL (`-OrgUrl "https://github.com/KooshaPari"`), PS double-encodes the quotes when the script came in via `iex`, and `config.cmd` sees `"\"https://github.com/KooshaPari\""` as the org URL — registration fails with `Invalid configuration provided for runnerRegistrationUrl`.

**Fix:** the script invokes `config.cmd` with the unquoted form: `--url https://github.com/KooshaPari`. The URL has no shell-special characters so unquoting is safe.

### 3.5 Firewall profile (Public → Private)

The Windows host originally had its primary network adapter classified as `Public`, which blocks SSH and the runner's outbound long-poll connection on first boot.

**Fix:** the script flips the active connection profile to `Private` (`Set-NetConnectionProfile -InterfaceAlias <iface> -NetworkCategory Private`) before adding the firewall rules. SSH (port 22) is opened only on the Private profile.

### 3.6 Parsec coexistence

Parsec's gaming-mode wants exclusive use of the GPU and audio devices. The runner service does not contend for these (no GUI, no GPU jobs by default), but **do not enable auto-start on the runner service** — leave it in `Manual`. Otherwise a runner job dispatched mid-Parsec-session can pin a CPU core during a game.

If a future job class needs GPU access (CUDA / MPS / DirectML), schedule those jobs only via a separate runner registration with a `[self-hosted, gpu, home]` label and pause Parsec via the gaming-mode pause hook (ADR-0008).

---

## 4. Verification Checklist

- [ ] `Get-Service actions.runner.*` shows the runner service in `Stopped (Manual)` state.
- [ ] GitHub org runners page lists `desktop-kooshapari-desk` as `Idle`.
- [ ] Test workflow with `runs-on: [self-hosted, heavy, home]` dispatches and completes successfully.
- [ ] After job completes, service returns to `Stopped`.
- [ ] Parsec session uninterrupted during a runner job (smoke-test with a no-op workflow).
- [ ] SSH from another Tailnet node reaches the host on port 22.
- [ ] `runneruser` password retrievable from Vaultwarden under `windows-runner/desktop-kooshapari-desk/runneruser`.

---

## 5. Tear-down / Replacement

```powershell
cd C:\actions-runner
.\config.cmd remove --token <removal-token-from-gh>
sc.exe delete "actions.runner.KooshaPari-phenotype-tooling.desktop-kooshapari-desk"
Remove-LocalUser runneruser
Remove-Item -Recurse -Force C:\actions-runner
```

Then revoke the Vaultwarden entry and remove the runner from the org runners page if it didn't auto-deregister.

---

## 6. References

- ADR-0003: Home desktop as heavy runner
- ADR-0007: Runner label routing taxonomy
- ADR-0008: Parsec gaming-mode pause
- Install script: `iac/scripts/install-windows-runner.ps1`
- Fix-up commit: `51e5ee2` (em-dash, password, description, OrgUrl)
- Day-1 setup runbook (cross-platform variant): `docs/runbooks/day1-home-runner-setup.md`
