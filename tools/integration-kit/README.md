# Shared Integration Kit (`instinct/shared-integration-kit-20261012`)

A drop-in bundle of CI/CD and developer-experience plumbing that any repo can
adopt with a single shell command. Built once, reused everywhere.

## What's in here

| Component | Path (source) | Path (after install) | Purpose |
|-----------|---------------|----------------------|---------|
| Reusable lint workflow | `.github/workflows/reusable-lint.yml` | `.github/workflows/reusable-lint.yml` | `workflow_call`-able lint step that auto-detects Rust / Node / Python inside the working-directory, runs `npm ci` / `npm install` before Node scripts, and runs the appropriate formatter + linter with `-D warnings`. |
| Reusable test workflow | `.github/workflows/reusable-test.yml` | `.github/workflows/reusable-test.yml` | `workflow_call`-able test runner with profile selection (`ci` / `dev`), coverage toggle (auto-installs `cargo-llvm-cov` when `coverage: true`), JUnit output, and nextest caching for Rust. |
| Reusable release workflow | `.github/workflows/reusable-release.yml` | `.github/workflows/reusable-release.yml` | `workflow_call`-able release step supporting `release-please` (Rust), `cargo-release`, and `python-build` (input is a plain string, validated at runtime; `choice` is unsupported in `workflow_call`). |
| Lefthook template | `tools/integration-kit/lefthook.yml` | `lefthook.yml` | Pre-commit (fmt + secrets + trailing-ws), commit-msg (conventional commit), pre-push (clippy / eslint / ruff). Failures propagate; no `\|\| true` swallowing. |
| MCP hooks template | `tools/integration-kit/mcp-hooks.json` | `.mcp-hooks.json` | Hooks for jcode / codex / forge / claude_code that block destructive commands, auto-run lefthook after edits, and emit desktop notifications. Uses `jq` to parse JSON-encoded `$CLAUDE_TOOL_INPUT`. |
| Install script | `tools/integration-kit/install.sh` | `tools/integration-kit/install.sh` | One-shot installer that copies the kit into another repo. `--dry-run` does not mkdir and does not verify; `--components` accepts whitespace and is normalized to lower-case. |

## Install

```bash
# From a clone of this repo (or any path containing the kit files)
bash tools/integration-kit/install.sh --target /path/to/other-repo

# Or, install only specific components
bash tools/integration-kit/install.sh \
  --target /path/to/other-repo \
  --components workflows,lefthook

# Dry-run to preview changes (no mkdir, no verification)
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
    uses: KooshaPari/PhenoShared/.github/workflows/reusable-lint.yml@<ref>
  test:
    uses: KooshaPari/PhenoShared/.github/workflows/reusable-test.yml@<ref>
    with:
      coverage: true
  release:
    if: startsWith(github.ref, 'refs/tags/')
    uses: KooshaPari/PhenoShared/.github/workflows/reusable-release.yml@<ref>
    secrets:
      RELEASE_PLEASE_TOKEN: ${{ secrets.RELEASE_PLEASE_TOKEN }}
```

Pin to a commit SHA or release tag in production to avoid surprises from
workflow drift. Replace `<ref>` with the target branch / tag / SHA.

> **Note on naming:** The reusable workflows use the `reusable-` prefix to
> avoid colliding with the host repo's own `lint.yml`, `test.yml`, and
> `release.yml` (if present). They live directly under `.github/workflows/`
> so GitHub picks them up as callable; their only trigger is `workflow_call`,
> so they will not run on push or pull_request by themselves.

## Components in detail

### `reusable-lint.yml`

Detects the primary language **inside the supplied `working-directory`** (not
at the repo root) by checking for `Cargo.toml`, `package.json`, or
`pyproject.toml`. Runs:

- **Rust**: `cargo fmt --all -- --check` + `cargo clippy --workspace --all-targets -- -D warnings`
- **Node**: `npm ci` / `yarn install --frozen-lockfile` / `pnpm install --frozen-lockfile` (lockfile-aware) → `npm run lint --if-present`
- **Python**: `ruff check .` (auto-installs ruff if missing)

### `reusable-test.yml`

- **Rust**: `cargo nextest run --workspace --profile <test-profile> --retries 2 --test-threads=12`
  with optional `cargo llvm-cov nextest` coverage (lcov.info) when `coverage: true`
  (auto-installs `cargo-llvm-cov`).
- **Node**: `npm ci` / `yarn install --frozen-lockfile` / `pnpm install --frozen-lockfile` → `npm test --if-present`
- **Python**: `pytest --junitxml=reports/junit.xml` with auto-installed pytest + pytest-cov

### `reusable-release.yml`

Three modes via the `release-tool` input (a plain string, validated at runtime
because `choice` is not supported in `workflow_call`):

- **release-please** (default for Rust) — opens/updates release PRs
- **cargo-release** — runs `cargo release --dry-run` then `cargo release` on tag push (token from `CARGO_REGISTRY_TOKEN` env)
- **python-build** — builds wheel + sdist, uploads to PyPI via `PYPI_TOKEN`

### `lefthook.yml`

Three hooks:

- `pre-commit`: parallel fmt (lang-detected), gitleaks scan (no `\|\| true`), trailing-whitespace check
- `commit-msg`: warns on non-conventional commit titles (does not fail)
- `pre-push`: clippy / eslint / ruff at workspace level; failure propagates

Install lefthook with: `lefthook install` (one-time per repo).

### `mcp-hooks.json`

Drop this into your harness config directory. Each harness uses a different
schema/location:

- **jcode**: `~/.jcode/hooks.json` (use as-is)
- **codex**: `~/.codex/hooks.toml` (convert JSON → TOML)
- **forge**: `~/.forge/hooks.yaml` (convert JSON → YAML)
- **Claude Code**: merge into `~/.claude/settings.json` under the `hooks` key

The hooks block destructive git/gh commands (`gh repo delete`, `git push --force`,
`git push --force-with-lease`, `git reset --hard`, `git clean -fd`,
`git branch -D`), log edit operations (using `jq` on the JSON `$CLAUDE_TOOL_INPUT`),
run lefthook after edits (failures propagate), and emit desktop notifications
on harness events (macOS via `osascript`, Linux via `notify-send`).

## Test on a scratch repo

```bash
# Dry-run against a real repo (no mkdir, no verification)
bash tools/integration-kit/install.sh --target ~/CodeProjects/Phenotype/repos/phenotype-registry --dry-run

# Actual install (only the workflows component, to minimize footprint)
bash tools/integration-kit/install.sh --target ~/CodeProjects/Phenotype/repos/phenotype-registry --components workflows
```

The post-install verification block prints ✓ / ✗ for each expected file.
Verification runs only on a non-dry-run install; for dry-runs, the WOULD COPY
log line is the verification.

## License

Same as the parent PhenoShared repo (operator-confirmed dual MIT/Apache).

## Author

`[Instinct] Authored by agent` — assembled by jcode on branch
`instinct/shared-integration-kit-20261012`. Not human-reviewed; treat as a
starting point and adjust the workflows / hook commands for your repo's
specific needs.
