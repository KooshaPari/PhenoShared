# FocalPoint Crates

Central registry of all FocalPoint Rust crates. Each crate is a standalone module with a single responsibility. See per-crate READMEs for detailed descriptions.

## Core Domain & State

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-domain](./focus-domain/README.md) | Domain entities (User, Device, Account), aggregate roots, invariants | `UserId`, `User` types |
| [focus-events](./focus-events/README.md) | Normalized event schema, dedupe keys | `NormalizedEvent` builder |
| [focus-rules](./focus-rules/README.md) | Rule DSL, evaluation, priority, cooldowns | `RuleBuilder::new()` |
| [focus-rewards](./focus-rewards/README.md) | Reward wallet, mutations, streaks | `RewardWallet::new()` |
| [focus-penalties](./focus-penalties/README.md) | Penalty escalation, bypass budget, lockout | `PenaltyState::new()` |
| [focus-planning](./focus-planning/README.md) | Task model, duration, priority, constraints | `Task::builder()` |

## Orchestration & Logic

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-eval](./focus-eval/README.md) | Event → Rule → Action pipeline | `RuleEvaluationPipeline::tick()` |
| [focus-policy](./focus-policy/README.md) | Enforcement policy generation from rules | `EnforcementPolicy::from_rules()` |
| [focus-scheduler](./focus-scheduler/README.md) | Rigidity-aware task scheduling | `RigidityScheduler::schedule()` |
| [focus-rituals](./focus-rituals/README.md) | Daily/weekly planning coach personality | `MorningBrief::run()` |
| [focus-mascot](./focus-mascot/README.md) | Coachy state machine (pose, emotion, bubble) | `MascotMachine::on_event()` |

## Data & Sync

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-storage](./focus-storage/README.md) | Storage traits and SQLite implementations | `SqlitePool::new()` |
| [focus-sync](./focus-sync/README.md) | Polling orchestrator, cursor, dedupe, retries | `SyncOrchestrator::tick()` |
| [focus-sync-store](./focus-sync-store/README.md) | Multi-device sync (CloudKit, CRDT) | `SyncStore::push()` |
| [focus-audit](./focus-audit/README.md) | Tamper-evident audit chain, hash verification | `AuditChain::append()` |
| [focus-backup](./focus-backup/README.md) | Encrypted backup/restore (age + tar+zstd) | `create_backup()` |

## Connectors

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-connectors](./focus-connectors/README.md) | Connector trait, manifest, auth, sync contract | `Connector::sync()` |
| [connector-canvas](./connector-canvas/README.md) | Canvas LMS (OAuth2, courses, assignments) | `CanvasConnector::sync()` |
| [connector-fitbit](./connector-fitbit/README.md) | Fitbit (OAuth2, activity, metrics) | `FitbitConnector::sync()` |
| [connector-gcal](./connector-gcal/README.md) | Google Calendar (OAuth2, time blocks) | `GcalConnector::sync()` |
| [connector-github](./connector-github/README.md) | GitHub (PAT, push events, PRs) | `GitHubConnector::sync()` |
| [connector-linear](./connector-linear/README.md) | Linear (OAuth2/PAT, issues, GraphQL) | `LinearConnector::sync()` |
| [connector-notion](./connector-notion/README.md) | Notion (token, pages, databases) | `NotionConnector::sync()` |
| [connector-readwise](./connector-readwise/README.md) | Readwise Reader (token, highlights, docs) | `ReadwiseConnector::sync()` |
| [connector-strava](./connector-strava/README.md) | Strava (OAuth2, activities, segments) | `StravaConnector::sync()` |
| [connector-testkit](./connector-testkit/README.md) | Fixture replay, mock sync, dedupe tests | `FixtureReplay::load()` |

## Interfaces & Integrations

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-coaching](./focus-coaching/README.md) | LLM provider trait (OpenAI-compatible, rate limit) | `CoachingProvider::complete()` |
| [focus-crypto](./focus-crypto/README.md) | Secrets management (Keychain, Linux SecretService) | `default_secure_store()` |
| [focus-calendar](./focus-calendar/README.md) | Calendar port trait, in-memory adapter | `CalendarPort::list_events()` |
| [focus-ffi](./focus-ffi/README.md) | UniFFI bindings (Swift, Kotlin) | Generated UDL scaffolding |
| [focus-time](./focus-time/README.md) | Clock abstraction (wall-clock, test clock) | `ClockPort::now()` |

## Language & Compilation

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-ir](./focus-ir/README.md) | Canonical IR format (JSON, versioned, hashed) | `Document::new()` |
| [focus-lang](./focus-lang/README.md) | Starlark → IR compiler (FPL) | `Compiler::compile()` |
| [focus-transpilers](./focus-transpilers/README.md) | TOML/Graph/Wizard ↔ IR round-trip | `transpile()` |

## Packaging & Distribution

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-templates](./focus-templates/README.md) | Rule template packs (TOML, ed25519 signed, `.fptpl`) | `TemplatePack::from_toml_str()` |
| [focus-icon-gen](./focus-icon-gen/README.md) | App icon generation (procedural, gradient, flame) | `generate_icon()` |
| [focus-asset-fetcher](./focus-asset-fetcher/README.md) | Audio asset fetcher (ffmpeg post-processing, cache) | `Fetcher::fetch_all()` |

## Operations & Tools

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| [focus-cli](./focus-cli/README.md) | Admin CLI (rules, wallet, sync, audit, schedule) | Clap subcommands |
| [focus-mcp-server](./focus-mcp-server/README.md) | MCP server (Claude integration, tools, resources) | `run_stdio()` |
| [focus-release-bot](./focus-release-bot/README.md) | Discord webhook poster (release notes) | `post_release()` |
| [focus-ci-watcher](./focus-ci-watcher/README.md) | CI monitor (fastlane lanes, Discord alerts) | `Watcher::start()` |
| [focus-webhook-server](./focus-webhook-server/README.md) | HTTP webhook receiver (GitHub, Notion, etc.) | `WebhookServer::start()` |

## Entitlements (Planned)

| Crate | Purpose | Entry Point |
|-------|---------|-------------|
| **focus-entitlements** (planned) | Subscription tiers, feature gates | Feature gate checks |

---

## Functional Requirement Coverage

See `FUNCTIONAL_REQUIREMENTS.md` (root) for complete traceability. All crates are indexed by FR:

- **FR-CONN** — Connectors: `focus-connectors`, `connector-*`, `connector-testkit`
- **FR-EVT** — Events: `focus-events`, `focus-sync`
- **FR-RULE** — Rules: `focus-rules`, `focus-eval`
- **FR-STATE** — State: `focus-rewards`, `focus-penalties`, `focus-audit`
- **FR-ENF** — Enforcement: `focus-policy`
- **FR-DATA** — Data & Storage: `focus-storage`, `focus-audit`, `focus-backup`
- **FR-PLAN** — Planning: `focus-planning`, `focus-scheduler`
- **FR-RITUAL** — Rituals: `focus-rituals`, `focus-mascot`
- **FR-FOCUS** — Evaluation: `focus-eval`

---

## Adding a New Crate

1. Create `crates/<name>/Cargo.toml` with `workspace = true`
2. Add to `members` in root `Cargo.toml`
3. Create `crates/<name>/src/lib.rs` with module tree
4. Write per-crate `README.md` (this template)
5. Update this directory-level `README.md` table above
6. Ensure all public APIs reference ≥1 FR in inline comments
7. Write tests with `// Traces to: FR-XXX-YYY` headers

## Complete crate index

Generated from `cargo metadata --no-deps`: this section lists all 226 publishable
workspace crates, alphabetically. Paths are relative to `crates/`.

| Crate | Path |
|-------|------|
| acceptance-contract | crates/acceptance-contract |
| agent-forecast | crates/agent-forecast |
| agileplus-cache | crates/agileplus-cache |
| agileplus-domain | crates/agileplus-domain |
| agileplus-error-core | crates/agileplus-error-core |
| agileplus-events | crates/agileplus-events |
| agileplus-git | crates/agileplus-git |
| agileplus-github | crates/agileplus-github |
| agileplus-graph | crates/agileplus-graph |
| agileplus-import | crates/agileplus-import |
| agileplus-nats | crates/agileplus-nats |
| agileplus-triage | crates/agileplus-triage |
| airlock-v2 | crates/airlock-v2 |
| anthropic-usage-poll | crates/anthropic-usage-poll |
| audit-privacy | crates/audit-privacy |
| bench-guard | crates/bench-guard |
| cliproxy-adapter | crates/cliproxy-adapter |
| cloud-cursor | crates/cloud-cursor |
| cloud-kilo | crates/cloud-kilo |
| commit-msg-check | crates/commit-msg-check |
| concurrent-exec | absorption/PhenoMLX-temp/perf-core/concurrent-exec |
| concurrent-exec-cuda | absorption/PhenoMLX-temp/perf-core/concurrent-exec-cuda |
| config-schema | crates/config-schema |
| configra-ops | crates/configra-ops |
| dag-scheduler | crates/dag-scheduler |
| datakit | crates/datakit |
| docs-health | crates/docs-health |
| driver-argv | crates/driver-argv |
| eidolon-core | crates/eidolon-core |
| eidolon-desktop | crates/eidolon-desktop |
| eidolon-mobile | crates/eidolon-mobile |
| eidolon-sandbox | crates/eidolon-sandbox |
| engine-a2a | crates/engine-a2a |
| engine-agentapi | crates/engine-agentapi |
| engine-claude | crates/engine-claude |
| engine-codex | crates/engine-codex |
| engine-conformance | crates/engine-conformance |
| engine-spec | crates/engine-spec |
| eval-harness | absorption/PhenoMLX-temp/perf-core/eval-harness |
| eyetracker-camera | crates/eyetracker-camera |
| eyetracker-cli | crates/eyetracker-cli |
| eyetracker-core | crates/eyetracker-core |
| eyetracker-domain | crates/eyetracker-domain |
| eyetracker-ffi | crates/eyetracker-ffi |
| eyetracker-inference | crates/eyetracker-inference |
| eyetracker-math | crates/eyetracker-math |
| fabric-capability | crates/fabric-capability |
| fabric-capability-ffi | crates/fabric-capability-ffi |
| fabric-capture | crates/fabric-capture |
| fabric-checker | crates/fabric-checker |
| fabric-daemon | crates/fabric-daemon |
| fabric-graph | crates/fabric-graph |
| fabric-graph-cli | crates/fabric-graph-cli |
| fabric-orchestrator | crates/fabric-orchestrator |
| fabric-persist | crates/fabric-persist |
| fabric-research-ledger | crates/fabric-research-ledger |
| fabric-surface-mojo | crates/fabric-surface-mojo |
| fabric-terminal | crates/fabric-terminal |
| fabric-workspace | crates/fabric-workspace |
| fake-codex-cloud | tools/fake-codex-cloud |
| fake-forge | tools/fake-forge |
| fleet-proto | absorption/PhenoMLX-temp/perf-core/fleet-proto |
| fleet-proto-zeromq | absorption/PhenoMLX-temp/perf-core/fleet-proto-zeromq |
| focus-always-on | crates/focus-always-on |
| focus-asset-fetcher | crates/focus-asset-fetcher |
| focus-audit | crates/focus-audit |
| focus-calendar | crates/focus-calendar |
| focus-ci-watcher | crates/focus-ci-watcher |
| focus-coaching | crates/focus-coaching |
| focus-crypto | crates/focus-crypto |
| focus-domain | crates/focus-domain |
| focus-entitlements | crates/focus-entitlements |
| focus-events | crates/focus-events |
| focus-icon-gen | crates/focus-icon-gen |
| focus-mascot | crates/focus-mascot |
| focus-observability | crates/focus-observability |
| focus-penalties | crates/focus-penalties |
| focus-planning | crates/focus-planning |
| focus-policy | crates/focus-policy |
| focus-release-bot | crates/focus-release-bot |
| focus-rewards | crates/focus-rewards |
| focus-rituals | crates/focus-rituals |
| focus-rules | crates/focus-rules |
| focus-scheduler | crates/focus-scheduler |
| focus-sync-store | crates/focus-sync-store |
| focus-templates | crates/focus-templates |
| focus-time | crates/focus-time |
| focus-ui | crates/focus-ui |
| fr-coverage | crates/fr-coverage |
| fr-trace | crates/fr-trace |
| hwledger-bench-cockpit | crates/hwledger/crates/hwledger-bench-cockpit |
| hwledger-cli | crates/hwledger/crates/hwledger-cli |
| kernel-registry | absorption/PhenoMLX-temp/perf-core/kernel-registry |
| legacy-scan | crates/legacy-scan |
| llm-router | crates/llm-router |
| logkit | crates/logkit |
| mcp-server | crates/mcp-server |
| metal-runtime | absorption/PhenoMLX-temp/perf-core/metal-runtime |
| model-kernels | absorption/PhenoMLX-temp/perf-core/model-kernels |
| model-plan | absorption/PhenoMLX-temp/perf-core/model-plan |
| native-abi | absorption/PhenoMLX-temp/perf-core/native-abi |
| nexus | crates/nexus |
| nvms-ffi | crates/pheno-compose-bindings |
| nvms-manifest | crates/nvms-manifest |
| orchestrator | crates/orchestrator |
| pheno-cache-adapter | crates/pheno-cache-adapter |
| pheno-compose-driver | crates/pheno-compose-driver |
| pheno-crypto | crates/pheno-crypto |
| pheno-errors | crates/pheno-errors |
| pheno-flags | crates/pheno-flags |
| pheno-fs | crates/pheno-fs |
| pheno-net | crates/pheno-net |
| pheno-otel | crates/argis-extensions/pheno-otel |
| pheno-schema-port | crates/pheno-schema-port |
| pheno-shell | crates/pheno-shell |
| pheno-testing | crates/pheno-testing |
| pheno-tracing | crates/pheno-tracing |
| pheno-vcs-core | crates/pheno-vcs-core |
| phenotype-async-traits | crates/phenotype-async-traits |
| phenotype-cache-adapter | crates/phenotype-cache-adapter |
| phenotype-casbin-wrapper | crates/phenotype-casbin-wrapper |
| phenotype-config | crates/phenotype-config |
| phenotype-config-core | crates/phenotype-config-core |
| phenotype-contract | crates/phenotype-contract |
| phenotype-contracts | crates/phenotype-contracts |
| phenotype-cost-core | crates/phenotype-cost-core |
| phenotype-crypto | crates/phenotype-crypto |
| phenotype-diff | crates/phenotype-diff |
| phenotype-error-core | crates/phenotype-error-core |
| phenotype-error-macros | crates/phenotype-error-macros |
| phenotype-errors | crates/phenotype-errors |
| phenotype-event-bus | crates/phenotype-event-bus |
| phenotype-flags | crates/phenotype-flags |
| phenotype-gfx | crates/phenotype-gfx |
| phenotype-git-core | crates/phenotype-git-core |
| phenotype-health | crates/phenotype-health |
| phenotype-http-client-core | crates/phenotype-http-client-core |
| phenotype-iter | crates/phenotype-iter |
| phenotype-journey-core | crates/phenotype-journey-core |
| phenotype-journeys-observability | crates/phenotype-journeys-observability |
| phenotype-logging | crates/phenotype-logging |
| phenotype-macros | crates/phenotype-macros |
| phenotype-mcp | crates/phenotype-mcp |
| phenotype-nvms-adapter | crates/phenotype-nvms-adapter |
| phenotype-observability | crates/phenotype-observability |
| phenotype-policy-engine | crates/phenotype-policy-engine |
| phenotype-port-traits | crates/phenotype-port-traits |
| phenotype-ports-canonical | crates/phenotype-ports-canonical |
| phenotype-process | crates/phenotype-process |
| phenotype-project-registry | crates/phenotype-project-registry |
| phenotype-rate-limit | crates/phenotype-rate-limit |
| phenotype-resilience | crates/phenotype-resilience |
| phenotype-retry | crates/phenotype-retry |
| phenotype-router-monitor | crates/phenotype-router-monitor |
| phenotype-service-registry | crates/phenotype-service-registry |
| phenotype-shared-config | crates/phenotype-shared-config |
| phenotype-state-machine | crates/phenotype-state-machine |
| phenotype-string | crates/phenotype-string |
| phenotype-telemetry | crates/phenotype-telemetry |
| phenotype-test-infra | crates/phenotype-test-infra |
| phenotype-time | crates/phenotype-time |
| phenotype-tooling-observability | crates/phenotype-tooling-observability |
| phenotype-validation | crates/phenotype-validation |
| phenovcs-observability | crates/phenovcs-observability |
| pine-compat | crates/pine-compat |
| pine-core | crates/pine-core |
| pine-loader | crates/pine-loader |
| pine-nvms | crates/pine-nvms |
| pine-syscall | crates/pine-syscall |
| playcua-native | native |
| qgate | crates/qgate |
| regress-baseline | absorption/PhenoMLX-temp/perf-core/regress-baseline |
| release-cut | crates/release-cut |
| runtime-process | crates/runtime-process |
| sharecli | crates/sharecli |
| sharecli-core | crates/sharecli-core |
| sharecli-ffi | crates/sharecli-ffi |
| sharecli-fleet | crates/sharecli-fleet |
| sharecli-fuse | crates/sharecli-fuse |
| sharecli-ipc | crates/sharecli-ipc |
| sharecli-mesh | crates/sharecli-mesh |
| sharecli-session | crates/sharecli-session |
| sharecli-sync | crates/sharecli-sync |
| sharecli-thermal-tui | crates/sharecli-thermal-tui |
| sharecli-tray-linux | crates/sharecli-tray-linux |
| sharecli-tray-windows | crates/sharecli-tray-windows |
| sidekick-messaging | crates/sidekick-messaging |
| spawn-core-sys | crates/spawn-core-sys |
| spec-decode | absorption/PhenoMLX-temp/perf-core/spec-decode |
| store-file | crates/store-file |
| store-sqlite | crates/store-sqlite |
| substrate-a2a | crates/a2a |
| substrate-app | crates/substrate-app |
| substrate-browser | crates/substrate-browser |
| substrate-browser-broker | crates/substrate-browser-broker |
| substrate-browser-cdp | crates/substrate-browser-cdp |
| substrate-browser-mcp | crates/substrate-browser-mcp |
| substrate-browser-provider | crates/substrate-browser-provider |
| substrate-core | crates/substrate-core |
| substrate-dag | crates/substrate-dag |
| substrate-memory | crates/substrate-memory |
| substrate-schedule | crates/substrate-schedule |
| substrate-serve-lock | crates/substrate-serve-lock |
| substrate-skills | crates/substrate-skills |
| substrate-trace | crates/substrate-trace |
| substrate-tui | crates/substrate-tui |
| teamcomm-cli | crates/teamcomm-cli |
| teamcomm-client | crates/teamcomm-client |
| teamcomm-daemon | crates/teamcomm-daemon |
| teamcomm-mcp | crates/teamcomm-mcp |
| teamcomm-protocol | crates/teamcomm-protocol |
| teamcomm-smoke | crates/teamcomm-smoke |
| temporal-grounding | crates/temporal-grounding |
| trace-gate | crates/trace-gate |
| traceability-core | crates/traceability-core |
| traceability-decorators | crates/traceability-decorators |
| transport-file | crates/transport-file |
| tree-attention | absorption/PhenoMLX-temp/perf-core/tree-attention |
| tree-attention-spirv | absorption/PhenoMLX-temp/perf-core/tree-attention-spirv |
| turbo-quant | absorption/PhenoMLX-temp/perf-core/turbo-quant |
| turbo-quant-c | absorption/PhenoMLX-temp/perf-core/turbo-quant-c |
| turbo-quant-mojo | absorption/PhenoMLX-temp/perf-core/turbo-quant-mojo |
| turbo-quant-nim | absorption/PhenoMLX-temp/perf-core/turbo-quant-nim |
| turbo-quant-zig | absorption/PhenoMLX-temp/perf-core/turbo-quant-zig |
| vpu-agents | absorption/PhenoMLX-temp/perf-core/vpu/agents |
| worktree-manager | crates/worktree-manager |
