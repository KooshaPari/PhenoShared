# BytePort Architecture

> Canonical architecture for the BytePort desktop deployment platform.
> Companion to `docs/CONTRIBUTING.md`. Repo-root `ARCHITECTURE.md` is the
> short-form overview; this document is the fuller reference and should be
> kept in sync when component boundaries change.

## 1. System Overview

BytePort is a multi-language desktop deployment application. A **Tauri 2**
desktop shell hosts a **SvelteKit** (Svelte 5) frontend and talks to a **Go** backend
service. The Rust side is organized as a Cargo workspace whose reusable
libraries (transport, DAG scheduling, OpenTelemetry, CLI bindings) are
consumed by the Tauri shell and by Phoenix infrastructure.

Three distinct build engines coexist in one repository:

| Engine | Location | Role |
|--------|----------|------|
| Rust (Cargo workspace) | `crates/*`, `frontend/web/src-tauri` | Desktop shell, transport, DAG, telemetry |
| Go modules | `backend/byteport`, `ports/otel_rum.go` | Server-side domain logic, persistence, auth |
| TypeScript (SvelteKit/Vite) | `frontend/web` | User-facing desktop/web UI and Tauri IPC surface |

## 2. Workspace / Component Inventory

### 2.1 Rust workspace (`Cargo.toml`)

Workspace members (`resolver = "3"`, `rust-toolchain.toml` pins **stable** with
`rustfmt`, `clippy`, `rust-src`):

| Crate | Responsibility | Key deps |
|-------|----------------|----------|
| `crates/byteport-transport` | Wire transport primitives shared by CLI and shell (serde models, errors) | serde, thiserror |
| `crates/byteport-cli` | Tools CLI bindings for transport/port/codec/UI | clap, byteport-transport |
| `crates/byteport-dag` | DAG foundation: executor interfaces (sync, async-pool, worktree-pool), topological sort, parallel-bucket scheduler | futures, rayon, tokio, serde_yaml, sha2, uuid |
| `crates/byteport-otel` | OpenTelemetry instrumentation: metrics, tracing, OTLP export | opentelemetry 0.28, tracing, tonic |
| `crates/byteport-integration` | Wires shared Phenotype crates (crypto, observability, health) from PhenoInfra | phenotype-* (git, rev `dd040ed1`) |
| `frontend/web/src-tauri` (`app`) | Tauri 2 shell: `byteport` binary + `app_lib` static/cdylib/rlib | tauri 2, clap, clap-ext, byteport-transport |
| `crates/integration` | Cross-crate test/integration surface | byteport-integration |

A `Cargo.lock` is committed; shared Phenotype crates are pinned to a
`PhenoInfra` git revision (see the `[workspace.dependencies]` block).

### 2.2 Go backend (`backend/`)

| Module | Responsibility |
|--------|----------------|
| `backend/byteport` | Domain service. Clean/dependency-inversion layout: `application/` (deployment use-cases), `domain/deployment` (entities, repos, services, status), `infrastructure/` (auth, clients, http, persistence, secrets), `container/` (wiring), `monitor/`. |
| `ports/otel_rum.go` | OpenTelemetry RUM-side hooks exposed over Go ports. |

Backend stack: **Gin** HTTP router, **GORM** (Postgres + SQLite drivers),
**WorkOS** auth, **go-jose** JWT, **Hashicorp Vault** / **AWS Secrets Manager**
secret backends, **godotenv** config, AWS SDK v2. Go module `byteport`.

### 2.3 Frontend (`frontend/web`)

- **SvelteKit 2** + **Svelte 5** + **Vite 8** + **Tailwind CSS 4** (`sveltekit-superforms`, `zod`, `bits-ui`, `lucide-svelte`).
- Pages under `src/routes/` (home, login, signup, docs, otel, preview, qa) plus `+layout.*` shell.
- **Tauri 2** integration: `src-tauri/` with `tauri.conf.json`, capabilities, icons, and `src/{lib.rs,main.rs}`.
- Testing: Vitest, Playwright, Storybook 8.

## 3. Data / Control Flow

```text
user actions
    -> frontend/web (SvelteKit)
        -> src-tauri (Tauri IPC via @tauri-apps/api)   [desktop]
        -> HTTP / REST                                 [hosted]
    -> backend/byteport (Gin)
        -> application/  (deployment use-cases)
        -> domain/deployment  (service, repository, status)
        -> infrastructure/  (persistence via GORM, auth via WorkOS,
                             secrets via Vault / AWS Secrets Manager)
    -> external systems (deployment providers, Postgres/SQLite)

telemetry: byteport-otel -> tracing/OTLP exports, SurfRUM (ports/otel_rum.go)
```

Control flow conventions:
- Domain layer holds the contract; `infrastructure` adapters implement ports.
- Timeouts and orchestration live in `application` use-cases.
- Cross-cutting concerns (config, telemetry, errors) are centralized; see
  repo `ADR.md` and `docs/adr/` for the recorded decisions.

## 4. Key Dependencies

| Dependency | Purpose |
|------------|---------|
| Tauri 2 (`@tauri-apps/api`, `tauri-plugin-log/plugins`) | Desktop shell, IPC, OS/log plugins |
| SvelteKit 2 (Svelte 5) / Vite | Frontend framework and bundler |
| gin-gonic/gin | Go HTTP router |
| gorm (postgres, sqlite) | ORM and persistence |
| workos-go / go-jose | AuthN/AuthZ and JWT |
| hashcorp/vault, aws-sdk-go-v2/secretsmanager | Secret retrieval |
| opentelemetry 0.28 + OTLP | Metrics/tracing export (rust) |
| PhenoInfra `phenotype-{crypto,observability,health}` (git pinned) | Shared Phenotype platform crates |

## 5. Build / Run Topology

`Taskfile.yml` (and the simpler `Makefile`) orchestrate all three engines:

```bash
task build            # rust (cargo build --workspace) + go + frontend
task build-rust       # cargo build --workspace
task build-go         # cd backend/byteport && go build ./...
task build-frontend   # cd frontend/web && npm run build
task test             # rust (compile), go test ./..., frontend tests
task lint             # cargo clippy -D warnings + go vet + npm run lint
task ci               # pre-commit + deny + audit gates (see justfile)
just rust-test        # cargo test --workspace (full)
```

Run topology:
1. `frontend/web/src-tauri` is the packaged desktop app; its `.taurignore` /
   `capabilities` scope which IPC commands the UI may invoke.
2. `backend/byteport` runs as the server; config is environment-driven
   (`.env.example`, godotenv).
3. `backend/database.db` shows the local SQLite persistence default; Postgres is
   supported via GORM for hosted deployments.

## 6. Conventions

- Keep the Tauri shell and Go services aligned on shared contracts; prefer
  explicit interfaces (`ports/`, `lib/`, `crates/byteport-transport`).
- Do not bypass service boundaries (each engine has its own layer rules).
- Decisions are captured as ADRs under `docs/adr/`.
