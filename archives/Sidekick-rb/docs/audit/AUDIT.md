# Sidekick — Deep Quality Audit (168 Pillars)

**Auditor:** strict quality audit (automated + manual evidence review)  
**Branch audited:** `origin/main` @ `5b7bb42`  
**Date:** 2026-06-24  
**Rubric:** `C:/Users/koosh/Dev/_AUDIT_RUBRIC.md` (12 areas × 14 pillars = 168)  
**Grading scale:** 0 absent · 1 stub · 2 partial · 3 adequate · 4 strong · 5 exemplary

---

## Executive Summary

| Area | Pillars | Sum | Avg /5 | % |
|------|---------|-----|--------|---|
| A. Architecture & Design | 14 | 35 | 2.50 | 50.0% |
| B. Domain Modeling & Types | 14 | 35 | 2.50 | 50.0% |
| C. API / Interface Design | 14 | 32 | 2.29 | 45.7% |
| D. Testing | 14 | 24 | 1.71 | 34.3% |
| E. CI/CD & Release | 14 | 33 | 2.36 | 47.1% |
| F. Security | 14 | 50 | 3.57 | 71.4% |
| G. Observability | 14 | 23 | 1.64 | 32.9% |
| H. Performance & Scalability | 14 | 36 | 2.57 | 51.4% |
| I. Data & Persistence | 14 | 11 | 0.79 | 15.7% |
| J. Docs & DX | 14 | 33 | 2.36 | 47.1% |
| K. Ops & Deploy | 14 | 23 | 1.64 | 32.9% |
| L. Governance & Traceability | 14 | 24 | 1.71 | 34.3% |
| **Overall** | **168** | **359** | **2.14** | **42.7%** |

**Headline:** Security CI posture is the strongest lane (F). The workspace is materially thinner than README/consolidation docs claim: only `sidekick-messaging` is a Cargo workspace member (`Cargo.toml:2-4`), Python `cheap-llm-mcp` is vendored but not CI-gated, and root FR/traceability docs are scaffolding. Data/persistence and ops/deploy are largely absent.

---

## A. Architecture & Design

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Hexagonal ports/adapters | 2/5 | `crates/sidekick-messaging/src/lib.rs:64-70` `MessagingAdapter` trait | No adapter implementations; no infra layer | Add `IMessageAdapter`/`SmsAdapter` impls behind trait |
| SOLID — Single Responsibility | 3/5 | `lib.rs` single cohesive module | README claims 4 canonical members (`README.md:37-47`) vs one workspace crate | Reconcile manifest, docs, and tree |
| SOLID — Open/Closed | 3/5 | Trait-based extension point `lib.rs:64` | Zero production adapters registered | Adapter registry + discovery |
| SOLID — Dependency Inversion | 2/5 | Trait exists | `Cargo.toml:22` `phenotype-errors` path dep unused by any crate | Remove or consume shared error crate |
| DRY (docs vs code) | 1/5 | Duplicated member tables `README.md:43-47`, `docs/index.md:36-41` | `docs/consolidation_notes.md:11-14` claims copied crates absent from tree | Single SSOT for membership |
| Module boundaries | 1/5 | `Cargo.toml:2-4` members = `sidekick-messaging` only | `cheap-llm-mcp/` vendored but outside workspace; `sidekick-presence`/`dispatch` missing | Add members or demote README claims |
| Coupling / cohesion | 2/5 | Messaging crate self-contained | Cross-repo `../pheno/crates/phenotype-errors` path coupling | Publish/registry dependency |
| Dependency direction (inward) | 2/5 | `sidekick-messaging` deps: serde, thiserror only | Workspace declares external path dep not used | Drop unused workspace deps |
| Layering (domain/app/infra) | 1/5 | Flat `lib.rs` | No separation for MCP bridge, HTTP, persistence | `domain/`, `ports/`, `adapters/` modules |
| No god objects | 4/5 | `lib.rs` 97 lines | `cheap-llm-mcp` globals `_router`, `_ledger` `server.py:18-19` | Inject dependencies in Python server |
| Cyclic dependencies | 5/5 | No cycles in Rust dep graph | — | Maintain |
| Public surface minimalism | 3/5 | Small public API in messaging | `release-registry.toml:10-24` lists non-repo crates | Registry reflects in-tree artifacts only |
| Dead flexibility | 2/5 | `release-registry.toml` dispatch entry `status=alpha` | Crates not present under `crates/` | Prune or import sources |
| Abstraction at two uses | 3/5 | `MessagingAdapter` before 2 impls | YAGNI risk on stub | Document intent or defer trait until 2nd provider |

**Area A average: 2.50 / 5 (50.0%)**

---

## B. Domain Modeling & Types

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Invariants encoded in types | 2/5 | `Message` struct `lib.rs:41-46` | Empty `body`/`recipient` allowed | Validated constructors / builder |
| Illegal states unrepresentable | 2/5 | `MessageProvider` enum `lib.rs:23-28` | Provider/recipient mismatch possible (Email to phone) | Newtype `Recipient` per channel |
| Newtypes over primitives | 1/5 | `recipient: String`, `body: String` `lib.rs:43-44` | No domain newtypes | `RecipientEmail`, `E164`, etc. |
| Ubiquitous language | 3/5 | `MessageProvider::{IMessage,SMS,Email}` | README uses "sidekick-presence" names not in code | Align glossary across docs/code |
| Enum exhaustiveness | 4/5 | `Display` match `lib.rs:32-36` | — | Keep `#[non_exhaustive]` if extending |
| Error type design (thiserror) | 4/5 | `MessagingError` `lib.rs:14-20` | `Unauthorized` never constructed in lib | Wire auth errors when adapters exist |
| Option/Result discipline | 3/5 | `Result<T>` alias `lib.rs:11` | No `?` propagation paths in stub | Implement adapter methods |
| No stringly-typed IDs | 1/5 | Plain `String` recipient | No message ID type | `MessageId(Uuid)` newtype |
| Value vs entity distinction | 2/5 | `Message` is value object | No conversation/thread entity | Model thread aggregate if needed |
| ID schemes | 1/5 | Absent | No correlation to external message IDs | Document provider ID mapping |
| Serde contracts | 3/5 | `Serialize, Deserialize` on domain types | No schema versioning | Add `#[serde(deny_unknown_fields)]` where safe |
| Clone/Debug conventions | 4/5 | Derives on public types per `CLAUDE.md` | — | Maintain on new types |
| Python typed config models | 4/5 | `@dataclass` `config.py:9-33` | — | Extend to runtime request models |
| Validation at construction | 1/5 | `Message::new` `lib.rs:50-60` | No trim/non-empty checks | `try_new` returning `Result` |

**Area B average: 2.50 / 5 (50.0%)**

---

## C. API / Interface Design

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| REST resource modeling | 0/5 | Absent | No HTTP API in workspace | N/A unless REST added |
| CLI ergonomics | 4/5 | `cheap-llm-mcp` CLI `cli.py:94` `doctor` subcommand | Not documented in root README quickstart | Link CLI in root docs |
| Versioning | 2/5 | Workspace `0.0.1` `Cargo.toml:8`; Python `0.4.0` `pyproject.toml:3` | Version skew across members | Unified collection version policy |
| Request/response contracts | 4/5 | MCP tools return typed dicts `server.py:57-74` | Rust trait returns bare `String` | Structured `SendReceipt` type |
| Idempotency | 2/5 | Absent explicit keys | Retries may duplicate sends (future) | Idempotency-Key for outbound messages |
| Pagination | 0/5 | Absent | N/A for current scope | Document N/A or add list APIs |
| HTTP status semantics | 3/5 | `retry.py:15` `RETRYABLE_STATUS` | Only in Python provider layer | Expose retry policy in docs |
| Backward compatibility | 2/5 | `cargo-semver-checks.yml:23` package `sidekick-messaging` | Python MCP tools not semver-checked | Add MCP contract/version tests |
| Schema docs (OpenAPI) | 1/5 | Absent OpenAPI | MCP-only surface | Generate MCP tool schema manifest |
| Input contracts | 3/5 | `Literal` provider param `server.py:52` | Rust `send` accepts any `Message` | Validate inputs at trait boundary |
| MCP tool surface completeness | 4/5 | `complete`, `health` tools `server.py:41-48,139` | Messaging crate has no MCP exposure | Bridge messaging to MCP or document deferral |
| Trait API stability | 2/5 | Pre-1.0 stub `release-registry.toml:21` `status=stub` | Breaking changes likely | Stabilize trait before 0.1.0 |
| Error mapping to API | 2/5 | `MessagingError` not exposed via MCP | Consumers can't distinguish errors | Error codes in MCP responses |
| Cost/rate API | 3/5 | `ledger.check_cap()` `server.py:64` | No user-facing quota API in Rust | Document caps in README |

**Area C average: 2.29 / 5 (45.7%)**

---

## D. Testing

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Unit tests | 3/5 | `lib.rs:72-96` 3 tests; 9 Python test modules under `cheap-llm-mcp/tests/` | Messaging tests don't exercise adapters | Adapter unit tests with fakes |
| Integration tests | 3/5 | `test_server_integration.py` | Not run in CI | Add pytest job to `ci.yml` |
| E2E tests | 1/5 | Absent cross-crate E2E | No workspace-level harness | Smoke MCP + messaging integration test |
| Property-based tests | 0/5 | Absent (`hypothesis` not in deps) | — | Add proptest/hypothesis for router |
| BDD / Gherkin | 0/5 | Absent | — | Optional `.feature` for FR acceptance |
| Coverage % tracked | 1/5 | `docs/reference/fr_coverage_matrix.md:5-8` reports 0 FRs | Root matrix empty/stale | Generate matrix in CI |
| Meaningful assertions | 2/5 | `tests/smoke_test.rs:7` `assert_eq!(2+2,4)` | Trivial smoke | Replace with workspace invariant test |
| Fixtures / factories | 4/5 | `conftest.py`, `test_router.py:32-50` fixture | Rust side lacks factories | `MessageBuilder` test helper |
| Determinism | 3/5 | HTTP mocked via `respx` in Python tests | Random jitter in `retry.py:33` | Seed RNG in tests |
| Test isolation | 3/5 | Ledger tests use temp paths | Global singletons in `server.py` | Reset globals between tests |
| Mutation resistance | 1/5 | Minimal Rust tests | High mutation survival | Strengthen assertions |
| Perf / load tests | 0/5 | Absent | — | Add benchmark crate or pytest-benchmark |
| Contract tests | 2/5 | `@pytest.mark.requirement("FR-LLM-*")` in tests | Root `docs/FUNCTIONAL_REQUIREMENTS.md` unrelated SIDE-* IDs | Align FR IDs repo-wide |
| Flaky-free CI | 1/5 | `ci.yml:13` only `cargo test` | Python suite not gated; network tests risk | CI pytest with mocks only |

**Area D average: 1.71 / 5 (34.3%)**

---

## E. CI/CD & Release

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Pipeline completeness | 3/5 | 11 workflows under `.github/workflows/` | No unified `ci` for Python | Polyglot CI matrix |
| `cargo fmt` gate | 2/5 | `.pre-commit-config.yaml:12` fmt hook | `ci.yml` lacks `cargo fmt --check` | Add fmt step to CI |
| Clippy gate | 4/5 | `ci.yml:14` `-D warnings` | — | Keep |
| Build matrix | 1/5 | `ubuntu-latest` only | No macOS/Windows | Add OS matrix for messaging |
| Release artifacts | 4/5 | `release-attestation.yml:40-60` | May produce empty exe set (lib-only crate) | Publish crate + Python wheel |
| Scheduled workflows | 2/5 | `cargo-audit.yml:11-12` weekly cron | No nightly full suite | Nightly workspace+python test |
| E2E workflow | 0/5 | Absent | — | Add `e2e.yml` MCP smoke |
| Artifact integrity / signing | 4/5 | SLSA attest `release-attestation.yml:83-86` | — | Extend to Python packages |
| Caching | 4/5 | `Swatinem/rust-cache@v2` in CI/release | No uv cache for Python | Add uv/pip cache |
| Required checks (documented) | 2/5 | README:158-164 lists gates | Branch protection not in-repo | Document required checks in CONTRIBUTING |
| Rollback procedure | 1/5 | Absent | — | Release rollback runbook |
| Changelog / release notes | 2/5 | `CHANGELOG.md:5-17` empty Unreleased | — | Maintain per-release notes |
| Public Ubuntu CI | 4/5 | All jobs `ubuntu-latest` | — | Keep free tier |
| Python package CI | 0/5 | Absent pytest/ruff in workflows | `cheap-llm-mcp` ungated | `uv run pytest` + ruff job |

**Area E average: 2.36 / 5 (47.1%)**

---

## F. Security

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Authentication | 2/5 | MCP server has no auth layer `server.py` | Open local MCP trust model | Document threat model; optional token |
| Authorization | 2/5 | `MessagingError::Unauthorized` `lib.rs:18-19` | Unused | Enforce when multi-tenant |
| Secrets via env (no hardcode) | 4/5 | `ProviderConfig.api_key` reads env `config.py:20-24` | `.env.example` only under `cheap-llm-mcp/` | Root `.env.example` index |
| Dependency CVE audit | 5/5 | `cargo-audit.yml` weekly + `rustsec/audit-check` | — | Keep |
| Supply chain (pinned actions) | 3/5 | Pinned: `cargo-audit.yml:19-20`; floating: `ci.yml:10` `@v4` | Mixed pinning policy | Pin all actions to SHA |
| SBOM | 4/5 | `sbom-refresh.yml`, `docs/security/sbom.json` | Python SBOM not evident at root | Include uv lock in SBOM |
| Input validation at boundaries | 3/5 | Config TOML validation `config.py:58-65` | MCP prompt length unbounded | Max prompt size guard |
| Injection safety | 3/5 | No SQL; HTTP JSON APIs | Prompt passed to providers raw | Sanitize/log redaction |
| TLS | 4/5 | HTTPS default URLs `config.py:80-102` | — | Enforce TLS in custom configs |
| Least privilege (CI) | 4/5 | `permissions: read-all` on most workflows | Attestation job needs write (justified) | Review per-job permissions |
| Rate limiting / cost caps | 3/5 | `Ledger` monthly cap `server.py:64` | Per-request rate limit absent | Token bucket for MCP tools |
| Secret scanning | 4/5 | `trufflehog.yml` `--only-verified` | — | Keep |
| CODEOWNERS | 4/5 | `.github/CODEOWNERS:6-15` | Single owner | Add backup reviewers |
| SAST (CodeQL) | 4/5 | `codeql.yml` Rust only | Python not analyzed | Add `languages: python` job |

**Area F average: 3.57 / 5 (71.4%)**

---

## G. Observability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Structured logging | 4/5 | `JsonFormatter` `logging_util.py:13-59` | Rust crate has no logging | Add `tracing` to messaging |
| Log levels | 3/5 | `setup_json_logging(level)` `logging_util.py:72-79` | Default INFO only | Configurable via env |
| Metrics (Prometheus/etc.) | 0/5 | Absent | — | Export request/latency counters |
| Tracing / spans | 1/5 | `tracing` in workspace deps `Cargo.toml:19` unused | No `#[instrument]` in Rust | Instrument adapter calls |
| Health / readiness | 3/5 | `cheapllm_check_health` `server.py:139-145` | No health for Rust workspace | Workspace health binary |
| Error reporting | 2/5 | Logs exceptions in JSON formatter | No Sentry/etc. | Optional error sink |
| Correlation IDs | 4/5 | `request_scope` `logging_util.py:62-69` | Not propagated to ledger entries | Include `request_id` in ledger |
| Dashboards | 0/5 | Absent | — | Link to org Grafana or document gap |
| Alerting | 0/5 | Absent | — | Alert on cost cap breach |
| Audit trail | 3/5 | `ledger.jsonl` `server.py:35-36` | Messaging sends not logged | Unified audit log |
| Rust tracing integration | 0/5 | Absent in `sidekick-messaging` | — | `tracing-subscriber` setup |
| SLO definitions | 0/5 | Absent | — | Define latency SLO for MCP tools |
| OpenTelemetry | 0/5 | Absent | — | OTel exporter optional |
| CI failure observability | 3/5 | Standard GitHub Actions logs | No build insights | Add test report artifacts |

**Area G average: 1.64 / 5 (32.9%)**

---

## H. Performance & Scalability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Hot-path profiling | 0/5 | Absent | — | `cargo flamegraph` / py-spy docs |
| Async / concurrency correctness | 4/5 | `async def complete` `server.py:49` | Sync trait `MessagingAdapter::send` | Async trait or blocking pool |
| Caching | 4/5 | `TTLCache` in `router.py:19,56-69` | Rust side none | Cache provider availability |
| N+1 avoidance | 3/5 | Sequential provider fallback `router.py:72-80` | Health checks loop providers | Parallel health probe |
| Resource bounds | 3/5 | `max_tokens` default 4096 `server.py:55` | No global concurrency limit | Semaphore on inflight requests |
| Streaming vs buffering | 4/5 | `stream_complete` tool + tests `test_streaming.py` | Rust messaging no streaming | Document streaming deferral |
| Backpressure | 1/5 | Absent explicit | Unbounded prompt size | Queue depth limits |
| Algorithmic complexity | 3/5 | O(providers) fallback loop | Fine at 3 providers | Document scaling limits |
| Load ceiling documented | 1/5 | Absent | — | Max RPS / concurrent MCP calls |
| Memory management | 2/5 | Module-level caches `server.py:18-19` | Potential growth | Bound cache size |
| Release profile tuning | 4/5 | `lto=true`, `opt-level=3` `Cargo.toml:24-26` | — | Keep |
| HTTP connection reuse | 3/5 | Provider clients in `openai_compat.py` | No explicit pool tuning | Configure httpx limits |
| Cost efficiency caps | 4/5 | `monthly_cost_cap_usd` `config.py:32` | — | Surface in ops docs |
| Benchmark harness | 0/5 | Absent | — | Criterion + pytest-benchmark |

**Area H average: 2.57 / 5 (51.4%)**

---

## I. Data & Persistence

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Schema design | 2/5 | `Message` struct only | No persistence schema | Define storage schema if needed |
| Versioned migrations | 0/5 | Absent | — | Add migration tool if stateful |
| Referential integrity | 0/5 | N/A — no RDBMS | — | Document stateless design |
| Indexing strategy | 0/5 | Absent | — | N/A until datastore |
| Backup / restore | 0/5 | Absent | — | Backup `~/.cheap-llm/ledger.jsonl` procedure |
| Transactions | 0/5 | Absent | — | Atomic ledger writes |
| Data validation on persist | 2/5 | Ledger append `ledger.py` (implied) | No schema validation on read | JSON schema for ledger lines |
| Consistency model | 1/5 | Append-only jsonl | No crash safety spec | fsync or sqlite |
| Persistence layer abstraction | 2/5 | File path hardcoded `server.py:35` | Not injectable | `LedgerStore` trait |
| Serde persistence | 3/5 | JSON lines ledger | — | Version field per entry |
| Reversible migrations | 0/5 | Absent | — | N/A |
| Encryption at rest | 0/5 | Absent | Ledger may contain metadata | Encrypt sensitive ledger fields |
| Retention policy | 1/5 | Absent | Ledger grows unbounded | Rotation/archival policy |
| ORM / SQL usage | 0/5 | Absent | — | Document intentional omission |

**Area I average: 0.79 / 5 (15.7%)**

---

## J. Docs & DX

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| README work-state header | 4/5 | AI-DD-META block `README.md:1-21` | No conventional progress bar | Add build/coverage badges that work |
| Quickstart | 3/5 | `docs/getting-started.md:19-39` | Fails clone-only without `../pheno` path dep | Standalone clone instructions |
| Install docs | 3/5 | Rust toolchain `rust-toolchain.toml` | Python `uv sync` not in root quickstart | Document cheap-llm setup |
| API reference | 2/5 | `cheap-llm-mcp/README.md` partial | No rustdoc published | `cargo doc` + MCP tool list |
| Runnable examples | 2/5 | README bash blocks `README.md:69-72` | Examples not verified in CI | `examples/` crate with tests |
| Onboarding | 3/5 | `CONTRIBUTING.md:7-11` workflow | Thin depth | Expand dev environment setup |
| CONTRIBUTING | 3/5 | Present `CONTRIBUTING.md` | No code style section for Python | Link ruff.toml conventions |
| Docs site populated | 3/5 | VitePress `docs/index.md`, `.vitepress/config.mjs` | Many propagated stubs | Fill intent/boundary sections |
| Media-proof / assets | 1/5 | `assets/logo-placeholder.svg` `README.md:31` | Placeholder logo | Replace with real asset |
| Code comment quality | 3/5 | Module docs `lib.rs:1-4` | Stale source comment `lib.rs:4` | Update agent-imessage reference |
| ADRs present | 1/5 | `docs/worklogs/ARCHITECTURE.md:3` scaffold only | No numbered ADRs | ADR-001 workspace scope |
| Consolidation doc accuracy | 1/5 | `consolidation_notes.md:11-14` claims copied crates | Tree contradicts | Rewrite consolidation status |
| FR documentation quality | 1/5 | `docs/FUNCTIONAL_REQUIREMENTS.md:11-16` generic SIDE-* | Unrelated to actual code | Rewrite from cheap-llm FR set |
| Cross-links / index | 3/5 | `docs/index.md` navigation | Broken sibling `../` links off-GitHub | Use full URLs in docs |

**Area J average: 2.36 / 5 (47.1%)**

---

## K. Ops & Deploy

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| Containerization (Dockerfile) | 0/5 | Absent (grep: no Dockerfile) | — | Multi-stage Rust + Python image |
| Docker Compose | 0/5 | Absent | — | `compose.yml` for local MCP |
| IaC / Kubernetes | 0/5 | Absent | — | Document k8s deferral or add manifests |
| Config via env + example | 3/5 | `crates/cheap-llm-mcp/.env.example` | No root example | Aggregate env template |
| Deploy healthchecks | 0/5 | Absent in deploy specs | MCP health not wired to orchestrator | K8s liveness → `cheap-llm doctor` |
| Graceful shutdown | 2/5 | `aclose` on providers `test_router.py:28-29` | MCP server shutdown not documented | Signal handlers |
| Deploy documentation | 1/5 | Absent root deploy guide | — | `docs/operations/deploy.md` |
| Reproducible builds | 3/5 | `--locked` `release-attestation.yml:44` | No `Cargo.lock` commit policy stated | Document lockfile policy |
| Secrets management | 2/5 | Env vars only | No K8s secrets / vault guide | Document secret injection |
| Rollback path | 1/5 | Absent | — | Pin previous release + attest verify |
| Toolchain pin | 4/5 | `rust-toolchain.toml:1-3` stable+clippy | — | Keep |
| Dev ergonomics (just) | 4/5 | `justfile:14` imports `phenotype.just` | Python recipes detect uv only at root if pyproject absent | Root pyproject or `just test-python` |
| Devcontainer | 0/5 | Absent (no `.devcontainer/`) | `audit_scorecard.json:369` false positive | Add devcontainer.json |
| MSRV documented | 3/5 | README:23 references toolchain | No explicit MSRV in Cargo.toml | `rust-version` key |

**Area K average: 1.64 / 5 (32.9%)**

---

## L. Governance & Traceability

| PILLAR | score/5 | evidence (file:line or absence) | gap | remediation |
|--------|---------|----------------------------------|-----|-------------|
| FR / NFR spec present | 2/5 | Root `docs/FUNCTIONAL_REQUIREMENTS.md` | Scaffolding only; cheap-llm has separate FR doc | Consolidate FR registry |
| Spec → impl → test linkage | 3/5 | `@pytest.mark.requirement` in `test_router.py:58+` | Rust tests lack FR markers | `#[test] #[fr("FR-MSG-001")]` pattern |
| Acceptance contracts typed | 1/5 | Absent | — | Typed acceptance structs per FR |
| Progression gates | 2/5 | `CLAUDE.md` quality gate commands | Not enforced in CI fully | CI = CLAUDE gates 1:1 |
| Coverage matrix | 1/5 | `fr_coverage_matrix.md:5-8` all zeros | Contradicts README 100% claims | Auto-generate matrix in CI |
| ADR discipline | 1/5 | Empty `docs/worklogs/ARCHITECTURE.md` | — | ADR per major decision |
| Decorator / annotation traceability | 3/5 | pytest `requirement` marker `pyproject.toml:28-30` | No enforcement test for orphans | CI check FR↔test mapping |
| No orphan code | 2/5 | `phenotype-errors` workspace dep unused | Dead workspace dependency | Remove or use |
| No untraced FR | 1/5 | README:58-62 claims 100% FR for external repos | In-repo FRs untraced | Honest coverage metrics |
| Requirements completeness | 1/5 | SIDE-001..006 unrelated to messaging | — | Rewrite from domain |
| Intent / boundary docs | 2/5 | `docs/intent/sidekick.md:25` `<To be filled>` | Propagated stubs | Complete L7 snapshots |
| AgilePlus mandate | 2/5 | `CLAUDE.md` references external AgilePlus | No in-repo work item links | Link specs in PR template |
| Audit scorecard accuracy | 1/5 | `audit_scorecard.json:39` "No source files" | False negatives | Regenerate scorecard |
| Release registry truth | 2/5 | `release-registry.toml:10-24` lists missing crates | Misleading status | Sync with actual tree |

**Area L average: 1.71 / 5 (34.3%)**

---

## Ranked Remediation Backlog (worst-first)

Priority uses **impact × gap severity** on the lowest-scoring pillars.

| Rank | Pillar | Area | Score | Remediation |
|------|--------|------|-------|-------------|
| 1 | ORM / persistence / migrations | I | 0/5 | Document stateless architecture OR add real datastore with migrations |
| 2 | Python CI gate | E | 0/5 | Add `uv run pytest` + ruff to `.github/workflows/ci.yml` |
| 3 | E2E workflow | E | 0/5 | MCP smoke workflow exercising `cheap-llm-mcp` |
| 4 | Dockerfile / Compose | K | 0/5 | Ship reproducible container for MCP server |
| 5 | Metrics / Prometheus | G | 0/5 | Export latency, token usage, error rate |
| 6 | FR coverage matrix (empty) | L | 1/5 | Generate FR↔test matrix; fail CI on gaps |
| 7 | Root FR doc scaffolding | L/J | 1/5 | Replace `SIDE-001..006` with real FR-MSG + FR-LLM rollup |
| 8 | Meaningful smoke test | D | 2/5 | Replace `2+2=4` with crate invariant test |
| 9 | Workspace/doc drift | A/J | 1/5 | Align `Cargo.toml` members, README, consolidation_notes |
| 10 | `cargo fmt` in CI | E | 2/5 | Add `cargo fmt --check` to main CI job |
| 11 | Rust observability | G | 0/5 | Wire `tracing` in `sidekick-messaging` |
| 12 | MessagingAdapter implementations | A/C | 2/5 | Implement at least one real adapter + integration test |
| 13 | Pin GitHub Actions to SHA | F | 3/5 | Replace floating `@v4` tags in `ci.yml` |
| 14 | CodeQL Python | F | 4/5 | Add Python analysis job |
| 15 | Devcontainer | K | 0/5 | Add `.devcontainer` for one-command onboarding |

---

## Punch-List: To Reach Perfect (All 5s)

Every pillar below must reach **5/5**. Grouped by area.

### A — Architecture
- [ ] Full hexagonal layout: domain / ports / adapters per crate with ≥2 adapter impls
- [ ] Workspace manifest = README member list; zero doc/code drift
- [ ] Published (not path) dependencies for all shared crates
- [ ] Layered modules with enforced dependency rules (e.g., `cargo-deny` bans)

### B — Domain
- [ ] Newtypes for all IDs and recipients; illegal states unrepresentable
- [ ] Validated constructors returning `Result` for every aggregate
- [ ] Unified error taxonomy across Rust + Python with stable codes

### C — API
- [ ] Versioned public API with semver + MCP contract tests
- [ ] OpenAPI or machine-readable MCP schema published in `docs/`
- [ ] Idempotent outbound operations with documented retry semantics

### D — Testing
- [ ] ≥90% line coverage Rust + Python with CI enforcement
- [ ] Property-based tests for router, retry, ledger
- [ ] E2E: clone → build → MCP round-trip in CI
- [ ] Mutation testing threshold met

### E — CI/CD
- [ ] Matrix: OS × Rust stable/beta × Python 3.12
- [ ] All CLAUDE.md gates in required CI checks
- [ ] Automated releases: crates.io + PyPI + signed attestations
- [ ] Nightly full suite + flaky test quarantine

### F — Security
- [ ] All actions SHA-pinned; Dependabot for uv lock
- [ ] CodeQL Rust + Python; cargo-deny + pip-audit
- [ ] Threat model doc; MCP auth option documented
- [ ] gitleaks + secret rotation runbook

### G — Observability
- [ ] `tracing` + OpenTelemetry across Rust and Python
- [ ] Prometheus metrics + Grafana dashboard JSON in repo
- [ ] SLOs with alerting on error budget burn
- [ ] Correlation IDs end-to-end including ledger

### H — Performance
- [ ] Criterion benchmarks in CI regression gate
- [ ] Documented load ceiling; backpressure on MCP
- [ ] Profiling guide with baseline numbers

### I — Data
- [ ] If stateful: versioned migrations, backups, encryption at rest
- [ ] If stateless: ADR documenting decision with ledger retention policy

### J — Docs
- [ ] README badges live (CI, coverage, crates.io)
- [ ] Runnable `examples/` tested in CI
- [ ] Complete ADR series; accurate consolidation doc
- [ ] FR registry single source of truth

### K — Ops
- [ ] Production Dockerfile + compose + optional k8s manifests
- [ ] Deploy runbook with health probes and rollback
- [ ] Devcontainer + root `.env.example`

### L — Governance
- [ ] 100% FR↔impl↔test traceability verified in CI
- [ ] Filled intent/boundary docs (no `<To be filled>`)
- [ ] Accurate audit scorecard regenerated from repo truth
- [ ] Release registry matches filesystem

---

## Audit Notes

- **Worktree:** Branch `audit/sidekick` reset to `origin/main` (`5b7bb42`) at `C:/Users/koosh/Dev/_wtAU/sidekick`. Requested path `C:\Users\koosh\Dev\_wtAU2$2` is occupied by an unrelated Go project and could not host a Sidekick worktree without destructive cleanup.
- **Builds:** Not executed per audit mandate.
- **Scope:** Evidence drawn from in-repo sources on `main`; external canonical repos (`agent-user-status`, `cheap-llm-mcp` upstream) referenced in README are out of tree and not scored as present implementations.

---

*End of audit — 168 pillars, overall 42.7% (359/840).*
