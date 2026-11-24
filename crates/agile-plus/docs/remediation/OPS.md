# Operations & Deploy Remediation — Audit Gap K-Ops (50%)

> **Scope:** Container packaging for the `agileplus` CLI, environment configuration, install/upgrade/rollback runbooks.  
> **Artifacts added:** root `Dockerfile` (CLI-focused), `docs/remediation/env.example.snippet` (additive env catalog).

## Container images

| File | Purpose | Status |
|------|---------|--------|
| `Dockerfile` | **New** — multi-stage build producing `agileplus` CLI binary only | Added in this PR |
| `Dockerfile.rust` | Full workspace compile (legacy single-stage) | Exists; no `runtime` stage despite `docker-compose.test.yml` reference |
| `python/Dockerfile.python` | MCP Python service | Exists |
| `agileplus-mcp/Dockerfile` | MCP alternate layout | Exists |
| `tests/integration/Dockerfile.test` | Integration test runner | Exists |

### Build CLI image (local)

```bash
# From repo root — requires agileplus-cli in workspace members (see note below)
docker build -f Dockerfile -t agileplus-cli:local .

# Smoke test
docker run --rm agileplus-cli:local agileplus --version
docker run --rm agileplus-cli:local agileplus --help
```

**Workspace membership note:** `origin/main` currently lists only `rust` under `[workspace].members`. Before the Dockerfile build succeeds in CI, expand `members` to include `crates/agileplus-cli` and its dependency graph (tracked in kitty-specs/003). Until then, prefer `cargo install --path crates/agileplus-cli` on the host.

### Integration stack (existing)

```bash
docker compose -f tests/integration/docker-compose.test.yml --profile full up --build
```

Services: `agileplus-core` (Rust), `agileplus-mcp` (Python), test runner. See environment block below.

### Local dev orchestration

`process-compose.yml` starts NATS, Dragonfly (Redis), Neo4j, and dependent services. Logs land in `.agileplus/logs/`.

```bash
process-compose up
```

---

## Environment configuration

### Canonical files

| File | Role |
|------|------|
| `.env.example` | Sentry / telemetry placeholders (root) |
| `docs/remediation/env.example.snippet` | **Additive** AgilePlus runtime variables (copy into `.env`) |

### Variable catalog (runtime)

| Variable | Default | Component | Description |
|----------|---------|-----------|-------------|
| `AGILEPLUS_DB` | `./agileplus.db` | CLI | SQLite path (`agileplus --db`) |
| `AGILEPLUS_HOME` | — | Agents / harnesses | Repo root for tooling |
| `AGILEPLUS_API_URL` | `http://localhost:8080` | MCP, integration tests | HTTP API base |
| `AGILEPLUS_API_KEY` | `dev-api-key` | API clients | `X-API-Key` header value |
| `AGILEPLUS_GRPC_ADDRESS` | `localhost:50051` | MCP | gRPC core address |
| `AGILEPLUS_GRPC_URL` | `agileplus-core:50051` | Compose | gRPC host:port |
| `AGILEPLUS_CORE_DATABASE_PATH` | `/data/agileplus.db` | Core container | Persistent DB mount |
| `AGILEPLUS_CORE_REPO_PATH` | `/repo` | Core container | Git repo mount |
| `AGILEPLUS_API_PORT` | `8080` | Core | HTTP listen port |
| `AGILEPLUS_API_GRPC_PORT` | `50051` | Core | gRPC listen port |
| `AGILEPLUS_TELEMETRY_ENABLED` | `true` | Core | OTLP on/off |
| `AGILEPLUS_LOG_LEVEL` | `info` | Core | Log filter |
| `AGILEPLUS_MCP_PORT` | `8081` | MCP | MCP HTTP port |
| `SENTRY_DSN` | — | All Rust binaries | Error reporting (see `.env.example`) |
| `SENTRY_ENVIRONMENT` | `development` | All Rust binaries | `development` / `staging` / `production` |
| `RUST_LOG` | — | All Rust binaries | `tracing` filter override |
| `RUST_BACKTRACE` | `1` | Dev | Set in `process-compose.yml` |

Pattern for future config keys: `AGILEPLUS_<SECTION>_<KEY>` (see kitty-specs WP15).

### Minimal local `.env` (developer)

```bash
# Copy snippet + Sentry block
cat docs/remediation/env.example.snippet >> .env
cp .env.example .env.sentry.example   # reference only — merge manually

export AGILEPLUS_DB=./agileplus.db
export AGILEPLUS_API_URL=http://localhost:8080
export AGILEPLUS_API_KEY=dev-api-key
```

---

## Install

### Option A — Cargo (recommended for developers)

```bash
rustup toolchain install nightly
rustup component add rustfmt clippy

# After workspace includes agileplus-cli:
cargo install --path crates/agileplus-cli --locked --force

agileplus --version
```

### Option B — Docker

```bash
docker build -f Dockerfile -t agileplus-cli:$(git rev-parse --short HEAD) .
docker tag agileplus-cli:$(git rev-parse --short HEAD) agileplus-cli:current
```

### Option C — process-compose full stack

```bash
cp docs/remediation/env.example.snippet .env
process-compose up
```

---

## Upgrade

1. **Record current version:** `agileplus --version` or `docker inspect agileplus-cli:current`.
2. **Backup SQLite:** `cp "$AGILEPLUS_DB" "${AGILEPLUS_DB}.$(date +%Y%m%d).bak"`.
3. **Pull / build new artifact:**
   - Cargo: `cargo install --path crates/agileplus-cli --locked --force`
   - Docker: build new tag, retag `current`.
4. **Run migrations** (implicit on first CLI open): any command touching DB runs `MigrationRunner`.
5. **Smoke test:**
   ```bash
   agileplus status
   agileplus list-projects
   ```
6. **Compose stack:** `docker compose -f tests/integration/docker-compose.test.yml pull && … up -d`.

---

## Rollback

### CLI binary rollback

```bash
# Cargo install previous git ref
git checkout <previous-tag>
cargo install --path crates/agileplus-cli --locked --force
git checkout -

# Or restore backed-up binary from CI artifact / package cache
```

### Database rollback

SQLite migrations are **forward-only**. Rollback procedure:

1. Stop all writers (`process-compose down` or stop core container).
2. Restore backup: `cp "${AGILEPLUS_DB}.YYYYMMDD.bak" "$AGILEPLUS_DB"`.
3. Align binary version with schema era (checkout matching git tag).
4. Verify: `agileplus dashboard --json | head`.

**Never** delete WAL/SHM files from a backup restore without stopping the process first.

### Docker rollback

```bash
docker tag agileplus-cli:<previous-sha> agileplus-cli:current
docker compose -f tests/integration/docker-compose.test.yml up -d agileplus-core
```

### Telemetry rollback

Unset `SENTRY_DSN` or set `AGILEPLUS_TELEMETRY_ENABLED=false` — no code deploy required.

---

## Health checks

| Endpoint / command | Expect |
|--------------------|--------|
| `curl -f http://localhost:8080/health` | 200 (core container) |
| `agileplus status` | Exit 0, project summary |
| `redis-cli -p 6379 ping` | `PONG` (Dragonfly) |
| NATS `8222/healthz` | 200 |

---

## Known gaps (ops audit)

- [ ] `Dockerfile.rust` missing `runtime` stage referenced by compose
- [ ] Workspace `members` on `main` does not include `agileplus-cli` (blocks Docker/Cargo workspace builds)
- [ ] No published OCI image / GHCR workflow for CLI-only artifact
- [ ] `.env.example` covers Sentry only — use `env.example.snippet` for runtime vars

---

## References

- `Dockerfile` — CLI image (this PR)
- `tests/integration/docker-compose.test.yml` — full-stack env block
- `process-compose.yml` — local service graph
- `.env.example` — Sentry template
- `docs/remediation/env.example.snippet` — runtime variables
