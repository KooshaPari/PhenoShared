# Packaging, Publishing & Deployment Prompt

Use this prompt with any AI coding agent to add system installers, one-liner installs, and release automation to a repository.

---

## Prompt

```
Add a complete packaging, publishing, and deployment pipeline to this repo. I need:

1. **System installers** for all platforms:
   - macOS: .app bundle, .dmg, .pkg installer
   - Windows: .msi installer, .nsis (.exe)
   - Linux: .deb (Debian/Ubuntu), .rpm (Fedora/RHEL), .AppImage

2. **Package manager distribution**:
   - Homebrew tap (macOS/Linux)
   - Winget package (Windows)
   - Snap package (Linux)
   - npm/pip/cargo package (if applicable to the language)

3. **One-liner install script** (`install.sh`):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/{owner}/{repo}/main/install.sh | sh
   ```
   - Auto-detect platform (os + arch)
   - Auto-detect latest version from GitHub API
   - Try native package manager first (brew, dpkg, rpm)
   - Fall back to binary tar.gz download
   - Color output, error handling, PATH hints

4. **CI/CD release workflow** (GitHub Actions):
   - Trigger on tag push (v*)
   - Build matrix: macOS (arm64, x86_64), Windows (x86_64), Linux (amd64, arm64)
   - Produce all installer artifacts
   - Upload to GitHub Release
   - Update install.sh with latest version

5. **Release configuration**:
   - For Go projects: goreleaser.yml with nfpms (deb/rpm), brews, winget, snapcraft
   - For Rust/Tauri projects: tauri-action with bundle targets
   - For Node.js projects: pkg or nexe for standalone binaries

For each artifact, verify it compiles and the workflow YAML is valid. Update INSTALL.md and README.md with install instructions for every method.
```

---

## Variants

### Go project (CLI tool)
```
Add packaging and release automation for this Go CLI tool:
- goreleaser.yml with builds for linux/darwin/windows × amd64/arm64
- nfpms section for .deb and .rpm packages
- Homebrew tap formula
- install.sh one-liner
- GitHub Actions release workflow using goreleaser-action
```

### Rust/Tauri desktop app
```
Add packaging and release automation for this Tauri desktop app:
- release-tauri.yml workflow building .app, .dmg, .pkg (macOS), .msi, .nsis (Windows), .deb, .rpm, .AppImage (Linux)
- TAURI_SIGNING_PRIVATE_KEY for update signatures
- install.sh that downloads the platform-specific installer
```

### Node.js/Python package
```
Add packaging and release automation:
- npm publish (or pip publish) on tag push
- Standalone binaries via pkg (Node) or PyInstaller (Python)
- Docker image build and push to GHCR
- install.sh one-liner for binary install
```

### Docker-first
```
Add packaging and release automation:
- Multi-platform Docker build (linux/amd64, linux/arm64)
- Push to GitHub Container Registry (ghcr.io)
- docker-compose.yml for production
- install.sh that runs docker pull + docker compose up
```
