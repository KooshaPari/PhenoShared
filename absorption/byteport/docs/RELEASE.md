# BytePort Desktop Release Process

## Overview

BytePort uses [Tauri](https://tauri.app) to build cross-platform desktop installers.
Releases are automated via GitHub Actions (`.github/workflows/release-tauri.yml`).

## Release Flow

### 1. Tag a Release

```bash
git tag v0.1.0
git push origin v0.1.0
```

Pushing a `v*` tag triggers the `Release Tauri` workflow, which builds installers on
all three platforms in parallel:

| Platform | Runner | Artifacts |
|----------|--------|-----------|
| macOS    | `macos-latest` | `.app`, `.dmg`, `.pkg` (universal binary: aarch64 + x86_64) |
| Windows  | `windows-latest` | `.msi`, `.nsis` (.exe installer) |
| Linux    | `ubuntu-22.04` | `.deb`, `.rpm`, `.AppImage` |

### 2. Workflow Steps

1. **Checkout** and set up Node 20 + Rust stable.
2. **Install system deps** (platform-specific: Homebrew on macOS, apt on Linux).
3. **Install frontend deps** (`npm ci` in `frontend/web`).
4. **Build Tauri app** via `tauri-apps/tauri-action@v0`.
5. **Upload artifacts** to a GitHub Release via `softprops/action-gh-release@v2`.
6. **Update `install.sh`** with the latest tag (auto-committed by the bot).

### 3. Signing (Windows)

Windows builds use Tauri's built-in signing. Set these repository secrets:

- `TAURI_SIGNING_PRIVATE_KEY` -- path to or contents of the signing key
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` -- passphrase for the key

macOS builds are **unsigned** by default. To enable code signing, add Apple Developer
secrets and update the workflow accordingly.

### 4. Local Install Script

Users can install via the one-liner curl script:

```bash
curl -fsSL https://raw.githubusercontent.com/KooshaPari/BytePort/main/install.sh | bash
```

The script auto-detects platform and downloads the correct installer from the latest
GitHub Release.

### 5. Manual Trigger

You can also trigger a release build manually from the Actions tab using
`workflow_dispatch`, providing a tag name as input.

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** -- breaking API or data-format changes
- **MINOR** -- new features, backward-compatible
- **PATCH** -- bug fixes

Update the version in `frontend/web/src-tauri/tauri.conf.json` before tagging:

```json
{
  "version": "0.2.0"
}
```

## Secrets Required

| Secret | Purpose | Required |
|--------|---------|----------|
| `GITHUB_TOKEN` | Upload release artifacts | Auto-provided |
| `TAURI_SIGNING_PRIVATE_KEY` | Windows installer signing | Windows builds |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Signing key passphrase | Windows builds |

## Troubleshooting

- **Build fails on macOS**: Ensure Xcode CLI tools are installed (`xcode-select --install`).
- **Linux missing deps**: The workflow installs `libwebkit2gtk-4.1-dev` and `libgtk-4-dev` automatically.
- **Tag not triggering**: Ensure the tag matches the `v*` pattern (e.g., `v0.1.0`, not `0.1.0`).
