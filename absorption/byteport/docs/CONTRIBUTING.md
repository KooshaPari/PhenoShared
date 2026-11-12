# Contributing to BytePort

Guidance for contributing to the BytePort desktop deployment platform.
This is a multi-language workspace (Rust, Go, TypeScript). Read
`docs/ARCHITECTURE.md` first for the component map.

## 1. Development Environment

Toolchain requirements (pinned by repo config):

| Tool | Version / Source | Notes |
|------|------------------|-------|
| Rust | `stable` (rust-toolchain.toml: rustfmt, clippy, rust-src) | `rustup` |
| Go | `1.26.0` (`backend/byteport/go.mod`) | `go.mod` module `byteport` |
| Node / npm | npm 10.8.2 (`packageManager` field, matches `mise.toml`) | used by `frontend/web` |
| Task | See `Taskfile.yml` | optional orchestrator (also `make`/`just`) |
| pre-commit | `pip install pre-commit` | `just precommit-install` |
| cargo-deny / cargo-audit / gitleaks / trufflehog | audit tools | `just audit` |

Recommended bootstrap:

```bash
# Run from the repository root. Each cd is independent of the previous one
# (this block is meant to be copy-pasted line by line, not pasted all at once).
rustup toolchain install stable --component rustfmt,clippy,rust-src
(cd frontend/web && npm ci --ignore-scripts)
(cd backend/byteport && go mod download)
task build                             # build all three engines
```

## 2. Build

Prefer the Taskfile orchestration; the underlying commands are listed for CI.

```bash
task build          # cargo build --workspace + go build ./... + npm run build
cargo build --workspace                # Rust workspace
cd backend/byteport && go build ./...  # Go backend
cd frontend/web && npm run build       # SvelteKit/Vite frontend
npm run tauri dev                      # run the desktop app (dev)
```

## 3. Test

```bash
task test                  # compile-only rust + go test ./... + frontend tests
task test-rust             # cargo test --workspace (full; slow — ~20 min timeout)
cd backend/byteport && go test ./...   # Go tests
cd backend/byteport && go test -race ./...# Go tests with race detector
cd frontend/web && npm test            # Vitest (falls back to npm run check)
cd frontend/web && npx playwright test # e2e (frontend)
```

Mutation testing and fuzzing live under `Taskfile.yml` (`mutants.toml`,
`fuzz/`, `tests/`). Coverage gates and CI parity are defined in the
`.github/workflows/` suite (`ci.yml`, `quality-gate.yml`, `tier2-coverage-gate.yml`).

## 4. Lint & Format

```bash
task lint          # cargo clippy --workspace -- -D warnings + go vet + npm run lint
cargo fmt --check  # rustfmt; repo config in rustfmt.toml (max_width 120)
cargo clippy --workspace -- -D warnings
cd backend/byteport && go vet ./... && golangci-lint run   # Go (golangci.yml)
cd frontend/web && npm run lint          # prettier --check && eslint
pre-commit run --all-files               # repo pre-commit hooks
```

Lint/format configs: `rustfmt.toml`, `clippy.toml`, `golangci.yml`,
`.editorconfig`, `.pre-commit-config.yaml`, `lefthook.yml` (pre-commit,
pre-push, and commit-msg hooks enforce formatting, clippy `-D warnings`,
`cargo deny`, `cargo audit`, and Conventional Commits).

## 5. Code Style

- **Rust**: rustfmt defaults from `rustfmt.toml`, clippy clean with `-D
  warnings`; workspace deps in `Cargo.toml`; keep public APIs exported.
- **Go**: `gofmt` clean; `go vet` clean; golangci-lint set with errcheck,
  gosimple, govet, ineffassign, staticcheck, unused, gosec, unconvert,
  unparam, gocritic (see `golangci.yml`); prefer the domain/infrastructure
  separation of `backend/byteport/internal`.
- **TypeScript/Svelte**: Prettier check + ESLint (`eslint.config.js`); Tailwind
  v4 conventions; types via `tsc --noEmit`.
- Feature modules should stay cohesive; split large files rather than growing
  them (see repo hygiene gates in `Taskfile.yml`).

## 6. Commit / PR Conventions

**Conventional Commits** are enforced by lefthook `commit-msg`:

```text
^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?: .{1,72}$
```

Every commit carries immutable-ledger trailers (repo norm):

```text
subject: type(scope): description

tx-agent:     jcode|codex|forge|human
tx-task:      <task/issue reference>
tx-validated: lint|test|build|manual|none
tx-scope:     <affected components>
tx-intent:    <one-line purpose>
```

PR flow:

1. Work on a short-lived feature branch.
2. Run `task ci` (or the equivalents in §2-§4) locally before pushing.
3. Open a PR; CI runs the `.github/workflows/` suite (build, lint, tests,
   deny, audit, coverage gates, e2e).
4. Address review; squash-merge on approval. Do not use `--force` pushes to
   shared branches.

## 7. Documentation

- Session-scoped work documents live under `docs/sessions/<YYYYMMDD>-<slug>/`
  (see existing entries such as `20260914-integration-evidence`).
- Architectural decisions are recorded as ADRs in `docs/adr/`.
- Keep `docs/ARCHITECTURE.md` and repo-root `ARCHITECTURE.md` in sync when
  component boundaries change.

## 8. Security

- Never commit secrets; `.env.example` documents required vars.
- `gitleaks detect` and `trufflehog filesystem` run in CI (manual hooks too).
- Report vulnerabilities via `SECURITY.md`.
