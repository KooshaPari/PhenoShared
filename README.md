# PhenoShared

Shared infrastructure workspace for the [Phenotype](https://github.com/KooshaPari)
org. It is a container repository, not a single-purpose project: it holds the
shared Rust crates, the reusable GitHub Actions workflows and composite actions,
and the shared documentation (including the Global Handbook) that the rest of the
fleet consumes.

Local clones of this repo are often still checked out as `repos/pheno`; the
canonical GitHub name is `KooshaPari/PhenoShared`, and `KooshaPari/pheno`
redirects to it.

## At a glance

| Field | Value | How measured |
| --- | --- | --- |
| Root workspace packages | **76** | `cargo metadata --no-deps` (2026-09-17) |
| `[workspace].members` entries | 73, plus 3 path-dep members | `Cargo.toml` |
| Binary targets in root workspace | **16** | `cargo metadata --no-deps` |
| First-level crate manifests under `crates/` | **329** | `ls crates/*/Cargo.toml` |
| Nested Cargo workspaces under `crates/` | **26** | `grep -rl '^\[workspace\]' --include=Cargo.toml` |
| Workspace version | `0.3.10` | `[workspace.package]` |
| Rust edition / MSRV | 2021 / `rust-version = "1.80"` | `Cargo.toml` |
| Unsafe code | `forbid` workspace-wide | `[workspace.lints.rust]` |
| Reusable workflow files | **84** | `find .github/workflows -maxdepth 1 -name '*.y*ml'` |
| Composite actions | **5** | `ls -d .github/actions/*/` |
| Markdown files under `docs/` | 2,507 | `find docs -name '*.md'` |
| ADRs | 82 in `docs/adr/`, 25 in `docs/adrs/` | directory listing |
| Registered project manifests | 178 | `projects/*.json` |
| License | `MIT OR Apache-2.0` | `Cargo.toml`, `LICENSE-MIT`, `LICENSE-APACHE` |

## What this repository is

Three cross-org functions are co-located in one workspace:

| Function | Location | Scope |
| --- | --- | --- |
| Shared Rust crates | `crates/` | 329 first-level manifests; 76 packages in the root workspace |
| Reusable workflows | `.github/workflows/` | 84 workflow files, called from other repos |
| Shared actions | `.github/actions/` | 5 composite actions |
| Shared docs | `docs/`, `handbook/` | Global Handbook, ADRs, absorption records, session artifacts |

The workspace consolidates infrastructure, tooling, agent frameworks, connectors,
compute-mesh IaC, and ecosystem governance that previously lived across many
standalone repositories. The absorption trail is recorded in
[`docs/ABSORPTION_INDEX.md`](docs/ABSORPTION_INDEX.md) and `docs/absorption/`
(33 per-project records).

## The substrate spine

The root workspace builds around `substrate`, the Tier 0 dispatch spine. It
routes a task to the best available coding engine through a deterministic planner
and a set of hexagonal ports, so consumers depend on one facade instead of wiring
adapters by hand. The dependency direction is enforced mechanically by
`arch-test`, which fails the build when an edge crosses the domain/adapter
boundary the wrong way.

### Core spine

| Crate | Path | Role |
| --- | --- | --- |
| `substrate` | `crates/substrate` | SDK facade: re-exports ports, domain types, planner, optional adapters. Features `app`, `spec`, `a2a`. |
| `substrate-core` | `crates/substrate-core` | Hexagonal core contracts (domain + ports). Depends only on `serde`, `thiserror`, `uuid`, `async-trait`. |
| `substrate-app` | `crates/substrate-app` | Application layer: `DispatchService` use-case and `DispatchPlanner`, generic over the core ports. |
| `engine-spec` | `crates/engine-spec` | Provider-agnostic `TaskSpec` to argv contract. |
| `arch-test` | `crates/arch-test` | Architecture conformance tests: enforces hexagonal dependency direction. |

### Inbound drivers

| Crate | Binary | Role |
| --- | --- | --- |
| `driver-cli` | `substrate` | Composition-root CLI: `dispatch`, `plan`, `argv`, `cloud-dispatch`, `serve`. |
| `driver-http` | `substrate-http` | HTTP/REST inbound driver for dispatch, planning, routing, and the A2A mailbox. |
| `driver-argv` | — | Multi-provider argv builders ported from `thegent-dispatch`. |
| `driver-mcp` | — | MCP inbound driver bridging `EnginePort`/`RoutingPort`/`ToolPort` over stdio JSON-RPC. |
| `context-budget` | — | `EnginePort` middleware enforcing per-conversation token budgets (reject/truncate/warn). |

### Engine adapters

| Crate | Role |
| --- | --- |
| `engine-forge` | `EnginePort` adapter driving the `forge` CLI. |
| `engine-codex` | `EnginePort` adapter for the `codex` CLI. |
| `engine-claude` | `EnginePort` adapter for the `claude` CLI (Claude Code). |
| `engine-agentapi` | HTTP client plus child-process manager for `agentapi-plusplus`. |
| `engine-a2a` | `EnginePort` adapter for the A2A Agent-to-Agent REST protocol. |
| `engine-conformance` | Conformance suite proving `EnginePort` stays harness-agnostic across adapters. |
| `cliproxy-adapter` | `EnginePort` adapter for `cliproxyapi-plusplus` (50+ agent CLIs behind one OpenAI-compatible endpoint). |

### Routing, ports, and transports

| Crate | Role |
| --- | --- |
| `phenotype-router` | Phenotype-owned router decision layer (ADR-050/051) with OTel-native span emission. |
| `routing-phenotype-router` | `RoutingPort` adapter delegating decisions to `phenotype-router`. |
| `omniroute-adapter` | `RoutingPort` adapter pointing forge's `openai_compatible` provider at OmniRoute. |
| `transport-file` | File-backed `TransportPort`: append-only JSONL mailboxes with lockfile-lease claim. |
| `store-file` | File-backed `StorePort`: one JSON file per task/result. |
| `store-sqlite` | SQLite-backed `MailboxStore`, `ClaimPort`, `MemoryPort`, `EventStorePort` adapters. |
| `runtime-process` | `ProcessPort`: cross-platform managed subprocess via `command-group`. |
| `file-watcher` | `WatcherPort`: debounced filesystem events via `notify`. |
| `substrate-serve-lock` | Lock-based single-instance guard for `substrate serve`. |

### Workflow and orchestration

| Crate | Role |
| --- | --- |
| `substrate-trace` | `TracePort` adapters: Noop, Recording, MultiTrace, AgilePlus, Tracera. |
| `substrate-schedule` | `SchedulePort`: cron/interval/daily/weekly `next_run` via `croner`. |
| `substrate-dag` | `WorkflowPort` DAG orchestration via `petgraph`. |
| `substrate-skills` | `SkillPort`/`ToolRegistry`: in-memory named skills with JSON-schema validation. |
| `substrate-memory` | `MemoryPort`: bounded ring buffer plus two-tier compose with `store-sqlite`. |
| `substrate-tui` | Terminal UI dashboard for the dispatch surface. |
| `substrate-a2a` | A2A-shaped wire schema (Task, Message, Artifact, Part); transport-agnostic. |
| `dispatch-bridge` | A2A/Wave envelope over HTTP+SSE+Unix-socket, wiring the spine across processes. |
| `phenotype-mcp` | MCP integration adapter for substrate routing and dispatch. |
| `supervisor` | Supervisor orchestration runtime for substrate workers. |
| `wave` | Parallel wave runner: N concurrent teammate lanes with sub-subagent fan-out. |
| `wave-3lane-tests` | Integration tests exercising sync, fanout, and tree lanes end to end. |
| `orchestrator` | `wave.toml` loader, dispatch trait, gated `claude -p` stream-json parser, JSONL watcher. |

### Cloud dispatch

| Crate | Role |
| --- | --- |
| `cloud-codex` | `CloudDispatchPort` adapter for OpenAI Codex Cloud. |
| `cloud-cursor` | `CloudDispatchPort` adapter for Cursor Cloud Agents (REST v1). |
| `cloud-kilo` | `CloudDispatchPort` adapter for Kilo (gateway LLM plus local git PR). |
| `cloud-dispatch-conformance` | Contract suite plus a fake `CloudDispatchPort` for the adapters above. |

## Absorbed crate families in the root workspace

### PhenoFabric (22 packages)

Physical execution substrate: capability inventory, topology, route compilation,
leases, surface isolation, and streaming.

| Crate | Role |
| --- | --- |
| `fabric-capability` | Capability discovery, descriptor signing, topology probing. |
| `fabric-capability-ffi` | C FFI bindings for `fabric-capability`. |
| `fabric-checker` | Cross-checks a capability probe against an application manifest; emits an admission decision. |
| `fabric-graph` | Topology graph model and route compilation. |
| `fabric-graph-cli` | Thin CLI over `fabric_graph::failover::replan()`; bridges Go callers without cgo. |
| `fabric-persist` | SQLite persistence for coordinator state. |
| `fabric-daemon` | Long-running coordinator: topology, leases, wire transport, health checks. |
| `fabric-orchestrator` | Wires coordinator, persist, wire server, and surface registry into one process. |
| `fabric-cli` (`fabric`) | Reference CLI: `cap`, `graph`, `route`, `workspace`. |
| `fabric-workspace` | Seat-leases and workspace state management. |
| `fabric-frame-transport` | HEVC/AV1 encoded frames over TCP for Parsec-style streaming. |
| `fabric-surface-mojo` | GPU compute surface backend with a Mojo FFI bridge. |
| `fabric-terminal` (`tf-web`, `tf-sync`) | Terminal mirroring: web server and sync tools. |
| `fabric-capture` | Windows Terminal content capture agent. |
| `fabric-tray` | System tray app: daemon lifecycle, quick actions, status. |
| `fabric-tui` | TUI dashboard for the daemon. |
| `fabric-gui` | Tauri v2 desktop shell with daemon integration. |
| `fabric-web` | Leptos WASM single-page frontend. |
| `fabric-research-ledger` | Research ledger surface. |
| `fabric-integration-tests` | Cross-crate integration tests. |
| `phenotype-nvms-adapter` | Maps `odin.nvms` application manifests onto Fabric capability descriptors. |
| `fabric-full-demo` (`fabric-full-demo`) | Boots daemon, loads topology, compiles routes, streams a test frame. |

### PhenoGfx (2 packages)

| Crate | Role |
| --- | --- |
| `phenotype-gfx` | Unified graphics kernel: voxel, LOD, streaming, postfx, water, voxelizer, terrain (ADR-004). |
| `phenotype-voxel` | Compatibility shim re-exporting the `phenotype-gfx` voxel kernel. |

### PhenoRegistry (3 packages)

| Crate | Role |
| --- | --- |
| `phenotype-project-registry` | Project registry. |
| `phenotype-service-registry` | Service registry and discovery with hexagonal port plus in-memory adapter. |
| `phenotype-health` | Health primitives for registry consumers. |

### PhenoInfra (3 packages)

| Crate | Role |
| --- | --- |
| `phenotype-crypto` | Hashing, symmetric encryption, key derivation, HMAC signatures. |
| `phenotype-observability` | Standardized header types and telemetry structures. |
| `phenotype-policy-engine` | Generic rule-based policy evaluation across domains. |

### Observability and test tooling

| Crate | Role |
| --- | --- |
| `pheno-otel` | Pinned OTLP export surface (`crates/argis-extensions/pheno-otel`). |
| `fake-forge` (`fake-forge`, `bench-fake-forge`) | Network-free fake forge for offline dispatch tests and benches. |
| `fake-codex-cloud` | Fake Codex Cloud endpoint for cloud-dispatch contract tests. |

## Crate inventory by prefix

First-level crate directories under `crates/`, grouped by naming prefix:

| Prefix | Count | Origin |
| --- | --- | --- |
| `pheno-*` | 117 | PhenoAI, PhenoAgent, and shared fleet primitives |
| `phenotype-*` | 75 | PhenoInfra, PhenoRegistry, cross-org infrastructure |
| `focus-*` | 43 | FocalPoint productivity platform |
| `agileplus-*` | 23 | AgilePlus planning and sync |
| `fabric-*` | 20 | PhenoFabric |
| `substrate-*` | 10 | substrate dispatch spine |
| `connector-*` | 9 | Connector integrations (GitHub, Linear, Notion, Fitbit, Strava, GCal, Readwise) |
| `eyetracker-*` | 8 | Eye tracking pipeline |
| `engine-*` | 7 | Engine adapters |
| `cloud-*` | 4 | Cloud dispatch adapters |
| `driver-*` | 4 | substrate inbound drivers |
| `eidolon-*` | 4 | Eidolon cross-platform surfaces |
| `store-*` | 2 | substrate store backends |
| `playcua-*` | 2 | PlayCua computer-use ports |
| others | ~60 | Standalone absorbed crates (sharecli, teamcomm, phenocompose, hexakit, and more) |

Not every manifest under `crates/` is a member of the root workspace. Some live
in nested sub-workspaces; see below.

## Beyond the root workspace

`crates/` also hosts **26 nested Cargo workspaces** that build independently:

- `crates/agile-plus/` — AgilePlus: domain, API, gRPC, sqlite, git, NATS,
  P2P sync, triage, telemetry.
- `crates/focus-*/`, `crates/connector-*` — FocalPoint platform (53 crates
  extracted from FocalPoint).
- `crates/phenocompose-*/` — PhenoCompose port traits, adapters, CLI.
- `crates/sharecli*/` — process/IO/syscall hypervisor with FUSE, mesh, fleet,
  and tray tiers.
- `crates/teamcomm-*/` — inter-agent coordination protocol, daemon, MCP server.
- `crates/pheno-proc-runtime/` — process runtime with queue and dedup fuzz
  targets.
- `crates/hexa-kit/`, `crates/argis-extensions/`, `crates/Cmdra/`,
  `crates/eyetracker-*/`, `crates/playcua-*/`.

Non-Rust surfaces:

| Path | What it is |
| --- | --- |
| `python/omlx_research/` | PhenoMLX research stack: `backends/`, `engines/`, `agents/`, `cli/`, `web.py`, `ports/`, `nanovm/`. |
| `cli/bin/omlx-research`, `cli/bin/omlx-cli` | PhenoMLX launchers. |
| `linux-client/`, `windows-client/`, `gui/` | PhenoMLX client launchers. |
| `scripts/phenotype-omlx-ready`, `scripts/phenotype-omlx-env.sh` | PhenoMLX readiness and environment wiring. |
| `projects/*.json` | 178 project registry manifests. |
| `sites/` | Astro/Bun landing site factory (see `SPEC.md`). |

## Reusable workflows

All workflows live in `.github/workflows/` and are referenced by other repos.
84 workflow files exist; the most-used groups:

| Category | Workflows |
| --- | --- |
| CI | `ci.yml`, `coverage.yml`, `e2e.yml`, `flaky-tests.yml` |
| Security | `codeql.yml`, `security-scan.yml`, `trufflehog.yml`, `secret-guard.yml`, `dependency-scan.yml` |
| Rust | `cargo-deny.yml`, `cargo-machete.yml`, `cargo-semver-checks.yml`, `deny.yml` |
| Release | `release.yml`, `release-binary.yml`, `release-crates.yml`, `release-npm.yml`, `publish.yml`, `sbom.yml` |
| Docs | `docs.yml`, `docs-check.yml`, `docs-lint.yml`, `docs-validation.yml`, `doc-links.yml` |
| Quality gates | `quality-gate.yml`, `policy-gate.yml`, `traceability-gate.yml`, `fr-coverage.yml` |
| Infrastructure / IaC | `terraform-plan.yml`, `tf-ci.yml`, `iac-rust.yml` |
| Governance and audit | `governance.yml`, `audit.yml`, `quarterly-audit.yml`, `no-idle-audit.yml` |
| Benchmarks and fuzzing | `bench.yml`, `benchmark.yml`, `fuzz.yml`, `fuzzing.yml` |

Every filename in the table above was verified present on 2026-09-17. See
[`.github/README.md`](.github/README.md) for the workflow-reference syntax.

## Composite actions

Five composite actions live in `.github/actions/`:

| Action | Description |
| --- | --- |
| `build-rust-binary` | Cross-platform Rust binary build |
| `run-benchmarks` | Benchmark runner |
| `run-tests` | Test runner with matrix support |
| `security-checks` | Aggregate security scanning |
| `setup-env` | Multi-tool environment setup |

## Quick start

Requires Rust stable (MSRV 1.80).

```bash
git clone git@github.com:KooshaPari/PhenoShared.git
cd PhenoShared

# Build the root workspace
cargo build --workspace

# Inspect the dispatch plan without spawning anything
cargo run -p driver-cli -- plan --engine forge --cwd . "fix the bug"

# Dispatch against the bundled network-free fake engine
cargo run -p driver-cli -- dispatch --fake --cwd . "echo hi"

# Provider-native argv for an external agent CLI
cargo run -p driver-cli -- argv --provider forge --prompt "hello" --dry-run

# Start the HTTP driver (single-instance guarded)
cargo run -p driver-cli -- serve
```

The `substrate` CLI reads engine binary locations from `FORGE_BIN`,
`CODEX_BIN`, `CLAUDE_BIN`, and `AGENTAPI_ENDPOINT`.

### PhenoMLX quick start

The absorbed PhenoMLX member keeps its own launchers and readiness check:

```bash
./scripts/phenotype-omlx-ready
./cli/bin/omlx-research doctor
./cli/bin/omlx-research inference --prompt "Hello" --policy auto
```

## Build, test, and quality gates

`Taskfile.yml` and `Makefile` mirror each other and drive plain Cargo, so they
work without extra tooling installed.

| Task | Command |
| --- | --- |
| Build | `cargo build --workspace` |
| Check | `cargo check --workspace --all-targets` |
| Format check | `cargo fmt --all --check` |
| Lint | `cargo clippy --workspace --all-targets -- -D warnings` |
| Test | `cargo test --workspace` |
| Architecture gate | `cargo test -p arch-test` |
| Dependency audit | `cargo deny check` (see `deny.toml`) |
| Coverage | `cargo tarpaulin` (see `tarpaulin.toml`) |
| Unused dependencies | `cargo machete` |

Equivalent entry points: `make check`, `make clippy`, `make verify`,
`make test-unit`, `task lint`, `task test`, `task fmt:check`.

CI runs `.github/workflows/ci.yml` across Rust, Python (ruff), Go, and
TypeScript, with `cargo-deny` advisories plus gitleaks and dependency review.

## Documentation map

Start with the canonical handbook rather than the root of `docs/`:

| Document | Purpose |
| --- | --- |
| [`docs/GLOBAL_HANDBOOK.md`](docs/GLOBAL_HANDBOOK.md) | Pinned canonical handbook for agent behavior, quality gates, portfolio, and delivery. Revision 2026-09-16. |
| [`docs/adr/`](docs/adr/) (82) and [`docs/adrs/`](docs/adrs/) (25) | Architecture decision records. |
| [`docs/ABSORPTION_INDEX.md`](docs/ABSORPTION_INDEX.md) | Which repositories were absorbed or retired, and where they went. |
| [`docs/absorption/`](docs/absorption/) (33) | Per-project absorption records. |
| [`docs/sessions/`](docs/sessions/) | Dated session artifacts: research, plans, DAG/WBS, validation. |
| [`docs/dossiers/`](docs/dossiers/) | Handoff dossiers for absorbed projects (PhenoRegistry, PhenoShared). |
| [`docs/architecture/`](docs/architecture/) | Port-trait and domain-model references. |
| [`handbook/`](handbook/) | Ecosystem handbook: specs, patterns, anti-patterns, ADRs. |
| [`crates/substrate/README.md`](crates/substrate/README.md) | SDK usage example and feature flags. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution workflow. |
| [`SECURITY.md`](SECURITY.md) | Vulnerability reporting. |
| [`llms.txt`](llms.txt) | Machine-readable repo orientation. |

## Known documentation debt

This repository is mid-consolidation, and several root-level documents are stale
artifacts from absorbed projects that still carry the wrong identity. They are
listed here so nobody is misled by them:

| File | Actual content | Status |
| --- | --- | --- |
| `ARCHITECTURE.md` | `phenotype-omlx` tier diagram | Wrong-project artifact; needs replacement covering the Rust spine. |
| `AGENTS.md` | `phenotype-omlx` agent contract | Wrong-project artifact. |
| `CHARTER.md` | `phenodocs` mission | Wrong-project artifact. |
| `PRD.md` | `phenotype-shared` requirements | Wrong-project artifact. |
| `SPEC.md`, `justfile` | `phenotype-landing` site factory | Scope-limited to `sites/`. |
| `SPINE.md` | `phenoDesign` spine declaration | Wrong-project artifact. |
| `docs/architecture.md` | `Pine` architecture draft | Wrong-project artifact. |
| `docs/architecture/overview.md`, `docs/architecture/ports.md` | AgilePlus port docs | Scoped to AgilePlus. |
| `CONTRIBUTING.md` | `Phenotype Fabric` | Scoped to an absorbed project. |
| `SECURITY.md` | `phenotype-shared-temp` | Scoped to an absorbed project. |
| `INDEX.md` | Phenotype Fabric document baseline | Scoped to Fabric. |
| 128 root-level `.md` files | Mixed provenance | Consolidation pending. |

Two further items:

- `Taskfile.yml`'s `ci` task calls `./scripts/ci-local.sh`, which is not present
  in the tree. Use `make check` or the Cargo commands above instead.
- `[workspace.package] repository` in `Cargo.toml` still points at a stale origin
  URL rather than `github.com/KooshaPari/PhenoShared`.

## Consuming PhenoShared

Crates:

```toml
[dependencies.phenotype-mcp]
git = "https://github.com/KooshaPari/PhenoShared"
package = "phenotype-mcp"
```

Or against a local clone:

```toml
[dependencies]
phenotype-mcp = { path = "../PhenoShared/crates/phenotype-mcp" }
```

Workflows: reference them from a consumer repo, for example

```yaml
jobs:
  ci:
    uses: KooshaPari/PhenoShared/.github/workflows/ci.yml@main
```

Repositories that consume these crates, workflows, or docs include
[phenotooling](https://github.com/KooshaPari/phenotooling),
[PhenoMLX](https://github.com/KooshaPari/PhenoMLX),
[HeliosLab](https://github.com/KooshaPari/HeliosLab), and other KooshaPari org
repos.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/GLOBAL_HANDBOOK.md`](docs/GLOBAL_HANDBOOK.md). Before adding a
cross-domain dependency, check whether an existing crate in the tables above
already covers it; the workspace prefers extending an adapter over a new parallel
implementation. Keep files under 500 lines, with 350 as the goal.

Agent-authored commits carry ledger trailers (`tx-agent`, `tx-validated`).
History is append-only: no force pushes and no history rewrites.

## Security

Report vulnerabilities per [`SECURITY.md`](SECURITY.md); do not open a public
issue for a suspected vulnerability. `gitleaks`, `cargo-deny`, CodeQL, and
dependency review run in CI.

## License

Dual-licensed under either of:

- MIT License — [`LICENSE-MIT`](LICENSE-MIT)
- Apache License 2.0 — [`LICENSE-APACHE`](LICENSE-APACHE)

at your option. The workspace default is
`[workspace.package] license = "MIT OR Apache-2.0"`. Third-party and vendored
code retains its upstream license; see `NOTICE` and per-crate `license` fields.
