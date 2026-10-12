# Shared Integration Kit (`instinct/shared-integration-kit-20261012`)

A drop-in bundle of CI/CD and developer-experience plumbing that any repo can
adopt with a single shell command. Built once, reused everywhere.

## What's in here

| Component | Path | Purpose |
|-----------|------|---------|
| Reusable lint workflow | `.github/workflows-reusable/lint.yml` | `workflow_call`-able lint step that auto-detects Rust / Node / Python and runs the appropriate formatter + linter with `-D warnings`. |
| Reusable test workflow | `.github/workflows-reusable/test.yml` | `workflow_call`-able test runner with profile selection (`ci` / `dev`), coverage toggle, JUnit output, and nextest caching for Rust. |
| Reusable release workflow | `.github/workflows-reusable/release.yml` | `workflow_call`-able release step supporting release-please (Rust), cargo-release, and python-build. |
| Lefthook template | `tools/integration-kit/lefthook.yml` | Pre-commit (fmt + secrets + trailing-ws), commit-msg (conventional commit), pre-push (clippy / eslint / ruff). |
| MCP hooks template | `tools/integration-kit/mcp-hooks.json` | Hooks for jcode / codex / forge / claude_code that block destructive commands, auto-run lefthook after edits, and emit desktop notifications. |
| Install script | `tools/integration-kit/install.sh` | One-shot installer that copies the kit into another repo. |

## Install

```bash
# From a clone of this repo (or any path containing the kit files)
bash tools/integration-kit/install.sh --target /path/to/other-repo

# Or, install only specific components
bash tools/integration-kit/install.sh \
  --target /path/to/other-repo \
  --components workflows,lefthook

# Dry-run to preview changes
bash tools/integration-kit/install.sh --target /path/to/other-repo --dry-run

# Force overwrite existing files
bash tools/integration-kit/install.sh --target /path/to/other-repo --force
```

## Using the reusable workflows

After installing, the target repo can call any of the reusable workflows from
its own workflow files. Example for a Rust crate:

```yaml
# .github/workflows/ci.yml  (in the target repo)
name: CI
on: [push, pull_request]

jobs:
  lint:
    uses: KooshaPari/PhenoShared/.github/workflows-reusable/lint.yml@instinct-shared-integration-kit
  test:
    uses: KooshaPari/PhenoShared/.github/workflows-reusable/test.yml@instinct-shared-integration-kit
    with:
      coverage: true
  release:
    if: startsWith(github.ref, 'refs/tags/')
    uses: KooshaPari/PhenoShared/.github/workflows-reusable/release.yml@instinct-shared-integration-kit
    secrets:
      RELEASE_PLEASE_TOKEN: ${{ secrets.RELEASE_PLEASE_TOKEN }}
```

Pin to a commit SHA or release tag in production to avoid surprises from
workflow drift.

## Components in detail

### `lint.yml`

Detects the primary language via the presence of `Cargo.toml`, `package.json`,
or `pyproject.toml`. Runs:

- **Rust**: `cargo fmt --all -- --check` + `cargo clippy --workspace --all-targets -- -D warnings`
- **Node**: `npm run lint --if-present` (only if a `lint` script exists)
- **Python**: `ruff check .` (auto-installs ruff if missing)

### `test.yml`

- **Rust**: `cargo nextest run --workspace --profile ci --retries 2 --test-threads=12`
  with optional `cargo llvm-cov` coverage (lcov.info) and JUnit upload.
- **Node**: `npm test --if-present`
- **Python**: `pytest --junitxml=reports/junit.xml` with auto-installed pytest + pytest-cov

### `release.yml`

Three modes via `release-tool` input:

- **release-please** (default for Rust) — opens/updates release PRs
- **cargo-release** — runs `cargo release` with token from `CARGO_REGISTRY_TOKEN` secret
- **python-build** — builds wheel + sdist, uploads to PyPI via `PYPI_TOKEN`

### `lefthook.yml`

Three hooks:

- `pre-commit`: parallel fmt (lang-detected), gitleaks scan, trailing-whitespace check
- `commit-msg`: warns on non-conventional commit titles (does not fail)
- `pre-push`: clippy / eslint / ruff at workspace level

Install lefthook with: `lefthook install` (one-time per repo).

### `mcp-hooks.json`

Drop this into your harness config directory. Each harness uses a different
schema/location:

- **jcode**: `~/.jcode/hooks.json` (use as-is)
- **codex**: `~/.codex/hooks.toml` (convert JSON → TOML)
- **forge**: `~/.forge/hooks.yaml` (convert JSON → YAML)
- **Claude Code**: merge into `~/.claude/settings.json` under the `hooks` key

The hooks block destructive git/gh commands (`gh repo delete`, `git push --force`,
`git reset --hard`), log edit operations, run lefthook after edits, and emit
desktop notifications on harness events.

## Test on a scratch repo

```bash
# Dry-run against a real repo
bash tools/integration-kit/install.sh --target ~/CodeProjects/Phenotype/repos/phenotype-registry --dry-run

# Actual install (only the workflows component, to minimize footprint)
bash tools/integration-kit/install.sh --target ~/CodeProjects/Phenotype/repos/phenotype-registry --components workflows
```

The post-install verification block prints ✓ / ✗ for each expected file.

## License

Same as the parent PhenoShared repo (operator-confirmed dual MIT/Apache).

## Author

`[Instinct] Authored by agent` — assembled by jcode on branch
`instinct/shared-integration-kit-20261012`. Not human-reviewed; treat as a
starting point and adjust the workflows / hook commands for your repo's
specific needs.