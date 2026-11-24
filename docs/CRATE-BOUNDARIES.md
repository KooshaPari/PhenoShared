# PhenoShared — Crate Boundaries

Deliverable: **D15.2**.

## Coverage and method

- Method: `cargo metadata --no-deps --format-version 1`, run at the
  repository root on
  **2026-11-12**, parsed in place. Exit code 0.
- **Coverage: 291 of 291 crates.** The metadata reported
  `workspace_members = 291` and
  `packages = 291`; every one appears exactly once below.
- Layers are assigned from the crate's manifest path prefix, which is read from
  the metadata,
  not guessed: `crates/` (267), `absorption/` (20), `examples/` (1),
  `tools/` (2), `native/` (1).
- "Depended on by" lists **workspace** crates only, taken from the
  `dependencies` array of
  each member's metadata entry. A crate with `0` has no dependent inside
  this workspace; it may
  still be consumed from outside, published, or dead — that distinction is
  **not** resolved
  here.
- Paths are shown without the trailing `/Cargo.toml`.
- "Owns" is given per **family**, from the crate names, their paths and their
  dependency edges.
  Per-crate intent statements were not read out of 291 `lib.rs` files, so an
  individual crate's
  exact responsibility is `UNKNOWN` where the family statement does not cover it.

`cmd/dagrun` is **not** in this table: it is a separate Go module
(`module github.com/KooshaPari/dagrun`) and is invisible to Cargo. See
`../cmd/dagrun/CONSOLIDATION.md` and `../cmd/dagrun/TRACEABILITY.md`.

## Layer summary

| Layer         | Members | Shape                                                                                               |
| ------------- | ------- | --------------------------------------------------------------------------------------------------- |
| `crates/`     | 267     | the shared library and binary surface; 163 of these paths contain nested workspaces per `README.md` |
| `absorption/` | 20      | absorbed PhenoMLX perf core, all under `absorption/PhenoMLX-temp/perf-core/`                        |
| `examples/`   | 1       | demo binary                                                                                         |
| `tools/`      | 2       | test fakes                                                                                          |
| `native/`     | 1       | native binding                                                                                      |

Aggregates from the same run: **121** crates have at least one in-workspace
dependent, **170** have none. Highest: `substrate-core` 36,
`fabric-capability` 15, `engine-spec` 12, `fabric-graph` 12, `focus-domain` 10,
`hwledger-search-core` 9, `phenocompose-port-types` 9, `substrate-a2a` 8,
`agileplus-domain` 6, `fabric-checker` 6, `fabric-frame-transport` 6.

---

## Layer: `crates/` (267)

### Family: `agileplus-*` — spec-driven development domain

Owns the AgilePlus domain model and its persistence/integration edges
(cache, domain, events, git, github, graph, import, nats, triage).

| Crate                | Path                        | Depended on by                                           |
| -------------------- | --------------------------- | -------------------------------------------------------- |
| agileplus-cache      | crates/agileplus-cache      | 0                                                        |
| agileplus-domain     | crates/agileplus-domain     | 6 (agileplus-cache, agileplus-events, agileplus-git, +3) |
| agileplus-error-core | crates/agileplus-error-core | 0                                                        |
| agileplus-events     | crates/agileplus-events     | 0                                                        |
| agileplus-git        | crates/agileplus-git        | 0                                                        |
| agileplus-github     | crates/agileplus-github     | 0                                                        |
| agileplus-graph      | crates/agileplus-graph      | 0                                                        |
| agileplus-import     | crates/agileplus-import     | 0                                                        |
| agileplus-nats       | crates/agileplus-nats       | 0                                                        |
| agileplus-triage     | crates/agileplus-triage     | 1 (agileplus-github)                                     |

### Family: `substrate-*` — agent-execution substrate

Owns the agent runtime: core traits, app assembly, the browser sub-stack
(broker/cdp/mcp/provider), dag, memory, schedule, skills, trace, serve-lock,
tui. `substrate-core` is the hub of the workspace at 36 dependents.

| Crate                      | Path                              | Depended on by                                            |
| -------------------------- | --------------------------------- | --------------------------------------------------------- |
| substrate                  | crates/substrate                  | 1 (sharecli)                                              |
| substrate-a2a              | crates/a2a                        | 8 (dispatch-bridge, driver-http, driver-mcp, +5)          |
| substrate-app              | crates/substrate-app              | 4 (driver-cli, driver-http, driver-mcp, +1)               |
| substrate-browser          | crates/substrate-browser          | 3                                                         |
| substrate-browser-broker   | crates/substrate-browser-broker   | 2                                                         |
| substrate-browser-cdp      | crates/substrate-browser-cdp      | 1                                                         |
| substrate-browser-mcp      | crates/substrate-browser-mcp      | 0                                                         |
| substrate-browser-provider | crates/substrate-browser-provider | 0                                                         |
| substrate-core             | crates/substrate-core             | **36** (cliproxy-adapter, cloud-codex, cloud-cursor, +33) |
| substrate-dag              | crates/substrate-dag              | 0                                                         |
| substrate-memory           | crates/substrate-memory           | 0                                                         |
| substrate-schedule         | crates/substrate-schedule         | 0                                                         |
| substrate-serve-lock       | crates/substrate-serve-lock       | 1 (driver-cli)                                            |
| substrate-skills           | crates/substrate-skills           | 0                                                         |
| substrate-trace            | crates/substrate-trace            | 0                                                         |
| substrate-tui              | crates/substrate-tui              | 0                                                         |

### Family: `driver-*` and `engine-*` — transport and model backends

Owns two separable axes: a driver (argv/cli/http/mcp) and an engine
(claude/codex/forge/agentapi/a2a/spec) behind `engine-spec`, plus conformance
tests tying them together.

| Crate              | Path                      | Depended on by                                     |
| ------------------ | ------------------------- | -------------------------------------------------- |
| driver-argv        | crates/driver-argv        | 1 (driver-cli)                                     |
| driver-cli         | crates/driver-cli         | 0                                                  |
| driver-http        | crates/driver-http        | 1 (driver-cli)                                     |
| driver-mcp         | crates/driver-mcp         | 0                                                  |
| engine-a2a         | crates/engine-a2a         | 0                                                  |
| engine-agentapi    | crates/engine-agentapi    | 3                                                  |
| engine-claude      | crates/engine-claude      | 3                                                  |
| engine-codex       | crates/engine-codex       | 3                                                  |
| engine-conformance | crates/engine-conformance | 5                                                  |
| engine-forge       | crates/engine-forge       | 3                                                  |
| engine-spec        | crates/engine-spec        | 12 (cliproxy-adapter, driver-cli, driver-http, +9) |

### Family: `cloud-*` and routing adapters — hosted-engine bridges

Owns the cloud variants of coding engines and the adapters that front them.

| Crate                      | Path                              | Depended on by                             |
| -------------------------- | --------------------------------- | ------------------------------------------ |
| cloud-codex                | crates/cloud-codex                | 2 (cloud-dispatch-conformance, driver-cli) |
| cloud-cursor               | crates/cloud-cursor               | 1 (driver-cli)                             |
| cloud-dispatch-conformance | crates/cloud-dispatch-conformance | 1 (cloud-codex)                            |
| cloud-kilo                 | crates/cloud-kilo                 | 1 (driver-cli)                             |
| cliproxy-adapter           | crates/cliproxy-adapter           | 1 (driver-mcp)                             |
| llm-router                 | crates/llm-router                 | 0                                          |
| omniroute-adapter          | crates/omniroute-adapter          | 1 (llm-router)                             |
| phenotype-router           | crates/phenotype-router           | 1 (routing-phenotype-router)               |
| routing-phenotype-router   | crates/routing-phenotype-router   | 2 (driver-http, driver-mcp)                |
| phenotype-router-monitor   | crates/phenotype-router-monitor   | 0                                          |
| bifrost-routing            | crates/bifrost-routing            | 0                                          |

### Family: store / transport / protocol edges

Owns the pluggable persistence and wire formats used by the driver and
substrate layers.

| Crate              | Path                      | Depended on by      |
| ------------------ | ------------------------- | ------------------- |
| store-file         | crates/store-file         | 3                   |
| store-sqlite       | crates/store-sqlite       | 5                   |
| transport-file     | crates/transport-file     | 3                   |
| dispatch-bridge    | crates/dispatch-bridge    | 1 (substrate-tui)   |
| wave               | crates/wave               | 1 (dispatch-bridge) |
| wave-3lane-tests   | crates/wave-3lane-tests   | 0                   |
| supervisor         | crates/supervisor         | 1 (wave)            |
| runtime-process    | crates/runtime-process    | 1 (sharecli)        |
| mcp-server         | crates/mcp-server         | 0                   |
| phenotype-mcp      | crates/phenotype-mcp      | 1 (driver-mcp)      |
| config-schema      | crates/config-schema      | 0                   |
| configra-ops       | crates/configra-ops       | 0                   |
| context-budget     | crates/context-budget     | 0                   |
| dag-scheduler      | crates/dag-scheduler      | 0                   |
| datakit            | crates/datakit            | 0                   |
| agent-forecast     | crates/agent-forecast     | 0                   |
| temporal-grounding | crates/temporal-grounding | 0                   |

### Family: `fabric-*` — capture and desktop orchestration

Owns the desktop fabric: capability detection, frame transport, graph, daemon,
orchestrator,
persistence, and every UI surface (gui, tray, tui, web, terminal, mojo
surface).

| Crate                    | Path                            | Depended on by                                                  |
| ------------------------ | ------------------------------- | --------------------------------------------------------------- |
| fabric-capability        | crates/fabric-capability        | **15** (fabric-capability-ffi, fabric-checker, fabric-cli, +12) |
| fabric-capability-ffi    | crates/fabric-capability-ffi    | 0                                                               |
| fabric-capture           | crates/fabric-capture           | 0                                                               |
| fabric-checker           | crates/fabric-checker           | 6                                                               |
| fabric-cli               | crates/fabric-cli               | 0                                                               |
| fabric-daemon            | crates/fabric-daemon            | 3                                                               |
| fabric-frame-transport   | crates/fabric-frame-transport   | 6                                                               |
| fabric-graph             | crates/fabric-graph             | 12                                                              |
| fabric-graph-cli         | crates/fabric-graph-cli         | 0                                                               |
| fabric-gui               | crates/fabric-gui               | 0                                                               |
| fabric-integration-tests | crates/fabric-integration-tests | 0                                                               |
| fabric-orchestrator      | crates/fabric-orchestrator      | 0                                                               |
| fabric-persist           | crates/fabric-persist           | 5                                                               |
| fabric-research-ledger   | crates/fabric-research-ledger   | 0                                                               |
| fabric-surface-mojo      | crates/fabric-surface-mojo      | 1 (fabric-orchestrator)                                         |
| fabric-terminal          | crates/fabric-terminal          | 0                                                               |
| fabric-tray              | crates/fabric-tray              | 2                                                               |
| fabric-tui               | crates/fabric-tui               | 0                                                               |
| fabric-web               | crates/fabric-web               | 0                                                               |
| fabric-workspace         | crates/fabric-workspace         | 2                                                               |

### Family: `focus-*` — focus/discipline product line

Owns a full vertical: domain and events at the core,
rituals/rules/policy/rewards/penalties on
top, scheduler/calendar/planning/time for cadence, ui/mascot/coaching for
experience, audit and
observability for evidence.

| Crate               | Path                       | Depended on by |
| ------------------- | -------------------------- | -------------- |
| focus-always-on     | crates/focus-always-on     | 0              |
| focus-asset-fetcher | crates/focus-asset-fetcher | 0              |
| focus-audit         | crates/focus-audit         | 4              |
| focus-calendar      | crates/focus-calendar      | 2              |
| focus-ci-watcher    | crates/focus-ci-watcher    | 0              |
| focus-coaching      | crates/focus-coaching      | 3              |
| focus-crypto        | crates/focus-crypto        | 0              |
| focus-domain        | crates/focus-domain        | **10**         |
| focus-entitlements  | crates/focus-entitlements  | 0              |
| focus-events        | crates/focus-events        | 3              |
| focus-icon-gen      | crates/focus-icon-gen      | 0              |
| focus-mascot        | crates/focus-mascot        | 1              |
| focus-observability | crates/focus-observability | 1              |
| focus-penalties     | crates/focus-penalties     | 1              |
| focus-planning      | crates/focus-planning      | 2              |
| focus-policy        | crates/focus-policy        | 0              |
| focus-release-bot   | crates/focus-release-bot   | 1              |
| focus-rewards       | crates/focus-rewards       | 1              |
| focus-rituals       | crates/focus-rituals       | 0              |
| focus-rules         | crates/focus-rules         | 2              |
| focus-scheduler     | crates/focus-scheduler     | 1              |
| focus-sync-store    | crates/focus-sync-store    | 0              |
| focus-templates     | crates/focus-templates     | 0              |
| focus-time          | crates/focus-time          | 0              |
| focus-ui            | crates/focus-ui            | 0              |

### Family: `sharecli-*` — share/discovery CLI and its fleet

Owns the CLI front end plus the subsystems it composes: fleet, mesh, fuse, ipc,
session,
sync, thermal tui, native trays.

| Crate                 | Path                         | Depended on by |
| --------------------- | ---------------------------- | -------------- |
| sharecli              | crates/sharecli              | 2              |
| sharecli-core         | crates/sharecli-core         | 1              |
| sharecli-ffi          | crates/sharecli-ffi          | 0              |
| sharecli-fleet        | crates/sharecli-fleet        | 4              |
| sharecli-fuse         | crates/sharecli-fuse         | 3              |
| sharecli-ipc          | crates/sharecli-ipc          | 2              |
| sharecli-mesh         | crates/sharecli-mesh         | 2              |
| sharecli-session      | crates/sharecli-session      | 2              |
| sharecli-sync         | crates/sharecli-sync         | 1              |
| sharecli-thermal-tui  | crates/sharecli-thermal-tui  | 1              |
| sharecli-tray-linux   | crates/sharecli-tray-linux   | 1              |
| sharecli-tray-windows | crates/sharecli-tray-windows | 1              |
| spawn-core-sys        | crates/spawn-core-sys        | 1 (sharecli)   |

### Family: `teamcomm-*` — team communication

Owns the protocol, the client, the daemon, an MCP surface and a smoke harness.

| Crate              | Path                      | Depended on by |
| ------------------ | ------------------------- | -------------- |
| teamcomm-cli       | crates/teamcomm-cli       | 0              |
| teamcomm-client    | crates/teamcomm-client    | 1              |
| teamcomm-daemon    | crates/teamcomm-daemon    | 1              |
| teamcomm-mcp       | crates/teamcomm-mcp       | 0              |
| teamcomm-protocol  | crates/teamcomm-protocol  | 5              |
| teamcomm-smoke     | crates/teamcomm-smoke     | 0              |
| sidekick-messaging | crates/sidekick-messaging | 0              |

### Family: `hwledger-*` — hardware ledger and model explorer search

Owns two things at once: a hardware ledger (bench, cli) and a model-explorer
search stack
(core, index, ingest, rag, skills, tags, server, mcp, evals). All live under
`crates/hwledger/...`, i.e. nested inside a crate directory.

| Crate                  | Path                                                                   | Depended on by |
| ---------------------- | ---------------------------------------------------------------------- | -------------- |
| hwledger-bench-cockpit | crates/hwledger/crates/hwledger-bench-cockpit                          | 0              |
| hwledger-cli           | crates/hwledger/crates/hwledger-cli                                    | 0              |
| hwledger-explorer-cli  | crates/hwledger/apps/model-explorer/rust/crates/hwledger-cli           | 0              |
| hwledger-mcp           | crates/hwledger/apps/model-explorer/rust/crates/hwledger-mcp           | 0              |
| hwledger-search-core   | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-core   | 9              |
| hwledger-search-evals  | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-evals  | 0              |
| hwledger-search-index  | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-index  | 3              |
| hwledger-search-ingest | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-ingest | 1              |
| hwledger-search-rag    | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-rag    | 0              |
| hwledger-search-skills | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-skills | 1              |
| hwledger-search-tags   | crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-tags   | 0              |
| hwledger-server        | crates/hwledger/apps/model-explorer/rust/crates/hwledger-server        | 1              |

Note: `hwledger-explorer-cli` and `hwledger-cli` declare the **same directory**
(`.../rust/crates/hwledger-cli`). Two package names, one path — worth resolving,
since a path
shared by two members is not a normal Cargo layout. The cause is `UNKNOWN` here.

### Family: `eidolon-*` — desktop/mobile client surfaces

Owns a shared core with three consumer surfaces (desktop, mobile, sandbox); `eidolon-core`
is the only member with dependents, all three of them in-family.

| Crate           | Path                   | Depended on by                                       |
| --------------- | ---------------------- | ---------------------------------------------------- |
| eidolon-core    | crates/eidolon-core    | 3 (eidolon-desktop, eidolon-mobile, eidolon-sandbox) |
| eidolon-desktop | crates/eidolon-desktop | 0                                                    |
| eidolon-mobile  | crates/eidolon-mobile  | 0                                                    |
| eidolon-sandbox | crates/eidolon-sandbox | 0                                                    |

### Family: `eyetracker-*` — eye tracking

Owns camera capture, domain model, inference, math, an FFI edge and a CLI.

| Crate                | Path                        | Depended on by |
| -------------------- | --------------------------- | -------------- |
| eyetracker-camera    | crates/eyetracker-camera    | 3              |
| eyetracker-cli       | crates/eyetracker-cli       | 0              |
| eyetracker-core      | crates/eyetracker-core      | 2              |
| eyetracker-domain    | crates/eyetracker-domain    | 4              |
| eyetracker-ffi       | crates/eyetracker-ffi       | 0              |
| eyetracker-inference | crates/eyetracker-inference | 2              |
| eyetracker-math      | crates/eyetracker-math      | 1              |

### Family: `pheno-compose-*` / `phenocompose-*` — compose runtime

Owns a port-and-adapter design: `-port-types` is the shared vocabulary (9
dependents), with
composer/di/runtime/publisher/secret ports and apple-container, wslc, secret-file,
plugin and
agentctl adapters.

| Crate                                | Path                                         | Depended on by           |
| ------------------------------------ | -------------------------------------------- | ------------------------ |
| pheno-cache-adapter                  | crates/pheno-cache-adapter                   | 0                        |
| pheno-compose-driver                 | crates/pheno-compose-driver                  | 0                        |
| pheno-config                         | crates/pheno-compose-pheno-config            | 1 (pheno-compose-driver) |
| nvms-ffi                             | crates/pheno-compose-bindings                | 1 (pheno-compose-driver) |
| pheno-i18n                           | crates/pheno-compose-i18n                    | 0                        |
| phenocompose-agentctl                | crates/pheno-compose-agentctl                | 0                        |
| phenocompose-apple-container-adapter | crates/pheno-compose-apple-container-adapter | 0                        |
| phenocompose-cli                     | crates/pheno-compose-phenocompose-cli        | 0                        |
| phenocompose-plugin-api              | crates/pheno-compose-plugin-api              | 1                        |
| phenocompose-plugin-sample           | crates/pheno-compose-plugin-sample           | 0                        |
| phenocompose-port-composer           | crates/pheno-compose-port-composer           | 2                        |
| phenocompose-port-di                 | crates/pheno-compose-port-di                 | 0                        |
| phenocompose-port-publisher          | crates/pheno-compose-port-publisher          | 2                        |
| phenocompose-port-runtime            | crates/pheno-compose-port-runtime            | 4                        |
| phenocompose-port-secret             | crates/pheno-compose-port-secret             | 2                        |
| phenocompose-port-types              | crates/pheno-compose-port-types              | **9**                    |
| phenocompose-secret-file-adapter     | crates/pheno-compose-secret-file-adapter     | 0                        |
| phenocompose-wslc-adapter            | crates/pheno-compose-wslc-adapter            | 0                        |

### Family: `pine-*` — sandbox / syscall runtime

Owns the syscall layer, a compat shim, a loader, the NVMS bridge and the core
model.

| Crate        | Path                | Depended on by |
| ------------ | ------------------- | -------------- |
| pine-compat  | crates/pine-compat  | 0              |
| pine-core    | crates/pine-core    | 4              |
| pine-loader  | crates/pine-loader  | 0              |
| pine-nvms    | crates/pine-nvms    | 0              |
| pine-syscall | crates/pine-syscall | 0              |

### Family: `phenotype-*` — org-wide primitives

Owns the lowest layer of the workspace: errors, config, crypto, observability,
retry,
rate-limit, ports, tracing, telemetry, iter, time, string, diff, health,
resilience.

| Crate                            | Path                                    | Depended on by      |
| -------------------------------- | --------------------------------------- | ------------------- |
| phenotype-async-traits           | crates/phenotype-async-traits           | 0                   |
| phenotype-cache-adapter          | crates/phenotype-cache-adapter          | 0                   |
| phenotype-casbin-wrapper         | crates/phenotype-casbin-wrapper         | 0                   |
| phenotype-config                 | crates/phenotype-config                 | 0                   |
| phenotype-config-core            | crates/phenotype-config-core            | 0                   |
| phenotype-contract               | crates/phenotype-contract               | 0                   |
| phenotype-contracts              | crates/phenotype-contracts              | 0                   |
| phenotype-cost-core              | crates/phenotype-cost-core              | 0                   |
| phenotype-crypto                 | crates/phenotype-crypto                 | 0                   |
| phenotype-diff                   | crates/phenotype-diff                   | 0                   |
| phenotype-error-core             | crates/phenotype-error-core             | 5                   |
| phenotype-error-macros           | crates/phenotype-error-macros           | 0                   |
| phenotype-errors                 | crates/phenotype-errors                 | 0                   |
| phenotype-event-bus              | crates/phenotype-event-bus              | 0                   |
| phenotype-flags                  | crates/phenotype-flags                  | 0                   |
| phenotype-gfx                    | crates/phenotype-gfx                    | 1 (phenotype-voxel) |
| phenotype-git-core               | crates/phenotype-git-core               | 0                   |
| phenotype-health                 | crates/phenotype-health                 | 2                   |
| phenotype-http-client-core       | crates/phenotype-http-client-core       | 0                   |
| phenotype-iter                   | crates/phenotype-iter                   | 0                   |
| phenotype-journey-core           | crates/phenotype-journey-core           | 0                   |
| phenotype-journeys-observability | crates/phenotype-journeys-observability | 0                   |
| phenotype-logging                | crates/phenotype-logging                | 0                   |
| phenotype-macros                 | crates/phenotype-macros                 | 0                   |
| phenotype-nvms-adapter           | crates/phenotype-nvms-adapter           | 3                   |
| phenotype-observability          | crates/phenotype-observability          | 0                   |
| phenotype-observably-macros      | crates/phenotype-observably-macros      | 2                   |
| phenotype-policy-engine          | crates/phenotype-policy-engine          | 0                   |
| phenotype-port-interfaces        | crates/phenotype-port-interfaces        | 0                   |
| phenotype-port-traits            | crates/phenotype-port-traits            | 0                   |
| phenotype-ports-canonical        | crates/phenotype-ports-canonical        | 0                   |
| phenotype-process                | crates/phenotype-process                | 0                   |
| phenotype-project-registry       | crates/phenotype-project-registry       | 0                   |
| phenotype-rate-limit             | crates/phenotype-rate-limit             | 0                   |
| phenotype-resilience             | crates/phenotype-resilience             | 0                   |
| phenotype-retry                  | crates/phenotype-retry                  | 0                   |
| phenotype-service-registry       | crates/phenotype-service-registry       | 0                   |
| phenotype-shared-config          | crates/phenotype-shared-config          | 0                   |
| phenotype-state-machine          | crates/phenotype-state-machine          | 0                   |
| phenotype-string                 | crates/phenotype-string                 | 0                   |
| phenotype-telemetry              | crates/phenotype-telemetry              | 0                   |
| phenotype-test-infra             | crates/phenotype-test-infra             | 0                   |
| phenotype-time                   | crates/phenotype-time                   | 0                   |
| phenotype-tooling-observability  | crates/phenotype-tooling-observability  | 1 (phinbox)         |
| phenotype-validation             | crates/phenotype-validation             | 0                   |
| phenotype-voxel                  | crates/phenotype-voxel                  | 0                   |

### Family: `pheno-*` (remaining shared utilities)

Owns smaller cross-cutting helpers that are not part of the `phenotype-`
primitive set.

| Crate                  | Path                               | Depended on by             |
| ---------------------- | ---------------------------------- | -------------------------- |
| pheno-context          | crates/pheno-context               | 0                          |
| pheno-crypto           | crates/pheno-crypto                | 0                          |
| pheno-errors           | crates/pheno-errors                | 2                          |
| pheno-flags            | crates/pheno-flags                 | 1                          |
| pheno-forge-scaffold   | crates/pheno-forge-scaffold        | 0                          |
| pheno-forge-smoke      | crates/pheno-forge-smoke           | 0                          |
| pheno-fs               | crates/pheno-fs                    | 0                          |
| pheno-net              | crates/pheno-net                   | 0                          |
| pheno-otel             | crates/argis-extensions/pheno-otel | 1 (substrate-trace)        |
| pheno-runtime-config   | crates/pheno-runtime-config        | 0                          |
| pheno-schema-port      | crates/pheno-schema-port           | 0                          |
| pheno-shell            | crates/pheno-shell                 | 0                          |
| pheno-testing          | crates/pheno-testing               | 0                          |
| pheno-tracing          | crates/pheno-tracing               | 3                          |
| pheno-vcs-core         | crates/pheno-vcs-core              | 1 (worktree-manager)       |
| phenovcs-observability | crates/phenovcs-observability      | 1 (worktree-manager)       |
| nvms-manifest          | crates/nvms-manifest               | 1 (phenotype-nvms-adapter) |
| phinbox                | crates/phinbox                     | 0                          |

### Family: ledger / verification / governance

Owns traceability gates, acceptance contracts, benchmark guards and doc health
checks.

| Crate                   | Path                           | Depended on by    |
| ----------------------- | ------------------------------ | ----------------- |
| acceptance-contract     | crates/acceptance-contract     | 1 (dag-scheduler) |
| traceability-core       | crates/traceability-core       | 2                 |
| traceability-decorators | crates/traceability-decorators | 1                 |
| trace-gate              | crates/trace-gate              | 0                 |
| arch-test               | crates/arch-test               | 0                 |
| bench-guard             | crates/bench-guard             | 0                 |
| doc-link-check          | crates/doc-link-check          | 0                 |
| docs-health             | crates/docs-health             | 0                 |
| fr-coverage             | crates/fr-coverage             | 0                 |
| fr-trace                | crates/fr-trace                | 0                 |
| perfharness             | crates/perfharness             | 0                 |
| release-cut             | crates/release-cut             | 0                 |
| commit-msg-check        | crates/commit-msg-check        | 0                 |
| qgate                   | crates/qgate                   | 0                 |
| audit-privacy           | crates/audit-privacy           | 0                 |
| legacy-scan             | crates/legacy-scan             | 0                 |
| fuzz-setup              | crates/fuzz-setup              | 0                 |

### Family: file / process / environment utilities

Owns small OS-level helpers.

| Crate                | Path                        | Depended on by |
| -------------------- | --------------------------- | -------------- |
| file-watcher         | crates/file-watcher         | 0              |
| worktree-manager     | crates/worktree-manager     | 0              |
| airlock-v2           | crates/airlock-v2           | 0              |
| klipdot-capture      | crates/klipdot-capture      | 0              |
| logkit               | crates/logkit               | 0              |
| nexus                | crates/nexus                | 0              |
| orchestrator         | crates/orchestrator         | 0              |
| anthropic-usage-poll | crates/anthropic-usage-poll | 0              |

### Family: CLI extension helpers

Owns clap-based argument extensions and their example.

| Crate    | Path                     | Depended on by              |
| -------- | ------------------------ | --------------------------- |
| clap-ext | crates/clap-ext          | 2 (basic, worktree-manager) |
| basic    | crates/clap-ext-examples | 0                           |

---

## Layer: `absorption/` (20)

### Family: `absorption/PhenoMLX-temp/perf-core/*`

Owns absorbed PhenoMLX inference performance work: concurrency, kernels, Metal
runtime, model
plans, spec decode, tree attention, the `turbo-quant` family and its
multi-language surfaces
(C, Mojo, Nim, Zig), plus `native-abi` and the `fleet-proto` pair.

Location note: every one of these 20 members sits under a directory named
`-temp`. Whether
that is a staging area or the permanent home is `UNKNOWN`; the dossier records it
as a risk.

| Crate                | Path                                                    | Depended on by           |
| -------------------- | ------------------------------------------------------- | ------------------------ |
| concurrent-exec      | absorption/PhenoMLX-temp/perf-core/concurrent-exec      | 1 (concurrent-exec-cuda) |
| concurrent-exec-cuda | absorption/PhenoMLX-temp/perf-core/concurrent-exec-cuda | 0                        |
| eval-harness         | absorption/PhenoMLX-temp/perf-core/eval-harness         | 0                        |
| fleet-proto          | absorption/PhenoMLX-temp/perf-core/fleet-proto          | 1                        |
| fleet-proto-zeromq   | absorption/PhenoMLX-temp/perf-core/fleet-proto-zeromq   | 0                        |
| kernel-registry      | absorption/PhenoMLX-temp/perf-core/kernel-registry      | 2                        |
| metal-runtime        | absorption/PhenoMLX-temp/perf-core/metal-runtime        | 0                        |
| model-kernels        | absorption/PhenoMLX-temp/perf-core/model-kernels        | 3                        |
| model-plan           | absorption/PhenoMLX-temp/perf-core/model-plan           | 2                        |
| native-abi           | absorption/PhenoMLX-temp/perf-core/native-abi           | 5                        |
| regress-baseline     | absorption/PhenoMLX-temp/perf-core/regress-baseline     | 0                        |
| spec-decode          | absorption/PhenoMLX-temp/perf-core/spec-decode          | 1                        |
| tree-attention       | absorption/PhenoMLX-temp/perf-core/tree-attention       | 2                        |
| tree-attention-spirv | absorption/PhenoMLX-temp/perf-core/tree-attention-spirv | 0                        |
| turbo-quant          | absorption/PhenoMLX-temp/perf-core/turbo-quant          | 1                        |
| turbo-quant-c        | absorption/PhenoMLX-temp/perf-core/turbo-quant-c        | 1                        |
| turbo-quant-mojo     | absorption/PhenoMLX-temp/perf-core/turbo-quant-mojo     | 1                        |
| turbo-quant-nim      | absorption/PhenoMLX-temp/perf-core/turbo-quant-nim      | 1                        |
| turbo-quant-zig      | absorption/PhenoMLX-temp/perf-core/turbo-quant-zig      | 1                        |
| vpu-agents           | absorption/PhenoMLX-temp/perf-core/vpu/agents           | 0                        |

---

## Layer: `examples/` (1)

| Crate            | Path               | Depended on by | Owns                                                                             |
| ---------------- | ------------------ | -------------- | -------------------------------------------------------------------------------- |
| fabric-full-demo | examples/full-demo | 0              | a demo binary wiring the fabric stack; depended on by none, so it is a leaf demo |

## Layer: `tools/` (2)

| Crate            | Path                   | Depended on by | Owns                                                                                                     |
| ---------------- | ---------------------- | -------------- | -------------------------------------------------------------------------------------------------------- |
| fake-codex-cloud | tools/fake-codex-cloud | 0              | a fake cloud-codex endpoint for tests; no workspace dependents, so it is exercised out-of-band `UNKNOWN` |
| fake-forge       | tools/fake-forge       | 0              | a fake forge engine for tests; same as above                                                             |

## Layer: `native/` (1)

| Crate          | Path   | Depended on by | Owns                                                                                                                                                   |
| -------------- | ------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| playcua-native | native | 0              | native bindings for the playcua surface; it depends on `pheno-errors`, `pheno-flags` and `pheno-tracing`, so it sits at the top of that small sub-tree |

---

## What this document does not establish

1. **Per-crate responsibility.** The family statements are derived from names,
   paths and
   dependency edges. For 291 crates, individual intent needs a `lib.rs` read
   each.
2. **Why 170 crates have no in-workspace dependent.** External consumers,
   publication, and
   dead code are indistinguishable from metadata alone.
3. **The `README.md` drift.** `cargo metadata` reports 291 members on 2026-11-12;
   the README's
   at-a-glance table says 290 measured 2026-11-11. Neither was re-derived here
   beyond the
   metadata run.
4. **The two-packages-one-path anomaly** in `hwledger-explorer-cli` / `hwledger-cli`.
5. **Anything Cargo cannot see.** `cmd/dagrun` is a Go module and is excluded by
   construction;
   `docs/`, `.github/`, `scripts/` and similar trees are not workspace members.
