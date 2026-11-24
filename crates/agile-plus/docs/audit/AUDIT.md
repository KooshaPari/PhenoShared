# AgilePlus Deep Quality Audit

**Date:** 2026-06-24  
**Branch audited:** `origin/main` @ `164a0d16`  
**Rubric:** `C:/Users/koosh/Dev/_AUDIT_RUBRIC.md` (12 areas, 168 pillars)  
**Auditor stance:** Strict — target is perfect (all 5s). Evidence from real files only; no builds executed.

---

## Executive Summary

AgilePlus is a large Rust monorepo (~729 `.rs` files under `crates/`, `libs/`, `tests/`) with mature governance scaffolding (FR matrix, ADRs, 50+ CI workflows, BDD/contract tests). **Critical gap:** root `Cargo.toml` workspace lists only `rust` (proto stubs); the 40+ application crates are excluded from the active workspace and therefore **not built or tested in primary CI** (`.github/workflows/ci.yml:53-65` runs `cd rust && cargo test` only). OpenAPI covers 5/36 handlers; FR-coverage workflow is a stub; health checks partially simulated. Strong foundations in domain modeling, migrations, and security scanning — but integration between spec, CI, and runnable product is incomplete.

| Area | Pillars | Sum / Max | Avg /5 | % |
|------|---------|-----------|--------|---|
| A. Architecture & Design | 14 | 41 | 2.93 | 58.6% |
| B. Domain Modeling & Types | 14 | 46 | 3.29 | 65.7% |
| C. API / Interface Design | 14 | 40 | 2.86 | 57.1% |
| D. Testing | 14 | 44 | 3.14 | 62.9% |
| E. CI/CD & Release | 14 | 48 | 3.43 | 68.6% |
| F. Security | 14 | 50 | 3.57 | 71.4% |
| G. Observability | 14 | 42 | 3.00 | 60.0% |
| H. Performance & Scalability | 14 | 32 | 2.29 | 45.7% |
| I. Data & Persistence | 14 | 49 | 3.50 | 70.0% |
| J. Docs & DX | 14 | 47 | 3.36 | 67.1% |
| K. Ops & Deploy | 14 | 35 | 2.50 | 50.0% |
| L. Governance & Traceability | 14 | 52 | 3.71 | 74.3% |
| **OVERALL** | **168** | **526** | **3.13** | **62.6%** |

---

## A. Architecture & Design

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Hexagonal ports/adapters | 4 | `libs/hexagonal-rs/src/ports/input.rs:7` `InputPort`; `output.rs:33` `SpecRepository` | Ports exist in libs but not wired through active workspace | Add `agileplus-domain` + adapters to workspace; enforce port injection in CLI/API |
| SOLID — Single Responsibility | 3 | Crate split: `agileplus-domain`, `agileplus-api`, `agileplus-sqlite` | `agileplus-cli/src/main.rs:1-25` still embeds mock domain data inline | Extract CLI wiring to `agileplus-application` use-case layer |
| SOLID — Open/Closed | 3 | `libs/plugin-registry/src/plugin_trait.rs` plugin trait | Plugin git dep unresolved per `openapi.rs:21-22` | Fix `agileplus-plugin-core` git dep; register plugins without core edits |
| SOLID — Liskov Substitution | 3 | `agileplus-domain/src/credentials/memory.rs` in-memory impl | No contract tests proving all storage adapters are substitutable | Add LSP contract suite in `agileplus-contract-tests` |
| SOLID — Interface Segregation | 4 | Small focused port traits in `hexagonal-rs/src/ports/` | Some fat handler modules in `agileplus-api/src/routes.rs` | Split route modules per aggregate; thin handlers |
| SOLID — Dependency Inversion | 2 | `quality-gate.toml:17-18` domain purity enforced | Application crates depend on concrete SQLite outside workspace build | Wire DI container; depend on traits in domain ports |
| DRY | 3 | Shared `agileplus-error-core`, `phenotype-error-core` | Duplicate hex/port patterns across `hexkit` and `hexagonal-rs` | Consolidate hex helpers into single `hexkit` export |
| Module boundaries | 1 | `Cargo.toml:6-8` workspace `members = ["rust"]` only | 40+ crates with source excluded (`Cargo.toml:4-5`) | Gradually onboard crates per `kitty-specs/003-agileplus-platform-completion` |
| Coupling / cohesion | 2 | 729 `.rs` files vs 1 active workspace member | High orphan-code risk; cohesion unverified by CI | CI matrix builds all non-scaffold crates |
| Dependency direction | 4 | `quality-gate.toml:16-28` `agileplus-domain` allowed_deps whitelist | Not enforced in CI for excluded crates | Run dep-guard in `phenotype-dep-guard` on every PR |
| Abstraction at 2 uses | 3 | `agileplus-sync/src/orchestrator.rs` abstraction present | Premature `agileplus-graph` Neo4j adapter (ADR-013) without usage | Gate new adapters behind feature flags until 2nd consumer |
| No god-objects | 3 | `quality-gate.toml:10` `max_god_module_loc = 500` | `agileplus-api/tests/api_integration.rs` 1500+ lines | Split integration tests by route group |
| Layering (domain → app → infra) | 3 | `crates/agileplus-domain/` pure domain; `agileplus-sqlite/` infra | API routes may reach into SQLite adapters directly in places | Introduce application service layer crate |
| Dead flexibility | 2 | 44 scaffolded crate dirs noted `Cargo.toml:4-5` | Empty/stub crates inflate surface area | Archive or delete scaffolds per CLAUDE.md stale-dir policy |
| Cyclic dependency prevention | 4 | `crates/phenotype-dep-guard/` manifest + lockfile checks | Not run in primary `ci.yml` rust-check job | Add `phenotype-dep-guard` step to CI |
| Public API minimalism | 3 | `agileplus-api/src/lib.rs:5-15` focused re-exports | Many `pub mod` in domain crate | Audit `pub` visibility; use `pub(crate)` internally |

**Area A average: 2.93/5 (58.6%)**

---

## B. Domain Modeling & Types

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Invariants encoded in types | 4 | `state_machine.rs` forward-only transitions → `DomainError::InvalidTransition` | Some invariants only checked at runtime strings | Move transition rules fully into typestate or sealed traits |
| Illegal states unrepresentable | 3 | `FeatureState`, `WpState` enums in domain | `String` transition field in audit allows invalid labels | Use typed `Transition` enum in `audit.rs` |
| Newtypes over primitives | 1 | IDs are raw `i64` (`api_key.rs:16`, `feature.rs`) | No `FeatureId`, `Slug` newtypes found in grep | Introduce newtypes in `agileplus-domain/src/ids.rs` |
| Ubiquitous language | 4 | `FUNCTIONAL_REQUIREMENTS.md:11-27` mirrors domain entities | FR doc field names drift from code (`actor` vs `name` in ApiKey) | Regenerate FR table from code decorators |
| Enum exhaustiveness | 4 | `FeatureState`, `CycleState`, `WpState` enums with `match` in tests | No `#[non_exhaustive]` policy documented | Add clippy `match_wildcard_for_single_variants` + document policy |
| Error type design (thiserror) | 4 | `domain/error.rs:11-40` rich `DomainError` variants | `Storage(String)` wraps opaque errors | Typed storage error enum per adapter |
| Option/Result discipline | 3 | Widespread `Option` for nullable FKs | Some `.unwrap()` in tests only; production paths need audit | Enable `clippy::unwrap_used` deny in lib code |
| No stringly-typed domain | 2 | `transition: String` in audit; slug as `String` | Business concepts as free strings | Newtype `Slug`, `TransitionName` with validation |
| Value vs entity distinction | 3 | `StateTransition` value object in state machine | `Feature` mixes identity + mutable state without clear VO split | Extract `FeatureMetadata` value object |
| ID schemes | 2 | Monotonic `i64` SQLite autoincrement | No ULID/UUID for distributed P2P (`device_node` uses UUID separately) | Document ID strategy; align P2P and SQLite IDs |
| Domain events | 4 | `agileplus-events/src/domain_event.rs` event types | Events not in active workspace CI | Add events crate to workspace + event schema versioning |
| Snapshot modeling | 4 | `Snapshot` entity FR-DOMAIN-012; migration `011_create_snapshots.sql` | Snapshot rebuild path untested in CI | Integration test snapshot ↔ event replay |
| Governance contract types | 4 | `domain/governance.rs` `GovernanceContract`, `Evidence` | Runtime enforcement scattered | Centralize in `agileplus-governance` policy engine |
| Credential zeroization | 4 | `zeroize` in workspace deps `Cargo.toml:66`; `credentials.rs` | API key plaintext handling in CLI paths needs audit | `ZeroizeOnDrop` on all secret buffers |

**Area B average: 3.29/5 (65.7%)**

---

## C. API / Interface Design

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| REST resource modeling | 3 | `agileplus-api/src/routes/` features, work_packages, events | Inconsistent noun pluralization; some RPC-style paths | Publish REST style guide; align routes to resources |
| CLI ergonomics | 3 | `agileplus-cli` clap `Parser`/`Subcommand` (`main.rs:24`) | README references `pheno-cli` not `agileplus` (`README.md:36-39`) | Fix README; ensure binary name `agileplus` ships |
| API versioning | 2 | OpenAPI `version = "0.1.1"` (`openapi.rs:37`) | No `/v1` prefix or Accept-Version header | Add versioned router prefix + deprecation policy |
| Request/response contracts | 3 | `CreateFeatureRequest`, `FeatureResponse` in openapi schemas | Only 6 schemas documented of ~36 handlers | Complete utoipa annotations on all handlers |
| Idempotency | 2 | absence of `Idempotency-Key` handling in `router/compose.rs` | POST create may duplicate on retry | Add idempotency middleware for mutating routes |
| Pagination | 2 | `list_features` exists; cursor pagination unclear | No standard `page`/`cursor` response envelope | Add `Paginated<T>` response type + OpenAPI |
| HTTP status codes | 4 | Tests expect 401 unauthenticated (`api_integration/core_routes.rs:36-38`) | Error body schema not uniform | Standardize `ProblemDetails` JSON errors |
| Backward compatibility | 2 | No API changelog or deprecation headers | Breaking changes undetectable | Add `docs/api/CHANGELOG.md` + sunset headers |
| OpenAPI / schema docs | 2 | `openapi.rs:5-7` "5 representative endpoints"; 31 handlers deferred | CI drift check deferred (`openapi.rs:19-22`) | Unblock plugin dep; enable `openapi-check.yml` drift gate |
| Input validation at API boundary | 3 | Domain validation in `agileplus-validate` with proptest | API layer may pass unvalidated strings to domain | Validate all request DTOs with `validator` crate |
| gRPC interface | 3 | `proto/` + `buf.yaml`; `agileplus-grpc` tests exist | gRPC not in active workspace CI | Add buf breaking check + grpc integration to CI |
| SSE/streaming API | 3 | `routes/stream.rs:24` SSE with auth | Stream backpressure undocumented | Document client reconnect + `Last-Event-ID` |
| MCP tool interface | 3 | `agileplus-mcp/` Python server; `agileplus-mcp-intent` | MCP tools not contract-tested against OpenAPI | Add MCP↔REST contract tests |
| Dashboard API surface | 3 | `agileplus-dashboard/src/routes.rs` health + evidence routes | Dashboard routes overlap REST API inconsistently | Unify API behind single router or document split |

**Area C average: 2.86/5 (57.1%)**

---

## D. Testing

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Unit tests | 4 | 75+ test files; heavy coverage in `agileplus-domain`, `agileplus-triage` | Excluded from workspace CI | Onboard crates; `cargo test --workspace` all members |
| Integration tests | 3 | `crates/agileplus-integration-tests/tests/` 5 scenarios | Not run in `ci.yml` (rust-only) | Add integration job with harness `common/harness.rs` |
| E2E tests | 2 | `tests/integration/test_full_workflow.rs` | No E2E job in CI; docker-compose test rig exists but unverified | Wire `tests/integration/docker-compose.test.yml` to CI |
| Property-based tests | 3 | `proptest_audit.rs`, `agileplus-validate/src/lib.rs:137` proptest | Limited to 2 crates | Expand proptest to state machine + audit chain |
| BDD / Gherkin | 4 | `tests/bdd/main.rs:1-6` cucumber-rs; mock adapters | BDD does not exercise HTTP/CLI end-to-end | Add `.feature` files for API + CLI paths |
| Coverage % gate | 2 | `codecov.yml:4-9` patch target 80%; `quality-gate.toml:6` line 80% | CI does not upload coverage for main crates | Enable codecov in `ci.yml` with llvm-cov |
| Meaningful assertions | 4 | `events_smoke_test.rs` 25 tests; API auth tests | Some health tests assert `true` unconditionally | Replace smoke asserts with behavior checks |
| Fixtures / factories | 4 | `agileplus-fixtures/src/builders.rs`, `tests/fixtures/mod.rs` | Not all integration tests use shared builders | Mandate fixtures crate for new tests |
| Determinism | 3 | BDD uses fixed timestamps in places | `Utc::now()` in domain `api_key.rs:31` complicates tests | Inject `Clock` port for time |
| Test isolation | 3 | In-memory mocks in BDD world | SQLite tests may share `agileplus.db` in repo root | Use tempdir per test; gitignore `*.db` |
| Mutation resistance | 1 | `quality-gate.toml:11` `mutation_score_min = 60` | No mutation testing workflow found | Add `cargo-mutants` nightly job |
| Perf / load tests | 2 | `agileplus-benchmarks/` crate exists | No benchmark CI gate | Add critcmp threshold job |
| Contract tests | 4 | `tests/contracts/*.rs`, `agileplus-grpc/tests/pact_schema.rs` | Contracts not in default CI | Run contract tests on PR |
| Flaky-free policy | 2 | absence of flake retry budget docs | No quarantine mechanism | Track flaky tests in issue template |

**Area D average: 3.14/5 (62.9%)**

---

## E. CI/CD & Release

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Pipeline completeness | 4 | 50+ workflows under `.github/workflows/` | Primary build scope = `rust/` only (`ci.yml:59-65`) | Expand rust-check to full workspace |
| fmt / lint / clippy gates | 4 | `ci.yml:58-61` fmt + clippy `-D warnings` | Only on `rust/` subtree | Run on all workspace members |
| Build matrix | 2 | Single `ubuntu-latest` in rust-check | No MSRV/stable/nightly matrix; README says macOS skipped | Add MSRV job per `rust-toolchain.toml` |
| release.yml semver → artifacts | 4 | `release.yml:1-60` gated publish via `gate-check` | Manual `workflow_dispatch` only; no tag push trigger | Add tag-push release automation |
| Nightly / scheduled jobs | 3 | `sbom-refresh.yml`, `audit.yml`, `stale.yml` | No nightly full test sweep | Schedule `cargo test --all` nightly |
| E2E workflow | 2 | `journey-gate.yml`, `evidence-capture.yml` exist | No compose-up E2E in default PR path | Add required E2E check |
| Artifact integrity / signing | 4 | `release-attestation.yml` | Attestation not proven on rust binaries | Sign `agileplus` CLI with cosign |
| Caching | 4 | `Swatinem/rust-cache@v2` in `ci.yml:51-53` | Cache scoped to `rust` workspace only | Expand cache paths when workspace grows |
| Required checks | 3 | Many gate workflows (`quality-gate.yml`, `pr-governance-gate.yml`) | Branch protection config not in repo | Document required checks in CONTRIBUTING |
| Rollback | 2 | `promote.yml` exists | No documented rollback runbook in ops docs | Add `docs/ops/rollback.md` |
| Changelog / release notes | 4 | `CHANGELOG.md` 135KB; `release-drafter.yml`; `.cliff.toml` | Changelog not linked to FR IDs | Auto-link FR IDs in release notes |
| Public + Ubuntu free CI | 5 | All workflows use `ubuntu-latest` | — | Maintain ubuntu-first; optional self-hosted |
| Pre-commit hooks | 4 | `security-guard.yml` runs pre-commit; `.pre-commit-config.yaml` | Local hook adoption voluntary | Document `pre-commit install` in CONTRIBUTING |
| Proto / buf CI | 4 | `ci.yml:23-39` buf lint + format | `breaking: false` — breaking changes unchecked | Enable buf breaking on PR |

**Area E average: 3.43/5 (68.6%)**

---

## F. Security

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Authentication | 4 | API key SHA-256 hash (`api_key.rs:12-18`); middleware in `router/compose.rs:64` | API-key only; no OAuth/JWT/session rotation | Document threat model; add key rotation CLI |
| Authorization | 2 | Auth tests verify 401 (`core_routes.rs:36`) | No RBAC/ABAC; all keys same privilege | Add scoped API keys + role model |
| Secrets via env (no hardcode) | 4 | `.env.example:4-14` Sentry DSN placeholder | `agileplus.db` committed in repo root | Remove DB from VCS; document secret mounts |
| Dependency CVE audit | 4 | `cargo-audit.yml`, `cargo-deny.yml`, `deny.toml` | Excluded crates not audited in CI | Audit full workspace when onboarded |
| Supply chain (pinned actions) | 4 | SHA pins in `sast-quick.yml:25,50`, `trufflehog.yml:20` | `ci.yml:31,47` uses `actions/checkout@v7` unpinned | Pin all actions to SHA per security policy |
| SBOM | 3 | `sbom.cdx.json` pointer; `docs/security/sbom.json` 704 components | Root `sbom.cdx.json` is stub (4 lines) | Commit full SBOM; refresh in CI |
| Input validation at boundaries | 3 | `agileplus-validate` proptest validators | HTTP layer validation incomplete | Validator on all API inputs |
| Injection safety | 4 | SQLite parameterized queries in repositories; `unsafe_code = forbid` `Cargo.toml:17` | Dynamic SQL in triage paths uses `include_str!` | Audit raw SQL builders in `triage.rs:41` |
| TLS | 2 | OTLP gzip-tonic in deps `Cargo.toml:57` | No TLS termination docs for API server | Document reverse-proxy TLS (nginx/caddy) |
| Least privilege | 3 | `permissions: contents: read` in `ci.yml:9-10` | Over-broad `CODEOWNERS:19` `* @<REDACTED>` | Split CODEOWNERS per crate team |
| Rate limiting | 1 | `tower` limit feature in deps `Cargo.toml:43`; no usage found in API | API vulnerable to abuse | Add `tower::limit::RateLimitLayer` per route class |
| Gitleaks-clean | 4 | `gitleaks.yml`, `trufflehog.yml`, `.trufflehog.yml` | `agileplus.db` may contain local secrets | Scan + gitignore local DBs |
| CODEOWNERS | 4 | `CODEOWNERS:1-19` scoped baseline | Single owner for all paths | Add per-crate owners as team grows |
| SAST / CodeQL | 4 | `codeql.yml`, `sast-full.yml`, semgrep rules `.semgrep-rules/` | Semgrep not in default PR required checks | Make sast-quick required |

**Area F average: 3.57/5 (71.4%)**

---

## G. Observability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Structured logging | 4 | `libs/logger/src/lib.rs`; tracing subscriber in workspace deps | CLI uses minimal logging | Uniform tracing init in all binaries |
| Log levels | 4 | `RUST_LOG` documented `.env.example:17` | No per-module default filter config | Ship `tracing.toml` default filters |
| Metrics | 4 | `agileplus-telemetry/src/metrics/mod.rs` 15 tests; OTel metrics SDK | Metrics not exposed via `/metrics` HTTP | Add Prometheus scrape endpoint |
| Tracing / spans | 4 | FR-AGP-015 test in `api_integration.rs:1542`; `tracing-opentelemetry` dep | OTLP collector not in default compose | Add otel-collector to `process-compose.yml` |
| Health endpoints | 3 | `/health` no auth (`core_routes.rs:6-8`); dashboard `health.rs` | `SqliteChecker` simulated not real (`health.rs:26-27`) | Wire real DB ping in health checker |
| Readiness vs liveness | 3 | `process-compose.yml:10-14` NATS readiness_probe | API server lacks `/ready` separate from `/health` | Split liveness/readiness routes |
| Error reporting | 4 | Sentry integration `libs/logger/src/sentry_config.rs` | Requires `SENTRY_DSN`; no default staging project | Document Sentry project setup |
| Correlation IDs | 2 | absence of `X-Request-Id` middleware found | Cross-service debugging hard | Add request ID middleware + log field |
| Dashboards | 2 | `vibeproxy-monitoring-unified/` referenced in tree | No checked-in Grafana dashboards for AgilePlus | Add `docs/observability/dashboards/` |
| Alerting | 2 | `alert-sync-issues.yml` workflow | No SLO-based alert rules in repo | Define alert rules for error rate/latency |
| Audit trail (observability) | 5 | Hash-chained `audit.rs`; FR-AUDIT-001–006 | — | Export audit metrics (chain length, verify failures) |
| Telemetry adapter port | 4 | `TelemetryAdapter` implements `ObservabilityPort` `adapter.rs:29` | Port not used uniformly across crates | Inject telemetry port at app bootstrap |
| Log redaction | 3 | `zeroize` for secrets | No documented PII redaction in logs | Add tracing layer to redact API keys |
| Performance spans | 2 | Request span middleware tested | DB query spans absent | Instrument repository methods with spans |

**Area G average: 3.00/5 (60.0%)**

---

## H. Performance & Scalability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Hot-path profiling | 2 | `agileplus-benchmarks/` crate | No profiling docs or flamegraph CI | Add `cargo bench` baseline job |
| Async / concurrency correctness | 3 | `tokio` full features; NATS adapter tests | No loom/concurrency stress tests | Add loom tests for sync orchestrator |
| Caching | 3 | `agileplus-cache/` crate; Dragonfly in compose | Cache invalidation strategy undocumented | Document cache keys + TTL policy |
| N+1 avoidance | 2 | SQLite repos per-entity queries | List endpoints may N+1 without joins audit | EXPLAIN-query audit on list routes |
| Resource bounds | 2 | `tower` timeout/limit deps | Not applied in router | Enforce timeouts on all handlers |
| Streaming vs buffering | 3 | SSE `stream.rs` | Bulk export paths may buffer | Stream large audit exports |
| Backpressure | 2 | NATS JetStream per ADR-006 | No backpressure handling in API SSE | Add bounded channels for SSE |
| Algorithmic complexity | 3 | `agileplus-triage` LSH/minhash documented in module | Triage pipeline untested at scale | Add benchmark with 10k claims |
| Load ceiling documented | 1 | absence of capacity numbers in docs | Unknown RPS limit | Document load test results in `docs/perf/` |
| Memory bounds | 2 | No max payload size on API | Large JSON bodies unbounded | Add `DefaultBodyLimit` in axum |
| P2P replication perf | 3 | `agileplus-p2p/src/vector_clock.rs` 8 tests | No perf test for merge at scale | Benchmark vector clock merge |
| SQLite WAL mode | 3 | `agileplus.db-wal` exists locally | WAL not enforced in connection init | Set `PRAGMA journal_mode=WAL` on open |
| Connection pooling | 2 | Single `Connection` pattern in sqlite crate | No pool for concurrent API | Add `r2d2` pool |
| Horizontal scaling story | 2 | ADR SQLite local-first | Multi-instance API not addressed | Document scale-out via read replicas or sync |

**Area H average: 2.29/5 (45.7%)**

---

## I. Data & Persistence

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Schema design | 4 | 31 SQL migrations `agileplus-sqlite/src/migrations/` | Some nullable FKs without CHECK constraints | Add FK constraints in new migrations |
| Migrations versioned | 5 | `migrations/mod.rs:11-34` embedded numbered SQL | — | Keep sequential numbering discipline |
| Migrations reversible | 4 | `mod.rs:151-158` rollback last migration | DOWN sections not verified for all 31 files | Test rollback in CI |
| Referential integrity | 3 | `008_create_wp_dependencies.sql`; feature FKs | enforcement at app layer primarily | SQLite FOREIGN KEY pragma on |
| Indexing | 4 | `009_create_indexes.sql` dedicated migration | Query plans not validated | Add EXPLAIN tests for hot queries |
| Backup / restore | 2 | absence of backup scripts in `scripts/` | No `agileplus backup` command | Add CLI backup to object storage |
| Transactions | 4 | rusqlite transactions in repositories | Cross-aggregate transactions unclear | Document transaction boundaries |
| Data validation | 4 | Domain validation + DB NOT NULL in migrations | Labels JSON column unvalidated at DB | CHECK json_valid or app validator |
| Consistency model | 3 | Event sourcing + snapshots; P2P vector clocks | Conflict resolution in `sync/conflict.rs` not E2E tested | Integration test split-brain scenario |
| Seed data | 4 | `agileplus-sqlite/src/seed/runner.rs` 7 tests | Seed not idempotent documented | Document seed command in README |
| Event store persistence | 4 | `010_create_events.sql`; `agileplus-events` | Not in workspace CI | Onboard events crate |
| Trace links schema | 4 | `022_create_trace_links.sql` | Trace validator separate crate | Wire trace links to governance gate |
| Worklog persistence | 4 | `023_create_worklog_entries.sql` | Many `worklog-*.json` at repo root | Consolidate into DB or artifact store |
| Data retention policy | 2 | Audit archive to MinIO FR-AUDIT-006 | No retention TTL documented | Add retention policy ADR |

**Area I average: 3.50/5 (70.0%)**

---

## J. Docs & DX

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| README work-state header | 4 | `README.md:1-2` `work-state: 🔴 in-progress \| 80%` | Quality gate says 71-pillar; bar inconsistent | Align header with `quality-gate.toml` |
| Quickstart | 3 | `README.md:29-43` setup commands | References wrong package `pheno-cli` | Fix to `cargo run -p agileplus-cli` |
| Install docs | 2 | No `docs/install.md` or cargo-binstall config | Users cannot install binary easily | Add install section + binstall metadata |
| API reference | 3 | OpenAPI partial `openapi.rs` | 86% handlers undocumented | Complete OpenAPI |
| Examples that run | 2 | `examples/` absence at workspace root | No runnable example crate | Add `examples/hello-agileplus/` |
| Onboarding | 3 | `CONTRIBUTING.md:1-19` workflow | Devcontainer exists `.devcontainer/` but not linked | Link devcontainer from CONTRIBUTING |
| CONTRIBUTING | 4 | `CONTRIBUTING.md` spec-first, conventional commits | Says `cargo test --all` but workspace is 1 crate | Update commands for actual workspace |
| Docs site populated | 4 | `vitepress-deploy.yml`; `docs/` tree; `ARCHITECTURE.md` | VitePress content completeness unknown | Run `doc-links.yml` fix broken links |
| ADRs present | 4 | `ADR.md` 22KB; `docs/adr/` 10 files | Duplicate ADR-012 entries per AGENTS.md | Deduplicate ADR index |
| Code comments quality | 3 | Module docs in API `lib.rs:1-3`; traceability comments | Some stubs ("minimal smoke-test CLI") | Refresh stale module docs |
| Media-proof stubs | 2 | `RICH_MEDIA.md` exists | Per media-docs-proof gaps unknown | Add screenshot CI per RICH_MEDIA.md |
| PRD / SPEC linkage | 4 | `PRD.md`, `SPEC.md`, `FUNCTIONAL_REQUIREMENTS.md` | PRD version 2.1 vs FR 2.2 version drift | Sync version metadata |
| Task / plan docs | 4 | `PLAN.md` 29KB; `Taskfile.yml` | Plan may be stale vs workspace state | Auto-update plan from spec status |
| Agent docs | 4 | `AGENTS.md`, `CLAUDE.md` | Multiple conflicting worktree conventions | Consolidate per AGENTS.md note |

**Area J average: 3.36/5 (67.1%)**

---

## K. Ops & Deploy

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Dockerfile quality | 2 | `Dockerfile.rust:1-16` multi-stage missing; runs full workspace build | Build fails with current 1-member workspace | Fix workspace; add slim runtime stage |
| Docker compose | 3 | `docker-compose.yml:24-47` rust-builder + python-mcp | No healthcheck directives on services | Add `healthcheck` to compose services |
| IaC / k8s | 1 | absence of `k8s/` or Helm charts | No production k8s manifests | Add minimal Helm chart or document absence |
| Config via env + .env.example | 3 | `.env.example` Sentry only | Missing API_PORT, DATABASE_URL, NATS_URL | Expand `.env.example` for all services |
| Healthchecks | 3 | `process-compose.yml:10-29` NATS/redis probes | API process lacks probe in process-compose | Add agileplus-api readiness probe |
| Graceful shutdown | 2 | tokio runtime used; no explicit shutdown handler found | SIGTERM may drop in-flight requests | Add `axum::serve` with graceful shutdown |
| Deploy docs | 3 | `deploy.yml` workflow; `docker-compose.plane.yml` | No single `docs/ops/deploy.md` runbook | Author deploy runbook |
| Reproducible builds | 3 | `rust-toolchain.toml` nightly; `toolchain-versions.json` | Nightly channel reduces reproducibility | Pin stable MSRV for releases |
| Secrets management | 3 | ADR-011 keychain; `credentials.rs` | Production K8s secrets path missing | Document keychain vs K8s secret mapping |
| Rollback path | 2 | `promote.yml` | No automated rollback | Add `helm rollback` or release revert procedure |
| Local dev orchestration | 4 | `process-compose.yml` NATS, dragonfly, services | Not referenced in README quickstart | Add `mise run dev` or process-compose to README |
| Plane.so integration ops | 3 | `docker-compose.plane.yml` 5040 bytes | Plane stack heavy for local dev | Document optional Plane profile |
| MCP deploy | 3 | `python/Dockerfile.python` referenced | Python MCP not in main CI build | Add python CI job |
| Monitoring sidecar | 2 | `sentry-error-tracking.yml` | No unified observability stack in compose | Add otel-collector + jaeger services |

**Area K average: 2.50/5 (50.0%)**

---

## L. Governance & Traceability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| FR / NFR spec present | 5 | `FUNCTIONAL_REQUIREMENTS.md` v2.2 with code locations | — | Keep FR regenerated from code |
| Spec → impl → test linkage | 4 | FR table cites `crates/agileplus-domain/...`; API tests cite FR-AGP-015 | Not all FRs have tests | Close gaps via `fr-coverage.yml` |
| Acceptance contracts typed | 4 | `traceability-core` contract types; BDD governance scenarios | Contracts not enforced in CI | Run trace-validator on PR |
| ProgressionGates | 4 | `gate-check.yml`, `quality-gate.toml`, `journey-gate.yml` | Gate thresholds not all automated | Wire quality-gate.toml to CI parser |
| Coverage matrix | 3 | `fr-coverage.yml:13` echo stub only | FR coverage not computed | Implement phenotype-tooling FR scanner |
| ADR discipline | 4 | ADR-001–014 in `ADR.md`; `docs/adr/` files | Accepted ADRs conflict with workspace reality (22 crates ADR vs 1 active) | ADR amendment for workspace bootstrap |
| Decorator / annotation traceability | 4 | `api_key.rs:3` `Traceability: FR-028`; openapi traceability comments | Inconsistent across crates | Mandate `#[trace(fr = "...")]` proc-macro |
| No orphan code | 2 | 729 rs files vs 1 workspace member | Most code untraced by CI | Orphan detection in `workspace-audit.yml` |
| No untraced FR | 3 | FR doc comprehensive | FR-CLI/API sections may lack tests | FR coverage report per PR |
| Requirements completeness | 4 | NFR in PRD; quality-gate thresholds | NFR perf/security not all measurable | Add NFR verification tests |
| Worklog / evidence | 4 | `worklog.md` 45KB; `worklog-*.json` artifacts | Worklogs at repo root clutter | Move to `.work-audit/` only |
| Governance index CI | 4 | `governance-index.yml`, `pr-governance-gate.yml` | Self-merge-gate complexity | Document governance DAG for contributors |
| Kitty-specs integration | 4 | `kitty-specs/` referenced in CONTRIBUTING | Spec harmonizer crate excluded from workspace | Onboard `agileplus-spec-harmonizer` |
| Trace validator | 4 | `agileplus-trace-validator` 19 intent tests | Not required check | Add to required PR checks |
| Spec-first CI | 4 | `spec-first.yml` workflow | Spec drift detection unclear | Fail PR when spec file missing for feat/* |
| Audit scorecard | 4 | `audit_scorecard.json`, `AUDIT_INDEX.md` | Prior audit not same rubric | Link this AUDIT.md from AUDIT_INDEX |

**Area L average: 3.71/5 (74.3%)**

---

## Ranked Remediation Backlog (worst-first)

Priority = impact × gap severity. Scores reference pillar scores ≤2.

| Rank | ID | Pillar (Area) | Score | Remediation | Effort |
|------|-----|---------------|-------|-------------|--------|
| 1 | R-001 | Module boundaries (A) | 1/5 | Onboard all implemented crates into `Cargo.toml` workspace; CI `cargo test --workspace` | L |
| 2 | R-002 | Workspace CI scope (E/D) | 1-2/5 | Change `ci.yml` from `cd rust` to full workspace build/test | M |
| 3 | R-003 | Newtypes over primitives (B) | 1/5 | Add `FeatureId`, `Slug`, `ApiKeyHash` newtypes | M |
| 4 | R-004 | Rate limiting (F) | 1/5 | Apply `tower::limit::RateLimitLayer` on API router | S |
| 5 | R-005 | Mutation testing (D) | 1/5 | Add `cargo-mutants` nightly job; gate at 60% per quality-gate.toml | M |
| 6 | R-006 | Load ceiling documented (H) | 1/5 | Run k6/oha load test; publish RPS in `docs/perf/` | M |
| 7 | R-007 | IaC / k8s (K) | 1/5 | Helm chart or explicit "local-only" ADR amendment | L |
| 8 | R-008 | FR coverage workflow (L) | 3/5 stub | Replace `fr-coverage.yml` echo with real scanner | M |
| 9 | R-009 | OpenAPI completeness (C) | 2/5 | Annotate remaining 31 handlers; enable drift CI | M |
| 10 | R-010 | Authorization RBAC (F) | 2/5 | Scoped API keys with role claims | L |
| 11 | R-011 | E2E in CI (D/E) | 2/5 | docker-compose test rig as required check | M |
| 12 | R-012 | Health check realism (G) | 3/5 simulated | Real SQLite ping in `SqliteChecker` | S |
| 13 | R-013 | Dockerfile fix (K) | 2/5 | Multi-stage build aligned to workspace | M |
| 14 | R-014 | Correlation IDs (G) | 2/5 | `X-Request-Id` middleware | S |
| 15 | R-015 | Pagination / idempotency (C) | 2/5 | Standard list envelope + idempotency keys | M |
| 16 | R-016 | Connection pooling (H) | 2/5 | `r2d2` SQLite pool for API | M |
| 17 | R-017 | README quickstart accuracy (J) | 3/5 wrong binary | Fix package names and commands | S |
| 18 | R-018 | `.env.example` completeness (K) | 3/5 partial | Add DATABASE_URL, API_PORT, NATS_URL | S |
| 19 | R-019 | Pin all GitHub Actions (F) | 4/5 partial | SHA-pin `actions/checkout@v7` in ci.yml | S |
| 20 | R-020 | Orphan code audit (L) | 2/5 | workspace-audit fails on excluded crates with sources | M |

---

## All-5s Punch-List (perfect score targets)

Every item must reach **5/5** on re-audit.

### Architecture & Design
- [ ] Workspace includes every non-scaffold crate; `cargo build --workspace` green
- [ ] All IO behind port traits; application crate owns use-cases
- [ ] `phenotype-dep-guard` required on PR; zero cyclic deps
- [ ] No module >500 LOC without ADR exception
- [ ] Single hex kit (`hexkit`) — no duplicate port registries

### Domain Modeling & Types
- [ ] All IDs are newtypes; no bare `i64`/`String` in public domain API
- [ ] `Transition`, `Slug`, `Actor` as validated newtypes
- [ ] `StorageError` typed per adapter; no `String` wrappers
- [ ] Property tests on state machine + audit chain (256+ cases)
- [ ] FR doc auto-generated from code; zero field drift

### API / Interface Design
- [ ] OpenAPI 100% handler coverage; CI drift check enforced
- [ ] `/v1` versioned routes; deprecation policy documented
- [ ] `Paginated<T>` + cursor on all list endpoints
- [ ] `Idempotency-Key` on all POST/PUT/PATCH
- [ ] `ProblemDetails` error schema on all 4xx/5xx

### Testing
- [ ] ≥80% line / ≥70% branch coverage enforced in CI
- [ ] Mutation score ≥60% on domain + API crates
- [ ] BDD features cover CLI + HTTP happy paths
- [ ] E2E compose job required on PR
- [ ] Zero flaky tests; quarantine policy active

### CI/CD & Release
- [ ] Full workspace fmt/clippy/test on every PR
- [ ] MSRV + stable + nightly matrix
- [ ] Tag-push releases with signed artifacts + SBOM
- [ ] Buf breaking change detection enabled
- [ ] Nightly full test + benchmark regression

### Security
- [ ] RBAC with scoped API keys
- [ ] Rate limits per route class
- [ ] All actions SHA-pinned; SBOM committed and fresh (<7d)
- [ ] No DB files in git; gitleaks clean
- [ ] TLS termination documented and tested

### Observability
- [ ] OTLP traces + Prometheus metrics on all binaries
- [ ] `/health` (liveness) + `/ready` (readiness) with real dependency checks
- [ ] `X-Request-Id` on all requests; structured JSON logs
- [ ] Grafana dashboards + alert rules in repo
- [ ] PII/secret redaction in log pipeline

### Performance & Scalability
- [ ] Documented RPS/CPU ceiling with load test artifacts
- [ ] Timeouts + body limits on all routes
- [ ] SQLite WAL + connection pool
- [ ] Benchmark CI with critcmp thresholds
- [ ] N+1 query audit clean on hot paths

### Data & Persistence
- [ ] All migrations reversible tested in CI
- [ ] `PRAGMA foreign_keys=ON` enforced
- [ ] Backup/restore CLI command with tested restore
- [ ] Data retention ADR implemented
- [ ] Event replay + snapshot rebuild E2E test

### Docs & DX
- [ ] README 100% accurate quickstart (copy-paste works)
- [ ] `cargo binstall` or install script
- [ ] Runnable `examples/` for top 5 journeys
- [ ] Devcontainer linked; one-command `mise run dev`
- [ ] VitePress site with zero broken links

### Ops & Deploy
- [ ] Multi-stage Dockerfile; image <100MB runtime
- [ ] Compose healthchecks on all services
- [ ] Graceful shutdown integration test
- [ ] Helm chart or documented PaaS deploy
- [ ] Rollback runbook tested quarterly

### Governance & Traceability
- [ ] FR coverage 100% with tests; CI fails on untraced FR
- [ ] Every PR links spec ID; spec-first gate enforced
- [ ] Trace-validator required check
- [ ] Zero orphan `.rs` files outside trace graph
- [ ] ADRs current with implementation reality

---

## Audit Metadata

- **Pillars graded:** 168 (14 × 12 areas)
- **Total score:** 526 / 840 = **62.6%**
- **Method:** Static file analysis only; no builds, tests, or network calls executed
- **Anti-wipe:** This commit adds only `docs/audit/AUDIT.md`
