# DevOps, CI/CD & Repository Hygiene Prompt

Use this prompt with any AI coding agent to bring a repo to production-grade DevOps state.

---

## Prompt

```
Audit and fix this repository's DevOps, CI/CD, and release infrastructure. Address ALL of the following:

## 0. Fork Sync Check
- Check if this repo is a fork. If yes: `git remote -v` to find upstream
- Run `git fetch upstream` and report how far behind main we are
- Create a sync PR if behind, or report status if current

## 1. Branch Hygiene
- List all remote branches: `git branch -r`
- Identify stale branches (no commit in 30+ days, or merged into main)
- List branches with open PRs vs branches with no PR
- Report: total branches, stale count, merged-but-not-deleted count
- Delete merged remote branches: `git push origin --delete <branch>`
- Do NOT delete branches with open PRs or recent activity (<30 days)

## 2. GitHub Actions Release CI (CRITICAL)
If the repo produces installable artifacts, it MUST have a release workflow:

### For Go CLI projects:
```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: stable
      - uses: goreleaser/goreleaser-action@v6
        with:
          version: '~> v2'
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### For Rust/Tauri desktop apps:
```yaml
# .github/workflows/release-tauri.yml
name: Release Tauri
on:
  push:
    tags: ['v*']
jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  build-windows:
    runs-on: windows-latest
    # ... similar steps
  build-linux:
    runs-on: ubuntu-22.04
    # ... similar steps with apt-get install
```

### For Node.js packages:
```yaml
# .github/workflows/release-npm.yml
name: Release NPM
on:
  push:
    tags: ['v*']
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### For Docker images:
```yaml
# .github/workflows/release-docker.yml
name: Release Docker
on:
  push:
    tags: ['v*']
jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          platforms: linux/amd64,linux/arm64
```

## 3. Install Scripts (curl one-liner)
Create `install.sh` at repo root:
```bash
#!/usr/bin/env bash
set -euo pipefail
GITHUB_REPO="owner/repo"
BINARY_NAME="binary"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
# Auto-detect platform, download from GitHub releases, install
# Support: macOS (arm64/x86_64), Linux (amd64/arm64), Windows (WSL)
# Methods: Homebrew tap, .deb, .rpm, binary tar.gz, Docker
```

Update README with install methods:
```markdown
## Install

### Binary (all platforms)
curl -fsSL https://raw.githubusercontent.com/{owner}/{repo}/main/install.sh | sh

### Homebrew (macOS/Linux)
brew install {owner}/{tap}/{formula}

### Docker
docker pull ghcr.io/{owner}/{repo}:latest

### npm (Node.js projects)
npm install -g {package}

### Go (Go projects)
go install github.com/{owner}/{repo}/cmd/{binary}@latest
```

## 4. GitHub Package Registry
If the project is a library/package, publish to the appropriate registry:
- Go: proxy.golang.org (auto on tag push if module path matches)
- npm: npmjs.com
- PyPI: pypi.org (via twine or trusted publishers)
- Docker: ghcr.io (via Docker workflow above)
- Cargo: crates.io (via cargo publish in release workflow)

## 5. Dependabot / Renovate Configuration
Verify `.github/dependabot.yml` or `renovate.json` exists and covers:
- Cargo dependencies (weekly)
- npm dependencies (weekly)
- GitHub Actions (weekly)
- Docker base images (weekly)

## 6. Branch Protection
Verify on GitHub (requires gh CLI or API):
- Main branch requires PR review (1+ reviewers)
- Status checks must pass before merge
- No force push to main
- Admin overrides disabled

## 7. Release Process Documentation
Update or create `docs/RELEASE.md`:
1. How to create a release (tag + push)
2. What CI builds automatically
3. Where artifacts appear (GH Releases, registries)
4. How to verify installation works
5. Rollback procedure

## 8. Cleanup Orphaned CI Workflows
- Check `.github/workflows/` for workflows that reference deleted files
- Check for duplicate/overlapping workflows
- Remove or consolidate: if you have both `ci.yml` and `test.yml` doing the same thing, merge them

For each item, implement the fix (don't just report). Commit changes.
```

---

## Portfolio-Specific Notes

### Repos tracked locally:
```
Phenotype/repos/nanovms/          Go CLI (NanoVMS)
Phenotype/repos/wt-byteport-tauri-20260911/   Rust/Tauri (BytePort)
```

### Known gaps (from audit):
1. **NanoVMS**: Has `.goreleaser.yml` but NO `.github/workflows/release.yml` that runs it
2. **BytePort**: Has `release-tauri.yml` (just created locally) but NOT pushed to remote. Remote has 2,500+ CI runs but zero release builds
3. **Both**: Tons of stale/unmerged remote branches (NanoVMS: 19+ unmerged, BytePort: 20+ unmerged)
4. **BytePort**: Is a fork of upstream Tauri template — may be behind

### Branch cleanup candidates:
```
NanoVMS:  agileplus-local/* (16 branches), dependabot/*, codex/*
BytePort: origin/codex/* (17+ branches), origin/audit/*, origin/ci/*, origin/feat/*
```

### Run this prompt on both repos to achieve:
- Release CI that actually builds and publishes on tag push
- Branch cleanup (delete merged stale branches)
- Fork sync if behind upstream
- Install scripts pushed to remote
- ghcr.io Docker images if applicable
- Updated README with all install paths
