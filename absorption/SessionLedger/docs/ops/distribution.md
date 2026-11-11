# Distribution — SessionLedger

How SessionLedger is packaged, where data lives, how to uninstall cleanly, and
how release integrity signing works, and what remains **deferred** for
platform code-signing / notarization. Complements
[`packaging/README.md`](../../packaging/README.md),
[`packaging/channels.md`](../../packaging/channels.md), the traditional Linux
systemd unit
[`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service),
and the tag-driven release workflow
[`.github/workflows/release.yml`](../../.github/workflows/release.yml).

Issue tracker: [#66](https://github.com/KooshaPari/SessionLedger/issues/66)
(signing + installer path).

---

## Release channels (current)

| Channel                      | Status                                              | Notes                                                                                                                                                                                                                                                                      |
| ---------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub Releases (`v*` tags)  | **Active**                                          | `release.yml` builds archives, publishes `SHA256SUMS` + a CycloneDX SBOM, and attempts GitHub provenance attestation and keyless cosign signing                                                                                                                            |
| GHCR OCI (`sl-daemon`)       | **Blocking on canonical `v*` tags (unconditional)** | Builds `crates/sl-daemon/Containerfile`, pushes `ghcr.io/kooshapari/sl-daemon`, keyless cosign + GitHub attestation + blocking `oci-cosign-verify` (`continue-on-error: false`); forks credential-gate OCI with an explicit reason                                         |
| Cargo source install         | **Active for developers**                           | `cargo install --path crates/sl-daemon --locked` or `cargo install --git … --path crates/sl-daemon`                                                                                                                                                                        |
| curl / irm install scripts   | **Active**                                          | `scripts/install.sh` (Linux/macOS) and `scripts/install.ps1` (Windows) install checksum-verified `sl-viewer` Release archives                                                                                                                                              |
| Local packaging scaffold     | **Active**                                          | `make -C packaging package-macos` / `package-linux` / `package-windows`                                                                                                                                                                                                    |
| Native installers (unsigned) | **Active, CI-smoked**                               | Release CI publishes unsigned MSI + macOS PKG, best-effort Linux `.deb`/AppImage, and portable viewer/daemon archives; Release smoke covers Windows ZIP + MSI silent install and macOS PKG expand; PR CI still runs unsigned portable clean-host smoke on `windows-latest` |
| Homebrew / winget            | **Manifests in-repo (not live)**                    | Formula + winget YAML templates; fill via `scripts/fill-packaging-checksums.ps1`, then [`brew-winget-publish.md`](brew-winget-publish.md) publish-readiness checklist + `scripts/brew-winget-publish-check.ps1 -SelfCheck` — live tap / winget-pkgs remain **unpaid**      |
| Scoop / crates.io / DMG      | Deferred                                            | Explicit placeholders only; no bucket, crate publication, DMG, or update automation exists yet                                                                                                                                                                             |
| Tray / menubar / auto-update | Soft / N-A                                          | Deliberate daemon + foreground viewer scope; see [ADR 0001](../adr/0001-desktop-companion-scope.md)                                                                                                                                                                        |
| User-initiated update check  | **Active**                                          | `sl-daemon check-update` compares installed version to GitHub latest release tag (no install); see [update-check.md](update-check.md)                                                                                                                                      |
| Mobile app presence          | Soft / N-A                                          | Deliberate desktop + daemon scope; see [ADR 0002](../adr/0002-mobile-presence.md)                                                                                                                                                                                          |

### Release matrix (CI)

From `.github/workflows/release.yml` (on `push` tags `v*`):

| Target triple              | Runner           | Artifacts                                                      | Status                         |
| -------------------------- | ---------------- | -------------------------------------------------------------- | ------------------------------ |
| `x86_64-unknown-linux-gnu` | `ubuntu-latest`  | viewer + daemon `.tar.gz`; best-effort `.deb` + AppImage       | **Shipped + smoke-tested**     |
| `x86_64-apple-darwin`      | `macos-latest`   | viewer + daemon `.tar.gz`; unsigned `.pkg` + `.app.tar.gz`     | Shipped                        |
| `aarch64-apple-darwin`     | `macos-latest`   | viewer + daemon `.tar.gz`; unsigned `.pkg` + `.app.tar.gz`     | **Shipped + PKG expand smoke** |
| `x86_64-pc-windows-msvc`   | `windows-latest` | viewer + daemon `.zip`; unsigned `SessionLedger-<ver>-x64.msi` | **Shipped + ZIP/MSI smoke**    |

Asset names (representative):

```text
sl-viewer-<tag>-x86_64-unknown-linux-gnu.tar.gz
sl-daemon-<tag>-x86_64-unknown-linux-gnu.tar.gz
sl-viewer-<tag>-x86_64-apple-darwin.tar.gz
sl-daemon-<tag>-x86_64-apple-darwin.tar.gz
sl-viewer-<tag>-aarch64-apple-darwin.tar.gz
sl-daemon-<tag>-aarch64-apple-darwin.tar.gz
sl-viewer-<tag>-x86_64-pc-windows-msvc.zip
sl-daemon-<tag>-x86_64-pc-windows-msvc.zip
SessionLedger-<ver>-x64.msi
SessionLedger-<ver>-aarch64.pkg
SessionLedger-<ver>-x86_64.pkg
SessionLedger-<ver>-aarch64.app.tar.gz
SessionLedger-<ver>-x86_64.app.tar.gz
sessionledger_<ver>_amd64.deb
SessionLedger-<ver>-x86_64.AppImage
SHA256SUMS
session-ledger.cdx.json
SHA256SUMS.sigstore.json
```

`session-ledger.cdx.json` is the CycloneDX SBOM and is required for the Release
job to succeed. GitHub build provenance is blocking on the canonical repository.
On every canonical `v*` tag, the GHCR `sl-daemon` cosign/attest/`oci-cosign-verify`
path is **unconditionally** release-blocking (`continue-on-error: false`).
Forks credential-gate OCI (no `packages:write` / OIDC). `SHA256SUMS.sigstore.json`
remains best-effort. Authenticode and Apple notarization stay deferred under ADR 0003 — published
MSI/PKG artifacts are **unsigned**.

### OCI cosign policy matrix (unconditional vs credential-gated)

| Context                                       | OCI build / sign / `oci-cosign-verify`   | `continue-on-error`                                     | Notes                                                            |
| --------------------------------------------- | ---------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- |
| Canonical `KooshaPari/SessionLedger` `v*` tag | **Required, release-blocking**           | **false** (implicit default; documented on verify step) | Unconditional on canonical tags — Release `needs: oci-image`     |
| Fork `v*` tag push                            | Skipped with explicit reason             | n/a (job succeeds; OCI steps gated off)                 | Credential-gated — no GHCR `packages:write` or OIDC attestations |
| Deploy-time (`scripts/oci-cosign-verify.ps1`) | Required when pulling a published digest | n/a (script fails closed)                               | Use `-AllowUnsigned` only for dry-runs                           |
| `SHA256SUMS` cosign `sign-blob`               | Best-effort                              | **true** on sign/publish steps                          | Unsigned archives remain valid without Sigstore bundle           |

Machine-check policy anchors (no registry, no cosign required):

```powershell
pwsh ./scripts/oci-cosign-verify.ps1 -SelfCheck
```

**Windows matrix status:** release CI produces an unsigned portable ZIP and a
real WiX v4 MSI (`SessionLedger-<ver>-x64.msi`), then `smoke-windows` runs ZIP
`--version` plus MSI silent install → `--version` → uninstall. Linux smoke
validates the viewer `.tar.gz`; macOS smoke expands the aarch64 PKG. The
Release is not created unless those smoke jobs pass. Authenticode signing
remains explicitly deferred.

### Installer matrix

| Platform / format       | Status                             | Current capability                                                                                        |
| ----------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Windows installable ZIP | **Partial, CI-smoked**             | Portable release binary is download/extract/execute-smoked; local package adds per-user install scripts   |
| Windows MSI / WiX v4    | **Active (unsigned)**              | Release CI builds and attaches `SessionLedger-<ver>-x64.msi`; silent install smoke; Authenticode deferred |
| Linux AppImage          | **Active (unsigned, best-effort)** | Release CI attaches when `packaging/linux/package-appimage.sh` succeeds                                   |
| Linux Debian package    | **Active (unsigned, best-effort)** | Release CI attaches when `packaging/linux/package-deb.sh` succeeds                                        |
| macOS `.app` / `.pkg`   | **Active (unsigned)**              | Release CI builds via `packaging/macos/` + `productbuild`; notarization deferred                          |

These installers use the same existing
[checksum, cosign, and GitHub attestation path](#release-integrity-signing-cosign)
when distributed as release assets. Platform-native signing is separate and
remains deferred.

---

## Data directories

SessionLedger does **not** yet declare XDG / AppData config homes in code.
Paths are env- and flag-driven. Prefer one explicit root so uninstall can wipe
a single tree.

### Local compose (`make dev`)

Root [`process-compose.yaml`](../../process-compose.yaml) sets:

| Variable      | Default      | Role                                                                |
| ------------- | ------------ | ------------------------------------------------------------------- |
| `SL_DATA_DIR` | `./.sl-data` | Local data root for the compose stack (bundles / out dir readiness) |
| `SL_PORT`     | `8080`       | Daemon HTTP bind port                                               |

Create the directory before readiness probes succeed:

```bash
mkdir -p "${SL_DATA_DIR:-./.sl-data}"
export SL_DATA_DIR="${SL_DATA_DIR:-./.sl-data}"
```

`/readyz` expects the configured out / data directory to exist (see
[`runbook.md`](runbook.md)).

### Daemon watch / out (crate compose & CLI)

The daemon crate’s own compose file and CLI use explicit watch/out paths:

| Variable / flag                             | Typical default                     | Role                                    |
| ------------------------------------------- | ----------------------------------- | --------------------------------------- |
| `SL_WATCH_DIR` / `--watch`                  | `./sessions` or `~/.forge/sessions` | Incoming `*.jsonl` transcripts          |
| `SL_OUT_DIR` / `--out`                      | `./okf-out`                         | Written `<session-id>.okf.json` bundles |
| `--data-dir` (archive / restore / validate) | `.`                                 | Bundle + `archive/<year>/<month>/` tree |

When aligning with `SL_DATA_DIR`, a common layout is:

```text
$SL_DATA_DIR/
  sessions/          # optional watch input
  out/               # OKF bundles (*.okf.json)
  archive/YYYY/MM/   # gzip archives from `sl archive`
  audit/             # append-only audit sink (events.jsonl or events.db)
    archive/         # operator-rotated copies (not created by sl-daemon)
```

Map with:

```bash
export SL_DATA_DIR="${SL_DATA_DIR:-$PWD/.sl-data}"
export SL_WATCH_DIR="${SL_WATCH_DIR:-$SL_DATA_DIR/sessions}"
export SL_OUT_DIR="${SL_OUT_DIR:-$SL_DATA_DIR/out}"
mkdir -p "$SL_WATCH_DIR" "$SL_OUT_DIR"
```

### Container / OCI

[`crates/sl-daemon/Containerfile`](../../crates/sl-daemon/Containerfile) mounts:

| Path in image    | Host mount example               |
| ---------------- | -------------------------------- |
| `/data/sessions` | `$HOME/.forge/sessions` (ro)     |
| `/data/out`      | `$PWD/okf-out` or a named volume |

Volumes are owned by non-root user `sl` (uid `10001`). The canonical daemon
image defines an OCI `HEALTHCHECK` that probes `GET /healthz` on
`127.0.0.1:8080` while `sl-daemon serve` is running.

On each `v*` tag, `release.yml` job `oci-image` builds that Containerfile,
pushes `ghcr.io/kooshapari/sl-daemon:<tag>` (and `latest` for non-prerelease
tags), keyless-cosign signs the digest, publishes GitHub build provenance to
the registry, and runs blocking `oci-cosign-verify` (`continue-on-error: false`)
before the Release job publishes assets. Canonical tags require this path
unconditionally; forks credential-gate OCI with an explicit reason so portable
archives remain valid.

Local build (no registry):

```bash
podman build -t sl-daemon:local -f crates/sl-daemon/Containerfile .
```

See [Verify an OCI image](#verify-an-oci-image-cosign) for deploy-time checks
(`scripts/oci-cosign-verify.ps1`).

### Future XDG / AppData (not implemented)

Documented intent only — no code yet:

| OS      | Config (future)                               | Data (future)                            |
| ------- | --------------------------------------------- | ---------------------------------------- |
| Linux   | `$XDG_CONFIG_HOME/sessionledger`              | `$XDG_DATA_HOME/sessionledger`           |
| macOS   | `~/Library/Application Support/SessionLedger` | same or `~/Library/Caches/SessionLedger` |
| Windows | `%APPDATA%\SessionLedger`                     | `%LOCALAPPDATA%\SessionLedger`           |

Until then, treat `SL_DATA_DIR` (and `--out` / `--data-dir`) as the SSOT.

---

## Clean-host install/uninstall evidence (unsigned)

**Scope:** repeatable install → launch → uninstall checks on a host with no prior
SessionLedger install. This lane covers **unsigned** portable ZIP and unsigned
MSI paths. It does **not** use Authenticode or notarization.

| Evidence type             | Where                                                       | What it proves                                                                                                           |
| ------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| CI scaffold smoke         | `ci.yml` job `installer-lifecycle-smoke`                    | Installer sources, uninstall docs, and clean-host checklist text are present                                             |
| CI Windows portable smoke | `ci.yml` job `clean-host-smoke-windows`                     | Unsigned ZIP → `Install.ps1` → `--version` → `Uninstall.ps1` on an ephemeral `windows-latest` runner with isolated paths |
| Release Windows MSI smoke | `release.yml` job `smoke-windows`                           | Unsigned MSI silent install → `--version` → uninstall                                                                    |
| Release macOS PKG smoke   | `release.yml` job `smoke-macos-pkg`                         | Unsigned aarch64 PKG expands with expected payload                                                                       |
| CI artifact               | `clean-host-evidence.json` (uploaded per Windows smoke run) | Machine-readable step log with run metadata                                                                              |
| Manual checklist          | Below                                                       | Human reruns on a VM or spare machine before release                                                                     |

Authenticode / notarized clean-host evidence remains deferred under
[ADR 0003](../adr/0003-platform-code-signing.md) and [#66](https://github.com/KooshaPari/SessionLedger/issues/66).

### Repeatable checklist — Windows unsigned portable ZIP

Run on a Windows host **without** an existing install at
`%LOCALAPPDATA%\Programs\SessionLedger`, no Start Menu shortcut named
`SessionLedger.lnk`, and no `HKCU\...\Uninstall\SessionLedger` key.

| Step              | Action                                                                                                  | Pass criteria                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1. Preflight      | Confirm paths above are absent; close any `sl-viewer` process                                           | No prior install artifacts                                                                                           |
| 2. Obtain package | `make -C packaging package-windows` **or** download the Release `.zip` and extract                      | `sl-viewer.exe`, `Install.ps1`, `Uninstall.ps1` present                                                              |
| 3. Install        | `powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1` from the extracted folder           | Exit code 0; binary under `%LOCALAPPDATA%\Programs\SessionLedger`                                                    |
| 4. Register       | Inspect Start Menu and Installed Apps                                                                   | `SessionLedger.lnk` exists; uninstall entry present                                                                  |
| 5. Launch         | `sl-viewer.exe --version` from the install dir                                                          | Prints expected `sl-viewer <version>`                                                                                |
| 6. Uninstall      | `powershell -NoProfile -ExecutionPolicy Bypass -File .\Uninstall.ps1` **or** Installed Apps → Uninstall | Exit code 0                                                                                                          |
| 7. Cleanup verify | Wait a few seconds, then re-check install dir, shortcut, registry key                                   | All removed; **user data dirs are intentionally preserved** (see [Uninstall / cleanliness](#uninstall--cleanliness)) |

Automated equivalent (writes `clean-host-evidence.json` when `-EvidencePath` is set):

```powershell
./scripts/installer-lifecycle-smoke.ps1 -WindowsInstallLifecycle `
  -EvidencePath packaging/dist/clean-host-evidence.json
```

PR CI runs the same path on `windows-latest` and uploads the evidence artifact.

### Repeatable checklist — Linux / macOS portable (manual)

CI does not yet automate these; use an isolated VM or user account.

**Linux Release `.tar.gz`**

1. Preflight: no `~/.local/bin/sl-viewer` from a prior `install.sh` run unless you intend to overwrite it.
2. Download Release archive + `SHA256SUMS`; verify checksum (see [Release integrity signing](#release-integrity-signing-cosign)).
3. Extract; run `./sl-viewer --version`.
4. Cleanup: delete the extracted folder and any data roots you created (`SL_DATA_DIR`, `./okf-out`, etc.).

**macOS Release `.tar.gz` or local `.app`**

1. Preflight: remove any prior `SessionLedger.app` copy from `/Applications` used for testing.
2. Extract or `make -C packaging package-macos`; run `./sl-viewer --version` or open the `.app` once.
3. Cleanup: delete the test `.app` / extracted tree; clear quarantine attrs if needed (see [macOS Gatekeeper notes](#macos-gatekeeper-notes-unsigned-builds)).

### What unsigned clean-host evidence does **not** cover

- Authenticode / Apple Developer ID signatures or SmartScreen/Gatekeeper trust
- Per-machine (ALLUSERS=1) MSI installs
- Full `dpkg -i` / AppImage desktop integration smoke beyond artifact presence
- Daemon install via systemd unit (documented separately above)
- Automatic updates or signed update channels

### User-initiated update check (no auto-install)

Operators can check whether a newer GitHub Release exists without downloading
or replacing binaries:

```bash
sl-daemon check-update
sl-daemon check-update --json
```

Exit `0` when up to date, `1` when a newer tag exists, `2` on error. This path
does **not** perform silent or background updates — see
[ADR 0001](../adr/0001-desktop-companion-scope.md) and
[update-check.md](update-check.md).

Machine-check anchors:

```powershell
pwsh ./scripts/update-check-check.ps1 -SelfCheck
```

---

## Install

### From GitHub Release

1. Download the archive for your platform from the latest `v*` Release.
2. Extract; run `./sl-viewer` (Unix) or `sl-viewer.exe` (Windows).
3. Start `sl-daemon` from the matching Release daemon archive (or from source)
   with an explicit `--watch` / `--out` (or compose + `SL_DATA_DIR`).

### From source (local packaging)

```bash
make -C packaging package-macos   # → packaging/dist/SessionLedger.app
make -C packaging package-linux   # → packaging/dist/linux/SessionLedger
# On Windows:
make -C packaging package-windows # → packaging/dist/sl-viewer-v<version>-x86_64-pc-windows-msvc.zip

# Linux installers (also best-effort on Release CI):
./packaging/linux/package-appimage.sh
./packaging/linux/package-deb.sh

# macOS .app + .pkg (unsigned):
./packaging/macos/package-app.sh
./packaging/macos/package-pkg.sh

# Windows MSI (unsigned; requires WiX v4):
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package-msi.ps1
```

The Windows ZIP can run portably or invoke `Install.ps1` for a per-user install.
Unsigned MSI builds are documented in
[`scripts/package-msi.md`](../../scripts/package-msi.md). See
[`packaging/README.md`](../../packaging/README.md) for the installer matrix.
See [`packaging/channels.md`](../../packaging/channels.md) for the current
cargo install path, GitHub Release archive channel, curl/irm install scripts,
Homebrew/winget in-repo manifests, and future Scoop placeholders.
Run [`scripts/installer-lifecycle-smoke.ps1`](../../scripts/installer-lifecycle-smoke.ps1)
for machine-checkable documentation assertions. On `windows-latest` CI, pass
`-WindowsInstallLifecycle` to exercise the unsigned Windows ZIP install path.
Release CI additionally smokes the unsigned MSI. Authenticode signing remains
deferred under #66 / ADR 0003. See
[Clean-host install/uninstall evidence (unsigned)](#clean-host-installuninstall-evidence-unsigned)
for the manual checklist and CI artifact path.

### Install scripts (Linux / macOS / Windows)

Checksum-verified `sl-viewer` install from GitHub Releases:

```bash
# Linux / macOS → ~/.local/bin/sl-viewer
curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
```

```powershell
# Windows → %LOCALAPPDATA%\Programs\SessionLedger\sl-viewer.exe
irm https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.ps1 | iex
```

Set `SL_VERSION=v0.1.0` to pin a release. On Unix, `SL_INSTALL_DIR` changes the
destination; on Windows it defaults under LocalAppData. Review the script before
piping it to a shell. These scripts do not enable automatic updates.

Homebrew and winget packaging templates are in-repo
([`packaging/homebrew/sessionledger.rb`](../../packaging/homebrew/sessionledger.rb),
[`packaging/winget/`](../../packaging/winget/)) and are **not** a live tap or
winget listing. Fill digests with
[`scripts/fill-packaging-checksums.ps1`](../../scripts/fill-packaging-checksums.ps1),
then follow the publish-readiness checklist in
[`brew-winget-publish.md`](brew-winget-publish.md) (SelfCheck:
`pwsh ./scripts/brew-winget-publish-check.ps1 -SelfCheck`). Live tap and
`microsoft/winget-pkgs` merge remain **unpaid**. MSI/PKG work stays under
`packaging/windows` and `packaging/macos` when those lanes are active —
portable curl/irm install does not replace them.

### Traditional Linux systemd service

For source installs of the daemon on a Linux host, install the sample unit from
[`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service).
It uses default `SL_*` values in the unit and an optional override file at
`/etc/sessionledger/sessionledger-daemon.env`:

```ini
SL_WATCH_DIR=/var/lib/sessionledger/sessions
SL_OUT_DIR=/var/lib/sessionledger/out
SL_HTTP_BIND=127.0.0.1:8080
SL_LOG_FORMAT=json
SL_INGEST_MAX_BODY_BYTES=1048576
SL_INGEST_MAX_CONCURRENCY=8
```

Example install flow:

```bash
cargo install --path crates/sl-daemon --locked
sudo install -m 0755 "$(command -v sl-daemon)" /usr/local/bin/sl-daemon
sudo useradd --system --home-dir /var/lib/sessionledger --shell /usr/sbin/nologin sessionledger
sudo install -d -o sessionledger -g sessionledger /var/lib/sessionledger/sessions /var/lib/sessionledger/out
sudo install -d /etc/sessionledger /etc/systemd/system
sudo install -m 0644 packaging/systemd/sessionledger-daemon.service /etc/systemd/system/sessionledger-daemon.service
sudo systemctl daemon-reload
sudo systemctl enable --now sessionledger-daemon
```

Create the `sessionledger` user/group before enabling the unit, or edit
`User=` / `Group=` for your host policy. The unit assumes the `sl-daemon`
binary is available at `/usr/local/bin/sl-daemon`; adjust `ExecStart=` if Cargo
installs it elsewhere. The service is configured with `Restart=on-failure`.

### Traditional server TLS reverse proxy (Caddy / nginx)

Keep `SL_HTTP_BIND=127.0.0.1:8080` on the systemd unit so the daemon stays on
loopback. Terminate TLS at the edge with either sample config:

| Proxy | Sample config                                                                    | Notes                                                                                                   |
| ----- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Caddy | [`packaging/caddy/Caddyfile`](../../packaging/caddy/Caddyfile)                   | Automatic HTTPS via ACME when DNS points at the host; set `SESSIONLEDGER_HOST` or edit the site address |
| nginx | [`packaging/nginx/sessionledger.conf`](../../packaging/nginx/sessionledger.conf) | HTTP→HTTPS redirect + `proxy_pass` to `127.0.0.1:8080`; supply your own cert paths                      |

Typical order: install and enable `sessionledger-daemon`, then install the
chosen proxy config and reload Caddy/nginx. Do not bind the daemon publicly
when the reverse proxy owns `:443`.

---

## Uninstall / cleanliness

The installable Windows ZIP registers `Uninstall.ps1` in Windows Installed Apps;
it removes the application and shortcut but deliberately preserves user data.
The unsigned WiX MSI uninstalls via `msiexec /x` (or Installed Apps) and likewise
preserves user data. For portable and source installations, use manual cleanup:

1. **Stop processes** — `make dev-down` or kill `sl-daemon` / `sl-viewer`.
2. **Remove binaries** — delete extracted Release folders, `packaging/dist/`,
   and any copied `.app` / `.exe`.
3. **Remove data** — delete the data root you configured:

```bash
# Local compose default
rm -rf ./.sl-data

# If you used a custom root
rm -rf "$SL_DATA_DIR"

# Common CLI outs (only if you used these paths)
rm -rf ./okf-out ./sessions
```

4. **macOS quarantine leftovers** — if you copied an `.app` into
   `/Applications`, remove that copy as well.
5. **Container volumes** — `podman volume rm …` / `docker volume rm …` for any
   named `sl-data` / out volumes you created.

Do **not** leave orphaned `.sl-data` trees in clone roots after experiments;
prefer a single `SL_DATA_DIR` outside the repo when testing long-lived data.

---

## Release integrity signing (cosign)

On a `v*` tag, release CI publishes `SHA256SUMS`, then a dependent best-effort
job requests a short-lived GitHub OIDC identity and runs cosign keyless
`sign-blob`. When successful, the same Release gains
`SHA256SUMS.sigstore.json`, which contains the signature, certificate, and
transparency-log verification material.

The signing job has `id-token: write` and `contents: write`, but each external
operation fails soft. A cosign installation, OIDC permission, signing, or
upload failure emits a workflow notice while leaving the unsigned archives and
checksums available.

### Verify a Release

Download the archive, `SHA256SUMS`, and `SHA256SUMS.sigstore.json` into one
directory. Replace `<tag>` with the exact Release tag:

```bash
cosign verify-blob \
  --bundle SHA256SUMS.sigstore.json \
  --certificate-identity "https://github.com/KooshaPari/SessionLedger/.github/workflows/release.yml@refs/tags/<tag>" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  SHA256SUMS

sha256sum --check SHA256SUMS
```

On Windows, use `Get-FileHash -Algorithm SHA256` to compare an archive with its
entry in `SHA256SUMS` after cosign verifies the checksums file.

Cosign proves the checksums file was signed by this repository's tag workflow;
the checksum comparison then binds the downloaded archive to that signed file.

### Verify an OCI image (cosign)

When the `oci-image` job succeeds for a Release tag on the canonical
repository, pull by digest and verify the keyless signature **before deploying**.
Prefer the helper script (Windows / PowerShell 7+, also fine under `pwsh` on
Linux/macOS):

```powershell
pwsh ./scripts/oci-cosign-verify.ps1 -Tag <tag> -Digest sha256:<digest>
# Optional: require GitHub OCI attestation as well
pwsh ./scripts/oci-cosign-verify.ps1 -Tag <tag> -Digest sha256:<digest> -RequireAttestation
```

The script fails closed when cosign cannot verify the digest. That is the
verify-on-deploy gate. Release CI runs the same blocking `oci-cosign-verify`
step (`continue-on-error: false`) on every canonical `v*` tag after sign and
attest. Forks credential-gate OCI; missing GHCR push or signature still leaves
portable archives + `SHA256SUMS` valid. Use `-AllowUnsigned` only for dry-runs
(`pwsh ./scripts/oci-cosign-verify.ps1 -SelfCheck` exercises the dry-run path).

Manual equivalent (replace `<tag>` and `<digest>`):

```bash
IMAGE=ghcr.io/kooshapari/sl-daemon
TAG=<tag>

digest="$(crane digest "${IMAGE}:${TAG}")"
# or: digest="$(cosign triangulate "${IMAGE}:${TAG}" | sed 's/.*@//')"

cosign verify \
  --certificate-identity "https://github.com/KooshaPari/SessionLedger/.github/workflows/release.yml@refs/tags/${TAG}" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  "${IMAGE}@${digest}"

gh attestation verify "oci://${IMAGE}@${digest}" \
  --repo KooshaPari/SessionLedger
```

If cosign or `gh attestation verify` reports no signature/attestation, treat
OCI provenance as unavailable for that tag and either rebuild locally from
`crates/sl-daemon/Containerfile` or fall back to the portable `sl-daemon`
archive path above. Do not treat a missing OCI signature as a successful
verify-on-deploy check. A protected GitHub Environment for releases remains
unpaid — see the [environment isolation checklist](hermetic-builds.md#environment-isolation-checklist-slsa-l3-gaps).

### Verify GitHub build provenance

Install and authenticate [GitHub CLI](https://cli.github.com/), then download
the archive you intend to run. Verify that GitHub's attestation store contains
provenance issued by this repository:

```bash
gh attestation verify \
  sl-viewer-<tag>-x86_64-unknown-linux-gnu.tar.gz \
  --repo KooshaPari/SessionLedger
```

Substitute the exact downloaded archive name on macOS or Windows. A successful
result verifies the artifact digest and its GitHub Actions provenance. It does
not replace the cosign + `SHA256SUMS` checks above, platform code signing, or
review of the source.

Inspect the attestation predicate for **materials metadata** that binds the build
to this repository at the Release tag commit. GitHub's SLSA v1 provenance lists
source inputs under `buildDefinition.resolvedDependencies` (older attestations
may use a top-level `materials` array). The subject block must name the archive
and carry a matching SHA-256 digest. See
[`reproducible-builds.md`](reproducible-builds.md#slsa-materials-metadata-partial-l3)
and the sample fixture at
[`docs/ops/fixtures/slsa-materials-contract.sample.json`](fixtures/slsa-materials-contract.sample.json).

Provenance is intentionally fail-soft during this rollout. If
`gh attestation verify` reports that no attestation exists, treat provenance as
unavailable for that Release and rely on cosign/checksum verification; do not
interpret the absence as a successful provenance check.

## Versioning & compatibility policy

SessionLedger release and data-surface versioning follow distinct rules:

| Surface                         | Policy                                                                                                                 | Source of truth                                                                                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Git tags / desktop binaries** | [SemVer](https://semver.org/) on `v*` tags (`v0.1.0` → version `0.1.0`)                                                | Root `Cargo.toml` `version` must match the tag body before tagging; [`CHANGELOG.md`](../../CHANGELOG.md) + [`versioning-policy.md`](versioning-policy.md) |
| **Release asset names**         | Tag-derived `VER` in CI (`sl-viewer-v<tag>-<target>`, `SessionLedger-<ver>-x64.msi`, `SessionLedger-<ver>-<arch>.pkg`) | [`.github/workflows/release.yml`](../../.github/workflows/release.yml) `derive version` step                                                              |
| **OKF export documents**        | `[major].[minor]` tuple with major-bump rejection rules                                                                | [`docs/reference/OKF-SPEC.md`](../reference/OKF-SPEC.md#13-versioning--compatibility)                                                                     |
| **SQLite schema**               | Forward-only migrations; consumers on older schema revisions upgrade via `sl-daemon` migrate                           | [`docs/ops/schema-migrations.md`](schema-migrations.md)                                                                                                   |

**Compatibility expectations for installers and archives:**

- Patch and minor SemVer releases should remain installable side-by-side only when
  documented (per-user MSI scope under `%LOCALAPPDATA%`; portable ZIP extracts are
  user-chosen paths). Major bumps may change default data locations or CLI contracts —
  read `CHANGELOG.md` before upgrading production data dirs.
- OKF major version mismatches are a hard reject at parse time; minor bumps are
  accepted with warnings per OKF-SPEC §13.
- Release CI does not auto-migrate user databases; run explicit migrate commands
  after upgrading `sl-daemon`.

Pin a specific desktop build with `SL_VERSION=v0.1.0` in
[`scripts/install.sh`](../../scripts/install.sh) or download the matching GitHub
Release assets for that tag.

## Serverless / edge deploy — NOT APPLICABLE

SessionLedger does **not** target Cloudflare Workers, Vercel, Netlify Edge, or
similar serverless/edge runtimes. Local daemon + desktop viewer scope wins over
an edge isolate data plane.

Decision record: [`docs/adr/0005-no-serverless-edge.md`](../adr/0005-no-serverless-edge.md).
Hermetic proof: `pwsh ./scripts/edge-deploy-scope-check.ps1 -SelfCheck`.

Absence of `wrangler.toml` / `vercel.json` is intentional.

## Platform code-signing & notarization — DEFERRED

See [`docs/adr/0003-platform-code-signing.md`](../adr/0003-platform-code-signing.md)
for the accepted deferral decision, portable trust model, and reconsider triggers.
Signing readiness checklist (unsigned MSI/PKG matrix, unpaid credential gates,
CI prerequisites without secret claims):
[`docs/ops/signing-readiness.md`](signing-readiness.md).

Release CI ships **unsigned binaries, MSI/PKG installers, and `.app` bundles**.
The following platform trust paths remain deferred under #66:

- Apple Developer ID signing, `notarytool` notarization, and stapling
- Windows Authenticode (`signtool`) for `sl-viewer.exe` and MSI artifacts

### macOS Gatekeeper notes (unsigned builds)

Until notarization lands, Gatekeeper will treat downloaded builds as untrusted:

| Symptom                                                                    | Mitigation (dev / internal only)                                          |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| “App can’t be opened because Apple cannot check it for malicious software” | System Settings → Privacy & Security → Open Anyway; or right-click → Open |
| Quarantine attribute on download                                           | `xattr -dr com.apple.quarantine /path/to/SessionLedger.app`               |
| `spctl --assess` fails                                                     | Expected for unsigned artifacts                                           |

Do **not** instruct end users to disable Gatekeeper globally. Prefer waiting for
signed+notarized Releases, or build from source (`cargo build -p sl-viewer`).

### Windows SmartScreen

Unsigned `sl-viewer.exe` from GitHub Releases may show SmartScreen warnings.
“More info → Run anyway” is acceptable for internal testing; Authenticode is
the production path (deferred).

---

## Related

- [`packaging/README.md`](../../packaging/README.md) — local Make targets
- [`packaging/channels.md`](../../packaging/channels.md) — install channel status
- [`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service) — traditional Linux service unit
- [`packaging/caddy/Caddyfile`](../../packaging/caddy/Caddyfile) — TLS reverse proxy (Caddy)
- [`packaging/nginx/sessionledger.conf`](../../packaging/nginx/sessionledger.conf) — TLS reverse proxy (nginx)
- [`runbook.md`](runbook.md) — `make dev`, health probes
- [`observability.md`](observability.md) — `/healthz`, `/readyz`, metrics
- [`SECURITY.md`](../../SECURITY.md) — supply chain / SBOM
- Issue [#66](https://github.com/KooshaPari/SessionLedger/issues/66) — signing + installers
