# BytePort — AGENTS.md

> **AI-agent constitution for `BytePort`.** Generated from the V3 §120
> SD4 SOTA pattern (V18 build/test/style/do-not-touch constitution) on
> 2026-06-12. Read this fully before making changes.

## Active DAG
- **V3 DAG:** `FLEET_DAG_v3.db` (Phenotype org task graph)
- **Current focus:** L5 #88 — Focus-repo README + AGENTS.md standardization

## Active DAG
- **V3 DAG:** `FLEET_DAG_v3.db` (Phenotype org task graph)
- **Current focus:** L5 #88 — Focus-repo README + AGENTS.md standardization

---

## Active DAG
- **V3 DAG:** `FLEET_DAG_v3.db` (Phenotype org task graph)
- **Current focus:** L5 #88 — Focus-repo README + AGENTS.md standardization

---

## 1. Quick start (build, test, lint)

```bash
# Hybrid task runner (just) — runs all three engines
just build    # Rust + Go + SvelteKit
just test     # cargo test --no-run + go test + npm test
just lint     # cargo clippy + go vet + npm run lint
just fmt      # cargo fmt --check + gofmt -l + prettier --check
just ci       # build + test + lint + fmt + deny + audit
just hygiene  # oversized files + TODO markers + governance file presence

# Rust workspace (Tauri shell) — members = ["frontend/web/src-tauri"]
cargo build --workspace
cargo test  --workspace
cargo clippy --workspace -- -D warnings
cargo fmt   --all -- --check

# Go backend (backend/byteport + backend/nvms)
cd backend/byteport && go build ./... && go test ./... && go vet ./...

# SvelteKit frontend (frontend/web)
cd frontend/web && pnpm install --frozen-lockfile && pnpm build

# Supply-chain (configured via deny.toml)
cargo deny check
cargo audit
```

---

## 2. Project layout (top-level dirs + purpose)

| Path | Purpose |
|------|---------|
| `backend/byteport/` | Go 1.25 deployment engine (Gin + GORM + SQLite, PASETO auth, AWS SDK) |
| `backend/bytebridge/` | Bridge / integration layer (legacy; in-process glue) |
| `backend/nvms/` | MicroVM runtime (Spin / `nvms` Go service) |
| `frontend/web/` | SvelteKit 2 + Svelte 5 + Tailwind 4 web frontend |
| `frontend/web/src-tauri/` | Tauri 2 desktop/mobile shell (Rust) |
| `docs/` | Architecture + AWS deployment + ADR index |
| `assets/` | Static assets (logos, screenshots) |
| `tools/` | Repository automation |
| `scripts/` | Build / release scripts |
| `.github/workflows/` | 20 CI workflows (ci, quality-gate, go-ci, lint, sonarcloud, …) |
| `start` | tmux-based dev/prod orchestrator (legacy `start dev` / `start prod`) |
| `odin.nvms` | Example NVMS manifest (single-file IaC) |

The repo is **polyglot hybrid**: Go is the primary backend; SvelteKit is
the primary web frontend; Rust (Tauri) is the desktop/mobile shell.

---

## 3. Key files (entry points, config files)

| File | Role |
|------|------|
| `Cargo.toml` | Root Rust workspace (members = `["frontend/web/src-tauri"]`) |
| `Cargo.lock` | Pinned dependency graph (Tauri) |
| `justfile` | Hybrid Rust+Go+TS task runner (L2 #24; recipes: build, test, lint, fmt, ci, hygiene) |
| `deny.toml` | cargo-deny advisories/bans/licenses/sources |
| `golangci.yml` | golangci-lint rule set (for the Go surface) |
| `rust-toolchain.toml` | Toolchain pin |
| `clippy.toml` | Lint config |
| `.pre-commit-config.yaml` | pre-commit hooks (rustfmt, clippy, prettier, eslint, gofmt, go vet, golangci-lint, trufflehog, gitleaks) |
| `.gitleaks.toml`, `.trufflehog.yml` | Secret-scanning config |
| `CODEOWNERS` | Per-path review routing |
| `cliff.toml` | git-cliff release-notes template |
| `release-drafter.yml` | release-drafter config |
| `sbom-refresh.yml` | SBOM refresh config |
| `renovate.json` | Renovate bot config (in `frontend/web/`) |
| `playwright.config.ts` (or similar) | E2E config (in `frontend/web/`) |
| `CLAUDE.md` | Claude-specific operating notes |
| `ARCHITECTURE.md` | Architecture deep dive |
| `CHARTER.md` | Project charter |
| `FUNCTIONAL_REQUIREMENTS.md` | Functional requirements |
| `ADR.md` | Architecture decisions |
| `CHANGELOG.md` | Release history |
| `LICENSE` | MIT license |
| `backend/byteport/cmd/` | Go CLI entrypoints |
| `frontend/web/src-tauri/src/main.rs` | Tauri desktop entrypoint |
| `odin.nvms` | Canonical NVMS manifest example |

---

## 4. Conventions

- **Commit message format** — Conventional Commits, scope = engine or
  concern: `feat(byteport): …`, `fix(bytebridge): …`,
  `feat(frontend): …`, `chore(tauri): …`. The scope names the engine.
- **Branch naming** — `<prefix>/<TID>-<topic>-<date>` where prefix ∈
  `{feat, fix, chore, ci, docs, refactor, test, perf, build}` and
  TID is a V3 DAG task ID (e.g. `L1-005`, `CC2-005`, `SD4`). Examples:
  `chore/L1-005-sota-benchmarks-2026-06-11`,
  `feat/L2-015-sota-2026-06-11`,
  `chore/SD4-2026-06-12` (this worktree).
- **Worklog schema** — V2 10-column JSON schema. Canonical reference:
  [`pheno-worklog-schema`](https://github.com/KooshaPari/pheno-worklog-schema)
  (or local `pheno-worklog-schema/` if vendored). Each task produces
  one worklog JSON at the repo root: `worklog-<TID>-<topic>.json`.
- **PR policy** — `main` is protected (1 reviewer required, no force-push).
  All changes flow through PRs.
- **CLI errors** — must print to stderr and exit non-zero. New CLI
  commands go in `backend/byteport/cmd/`.
- **Credentials** — read from env vars or `~/.aws/credentials`; never hardcoded.
- **NVMS manifest** — strictly validated; fail loudly on schema errors.
  The schema is the single source of truth for the IaC contract.
- **Encoding** — UTF-8, no BOM. Never commit agent dirs.

---

## 5. Common tasks

### Add a Go dep to `backend/byteport`

```bash
cd backend/byteport
go get github.com/<owner>/<repo>@<version>
go mod tidy
go build ./... && go test ./...
```

### Add a Rust dep to `frontend/web/src-tauri`

```bash
cargo add -p <tauri-crate-name> <crate-name> --features <feature>
cargo build --workspace
cargo deny check
```

### Add a SvelteKit dep to `frontend/web`

```bash
cd frontend/web
pnpm add <pkg>
pnpm install --frozen-lockfile
```

### Add a test

- **Go unit test** — co-located `*_test.go`. Use stdlib `testing` plus
  `testify` (or `gomock` for interface mocks).
- **Go integration** — `backend/byteport/tests/integration/<topic>_test.go`.
  Use `testcontainers-go` for ephemeral infra.
- **Rust unit** — `#[cfg(test)] mod tests` at the bottom of the file.
- **Svelte component test** — `*.test.ts` next to the component, runner
  is `vitest`.
- **E2E** — Playwright in `frontend/web/tests/e2e/`.
- **Benchmarks** — Go: `go test -bench=. -benchmem`; Rust: criterion
  via the `benchmarks` crate (when added).

### Run benchmarks

```bash
# Go
cd backend/byteport && go test -bench=. -benchmem ./...

# Rust (when added)
cargo bench --workspace
```

---

## 6. Tooling

- **Task runner: `justfile` (casey/just).** Chosen for the L2 #24 SOTA
  because: (1) casey/just is the org-wide standard (mirrors AgilePlus,
  PlayCua, nanovms, PhenoCompose), (2) BytePort is polyglot
  (Rust + Go + TS) and the justfile's `build-rust / build-go /
  build-frontend` recipes compose cleanly into `just build = build-rust +
  build-go + build-frontend`, (3) the `just hygiene` recipe bundles the
  oversized-file + TODO + governance-file checks that were scattered
  across ad-hoc scripts.
- **Linter:**
  - Rust: `cargo clippy --workspace -- -D warnings` (CI-enforced).
  - Go: `go vet ./...` + `golangci-lint run` (CI-enforced).
  - Frontend: `npm run lint` (prettier --check + eslint).
- **Formatter:**
  - Rust: `cargo fmt --all -- --check` (CI-enforced).
  - Go: `gofmt -l <dir>` (advisory in CI; `gofmt -w` to fix).
  - Frontend: `npm run format:check` (or `format -- --check`).
- **Pre-commit: pre-commit framework** (`.pre-commit-config.yaml`) running
  rustfmt, clippy, prettier, eslint, gofmt, go vet, golangci-lint,
  trufflehog, gitleaks. Install with
  `brew install pre-commit && pre-commit install`.
- **Supply-chain: `cargo-deny` + `cargo-audit` + `npm audit` + `govulncheck`**
  (deny.toml + cargo-audit.yml + lint.yml + go-ci.yml).
- **Coverage: cargo llvm-cov + Codecov** (codecov.yml).
- **SBOM: `sbom-refresh.yml`** (CycloneDX).
- **Releases: `git-cliff`** (cliff.toml) + release-drafter (release-drafter.yml).
- **VCS: git worktrees** — work in `BytePort-wtrees/<topic>/`, never
  directly in the canonical `BytePort/` checkout on `main`.

---

## 7. Do not touch (without an explicit task)

- `Cargo.toml [workspace.members]` — adding/removing members is an L2 SOTA task.
- `rust-toolchain.toml` — toolchain pin is contractual.
- `deny.toml`, `clippy.toml`, `golangci.yml` — version pins / rule sets are intentional.
- `backend/byteport/go.mod` `go` directive — Go 1.25+ is contractual.
- `odin.nvms` schema — the NVMS manifest is the single source of truth
  for the IaC contract; changing the schema is a breaking change.
- `frontend/web/src-tauri/Cargo.toml` `[lib] crate-type` — Tauri requires
  the C-ABI `cdylib` output; changing it is a breaking change.
- The hybrid stack split (Go + SvelteKit + Tauri) — the L1 audit at
  `BytePort/STATUS_2026_06_10.md` confirms the Loco.rs / Rust narrative
  is retired; do not resurrect it.
- The `.pre-commit-config.yaml` `trufflehog` hook id — replaced by the
  `phenotype-secret-scan` workflow in a future L2 pass.
- `CODEOWNERS` — review routing is governance-mandated.

---

## 8. Reference

- **V3 §120 (SD4 SOTA pattern)** — this file's section layout.
- **V18 §110 pheno-otel AI-DD crutches** — the 5-convention-file pattern
  (AGENTS.md, llms.txt, WORKLOG.md, CHANGELOG.md, LICENSE-MIT).
- **V11 §70.3 (AX/L16 acceptance)** — `cargo clippy --workspace -- -D warnings`
  + `go vet ./...` + `npm run lint` clean is the canonical gate.
- **FLEET_100TASK_DAG_V3.md** — task IDs (`L1-005`, `CC2-005`, `SD4`).
- **CLAUDE.md** — Claude-specific operating notes.
- **CHARTER.md** — project charter (mission + scope).
- **ARCHITECTURE.md** — architecture deep dive.
- **ADR.md** — architecture decisions.
- **phenotype-org-governance/SUPERSEDED.md** — governance authority
  (when present, supersedes local conventions).

---

## 9. Architecture Decision Records

BytePort documents architecture decisions in two locations:
- **`ADR.md`** (root) --- summary of key decisions
- **`docs/adr/`** --- individual ADR files with full context
- **`docs/decisions/`** --- MADR-format decision records template

| ID | Title | Status | Location |
|----|-------|--------|----------|
| ADR-001 | NVMS/BytePort IaC Manifest Format | Accepted | [`ADR.md`](ADR.md) |
| ADR-002 | AWS as Primary Deployment Target | Accepted | [`ADR.md`](ADR.md) |
| ADR-003 | Go Backend + Web Frontend Architecture | Accepted | [`ADR.md`](ADR.md) |
| ADR-004 | LLM-Assisted Portfolio Template Generation | Accepted | [`ADR.md`](ADR.md) |
| ADR-005 | CLI-First Interface | Accepted | [`ADR.md`](ADR.md) |
| ADR-001 | Architecture --- Backend and System Architecture | Accepted | [`docs/adr/ADR-001-architecture.md`](docs/adr/ADR-001-architecture.md) |
| ADR-002 | Zero-Copy Strategy | --- | [`docs/adr/ADR-002-zero-copy-strategy.md`](docs/adr/ADR-002-zero-copy-strategy.md) |
| ADR-003 | Adaptive Compression | --- | [`docs/adr/ADR-003-adaptive-compression.md`](docs/adr/ADR-003-adaptive-compression.md) |
| ADR-004 | Schema Registry | --- | [`docs/adr/ADR-004-schema-registry.md`](docs/adr/ADR-004-schema-registry.md) |
| ADR-005 | Load Balancing | --- | [`docs/adr/ADR-005-load-balancing.md`](docs/adr/ADR-005-load-balancing.md) |
| ADR-006 | Transport Layer | --- | [`docs/adr/ADR-006-transport-layer.md`](docs/adr/ADR-006-transport-layer.md) |
| ADR-007 | Security Architecture | --- | [`docs/adr/ADR-007-security-architecture.md`](docs/adr/ADR-007-security-architecture.md) |
| ADR-008 | Observability | --- | [`docs/adr/ADR-008-observability.md`](docs/adr/ADR-008-observability.md) |
| ADR-009 | Error Handling | --- | [`docs/adr/ADR-009-error-handling.md`](docs/adr/ADR-009-error-handling.md) |
| ADR-010 | Wire Protocol | --- | [`docs/adr/ADR-010-wire-protocol.md`](docs/adr/ADR-010-wire-protocol.md) |
| ADR-011 | Configuration Schema | --- | [`docs/adr/ADR-011-configuration-schema.md`](docs/adr/ADR-011-configuration-schema.md) |
| ADR-012 | API Design | --- | [`docs/adr/ADR-012-api-design.md`](docs/adr/ADR-012-api-design.md) |
| ADR-013 | Performance Optimization | --- | [`docs/adr/ADR-013-performance-optimization.md`](docs/adr/ADR-013-performance-optimization.md) |
| ADR-014 | Feature Flags | --- | [`docs/adr/ADR-014-feature-flags.md`](docs/adr/ADR-014-feature-flags.md) |
| --- | Record Architecture Decisions (MADR template) | --- | [`docs/decisions/0001-record-architecture-decisions.md`](docs/decisions/0001-record-architecture-decisions.md) |

## 10. License

MIT. See `LICENSE`.
Copyright 2026 Koosha Pari.
