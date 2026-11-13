# Crates

Generated index of the publishable crates in this workspace.

Do not hand-edit. Regenerate with:

```
python3 scripts/gen-crates-readme.py
```

Requires Python 3.11 or newer. The index is derived from the workspace
manifests: the `[workspace] members` of `Cargo.toml` plus the path
dependencies they reach, minus anything under `[workspace] exclude`.
A crate is listed when its `[package] publish` flag does not forbid it:
`publish` absent, or present and neither `false` nor an empty list. An
inherited `publish.workspace = true` resolves to `[workspace.package].
publish`.

Each description is the crate's own: its `[package] description` (an
inherited `description.workspace = true` resolves to `[workspace.package]
description`), else the first prose line of the crate's own README. A
description longer than 140 characters is elided at a word
boundary and marked with an ellipsis.

Publishable crates: **227**

| Crate                              | Path                                                         | Description                                                                                                                                 |
| ---------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `acceptance-contract`              | `crates/acceptance-contract`                                 | Declarative acceptance-contract engine with hard and soft probes                                                                            |
| `agent-forecast`                   | `crates/agent-forecast`                                      | Per-category p50/p90 token budget forecasting from agent history                                                                            |
| `agileplus-cache`                  | `crates/agileplus-cache`                                     | —                                                                                                                                           |
| `agileplus-domain`                 | `crates/agileplus-domain`                                    | AgilePlus domain layer: core entities, configuration, credentials, ports, errors, governance, audit, and state-machine models. This crate…  |
| `agileplus-error-core`             | `crates/agileplus-error-core`                                | Unified error handling for AgilePlus ecosystem                                                                                              |
| `agileplus-events`                 | `crates/agileplus-events`                                    | Event sourcing engine for AgilePlus with append-only event storage, hash-chain verification, snapshot management, aggregate replay, and…    |
| `agileplus-git`                    | `crates/agileplus-git`                                       | —                                                                                                                                           |
| `agileplus-github`                 | `crates/agileplus-github`                                    | —                                                                                                                                           |
| `agileplus-graph`                  | `crates/agileplus-graph`                                     | —                                                                                                                                           |
| `agileplus-import`                 | `crates/agileplus-import`                                    | —                                                                                                                                           |
| `agileplus-nats`                   | `crates/agileplus-nats`                                      | —                                                                                                                                           |
| `agileplus-triage`                 | `crates/agileplus-triage`                                    | —                                                                                                                                           |
| `airlock-v2`                       | `crates/airlock-v2`                                          | Conservative auto-save / push daemon for git repositories (vendored from .airlock/bin/airlock-v2.py)                                        |
| `anthropic-usage-poll`             | `crates/anthropic-usage-poll`                                | Daemon polling Anthropic Admin API for token usage data                                                                                     |
| `audit-privacy`                    | `crates/audit-privacy`                                       | Privacy audit utility for phenotype-tooling                                                                                                 |
| `bench-guard`                      | `crates/bench-guard`                                         | Benchmark guard for phenotype-tooling                                                                                                       |
| `cliproxy-adapter`                 | `crates/cliproxy-adapter`                                    | EnginePort adapter for \<REDACTED>/cliproxyapi-plusplus — the Plus fork of router-for-me/CLIProxyAPI exposing 50+ agent CLIs (claude…       |
| `cloud-cursor`                     | `crates/cloud-cursor`                                        | CloudDispatchPort adapter for Cursor Cloud Agents (REST API v1).                                                                            |
| `cloud-kilo`                       | `crates/cloud-kilo`                                          | CloudDispatchPort adapter for Kilo — gateway LLM + local git PR (no cloud-agent REST API).                                                  |
| `commit-msg-check`                 | `crates/commit-msg-check`                                    | Commit-message checker for phenotype-tooling                                                                                                |
| `concurrent-exec`                  | `absorption/PhenoMLX-temp/perf-core/concurrent-exec`         | —                                                                                                                                           |
| `concurrent-exec-cuda`             | `absorption/PhenoMLX-temp/perf-core/concurrent-exec-cuda`    | CUDA-native sibling of concurrent-exec. Linux/Windows + NVIDIA only.                                                                        |
| `config-schema`                    | `crates/config-schema`                                       | Extensible configuration schema validation for JSON-based configs                                                                           |
| `configra-ops`                     | `crates/configra-ops`                                        | Observability and operations primitives for Configra services                                                                               |
| `dag-scheduler`                    | `crates/dag-scheduler`                                       | Run acceptance-contracts through a dependency-ordered DAG                                                                                   |
| `datakit`                          | `crates/datakit`                                             | Data transformation and ETL framework for the Phenotype ecosystem                                                                           |
| `docs-health`                      | `crates/docs-health`                                         | Scans markdown files for vale/markdownlint compliance and broken links                                                                      |
| `driver-argv`                      | `crates/driver-argv`                                         | Multi-provider argv builders ported from thegent-dispatch.                                                                                  |
| `eidolon-core`                     | `crates/eidolon-core`                                        | —                                                                                                                                           |
| `eidolon-desktop`                  | `crates/eidolon-desktop`                                     | —                                                                                                                                           |
| `eidolon-mobile`                   | `crates/eidolon-mobile`                                      | —                                                                                                                                           |
| `eidolon-sandbox`                  | `crates/eidolon-sandbox`                                     | —                                                                                                                                           |
| `engine-a2a`                       | `crates/engine-a2a`                                          | EnginePort adapter for the A2A Agent-to-Agent REST protocol.                                                                                |
| `engine-agentapi`                  | `crates/engine-agentapi`                                     | EnginePort HTTP client + child-process manager for agentapi-plusplus (multi-agent HTTP gateway over PTY).                                   |
| `engine-claude`                    | `crates/engine-claude`                                       | EnginePort adapter for the claude CLI (Claude Code).                                                                                        |
| `engine-codex`                     | `crates/engine-codex`                                        | EnginePort adapter for the codex CLI (gpt-codex-spark).                                                                                     |
| `engine-conformance`               | `crates/engine-conformance`                                  | Conformance suite proving EnginePort is harness-agnostic — run against any adapter.                                                         |
| `engine-spec`                      | `crates/engine-spec`                                         | Provider-agnostic TaskSpec -> argv contract.                                                                                                |
| `eval-harness`                     | `absorption/PhenoMLX-temp/perf-core/eval-harness`            | MMLU/GPQA/terminal-bench quality eval harness for TurboQuant+                                                                               |
| `eyetracker-camera`                | `crates/eyetracker-camera`                                   | Webcam capture module for eye tracking                                                                                                      |
| `eyetracker-cli`                   | `crates/eyetracker-cli`                                      | Eye tracker CLI application                                                                                                                 |
| `eyetracker-core`                  | `crates/eyetracker-core`                                     | —                                                                                                                                           |
| `eyetracker-domain`                | `crates/eyetracker-domain`                                   | —                                                                                                                                           |
| `eyetracker-ffi`                   | `crates/eyetracker-ffi`                                      | —                                                                                                                                           |
| `eyetracker-inference`             | `crates/eyetracker-inference`                                | ML inference pipeline for eye tracking                                                                                                      |
| `eyetracker-math`                  | `crates/eyetracker-math`                                     | —                                                                                                                                           |
| `fabric-capability`                | `crates/fabric-capability`                                   | Fabric capability discovery, descriptor signing, and topology probing                                                                       |
| `fabric-capability-ffi`            | `crates/fabric-capability-ffi`                               | C FFI bindings for fabric-capability                                                                                                        |
| `fabric-capture`                   | `crates/fabric-capture`                                      | Phenotype Fabric Windows Terminal content capture agent                                                                                     |
| `fabric-checker`                   | `crates/fabric-checker`                                      | PF-WP-011: cross-checks a Fabric capability probe against an application manifest and emits a structured admission decision.                |
| `fabric-daemon`                    | `crates/fabric-daemon`                                       | Long-running coordinator daemon for Phenotype Fabric. Manages topology, leases, wire transport, and health checks.                          |
| `fabric-graph`                     | `crates/fabric-graph`                                        | Fabric topology graph model and route compilation                                                                                           |
| `fabric-graph-cli`                 | `crates/fabric-graph-cli`                                    | Thin CLI binary that calls fabric_graph::failover::replan() and prints JSON. Bridges the Go cmd/checker and the Rust failover module…       |
| `fabric-orchestrator`              | `crates/fabric-orchestrator`                                 | End-to-end daemon orchestrator for Phenotype Fabric. Wires coordinator, persist, wire server, and surface registry into a single running…   |
| `fabric-persist`                   | `crates/fabric-persist`                                      | SQLite persistence layer for Phenotype Fabric coordinator state                                                                             |
| `fabric-research-ledger`           | `crates/fabric-research-ledger`                              | —                                                                                                                                           |
| `fabric-surface-mojo`              | `crates/fabric-surface-mojo`                                 | GPU compute surface backend with Mojo FFI bridge for Phenotype Fabric                                                                       |
| `fabric-terminal`                  | `crates/fabric-terminal`                                     | Phenotype Fabric terminal mirroring — web server and sync tools                                                                             |
| `fabric-workspace`                 | `crates/fabric-workspace`                                    | Fabric seat-leases and workspace state management                                                                                           |
| `fake-codex-cloud`                 | `tools/fake-codex-cloud`                                     | Network-free stand-in for `codex cloud` CLI, used by cloud-codex tests.                                                                     |
| `fake-forge`                       | `tools/fake-forge`                                           | A network-free stand-in for the forge CLI, used by tests and the --fake flag.                                                               |
| `fleet-proto`                      | `absorption/PhenoMLX-temp/perf-core/fleet-proto`             | —                                                                                                                                           |
| `fleet-proto-zeromq`               | `absorption/PhenoMLX-temp/perf-core/fleet-proto-zeromq`      | Fleet dispatch protocol — C++ ZeroMQ transport (libzmq via pkg-config)                                                                      |
| `focus-always-on`                  | `crates/focus-always-on`                                     | Habit predictor and nudge engine for the always-on agent pipeline.                                                                          |
| `focus-asset-fetcher`              | `crates/focus-asset-fetcher`                                 | Asset downloader and post-processor for FocalPoint audio resources. Fetches SFX and phoneme samples from manifest, post-processes via…      |
| `focus-audit`                      | `crates/focus-audit`                                         | Append-only audit log with tamper-evident SHA-256 hash chains. Each record commits to its predecessor's hash; the first record chains from… |
| `focus-calendar`                   | `crates/focus-calendar`                                      | Calendar port abstraction and in-memory reference implementation. Defines the trait contract that the scheduler and rule engine use to…     |
| `focus-ci-watcher`                 | `crates/focus-ci-watcher`                                    | CI integration monitor for FocalPoint. Polls `origin/main` at configurable intervals; when new commits are detected, clones into an…        |
| `focus-coaching`                   | `crates/focus-coaching`                                      | LLM provider trait and OpenAI-compatible HTTP client. Shapes POST `/chat/completions` calls with Bearer token authentication and simple…    |
| `focus-crypto`                     | `crates/focus-crypto`                                        | Token wrapping, secure secret storage abstraction, and integrity digests. Provides OS keychain integration (Apple Keychain on iOS/macOS…    |
| `focus-domain`                     | `crates/focus-domain`                                        | Canonical domain entities, IDs, aggregate roots, and invariants. Pure types with no persistence, no I/O. Defines `UserId`, `DeviceId`…      |
| `focus-entitlements`               | `crates/focus-entitlements`                                  | Subscription tier management and feature gates for FocalPoint.                                                                              |
| `focus-events`                     | `crates/focus-events`                                        | Normalized event schema, dedupe keys, trace references. Defines the canonical `NormalizedEvent` struct that all connectors emit. Events…    |
| `focus-icon-gen`                   | `crates/focus-icon-gen`                                      | Procedural app icon generator for FocalPoint. Renders a flame icon inspired by the Coachy mascot using pure Rust pixel manipulation…        |
| `focus-mascot`                     | `crates/focus-mascot`                                        | Coachy — the FocalPoint mascot state machine. Fiery flame-shaped coach with red cape and gold-star buckle. The Rust side owns logical…      |
| `focus-observability`              | `crates/focus-observability`                                 | —                                                                                                                                           |
| `focus-penalties`                  | `crates/focus-penalties`                                     | Penalty state machine: escalation tiers, bypass budget, lockout windows, debt balance, strict mode. Traces to FR-STATE-002. Manages…        |
| `focus-planning`                   | `crates/focus-planning`                                      | Task model for the Motion-layer scheduler. Traces to FR-PLAN-001. Provides pure data types the scheduler consumes: `Task`, `DurationSpec`…  |
| `focus-policy`                     | `crates/focus-policy`                                        | Enforcement policy generation from rule decisions. Traces to FR-ENF-001. Converts rule-fired events (e.g., "exceeded daily limit") into…    |
| `focus-release-bot`                | `crates/focus-release-bot`                                   | Discord webhook poster for FocalPoint release notes. Posts release notes to a Discord webhook as formatted embeds with fields for version…  |
| `focus-rewards`                    | `crates/focus-rewards`                                       | Reward wallet aggregate and mutations. Traces to FR-STATE-001. Manages earned_credits, spent_credits, streaks, unlock_balances…             |
| `focus-rituals`                    | `crates/focus-rituals`                                       | Coachy's Planning Coach personality. Traces to FR-RITUAL-001..004. Builds Sunsama-style Morning Brief ("what's your intention?") and…       |
| `focus-rules`                      | `crates/focus-rules`                                         | Rule DSL, evaluation, priority, cooldowns, explanation. Traces to FR-RULE-001..008. Defines `Rule` primitive: trigger (event type match)…   |
| `focus-scheduler`                  | `crates/focus-scheduler`                                     | Rigidity-aware task scheduler. Traces to FR-PLAN-002. Greedy priority-weighted bin-packing into free time between calendar events…          |
| `focus-sync-store`                 | `crates/focus-sync-store`                                    | Multi-device sync store trait and in-memory implementations. Defines abstract sync interface for syncing state (rules, tasks, wallet…       |
| `focus-templates`                  | `crates/focus-templates`                                     | Template-pack format: distributable bundle of focus `Rule` drafts plus recommended connectors and mascot-copy overrides. Serialized as…     |
| `focus-time`                       | `crates/focus-time`                                          | Clock abstraction for deterministic tests. Provides `ClockPort` trait with `SystemClock` (wall-clock) and `TestClock` (manually-advanced)…  |
| `focus-ui`                         | `crates/focus-ui`                                            | —                                                                                                                                           |
| `fr-coverage`                      | `crates/fr-coverage`                                         | FR coverage analysis for phenotype-tooling                                                                                                  |
| `fr-trace`                         | `crates/fr-trace`                                            | FR -> test traceability scanner (AgilePlus FR-\* convention)                                                                                |
| `hwledger-bench-cockpit`           | `crates/hwledger/crates/hwledger-bench-cockpit`              | Bench cockpit server — Rust Axum port of the Go server                                                                                      |
| `hwledger-cli`                     | `crates/hwledger/crates/hwledger-cli`                        | CLI tool for hwLedger dev servers, benchmarks, and service management                                                                       |
| `kernel-registry`                  | `absorption/PhenoMLX-temp/perf-core/kernel-registry`         | —                                                                                                                                           |
| `legacy-scan`                      | `crates/legacy-scan`                                         | Detects scripting-policy violations and deprecated library usage                                                                            |
| `llm-router`                       | `crates/llm-router`                                          | LLM routing with multi-provider support                                                                                                     |
| `logkit`                           | `crates/logkit`                                              | Zero-cost structured logging framework                                                                                                      |
| `mcp-server`                       | `crates/mcp-server`                                          | MCP protocol server implementation                                                                                                          |
| `metal-runtime`                    | `absorption/PhenoMLX-temp/perf-core/metal-runtime`           | Metal-only pipeline that takes a model-plan ModelPlan and produces an executable pipeline, with cache, bounded compilation, device…         |
| `model-kernels`                    | `absorption/PhenoMLX-temp/perf-core/model-kernels`           | Model-family kernel packages: attention, MoE, recurrent, diffusion, and quantization primitives with scalar oracles and Rust kernels.       |
| `model-plan`                       | `absorption/PhenoMLX-temp/perf-core/model-plan`              | Pure Rust domain crate: ModelPlan, OperatorPlan, StatePlan, scheduler policy, and reference interpreter for the Metal model runtime.        |
| `native-abi`                       | `absorption/PhenoMLX-temp/perf-core/native-abi`              | Versioned Native ABI v1 contract — shared between C, Zig, Rust, Mojo, Nim, Go backends                                                      |
| `nexus`                            | `crates/nexus`                                               | Service registry and discovery                                                                                                              |
| `nvms-ffi`                         | `crates/pheno-compose-bindings`                              | Rust FFI bindings to NVMS Go Core                                                                                                           |
| `nvms-manifest`                    | `crates/nvms-manifest`                                       | `odin.nvms` v0.2 schema + validator + JSON Schema emission.                                                                                 |
| `orchestrator`                     | `crates/orchestrator`                                        | L120 MVP orchestrator: TOML wave.toml loader, dispatch trait, claude -p stream-json parser (gated), JSONL WatcherPort adapter.              |
| `pheno-cache-adapter`              | `crates/pheno-cache-adapter`                                 | —                                                                                                                                           |
| `pheno-compose-driver`             | `crates/pheno-compose-driver`                                | PhenoCompose NVMS Driver - Rust interface to NVMS 3-tier isolation                                                                          |
| `pheno-crypto`                     | `crates/pheno-crypto`                                        | Cryptographic utilities for Pheno                                                                                                           |
| `pheno-errors`                     | `crates/pheno-errors`                                        | Canonical AppError type used across the phenotype/pheno-\* fleet. L5 #81 wiring for PlayCua.                                                |
| `pheno-flags`                      | `crates/pheno-flags`                                         | Env-driven boolean feature flags for PlayCua (and the rest of the pheno-\* fleet). L5 #81 wiring.                                           |
| `pheno-fs`                         | `crates/pheno-fs`                                            | Filesystem utilities for Pheno                                                                                                              |
| `pheno-net`                        | `crates/pheno-net`                                           | Network utilities for Pheno                                                                                                                 |
| `pheno-otel`                       | `crates/argis-extensions/pheno-otel`                         | OpenTelemetry OTLP exporter substrate for the pheno-\* fleet (ADR-037). Provides OtlpPort + Stdout/HttpExporter adapters; consumers depend… |
| `pheno-schema-port`                | `crates/pheno-schema-port`                                   | PhenoSchema hexagonal port definitions                                                                                                      |
| `pheno-shell`                      | `crates/pheno-shell`                                         | CLI shell framework for Pheno                                                                                                               |
| `pheno-testing`                    | `crates/pheno-testing`                                       | Testing utilities for Pheno                                                                                                                 |
| `pheno-tracing`                    | `crates/pheno-tracing`                                       | Canonical port-driven distributed tracing substrate for the pheno-\* fleet (ADR-036). Provides TracePort + InMemory/Stdout adapters…        |
| `pheno-vcs-core`                   | `crates/pheno-vcs-core`                                      | VCS primitives for PhenoVCS registry                                                                                                        |
| `phenotype-agent-contracts`        | `absorption-residue-Agentora/rust/phenotype-agent-contracts` | HTTP and agent adapter contract traits for the Phenotype ecosystem (Agentora terminal owner)                                                |
| `phenotype-async-traits`           | `crates/phenotype-async-traits`                              | —                                                                                                                                           |
| `phenotype-cache-adapter`          | `crates/phenotype-cache-adapter`                             | Phenotype shared crate                                                                                                                      |
| `phenotype-casbin-wrapper`         | `crates/phenotype-casbin-wrapper`                            | Casbin adapter providing policy enforcement for the Phenotype ecosystem                                                                     |
| `phenotype-config`                 | `crates/phenotype-config`                                    | Layered configuration for Phenotype tooling (figment + serde + env)                                                                         |
| `phenotype-config-core`            | `crates/phenotype-config-core`                               | Core configuration management for Phenotype                                                                                                 |
| `phenotype-contract`               | `crates/phenotype-contract`                                  | —                                                                                                                                           |
| `phenotype-contracts`              | `crates/phenotype-contracts`                                 | Hexagonal architecture ports and contracts for phenotype-infrakit                                                                           |
| `phenotype-cost-core`              | `crates/phenotype-cost-core`                                 | Cost calculation, pricing models, and budget enforcement for LLM operations                                                                 |
| `phenotype-crypto`                 | `crates/phenotype-crypto`                                    | Cryptographic utilities for Phenotype — hashing, symmetric encryption, key derivation, and HMAC signatures                                  |
| `phenotype-diff`                   | `crates/phenotype-diff`                                      | Line-level unified diff and patch-apply library (migrated from \<REDACTED>/Diffuse); wraps `similar`                                        |
| `phenotype-error-core`             | `crates/phenotype-error-core`                                | Canonical error types for Phenotype crates. Use this crate to keep API, domain, repository, configuration, storage, and wire-format errors… |
| `phenotype-error-macros`           | `crates/phenotype-error-macros`                              | Unified error handling macros for Phenotype ecosystem (result conversion, context enrichment, error propagation)                            |
| `phenotype-errors`                 | `crates/phenotype-errors`                                    | \*\*DEPRECATED\*\*: Use `phenotype-error-core` directly instead.                                                                            |
| `phenotype-event-bus`              | `crates/phenotype-event-bus`                                 | —                                                                                                                                           |
| `phenotype-flags`                  | `crates/phenotype-flags`                                     | Synchronous, in-memory feature-flag set with environment-variable loading                                                                   |
| `phenotype-gfx`                    | `crates/phenotype-gfx`                                       | Unified graphics kernel: voxel, LOD, streaming, postfx, water, voxelizer, terrain. Single Rust core per ADR-004.                            |
| `phenotype-git-core`               | `crates/phenotype-git-core`                                  | Phenotype git core crate                                                                                                                    |
| `phenotype-health`                 | `crates/phenotype-health`                                    | —                                                                                                                                           |
| `phenotype-http-client-core`       | `crates/phenotype-http-client-core`                          | Unified HTTP client patterns and pooling strategies for Phenotype ecosystem                                                                 |
| `phenotype-iter`                   | `crates/phenotype-iter`                                      | PhenoShared workspace member                                                                                                                |
| `phenotype-journey-core`           | `crates/phenotype-journey-core`                              | Shared types and verification logic for Phenotype journey manifests                                                                         |
| `phenotype-journeys-observability` | `crates/phenotype-journeys-observability`                    | OTel/OTLP observability for the phenotype-journeys workspace                                                                                |
| `phenotype-logging`                | `crates/phenotype-logging`                                   | —                                                                                                                                           |
| `phenotype-macros`                 | `crates/phenotype-macros`                                    | —                                                                                                                                           |
| `phenotype-mcp`                    | `crates/phenotype-mcp`                                       | Phenotype MCP integration adapter for substrate routing and dispatch.                                                                       |
| `phenotype-nvms-adapter`           | `crates/phenotype-nvms-adapter`                              | Bridge between odin.nvms v0.2 application manifests and Phenotype Fabric CapabilityDescriptors.                                             |
| `phenotype-observability`          | `crates/phenotype-observability`                             | Standardized header types and telemetry structures for Phenotype ecosystem                                                                  |
| `phenotype-policy-engine`          | `crates/phenotype-policy-engine`                             | Generic policy evaluation engine for Phenotype, supporting rule-based policy decision-making across all domains                             |
| `phenotype-port-traits`            | `crates/phenotype-port-traits`                               | —                                                                                                                                           |
| `phenotype-ports-canonical`        | `crates/phenotype-ports-canonical`                           | \*\*DEPRECATED\*\*: Use `phenotype-port-traits` directly instead.                                                                           |
| `phenotype-process`                | `crates/phenotype-process`                                   | —                                                                                                                                           |
| `phenotype-project-registry`       | `crates/phenotype-project-registry`                          | Project registry for Phenotype                                                                                                              |
| `phenotype-rate-limit`             | `crates/phenotype-rate-limit`                                | —                                                                                                                                           |
| `phenotype-resilience`             | `crates/phenotype-resilience`                                | Shared resilience primitives (rate limiter, circuit breaker, bulkhead) for Phenotype-org services                                           |
| `phenotype-retry`                  | `crates/phenotype-retry`                                     | —                                                                                                                                           |
| `phenotype-router-monitor`         | `crates/phenotype-router-monitor`                            | PhenoShared workspace member                                                                                                                |
| `phenotype-service-registry`       | `crates/phenotype-service-registry`                          | Service registry and discovery with hexagonal port + in-memory adapter (migrated from \<REDACTED>/Servion)                                  |
| `phenotype-shared-config`          | `crates/phenotype-shared-config`                             | Shared configuration types and utilities for Phenotype crates                                                                               |
| `phenotype-state-machine`          | `crates/phenotype-state-machine`                             | Phenotype shared crate                                                                                                                      |
| `phenotype-string`                 | `crates/phenotype-string`                                    | —                                                                                                                                           |
| `phenotype-telemetry`              | `crates/phenotype-telemetry`                                 | —                                                                                                                                           |
| `phenotype-test-infra`             | `crates/phenotype-test-infra`                                | —                                                                                                                                           |
| `phenotype-time`                   | `crates/phenotype-time`                                      | —                                                                                                                                           |
| `phenotype-tooling-observability`  | `crates/phenotype-tooling-observability`                     | OTel/OTLP observability for the phenotype-tooling workspace — Prometheus metrics, /health endpoint, SLOs                                    |
| `phenotype-validation`             | `crates/phenotype-validation`                                | PhenoShared workspace member                                                                                                                |
| `phenovcs-observability`           | `crates/phenovcs-observability`                              | PhenoVCS observability substrate — thin re-export of pheno-tracing (ADR-012, ADR-036)                                                       |
| `pine-compat`                      | `crates/pine-compat`                                         | —                                                                                                                                           |
| `pine-core`                        | `crates/pine-core`                                           | —                                                                                                                                           |
| `pine-loader`                      | `crates/pine-loader`                                         | —                                                                                                                                           |
| `pine-nvms`                        | `crates/pine-nvms`                                           | —                                                                                                                                           |
| `pine-syscall`                     | `crates/pine-syscall`                                        | —                                                                                                                                           |
| `playcua-native`                   | `native`                                                     | —                                                                                                                                           |
| `qgate`                            | `crates/qgate`                                               | Granular-recursive quality gate CLI: 85%+ coverage per-module, all check types, JSON+tree reports                                           |
| `regress-baseline`                 | `absorption/PhenoMLX-temp/perf-core/regress-baseline`        | Deterministic regression baselines for model-runtime kernels: record/verify a known-good (inputs, outputs) snapshot per kernel.             |
| `release-cut`                      | `crates/release-cut`                                         | Release-cut utility for phenotype-tooling                                                                                                   |
| `runtime-process`                  | `crates/runtime-process`                                     | ProcessPort implementation: cross-platform managed subprocess via command-group.                                                            |
| `sharecli`                         | `crates/sharecli`                                            | Shared CLI process manager for multi-project agent orchestration                                                                            |
| `sharecli-core`                    | `crates/sharecli-core`                                       | Hypervisor engine tier for sharecli — process spawn/lifecycle/IO-ownership with Lock-Wait-Cache coalescing                                  |
| `sharecli-ffi`                     | `crates/sharecli-ffi`                                        | C-ABI FFI surface for sharecli — consumed by Swift macOS tray                                                                               |
| `sharecli-fleet`                   | `crates/sharecli-fleet`                                      | Fleet registry and thermal governor for sharecli — NATS-based device coordination                                                           |
| `sharecli-fuse`                    | `crates/sharecli-fuse`                                       | FUSE IO-interception layer for the sharecli OS process/IO/syscall hypervisor                                                                |
| `sharecli-ipc`                     | `crates/sharecli-ipc`                                        | IPC server + coalesce/debounce/queue primitives for sharecli — Unix socket JSON-RPC + Lock-Wait-Cache command deduplication                 |
| `sharecli-mesh`                    | `crates/sharecli-mesh`                                       | Mesh substrate for sharecli — Maildir-style task queue (ported from thegent)                                                                |
| `sharecli-session`                 | `crates/sharecli-session`                                    | —                                                                                                                                           |
| `sharecli-sync`                    | `crates/sharecli-sync`                                       | Loom-model-checked sync primitives for sharecli ProcessPool (C00 L7)                                                                        |
| `sharecli-thermal-tui`             | `crates/sharecli-thermal-tui`                                | Live thermal-gate / hypervisor-state TUI for sharecli                                                                                       |
| `sharecli-tray-linux`              | `crates/sharecli-tray-linux`                                 | Linux systemtray integration for sharecli (ksni/freedesktop)                                                                                |
| `sharecli-tray-windows`            | `crates/sharecli-tray-windows`                               | Native system-tray client for sharecli (FR-007 AC-007.51/AC-007.52/AC-007.54): tray-icon NotificationIcon + IPC sidecar spawn + dashboard…  |
| `sidekick-messaging`               | `crates/sidekick-messaging`                                  | Multi-provider messaging adapter for agent notifications.                                                                                   |
| `spawn-core-sys`                   | `crates/spawn-core-sys`                                      | FFI bindings to the Zig spawn-core hot loop (Unix); Windows keeps API parity with a local Mutex/Condvar semaphore and Unsupported spawn…    |
| `spec-decode`                      | `absorption/PhenoMLX-temp/perf-core/spec-decode`             | —                                                                                                                                           |
| `store-file`                       | `crates/store-file`                                          | File-backed StorePort: one JSON file per task/result, lockfile-lease atomic claim.                                                          |
| `store-sqlite`                     | `crates/store-sqlite`                                        | SQLite-backed MailboxStore, ClaimPort, MemoryPort, and EventStorePort adapters (bundled SQLite).                                            |
| `substrate-a2a`                    | `crates/a2a`                                                 | A2A-shaped wire schema (Task, Message, Artifact, Part). Transport-agnostic; depends only on serde/uuid/thiserror.                           |
| `substrate-app`                    | `crates/substrate-app`                                       | Application layer: DispatchService use-case and DispatchPlanner, generic over the core ports.                                               |
| `substrate-browser`                | `crates/substrate-browser`                                   | Browser profile generations and lease authority for concurrent agent use.                                                                   |
| `substrate-browser-broker`         | `crates/substrate-browser-broker`                            | Lease-guarded browser broker: profiles, generations, live sessions, viewer.                                                                 |
| `substrate-browser-cdp`            | `crates/substrate-browser-cdp`                               | Chrome DevTools Protocol provider: headless launch, snapshot, act, capture.                                                                 |
| `substrate-browser-mcp`            | `crates/substrate-browser-mcp`                               | MCP bridge exposing the browser lease broker to coding agents.                                                                              |
| `substrate-browser-provider`       | `crates/substrate-browser-provider`                          | BRIDGE provider adapter: speaks the normalized browser protocol over stdio NDJSON.                                                          |
| `substrate-core`                   | `crates/substrate-core`                                      | Hexagonal core contracts (domain + ports) for substrate. Depends on nothing but serde/thiserror/uuid/async-trait.                           |
| `substrate-dag`                    | `crates/substrate-dag`                                       | WorkflowPort DAG orchestration via petgraph.                                                                                                |
| `substrate-memory`                 | `crates/substrate-memory`                                    | MemoryPort: bounded ring buffer + two-tier compose with store-sqlite.                                                                       |
| `substrate-schedule`               | `crates/substrate-schedule`                                  | SchedulePort implementation: cron/interval/daily/weekly next_run via croner.                                                                |
| `substrate-serve-lock`             | `crates/substrate-serve-lock`                                | Lock-based single-instance guard for substrate `serve` commands.                                                                            |
| `substrate-skills`                 | `crates/substrate-skills`                                    | SkillPort/ToolRegistry: in-memory named skills with JSON schema validation.                                                                 |
| `substrate-trace`                  | `crates/substrate-trace`                                     | TracePort adapters: Noop, Recording, MultiTrace, AgilePlus, Tracera.                                                                        |
| `substrate-tui`                    | `crates/substrate-tui`                                       | Terminal UI dashboard for the substrate dispatch surface                                                                                    |
| `teamcomm-cli`                     | `crates/teamcomm-cli`                                        | teamcomm cli — Phenotype infrastructure crate (phenotype-teamcomm)                                                                          |
| `teamcomm-client`                  | `crates/teamcomm-client`                                     | teamcomm client — Phenotype infrastructure crate (phenotype-teamcomm)                                                                       |
| `teamcomm-daemon`                  | `crates/teamcomm-daemon`                                     | teamcomm daemon — long-running multi-agent coordinator                                                                                      |
| `teamcomm-mcp`                     | `crates/teamcomm-mcp`                                        | teamcomm MCP server — exposes coordination primitives as MCP tools                                                                          |
| `teamcomm-protocol`                | `crates/teamcomm-protocol`                                   | teamcomm protocol — wire types for inter-agent coordination                                                                                 |
| `teamcomm-smoke`                   | `crates/teamcomm-smoke`                                      | Smoke harness for the teamcomm daemon — brings up daemon, exercises wire methods, shuts down                                                |
| `temporal-grounding`               | `crates/temporal-grounding`                                  | Temporal grounding utilities for Claude Code agent sessions                                                                                 |
| `trace-gate`                       | `crates/trace-gate`                                          | CI gate binary: scans source annotations, checks FR coverage, exits 1 on missing coverage                                                   |
| `traceability-core`                | `crates/traceability-core`                                   | Unified PM/traceability core: superset of tracera-core + agileplus-domain                                                                   |
| `traceability-decorators`          | `crates/traceability-decorators`                             | Source-file scanner that extracts FR/spec trace annotations and emits ScanTraceLink records                                                 |
| `transport-file`                   | `crates/transport-file`                                      | File-backed TransportPort: append-only JSONL mailboxes with lockfile-lease atomic claim.                                                    |
| `tree-attention`                   | `absorption/PhenoMLX-temp/perf-core/tree-attention`          | —                                                                                                                                           |
| `tree-attention-spirv`             | `absorption/PhenoMLX-temp/perf-core/tree-attention-spirv`    | phenotype-omlx tree-attention kernel — Swift/Metal/SPIR-V backend                                                                           |
| `turbo-quant`                      | `absorption/PhenoMLX-temp/perf-core/turbo-quant`             | CPU-side TurboQuant encode/decode used by `perf-core` and the Python FFI.                                                                   |
| `turbo-quant-c`                    | `absorption/PhenoMLX-temp/perf-core/turbo-quant-c`           | C ABI base for TurboQuant — universal FFI layer                                                                                             |
| `turbo-quant-mojo`                 | `absorption/PhenoMLX-temp/perf-core/turbo-quant-mojo`        | phenotype-omlx turbo-quant in Mojo (cross-language FFI polyglot crate)                                                                      |
| `turbo-quant-nim`                  | `absorption/PhenoMLX-temp/perf-core/turbo-quant-nim`         | Nim dynlib binding to TurboQuant C ABI                                                                                                      |
| `turbo-quant-zig`                  | `absorption/PhenoMLX-temp/perf-core/turbo-quant-zig`         | phenotype-omlx turbo-quant in Zig (cross-language FFI polyglot crate)                                                                       |
| `vpu-agents`                       | `absorption/PhenoMLX-temp/perf-core/vpu/agents`              | vPU Agent Harness — ForgeCode-compatible multi-device orchestrator                                                                          |
| `worktree-manager`                 | `crates/worktree-manager`                                    | Git worktree automation and management                                                                                                      |

## Not published

These 65 workspace crates set `publish = false`, so cargo
does not publish them and they are deliberately absent from the index
above.

| Crate                                  | Path                                                                     |
| -------------------------------------- | ------------------------------------------------------------------------ |
| `arch-test`                            | `crates/arch-test`                                                       |
| `basic`                                | `crates/clap-ext-examples`                                               |
| `bifrost-routing`                      | `crates/bifrost-routing`                                                 |
| `clap-ext`                             | `crates/clap-ext`                                                        |
| `cloud-codex`                          | `crates/cloud-codex`                                                     |
| `cloud-dispatch-conformance`           | `crates/cloud-dispatch-conformance`                                      |
| `context-budget`                       | `crates/context-budget`                                                  |
| `dispatch-bridge`                      | `crates/dispatch-bridge`                                                 |
| `doc-link-check`                       | `crates/doc-link-check`                                                  |
| `driver-cli`                           | `crates/driver-cli`                                                      |
| `driver-http`                          | `crates/driver-http`                                                     |
| `driver-mcp`                           | `crates/driver-mcp`                                                      |
| `engine-forge`                         | `crates/engine-forge`                                                    |
| `fabric-cli`                           | `crates/fabric-cli`                                                      |
| `fabric-frame-transport`               | `crates/fabric-frame-transport`                                          |
| `fabric-full-demo`                     | `examples/full-demo`                                                     |
| `fabric-gui`                           | `crates/fabric-gui`                                                      |
| `fabric-integration-tests`             | `crates/fabric-integration-tests`                                        |
| `fabric-tray`                          | `crates/fabric-tray`                                                     |
| `fabric-tui`                           | `crates/fabric-tui`                                                      |
| `fabric-web`                           | `crates/fabric-web`                                                      |
| `file-watcher`                         | `crates/file-watcher`                                                    |
| `fuzz-setup`                           | `crates/fuzz-setup`                                                      |
| `hwledger-explorer-cli`                | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-cli`           |
| `hwledger-mcp`                         | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-mcp`           |
| `hwledger-search-core`                 | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-core`   |
| `hwledger-search-evals`                | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-evals`  |
| `hwledger-search-index`                | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-index`  |
| `hwledger-search-ingest`               | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-ingest` |
| `hwledger-search-rag`                  | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-rag`    |
| `hwledger-search-skills`               | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-skills` |
| `hwledger-search-tags`                 | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-search-tags`   |
| `hwledger-server`                      | `crates/hwledger/apps/model-explorer/rust/crates/hwledger-server`        |
| `klipdot-capture`                      | `crates/klipdot-capture`                                                 |
| `omniroute-adapter`                    | `crates/omniroute-adapter`                                               |
| `perfharness`                          | `crates/perfharness`                                                     |
| `pheno-config`                         | `crates/pheno-compose-pheno-config`                                      |
| `pheno-context`                        | `crates/pheno-context`                                                   |
| `pheno-forge-scaffold`                 | `crates/pheno-forge-scaffold`                                            |
| `pheno-forge-smoke`                    | `crates/pheno-forge-smoke`                                               |
| `pheno-i18n`                           | `crates/pheno-compose-i18n`                                              |
| `pheno-runtime-config`                 | `crates/pheno-runtime-config`                                            |
| `phenocompose-agentctl`                | `crates/pheno-compose-agentctl`                                          |
| `phenocompose-apple-container-adapter` | `crates/pheno-compose-apple-container-adapter`                           |
| `phenocompose-cli`                     | `crates/pheno-compose-phenocompose-cli`                                  |
| `phenocompose-plugin-api`              | `crates/pheno-compose-plugin-api`                                        |
| `phenocompose-plugin-sample`           | `crates/pheno-compose-plugin-sample`                                     |
| `phenocompose-port-composer`           | `crates/pheno-compose-port-composer`                                     |
| `phenocompose-port-di`                 | `crates/pheno-compose-port-di`                                           |
| `phenocompose-port-publisher`          | `crates/pheno-compose-port-publisher`                                    |
| `phenocompose-port-runtime`            | `crates/pheno-compose-port-runtime`                                      |
| `phenocompose-port-secret`             | `crates/pheno-compose-port-secret`                                       |
| `phenocompose-port-types`              | `crates/pheno-compose-port-types`                                        |
| `phenocompose-secret-file-adapter`     | `crates/pheno-compose-secret-file-adapter`                               |
| `phenocompose-wslc-adapter`            | `crates/pheno-compose-wslc-adapter`                                      |
| `phenotype-observably-macros`          | `crates/phenotype-observably-macros`                                     |
| `phenotype-port-interfaces`            | `crates/phenotype-port-interfaces`                                       |
| `phenotype-router`                     | `crates/phenotype-router`                                                |
| `phenotype-voxel`                      | `crates/phenotype-voxel`                                                 |
| `phinbox`                              | `crates/phinbox`                                                         |
| `routing-phenotype-router`             | `crates/routing-phenotype-router`                                        |
| `substrate`                            | `crates/substrate`                                                       |
| `supervisor`                           | `crates/supervisor`                                                      |
| `wave`                                 | `crates/wave`                                                            |
| `wave-3lane-tests`                     | `crates/wave-3lane-tests`                                                |
