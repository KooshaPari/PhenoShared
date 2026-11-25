# SessionLedger Packaging

Build and package the `sl-viewer` desktop app for distribution. Full ops
guide (data dirs, uninstall, signing deferral, Windows matrix):
[`docs/ops/distribution.md`](../docs/ops/distribution.md).
Mobile presence is intentionally Soft / N-A for the current desktop-plus-daemon
scope; see [`docs/adr/0002-mobile-presence.md`](../docs/adr/0002-mobile-presence.md).
Install channel status is tracked in [`channels.md`](channels.md). A traditional
Linux service unit lives at
[`systemd/sessionledger-daemon.service`](systemd/sessionledger-daemon.service);
TLS edge samples are
[`caddy/Caddyfile`](caddy/Caddyfile) and
[`nginx/sessionledger.conf`](nginx/sessionledger.conf).

## Prerequisites

- Rust toolchain (rustup)
- For macOS: Xcode command line tools (`productbuild` for PKG)
- For Linux: standard build essentials; `appimagetool` for AppImage or
  `dpkg-deb` for the Debian package
- For Windows: PowerShell 5.1+ and the MSVC Rust target/toolchain; WiX v4
  (`dotnet tool install --global wix`) for MSI builds

## Usage

```sh
# macOS .app + .pkg (unsigned)
./packaging/macos/package-app.sh
./packaging/macos/package-pkg.sh

# Linux binary
make -C packaging package-linux

# Windows installable/portable ZIP (run on Windows)
make -C packaging package-windows
# Equivalent:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package-windows.ps1

# Windows MSI (unsigned; requires WiX v4 + layout from package-windows)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package-msi.ps1

# Linux installer candidates (also attached best-effort by release CI)
./packaging/linux/package-appimage.sh
./packaging/linux/package-deb.sh

# macOS + Linux (host-local Make scaffolds)
make -C packaging package-all
```

## Output (local)

| Platform | Output                                                                                           |
| -------- | ------------------------------------------------------------------------------------------------ |
| macOS    | `packaging/dist/SessionLedger.app`, `SessionLedger-<ver>[-arch].pkg`                             |
| Linux    | `packaging/dist/linux/SessionLedger`; optional `.deb` / AppImage                                 |
| Windows  | `packaging/dist/sl-viewer-v<version>-x86_64-pc-windows-msvc.zip` + `SessionLedger-<ver>-x64.msi` |

## Release matrix (GitHub Actions)

Tag push (`v*`) builds via [`.github/workflows/release.yml`](../.github/workflows/release.yml):

| Target                            | Artifacts                                                      | CI validation                                                            |
| --------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Linux `x86_64-unknown-linux-gnu`  | viewer + daemon `.tar.gz`; best-effort `.deb` + AppImage       | Download, extract, binary `--version`; optional installer presence check |
| macOS Intel `x86_64-apple-darwin` | viewer + daemon `.tar.gz`; unsigned `.pkg` + `.app.tar.gz`     | Build/archive                                                            |
| macOS ARM `aarch64-apple-darwin`  | viewer + daemon `.tar.gz`; unsigned `.pkg` + `.app.tar.gz`     | PKG expand smoke                                                         |
| Windows `x86_64-pc-windows-msvc`  | viewer + daemon `.zip`; unsigned `SessionLedger-<ver>-x64.msi` | ZIP `--version` + MSI silent install → `--version` → uninstall           |

## Clean-host checklist (unsigned)

Repeatable install → launch → uninstall evidence **without** Authenticode.
Full ops narrative: [`docs/ops/distribution.md`](../docs/ops/distribution.md#clean-host-installuninstall-evidence-unsigned).

### Windows portable ZIP (automated in PR CI)

PR CI job `clean-host-smoke-windows` on `windows-latest` runs:

```powershell
./scripts/installer-lifecycle-smoke.ps1 -WindowsInstallLifecycle `
  -EvidencePath packaging/dist/clean-host-evidence.json
```

### Windows MSI (automated in Release CI)

Release job `smoke-windows` silently installs the unsigned MSI, runs
`sl-viewer.exe --version`, then uninstalls. See
[`scripts/package-msi.md`](../scripts/package-msi.md).

### Linux / macOS (manual + Release PKG expand)

| Platform | Package                                           | Verify                         | Cleanup                                                    |
| -------- | ------------------------------------------------- | ------------------------------ | ---------------------------------------------------------- |
| Linux    | Release `.tar.gz` / best-effort `.deb` / AppImage | `./sl-viewer --version`        | Delete extract tree + configured data dirs                 |
| macOS    | Release `.pkg` / `.app.tar.gz`                    | expand PKG or open `.app` once | Remove test `.app`; Gatekeeper notes in distribution guide |

Signed MSI / Authenticode evidence is explicitly out of scope for this checklist.

## Installer status matrix

| Platform / format       | Status                             | Scope                                                                                        |
| ----------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------- |
| Windows installable ZIP | **Partial, CI-smoked**             | Release + PR clean-host portable install/uninstall                                           |
| Windows MSI (WiX v4)    | **Active (unsigned)**              | Release CI builds `SessionLedger-<ver>-x64.msi`; silent install smoke; Authenticode deferred |
| Linux AppImage          | **Active (unsigned, best-effort)** | Release CI attaches when `package-appimage.sh` succeeds                                      |
| Linux `.deb`            | **Active (unsigned, best-effort)** | Release CI attaches when `package-deb.sh` succeeds                                           |
| macOS `.app` / `.pkg`   | **Active (unsigned)**              | Release CI builds via `productbuild`; notarization deferred                                  |

Release CI publishes portable viewer and daemon archives, the unsigned Windows
MSI, unsigned macOS PKGs, and best-effort Linux installers. Platform-native
signing remains deferred under ADR 0003.
`scripts/installer-lifecycle-smoke.ps1` dry-runs scaffold and clean-host-doc
assertions on any host with PowerShell. On `windows-latest` CI the
`clean-host-smoke-windows` job runs `-WindowsInstallLifecycle` for the
unsigned portable ZIP path. Linux details are in
[`packaging/linux/README.md`](linux/README.md); macOS scripts are in
[`packaging/macos/`](macos/).

## Installer script draft (not published)

[`scripts/install.sh`](../scripts/install.sh) downloads the latest Linux/macOS
archive from GitHub Releases, verifies it against `SHA256SUMS`, and installs
`sl-viewer` to `~/.local/bin` by default. It is a repository draft, not a
published package-manager channel:

```sh
curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
```

Pin a release with `SL_VERSION=v0.1.0`; override the destination with
`SL_INSTALL_DIR=/desired/bin`. Review the script before piping it to a shell.

## Homebrew / winget templates (not live channels)

In-repo formula + winget YAML live under [`homebrew/`](homebrew/) and
[`winget/`](winget/). They are templates only — there is no published tap and
no `winget-pkgs` listing until unpaid gates in
[`docs/ops/brew-winget-publish.md`](../docs/ops/brew-winget-publish.md) flip.
Hermetic proof: `pwsh ./scripts/brew-winget-publish-check.ps1 -SelfCheck`.

After a `v*` Release, fill digests from that Release's `SHA256SUMS`:

```powershell
pwsh ./scripts/fill-packaging-checksums.ps1 -Sha256Sums ./SHA256SUMS -Version v0.1.0
```

Channel status: [`channels.md`](channels.md).

## Versioning (SemVer + compat)

- Release tags use `v*` SemVer (`v0.1.0`); CI strips the `v` for MSI/PKG file names
  (`SessionLedger-0.1.0-x64.msi`). Keep root `Cargo.toml` `version` aligned with
  the tag before pushing.
- OKF exports use a separate `[major].[minor]` policy — see
  [`docs/reference/OKF-SPEC.md`](../docs/reference/OKF-SPEC.md#13-versioning--compatibility).
- Full release/install compatibility notes:
  [`docs/ops/distribution.md`](../docs/ops/distribution.md#versioning--compatibility-policy).

## Notes

- Binaries are built with `cargo build --release`
- macOS bundle includes a minimal `Info.plist`
- **Platform code-signing / Apple notarization: DEFERRED** — see
  [`docs/ops/distribution.md`](../docs/ops/distribution.md#platform-code-signing--notarization--deferred)
  (Gatekeeper / SmartScreen notes for unsigned builds)
- Release CI publishes `SHA256SUMS` and attempts a best-effort GitHub OIDC
  cosign signature (`SHA256SUMS.sigstore.json`); signing failures do not block
  the Release. On every canonical `v*` tag, the GHCR `sl-daemon` OCI image is
  built, keyless-cosign signed, attested, and **unconditionally**
  release-blocking via `oci-cosign-verify` (`continue-on-error: false`); forks
  credential-gate OCI. See the
  [OCI cosign policy matrix](../docs/ops/distribution.md#oci-cosign-policy-matrix-unconditional-vs-credential-gated)
  and [cosign verification path](../docs/ops/distribution.md#release-integrity-signing-cosign).
  Deploy-time OCI gate:
  [`scripts/oci-cosign-verify.ps1`](../scripts/oci-cosign-verify.ps1)
  (`pwsh ./scripts/oci-cosign-verify.ps1 -SelfCheck` for policy anchors).
- Data root for local compose: `SL_DATA_DIR` (default `./.sl-data`); uninstall
  steps documented in the distribution guide
