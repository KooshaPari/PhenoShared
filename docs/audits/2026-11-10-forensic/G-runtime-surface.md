# Forensic Lane G — Runtime / Service Surface of PhenoShared

- **Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
- **Date:** 2026-11-10
- **Mode:** READ-ONLY. No git mutations, no writes inside the repo.
- **Scope:** what can actually RUN here, and on what ports.
- **Workspace:** Cargo workspace, `resolver = "2"`, ~438 member entries in `Cargo.toml`, 117 `[[bin]]` targets discovered under `crates/` + `apps/`.

Evidence convention: every row cites a file or command output. Anything not directly
observed is marked **UNSUPPORTED / UNKNOWN**.

---

## 1. Executable inventory

117 `[[bin]]` targets exist repo-wide. The table below lists the binaries that plausibly
constitute a *service / runtime surface* (long-lived process, listener, daemon, or agent
endpoint), plus the notable one-shot tools. Build-only, fuzz, xtask, and codegen binaries are
summarised separately.

### 1a. Long-lived / listener binaries

| Binary | Crate | Purpose | Evidence |
|---|---|---|---|
| `fabric-daemon` | `crates/fabric-daemon` | Fabric daemon: topology, leases, wire transport, health. `start` subcommand binds a TCP listener. | `crates/fabric-daemon/src/main.rs` (`clap::Parser`, `TcpListener::bind(&addr)`); unit `deploy/systemd/fabric-daemon.service` |
| `fabric` (fabric-cli) | `crates/fabric-cli` | CLI client for the daemon (`health --connect 127.0.0.1:9400`), auth token dir under home | `crates/fabric-cli/src/main.rs`, `src/commands/auth.rs`; healthcheck in `docker-compose.yml` |
| `brokerd` | `crates/substrate-browser-broker` | Browser lease broker. Default `127.0.0.1:8787`; refuses non-loopback bind without a bearer token. | `src/main.rs` doc comment + `--bind` default; `deploy/browser-broker/browser-broker.service` |
| `phinbox` | `crates/phinbox` | Inbox daemon + CLI + MCP. HTTP daemon default port **7117**; Unix socket IPC. | `src/inbox/daemon/mod.rs` (`DEFAULT_PORT: u16 = 7117`), `src/inbox/ipc/server.rs` (`UnixListener`) |
| `phinbox-...` (MCP bin) | `crates/phinbox` | `bin_mcp.rs` / `mcp/router.rs` — MCP server named `phinbox_mcp` | `src/bin_mcp.rs`, `src/mcp/router.rs:97` |
| `phenotype-daemon` | `crates/pheno-agent/phenotype-daemon` | Agent daemon. Unix socket **and** TCP loopback. | `src/main.rs` (`UnixListener`, `TcpListener`) |
| `focalpoint-webhook-server` | `crates/focus-webhook-server` | HTTP webhook receiver, `--bind` arg required | `src/main.rs:131` |
| `focalpoint-mcp-server` | `crates/focus-mcp-server` | MCP over HTTP/SSE, default `127.0.0.1:8473`, default insecure bearer token if env unset | `src/transport/http_sse.rs:105-124` |
| `teamcomm-daemon` | `crates/teamcomm-daemon` | Team-comm daemon, Unix socket + pidfile | `src/main.rs:153` (`--socket-path`), `src/config.rs` |
| `sharecli-ipc` | `crates/sharecli-ipc` | Unix-socket IPC server (`~/.local/share/sharecli/ipc.sock`) | `src/main.rs:3,133-138` |
| `gateway-tools` | `crates/gateway-tools` | `serve` subcommand: axum HTTP cockpit `GET /health /v1/cast /v1/util /v1/splash /v1/inspect/<module>`, default **8081** | `src/main.rs:146` |
| `substrate` | `crates/driver-cli` | Substrate driver CLI | `[[bin]] name = "substrate"` |
| `substrate-http` | `crates/driver-http` | HTTP driver: `TcpListener::bind(addr)` (hyper/axum server) | `crates/apisync/...` pattern; driver-http bin |
| `start_api` (agileplus-api lib) | `crates/agileplus-api` | HTTP API server; bind host from `API_HOST`/`AGILEPLUS_API_HOST` (default `0.0.0.0`), port from `AppConfig.api.port` | `src/main.rs:20,58-68`; `src/router.rs:173` |
| `teamb2-30100-vllm` (unit only) | `serving/` | vLLM service unit, port 30100 implied by unit name | `serving/tb2-30100-vllm.service` — **binary presence not proven** |
| `phenotype-daemon` (2nd def) | `crates/pheno-agent/phenotype-daemon` | see §8 conflict note | as above |

### 1b. Notable one-shot / tool binaries (no listener)

`qgate`, `ptx`, `audit-privacy`, `agent-forecast`, `airlock-v2`, `tokenledger`, `fabric-tui`,
`substrate-tui`, `configra-ops`, `eyetracker`, `docs-health`, `doc-link-check`, `fr-trace`,
`fr-coverage`, `wtm`, `hexakit`, `phenotype-router`, `agileplus`, `agileplus-governance`,
`agileplus-mcp-intent`, `agileplus-agent-service`, `sharecli`, `sharecli-tray-linux`,
`sharecli-tray-windows`, `sbom-gen`, `perfharness`, `commit-msg-check`, `acceptance-contract`,
`phenotype-manifest`, `dump-schema`, `phenotype-forge`, `pheno-compose`, `pheno-forge-smoke`,
`pheno-sidecar-stub`, `pareto-server`, `anthropic-usage-poll`, `argis-monitor`.

### 1c. Fuzz / test-only / build-only bins (not runtime surface)

`parse_message`, `fuzz_target_1`, `fuzz_queue_enqueue`, `fuzz_bloom_filter`, `parse_backlog`,
`router_dispatch`, `uniffi-bindgen` (x2), `xtask-anti-patterns`, `perf_gate`, `fuse-mount-smoke`,
`fuse-smoke`, `breach_sim`, `sidekick-healthcheck`, `eidolon-vsock-agent`,
`eidolon-xcui-helper`, `playcua-app`, `focalpoint-icon-gen`, `focalpoint-fetch-assets`,
`fabric-gui` (Tauri — see §5).

---

## 2. Service / daemon table

| Service | Port / socket | Protocol | Supervised by | Evidence |
|---|---|---|---|---|
| `fabric-daemon` | **9400** (wire, TCP JSON), **9401** (Prometheus metrics) | TCP JSON + HTTP metrics | systemd (`deploy/systemd/fabric-daemon.service`), Docker compose (`docker-compose.yml`) | `docker-compose.yml:21-23`; unit file |
| `fabric-daemon` (standalone listen arg) | configurable via `--listen` / `FABRIC_LISTEN` | TCP | — | `crates/fabric-daemon/src/main.rs:48,104` |
| `brokerd` (browser lease broker) | **127.0.0.1:8787** | HTTP, lease + fencing token | systemd + launchd (`com.kooshapari.browser-broker.plist`) | `crates/substrate-browser-broker/src/main.rs:36`; `deploy/browser-broker/*` |
| `browser-broker-mcp` | **stdio only** (no socket) | MCP JSON-RPC over stdin/stdout | launched by harness | `crates/substrate-browser-mcp/src/bin/browser-broker-mcp.rs:1-4` |
| `phinbox` inbox daemon | **7117** (default) + Unix socket | HTTP + Unix socket | CLI `phinbox daemon`, lockfile in inbox root | `crates/phinbox/src/inbox/daemon/mod.rs:42,105`; `ipc/server.rs:36` |
| `phenotype-daemon` | Unix `/tmp/phenotype-daemon.sock`; TCP `127.0.0.1:9456` (main.rs) | JSON-RPC over UDS or TCP | manual | `crates/pheno-agent/phenotype-daemon/src/main.rs:25,28,69,88` |
| `teamcomm-daemon` | Unix socket + pidfile (paths from config) | Unix socket | manual | `crates/teamcomm-daemon/src/main.rs:153`; `config.rs:62` |
| `sharecli-ipc` | `~/.local/share/sharecli/ipc.sock` | Unix socket | manual / tray app | `crates/sharecli-ipc/src/main.rs:133-138` |
| `focalpoint-webhook-server` | `--bind` (no default proven) | HTTP | manual | `crates/focus-webhook-server/src/main.rs:131` |
| `focalpoint-mcp-server` | **127.0.0.1:8473** (default) | MCP over HTTP/SSE (`/mcp/tools`, `/mcp/events`, `/mcp/tool/:name`) | manual; env `FOCALPOINT_MCP_HTTP_ADDR` | `crates/focus-mcp-server/src/transport/http_sse.rs:105-124` |
| `gateway-tools serve` | **8081** (default, explicitly chosen to avoid gateway's :8080) | HTTP (axum 0.8) | manual | `crates/gateway-tools/src/main.rs:146` |
| `agileplus-api` | `API_HOST:AppConfig.api.port` | HTTP | manual | `crates/agileplus-api/src/main.rs:58-68` |
| Prometheus (compose) | **9090** | HTTP | docker compose | `docker-compose.yml:59` |
| Grafana (compose) | **3000** | HTTP | docker compose | `docker-compose.yml:86` |
| PostgreSQL (plane compose) | **5432** | PG wire | docker compose | `docker-compose.plane.yml:25` |
| Redis (plane compose) | **6379** | Redis RESP | docker compose | `docker-compose.plane.yml:37` |
| Plane API (plane compose) | **8000** | HTTP | docker compose | `docker-compose.plane.yml:65` |
| Plane web (plane compose) | **3100→3000** | HTTP | docker compose | `docker-compose.plane.yml:84` |
| promptadapter | **8090** | HTTP | docker compose | `promptadapter/docker-compose.yml:7` |
| promptadapter redis | **6379** | Redis | docker compose | `promptadapter/docker-compose.yml:21` |
| infrakit (absorption) | **8000** | HTTP | docker compose | `absorption/PhenoInfra/infrakit/docker-compose.yml:17` |
| PhenoInfra | **8080** | HTTP | docker compose | `absorption/PhenoInfra/docker-compose.yml:6` |
| slm-server | **8000**, **8081** | HTTP | docker compose | `crates/argis-extensions/slm-server/docker-compose.yml:18,33` |
| argis-extensions redis / svc / svc2 | **6379**, **8090**, **8091** | mixed | docker compose | `crates/argis-extensions/docker-compose.yml:7,21,44` |
| datakit | **8080** | HTTP | docker compose | `crates/datakit/docker-compose.yml:6` |
| integration test stack | **50051** (gRPC), **8080**, **8081** | gRPC + HTTP | docker compose (test) | `tests/integration/docker-compose.test.yml:20-21,51` |
| `tb2-30100-vllm` | **30100** | HTTP (vLLM) | systemd unit present | `serving/tb2-30100-vllm.service` (unit only; binary presence unproven) |

Launchd units found live in-tree: 15 under `absorption/resume-all/launchd/`
(`com.REDACTED.resume-all-*.plist`) — these are **absorbed/vendored** artifacts, not
first-party runtime services of this repo.

---

## 3. MCP surface

| Server | Transport | Tools | Evidence |
|---|---|---|---|
| `browser-broker-mcp` (`brokerd` over MCP) | **stdio** (explicitly no socket) | Documents `broker_status`, `broker_acquire`, `broker_purge`, `broker_lease`/`release`, `broker_reap`, `broker_live` (tool names visible in `#[tool(name = "...")]`). Exact count **UNKNOWN** without full file read. | `crates/substrate-browser-mcp/src/bin/browser-broker-mcp.rs` |
| `phinbox_mcp` | stdio | Tool list not enumerated in the greps (router declares server name only); count **UNKNOWN** | `crates/phinbox/src/mcp/router.rs:97`, `src/bin_mcp.rs` |
| `focalpoint-mcp-server` | **HTTP/SSE** | `list_tools`, `invoke_tool` via `/mcp/tools`, `/mcp/tool/:tool_name`; count **UNKNOWN** | `crates/focus-mcp-server/src/transport/http_sse.rs`; `src/tools.rs` |
| `phenotype-mcp-sdk-rs` | library (transport abstraction) | not a server | `crates/agile-plus/crates/phenotype-mcp-sdk-rs/src/{lib,transport,macros}.rs` |
| `mcp-server` | library only (`src/lib.rs` only, no bin) | generic MCP registry (`McpServer`, `register_tool`) | `crates/mcp-server/src/lib.rs` |
| `driver-mcp` | library only (`src/lib.rs`) | no bin target | `crates/driver-mcp/src/lib.rs` |
| `teamcomm-mcp` | crate present | not inspected | `crates/teamcomm-mcp` |
| Plugin manifest servers | stdio, **Python** | 3 servers: `substrate` (`SUBSTRATE_HTTP_URL=http://127.0.0.1:8080`), `substrate-dispatch` (`OMNIROUTE_URL=http://127.0.0.1:20128`), `pheno-org` (`PARPOURA_BASE_URL=http://127.0.0.1:8001`) | `plugins/phenotype-bundle/mcp.json` |

Note: the plugin manifest declares **Python** servers that are **not** Rust binaries in this
repo (`servers/substrate/*.py`, `servers/pheno-org/*.py`). Their presence on disk is
**UNPROVEN** by these greps.

---

## 4. CLI surface

~50+ crates derive `clap::Parser` (`grep -rl 'clap::Parser|derive(Parser)'`). Principal CLI
entry points:

- `fabric` / `fabric-cli` — daemon client (`health`, `auth`, …)
- `fabric-tui`, `substrate-tui` — TUI clients (§5)
- `substrate` (driver-cli), `driver-http` server
- `phinbox` — `daemon`, `open`, `ask`, `inbox` subcommands (`src/cli/*.rs`)
- `phenotype-daemon`, `teamcomm-daemon`, `sharecli`, `sharecli-ipc`
- `agileplus` (two crates: `crates/agileplus-cli`, `crates/agile-plus/crates/agileplus-cli`)
- `agileplus-governance`, `agileplus-mcp-intent`, `agileplus-agent-service`
- `gateway-tools`, `brokerd`, `phenotype-router`, `hexakit`
- `ptx`, `qgate`, `tokenledger`, `airlock-v2`, `configra-ops`, `docs-health`, `doc-link-check`,
  `fr-trace`, `fr-coverage`, `sbom-gen`, `perfharness`, `wtm`, `eyetracker`
- `pheno-compose`, `phenotype-forge`, `phenotype-manifest`, `acceptance-contract`,
  `commit-msg-check`, `agent-forecast`, `anthropic-usage-poll`, `argis-monitor`, `pareto-server`
- `clikit` (`crates/Cmdra`)

---

## 5. GUI / TUI surface

| Surface | Crate | Kind | Evidence |
|---|---|---|---|
| `fabric-tui` | `crates/fabric-tui` | Terminal UI | `[[bin]] name = "fabric-tui"` |
| `substrate-tui` | `crates/substrate-tui` | Terminal UI | `[[bin]] name = "substrate-tui"` |
| `fabric-gui` | `crates/fabric-gui` (+ `src-tauri`, **workspace-excluded**) | Tauri desktop | `Cargo.toml` exclude list; `mkdir` not built in CI |
| `sharecli-tray-linux` / `-windows` | `crates/sharecli-tray-*` | System tray | `[[bin]]` targets |
| `fabric-tray` | `crates/fabric-tray` | System tray | `[[bin]]` |
| `eidolon-desktop`, `eidolon-mobile` | `crates/eidolon-*` | Desktop / mobile surfaces | workspace members |
| `phinbox-app` | `apps/phinbox-app` | GUI app (Info.plist) | `apps/phinbox-app/Info.plist` |
| `apps/desktop`, `apps/tooling` | `apps/*` | Tauri (Entitlements.plist) | `apps/desktop/Entitlements.plist`, `apps/tooling/src-tauri/Entitlements.plist` |
| `phinbox` tray | `crates/phinbox` | Tray URL served by daemon | `src/inbox/daemon/mod.rs:122` |

---

## 6. Configuration and environment variables

| Variable | Consumer | Default | Evidence |
|---|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | tracing substrate | `http://localhost:4317` | `.env.example` |
| `OTEL_SERVICE_NAME` | tracing | `phenotype-infra` | `.env.example` |
| `RUST_LOG` | all | `info` (+ `oci_*` debug) | `.env.example`; `phenotype-daemon` |
| `FABRIC_LISTEN` | fabric-daemon | (compose comment) `0.0.0.0:9400` | `docker-compose.yml:26` |
| `FABRIC_LOG_LEVEL` | fabric-daemon | `info` | `docker-compose.yml:27` |
| `API_HOST` / `AGILEPLUS_API_HOST` | agileplus-api | `0.0.0.0` | `agileplus-api/src/main.rs:59-62` |
| `DATABASE_URL` | agileplus-api | — | `agileplus-api/src/main.rs:37` |
| `FOCALPOINT_MCP_HTTP_ADDR` | focus-mcp-server | `127.0.0.1:8473` | `focus-mcp-server/.../http_sse.rs:105` |
| `FOCALPOINT_MCP_HTTP_TOKEN` | focus-mcp-server | `focalpoint-default-insecure-token` (**insecure default**) | `http_sse.rs:101` |
| `SUBSTRATE_HTTP_URL` | MCP plugin | `http://127.0.0.1:8080` | `plugins/phenotype-bundle/mcp.json` |
| `SUBSTRATE_TEAM_ID` / `SUBSTRATE_AGENT_NAME` | MCP plugin | `default` / `lead` | same |
| `OMNIROUTE_URL` | MCP plugin | `http://127.0.0.1:20128` | same |
| `PARPOURA_BASE_URL` | MCP plugin | `http://127.0.0.1:8001` | same |
| `BROKER_TOKEN` | brokerd | (required for non-loopback) | `deploy/browser-broker/browser-broker.service` |
| `CHROME_BIN` | brokerd | `/usr/bin/chromium` (unit) | same |
| `XDG_DATA_HOME` / `XDG_CONFIG_HOME` | phinbox, sharecli, klipdot, sharecli-fleet | per standard | `phinbox/src/inbox/mod.rs:258`, `sharecli-fleet/src/detect.rs:163` |
| `VITE_API_URL` etc. | AgilePlus dashboard web | `http://localhost:3000` | `.env.development.example` |

Compose env: `POSTGRES_USER` / `POSTGRES_PASSWORD` (plane). `LM_PROVIDER` / `REDIS_URL`
(promptadapter).

---

## 7. Runtime state locations on disk

| Path | Written by | Evidence |
|---|---|---|
| `~/Library/Application Support/phinbox` (macOS) / `$XDG_DATA_HOME/phinbox` | phinbox (inbox root, lockfile) | `crates/phinbox/src/inbox/mod.rs:251-263` |
| `~/Library/Application Support/...` | tokn / tokn-tokenledger ingest | `crates/tokn/src/ingest.rs:233-263`; `tokn-tokenledger/src/ingest/mod.rs:237-267` |
| `~/.local/share/sharecli/ipc.sock` | sharecli-ipc | `crates/sharecli-ipc/src/main.rs:133` |
| `~/.local/state/browser-broker` (default) / `/var/lib/browser-broker` (unit) | brokerd profile generations, leases | `substrate-browser-broker/src/main.rs:4`; unit `--root /var/lib/browser-broker` |
| `/var/lib/fabric` (container) / `./data` (host bind) | fabric-daemon SQLite | `docker-compose.yml:25`; unit `StateDirectory=fabric` |
| `/tmp/phenotype-daemon.sock` | phenotype-daemon UDS | `phenotype-daemon/src/main.rs:25` |
| teamcomm socket + pidfile | teamcomm-daemon | `teamcomm-daemon/src/config.rs:62` |
| `dirs::data_dir()` / `config_dir()` app dirs | klipdot-capture, pheno-terminal | `crates/klipdot-capture/src/util.rs:180-200` |
| `~/.config/...` config dirs | fabric-cli auth token dir; focus interceptor | `crates/fabric-cli/src/commands/auth.rs:176`; `pheno-terminal/src/interceptor.rs:626` |
| `/etc/fabric/config.toml`, `/etc/browser-broker.env` | system units | `deploy/systemd/*`, `deploy/browser-broker/*` |
| `~/.cache/huggingface` (bind) | slm-server container | `argis-extensions/slm-server/docker-compose.yml:20` |

---

## 8. Port collision / ownership map

| Port | Owner(s) | Collision? |
|---|---|---|
| **3000** | Grafana (compose), Plane web (host side 3100→3000 in container), Vite dashboard dev server | **Shared across compose stacks** — cannot all run simultaneously on host |
| **6379** | Redis: plane compose, promptadapter, argis-extensions; `agileplus-config` CacheConfig default | **4 declared owners** — same port reused by separate stacks |
| **8000** | Plane API, infrakit, slm-server, AgilePlus docker-compose | **4 declared owners** |
| **8080** | PhenoInfra, datakit, gateway default (implicitly, per comment), integration-test stack, `SUBSTRATE_HTTP_URL` | **Heavy contention**; `gateway-tools` explicitly dodges it by choosing 8081 |
| **8081** | gateway-tools (default), slm-server, integration-test stack | **3 owners** |
| **8090** | promptadapter, argis-extensions | **2 owners** |
| **8091** | argis-extensions svc2 | unique in repo |
| **5432** | PostgreSQL (plane compose) | unique |
| **7117** | phinbox inbox daemon | unique |
| **8473** | focalpoint-mcp-server | unique |
| **8787** | brokerd | unique |
| **9400 / 9401** | fabric-daemon wire / metrics | unique |
| **9456** | phenotype-daemon TCP (main.rs) | **CONFLICT:** `protocol.rs:186` declares `DEFAULT_TCP_PORT: u16 = 8953` while `main.rs:28` declares `9456` for the same constant name; which one executes depends on module resolution — **flag as defect / UNKNOWN at runtime** |
| **8953** | phenotype-daemon (protocol.rs alternate) | conflicts with 9456 above |
| **20128** | OmniRoute (external, referenced by MCP plugin) | external to repo |
| **8001** | Parpoura (external, referenced by MCP plugin) | external |
| **30100** | tb2-30100-vllm unit | unique |
| **50051** | gRPC (integration test stack) | test-only |
| **3284–4284** | `engine-agentapi` ephemeral port range | dynamic |
| **8317–9317** | `cliproxy-adapter` ephemeral port range | dynamic |
| **3030** | `pheno-forge-smoke` sidecars default | unique |
| **4317** | OTLP collector (env default) | unique |

Also seen in source but loopback/dynamic: `127.0.0.1:0` (phinbox ask test), `12345`
(STUN test), `3478` (STUN protocol test) — test-only.

---

## 9. Declared but without a proven runnable entry point

| Declared thing | Status | Why |
|---|---|---|
| `serving/tb2-30100-vllm.service` | **UNKNOWN** | Systemd unit present; no matching binary/crate found in the workspace grep set |
| `plugins/phenotype-bundle/mcp.json` → `servers/substrate/*.py`, `servers/pheno-org/*.py` | **UNKNOWN** | Referenced by manifest; existence of `.py` files not proven by these greps |
| `compose/substrate-gateway.json`, `compose/forge-daemon.json` | **UNKNOWN** | Compose-directory manifests; not inspected as runtime entry points |
| `crates/forge_daemon` | **NOT BUILT** | Explicitly in workspace `exclude` list (`Cargo.toml`) |
| `crates/fabric-gui/src-tauri` | **NOT BUILT IN CI** | Workspace-excluded (GTK/WebKit/libsoup build constraint) |
| `crates/driver-mcp` | **LIBRARY ONLY** | `src/lib.rs` present, no `[[bin]]` |
| `crates/mcp-server` | **LIBRARY ONLY** | `src/lib.rs` generic registry, no bin |
| `teamb2-30100` / vLLM serving | **UNKNOWN** | See above |
| 15 launchd `com.REDACTED.resume-all-*.plist` | **ABSORBED** | Under `absorption/resume-all/`; vendored, not first-party |
| `apps/bench-cockpit`, `apps/byteport` | **UNKNOWN** | Listed under `apps/` but no bin target captured in the `[[bin]]` sweep |
| Phinbox MCP tool count | **UNKNOWN** | Router declares server name `phinbox_mcp`; tool enumeration requires a full file read beyond budget |
| `teamcomm-mcp` tools | **UNKNOWN** | Crate present, not inspected |
| Substrate browser MCP exact tool count | **UNKNOWN** | Six `#[tool(name=...)]` names visible; grep not exhaustive |
| `phenotype-daemon` effective TCP port | **CONFLICT** | 9456 vs 8953 declared in two modules of the same crate |
| Motion of `fabric-daemon` default listen addr | **UNKNOWN** | `--listen` is `Option<String>`; actual default comes from `fabric-daemon` config (not opened) |

---

## Appendix — method / budget notes

- ~13 bash invocations used. All recursive searches rooted at the repo
  (`/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`), never `$HOME` or `/`.
- `find` bounded with `-maxdepth 3-4`; excludes applied to `target/`.
- No git commands run. No writes inside the repo; only the report file in
  `PhenoShared-space/analysis/2026-11-10-forensic/`.
- Counts: 438 workspace membership lines, 117 `[[bin]]` targets, 19 compose files,
  5 first-party systemd units (2 in `deploy/`, 1 `teamcomm-daemon.service`, 1 `serving/`,
  1 `scripts/cron/*.plist`), 6 MCP-related crates.
