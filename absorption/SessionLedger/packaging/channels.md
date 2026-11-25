# SessionLedger Install Channels

This page tracks the supported, partial, and future ways to install
SessionLedger artifacts. It complements the local packaging targets in
[`packaging/README.md`](README.md) and the operational distribution guide in
[`docs/ops/distribution.md`](../docs/ops/distribution.md).

## Channel Status

| Channel                    | Status                                    | Artifact / command                                                                                                                                                                                                                                                       |
| -------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cargo from source          | **Active for developers**                 | `cargo install --path crates/sl-daemon --locked`; or `cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon`                                                                                                                  |
| GitHub Releases archives   | **Active**                                | Tagged `v*` releases publish `sl-viewer-<tag>-<target>.tar.gz` / `.zip`, checksums, SBOM, and best-effort provenance                                                                                                                                                     |
| curl / irm install scripts | **Active**                                | `scripts/install.sh` (Linux/macOS) and `scripts/install.ps1` (Windows) install checksum-verified `sl-viewer` archives from GitHub Releases                                                                                                                               |
| Homebrew formula           | **Manifests in-repo (not a live tap)**    | Template at [`packaging/homebrew/sessionledger.rb`](homebrew/sessionledger.rb); fill digests with [`scripts/fill-packaging-checksums.ps1`](../scripts/fill-packaging-checksums.ps1), then follow [`docs/ops/brew-winget-publish.md`](../docs/ops/brew-winget-publish.md) |
| winget manifests           | **Manifests in-repo (not on winget yet)** | Templates under [`packaging/winget/`](winget/); same fill script + publish doc before opening a `microsoft/winget-pkgs` PR                                                                                                                                               |
| Windows installable ZIP    | **Partial, CI-smoked**                    | Release ZIP is smoke-tested; local package adds PowerShell install/uninstall scripts                                                                                                                                                                                     |
| Linux AppImage / `.deb`    | **Partial local scaffolds**               | Developer-only scripts under `packaging/linux/`; not release channels                                                                                                                                                                                                    |
| Scoop bucket               | **Future placeholder**                    | No manifest, bucket, or update automation exists yet                                                                                                                                                                                                                     |
| crates.io                  | **Future placeholder**                    | No crates are published to crates.io yet                                                                                                                                                                                                                                 |

Native MSI / PKG installer lanes (when concurrent) live under `packaging/windows`
and `packaging/macos` — see [`packaging/README.md`](README.md). The curl/irm
scripts and brew/winget templates target portable GitHub Release archives and
do not replace those installer formats.

## curl / irm install scripts

Linux / macOS (checksum-verified `sl-viewer`):

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.ps1 | iex
```

Set `SL_VERSION=v0.1.0` to pin a release. On Unix, `SL_INSTALL_DIR` overrides
the destination (default `~/.local/bin`). On Windows, `SL_INSTALL_DIR` defaults
to `%LOCALAPPDATA%\Programs\SessionLedger`. Review the script before piping it
to a shell.

## Cargo Install Path

The daemon/CLI crate can be installed from a checkout or directly from GitHub:

```bash
cargo install --path crates/sl-daemon --locked
# or, without a local clone:
cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon
```

This installs the `sl-daemon` binary into Cargo's configured bin directory
(`~/.cargo/bin` by default). Start the long-running daemon with native local
session auto-discovery:

```bash
sl-daemon serve \
  --out "$HOME/.local/share/sessionledger/out" \
  --http-bind 127.0.0.1:8080
```

Add `--watch <path>` only when overriding discovery for a custom transcript
root.

`cargo install` is a developer/source channel. It does not provide automatic
updates, package-manager metadata, desktop integration, or platform signing.

## GitHub Releases Archives

Tagged releases (`v*`) publish portable `sl-viewer` archives:

```text
sl-viewer-<tag>-x86_64-unknown-linux-gnu.tar.gz
sl-viewer-<tag>-x86_64-apple-darwin.tar.gz
sl-viewer-<tag>-aarch64-apple-darwin.tar.gz
sl-viewer-<tag>-x86_64-pc-windows-msvc.zip
```

Each Release also publishes `SHA256SUMS`, `session-ledger.cdx.json`, and a
best-effort `SHA256SUMS.sigstore.json`. On the same tag, canonical CI
unconditionally builds/pushes `ghcr.io/kooshapari/sl-daemon`, keyless-cosign
signs it, and blocking-verifies with `oci-cosign-verify` (`continue-on-error:
false`); forks credential-gate OCI. Verify archives with
the checksum / cosign flow in
[`docs/ops/distribution.md`](../docs/ops/distribution.md); for OCI deploy checks
run [`scripts/oci-cosign-verify.ps1`](../scripts/oci-cosign-verify.ps1).

GitHub Releases are the current user-facing archive channel for `sl-viewer`.
The daemon is also available as a best-effort GHCR image, from source
(`cargo install --git` / `--path`), or via local process-compose / Containerfile.

## Homebrew And winget (templates only — not live)

These channels are **not** published yet. Do not advertise
`brew install …` or `winget install KooshaPari.SessionLedger` as working
install paths until a tap / winget-pkgs merge exists.

1. Fill digests from a Release `SHA256SUMS`:

   ```powershell
   pwsh ./scripts/fill-packaging-checksums.ps1 -Sha256Sums ./SHA256SUMS -Version v0.1.0
   ```

2. Follow the external publish checklist (live tap / winget-pkgs remain
   **unpaid** until those gates flip):
   [`docs/ops/brew-winget-publish.md`](../docs/ops/brew-winget-publish.md).
3. Hermetic SelfCheck (no brew/winget/network):

   ```powershell
   pwsh ./scripts/brew-winget-publish-check.ps1 -SelfCheck
   ```

- Homebrew template: [`packaging/homebrew/sessionledger.rb`](homebrew/sessionledger.rb)
  (`sl-viewer` from Release tarballs; daemon via Cargo in caveats).
- winget templates: [`packaging/winget/`](winget/) (portable Windows ZIP).

Scoop remains an explicit placeholder only.
