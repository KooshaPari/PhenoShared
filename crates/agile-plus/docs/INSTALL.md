# Installing AgilePlus

AgilePlus ships three distribution channels plus an optional Windows Start Menu shortcut.

| Channel | Best for | Command / location |
|---------|----------|-------------------|
| **cargo install** | Developers building from source | `cargo install --path crates/agileplus-cli --locked` |
| **Prebuilt binaries** | Quick install without a Rust toolchain | [GitHub Releases](https://github.com/KooshaPari/AgilePlus/releases) |
| **crates.io** | Rust projects adding the CLI as a dependency | `cargo install agileplus-cli --locked` |
| **Start Menu** (Windows) | Desktop launcher under Phenotype-Apps | `packaging/start-menu.ps1` |

## Prerequisites

- **Rust** (nightly toolchain recommended): [rustup.rs](https://rustup.rs/)
- **Git** 2.x
- **protoc** 28.x (only when building from source in this monorepo)

## 1. Install from source (`cargo install`)

From a clone of this repository:

```bash
git clone https://github.com/KooshaPari/AgilePlus.git
cd AgilePlus
cargo install --path crates/agileplus-cli --locked
agileplus --version
```

The installed binary lands in `~/.cargo/bin/agileplus` (or `%USERPROFILE%\.cargo\bin\agileplus.exe` on Windows).

## 2. Prebuilt binaries (GitHub Releases)

Tagged releases (`v*`) publish matrix-built archives for Linux, macOS (x86_64 + Apple Silicon), and Windows.

1. Open [Releases](https://github.com/KooshaPari/AgilePlus/releases).
2. Download the archive for your platform, for example:
   - `agileplus-<version>-agileplus-linux-x86_64.tar.gz`
   - `agileplus-<version>-agileplus-macos-aarch64.tar.gz`
   - `agileplus-<version>-agileplus-windows-x86_64.zip`
3. Extract and place `agileplus` (or `agileplus.exe`) on your `PATH`.

Nightly/hourly CI artifacts are also uploaded by `.github/workflows/nightly.yml` (retention: 7 days).

## 3. Install from crates.io

Once published:

```bash
cargo install agileplus-cli --locked
agileplus --version
```

Library crates (`agileplus-domain`, `agileplus-sqlite`, etc.) are published alongside the CLI on each `v*` tag via `.github/workflows/agileplus-release.yml`.

**Repository secret:** `CARGO_REGISTRY_TOKEN` (crates.io API token).

## 4. Windows Start Menu shortcut (Phenotype-Apps)

After installing the binary (any channel above):

```powershell
# Default: ~/.cargo/bin/agileplus.exe + packaging/agileplus.ico
.\packaging\start-menu.ps1

# Custom binary or icon
.\packaging\start-menu.ps1 `
  -BinaryPath "C:\Tools\agileplus.exe" `
  -IconPath ".\packaging\agileplus.ico"
```

This creates:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Phenotype-Apps\AgilePlus.lnk
```

Place a project icon at `packaging/agileplus.ico` (referenced by the script; optional but recommended).

## Verify installation

```bash
agileplus --version
agileplus --help
```

## Quick project bootstrap

No `agileplus init` command exists. In a git repo, create or revise a feature spec with the SDD CLI (interactive interview, or `--from-file`):

```bash
cd my-project
agileplus specify --feature my-feature
# or: agileplus specify --feature my-feature --from-file ./draft-spec.md
agileplus list
```

Platform health is **not** a top-level `agileplus status` (that is not a product feature command). Use:

```bash
agileplus platform status
```

On this machine, the PATH `agileplus` wrapper routes `platform status` to `.agileplus/platform-status.sh` (real HTTP probes). Neo4j is optional — status does not require it.

## CI release system

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/agileplus-release.yml` | Tag `v*` | Matrix binaries + GitHub Release + crates.io publish |
| `.github/workflows/nightly.yml` | Hourly `0 * * * *` + daily `0 6 * * *` | Build, test, upload nightly artifacts |
| `.github/workflows/e2e.yml` | PR/push (CLI paths) | Installed CLI specify / list round-trip (no `init` / top-level `status`) |

E2E harnesses:

- `scripts/e2e.sh` — shell round-trip (used in CI)
- `tests/e2e/roundtrip.rs` — Rust integration test (`AGILEPLUS_BIN` env var)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `agileplus: command not found` | Add `~/.cargo/bin` to `PATH` |
| Build fails on `protoc` | Install protobuf compiler 28.x |
| crates.io publish fails in CI | Ensure `CARGO_REGISTRY_TOKEN` secret is set |
| Start Menu shortcut has no icon | Add `packaging/agileplus.ico` or pass `-IconPath` |
