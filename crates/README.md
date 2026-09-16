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
