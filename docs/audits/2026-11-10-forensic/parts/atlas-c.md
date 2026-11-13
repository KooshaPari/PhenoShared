## Non-Rust surfaces

PhenoShared is a Rust workspace with heavy multi-language satellites; the actual code mass is Python.

| Language | Tracked files | LOC | Purpose / note |
|---|---|---|---|
| Python `.py` | 5,709 | 720,862 | Largest by LOC (~52%). Entrypoints: `python/` (314), `servers/` (386), `agents/` (1,534) |
| Go | 2,819 | 243,250 | ~18% of code LOC; `go-fabric/`, `linux-client/`, `windows-client/`, `native/` |
| TypeScript `.ts` | 2,884 | 30,445 | ~3.4% of measured LOC |
| TSX `.tsx` | 2,327 | 16,149 | React surfaces (`sites/`, `web/`, `dashboard/`) |
| JavaScript `.js` | 375 | 16,339 | ~1.2% of measured LOC |

**File counts are `git ls-files` tracked counts and are authoritative. The LOC column is not, and is
not reconcilable with them:** ~30k LOC across 2,884 `.ts` files (~11 LOC/file) and ~16k across 2,327
`.tsx` files (~7 LOC/file) are far below a plausible per-file average, so those LOC figures describe a
filtered subset whose inclusion rule was not recorded. Treat the LOC column as a lower bound per
language, not a total. Measured tracked total across rs+py+ts+tsx+js+go+sh is 21,797 files.
Plugin manifest also declares 3 Python MCP servers (`servers/substrate/*.py`, `servers/pheno-org/*.py`);
on-disk presence UNPROVEN.

## Runtime surface

154 `[[bin]]` declarations across tracked manifests, and 85 crates under `crates/` with a top-level `src/main.rs`. Service-forming binaries: `fabric-daemon`, `fabric` (`fabric-cli`), `brokerd` (`substrate-browser-broker`), `phinbox`, `phenotype-daemon` (`pheno-agent`), `teamcomm-daemon`, `sharecli-ipc`, `focalpoint-webhook-server`, `focalpoint-mcp-server` (`focus-mcp-server`), `gateway-tools serve`, `start_api` (`agileplus-api`). One-shot tools: `qgate`, `ptx`, `audit-privacy`, `tokenledger`, `docs-health`, `sbom-gen`, `perfharness`, `phenotype-router`, `hexakit`, `agileplus`, `sharecli`, `argis-monitor`.

| Service | Port / socket | Protocol |
|---|---|---|
| `fabric-daemon` | 9400 wire, 9401 metrics | TCP JSON + HTTP metrics |
| `brokerd` | 127.0.0.1:8787 | HTTP (lease + fencing token) |
| `phinbox` | 7117 default + Unix socket | HTTP + UDS |
| `phenotype-daemon` | `/tmp/phenotype-daemon.sock`, TCP 127.0.0.1:9456 | JSON-RPC |
| `teamcomm-daemon` | Unix socket + pidfile | UDS |
| `sharecli-ipc` | `~/.local/share/sharecli/ipc.sock` | UDS |
| `focalpoint-mcp-server` | 127.0.0.1:8473 | MCP HTTP/SSE |
| `gateway-tools serve` | 8081 | HTTP |
| `agileplus-api` | `API_HOST:AppConfig.api.port` | HTTP |

Defect: `9456` (main.rs) vs `8953` (`DEFAULT_TCP_PORT`, protocol.rs:186) for the same phenotype-daemon constant; runtime value UNKNOWN. Compose-only: 9090, 3000, 5432, 6379, 8000, 3100, 8090, 8080, 8081, 8091, 50051 (gRPC), 30100 (vLLM unit, binary unproven).

MCP servers: `browser-broker-mcp` (stdio, no socket), `phinbox_mcp` (stdio), `focalpoint-mcp-server` (HTTP/SSE). Library-only: `phenotype-mcp-sdk-rs`, `mcp-server`, `driver-mcp`; `teamcomm-mcp` not inspected. Tool counts UNKNOWN.

GUI/TUI: `fabric-tui`, `substrate-tui` (terminal); `fabric-gui` (Tauri, workspace-excluded); `fabric-tray`, `sharecli-tray-linux`/`-windows`; `eidolon-desktop`, `eidolon-mobile`, `apps/phinbox-app`. ~50+ crates derive `clap::Parser`.

## Data and knowledge surfaces

Markdown outnumbers code: 10,532 `.md` vs 7,209 `.rs`, 5,709 `.py`.

| Surface | Count | Note |
|---|---|---|
| `docs/` | 11,721 files (2,494 `.md`) | docs, ADRs, `absorbed-from-*` |
| `audits/` | 1,750 | audit records |
| Markdown total | 10,532 tracked | repo-wide; `docs/` holds 2,494 of them |
| `kitty-specs/` | 170 | specs |
| `projects/` | 178 | records |
| `handbook/` | 142 | records |
| `state/` | 193 | state artifacts |
| `bench/` | 391 | ops/benchmarks |

Record/governance dirs: `adrs/`, `architecture/`, `spec/`+`specs/`+`agileplus-specs/`, `plans/`, `findings/`, `audits/`+`audit/`, `evidence/`, `attestations/`, `verification/`+`verifier/`, `worklog/`+`worklogs/`, `governance/`+`phenotype-governance/`, `grades/`, `promotion/`, `risks/`, `patterns/`, `contracts/`, `schemas/`, `tokens/`, `locales/`, `anti-patterns/`, `beads/`. State: `traces/`, `datasets/`, `sbom/`, `assets/`, `experiments/`, `playground/`. Per-directory counts beyond the top 22 are UNKNOWN. Absorbed (excluded from first-party metrics): `absorption/` 4,414, `_archived/` 632, `archive/`+`archives/` 225.

## Dependency and supply-chain shape

- No dependency-graph analysis was performed; family boundaries are inferred from name prefix, not import edges.
- Lockfile size is measured: 1,904 package entries in `Cargo.lock`. Duplicate dependency versions and per-crate license posture were not analysed: **UNKNOWN** (the repo-wide license split is in the supply-chain evidence, not per crate).
- Vendoring is material: a `.vendor/lancedb` third-party tree (9 of the 10 largest tracked `.rs` files are vendored or archived absorbed copies), and AgilePlus is vendored three times (`agileplus-*` 23 dirs, `agile-plus/crates/` 51, `hexa-kit/agileplus/crates/` 25). Raw per-directory LOC therefore overstates the codebase ~2.2x.
- `sbom-gen`, `audit-privacy`, `acceptance-contract` binaries exist and `sbom/` is present; output state UNKNOWN.

