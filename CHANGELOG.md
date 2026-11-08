# Changelog

## [Unreleased]

### Added
- **P3, L5-105 (2026-06-18):** Absorption completion record for `Metron` + `Traceon` → `PhenoObservability`. Both repos are already absorbed as workspace members `crates/metrickit` (PR #157, 2026-06-17) and `crates/tracingkit` (PR #161, 2026-06-17). This changelog entry records the completion of P3 per `phenotype-registry/ECOSYSTEM_MAP.md §6`. See `docs/migrations/metron-traceon-merge-2026-06-18.md` for full validation evidence (69/69 tests pass, byte-identical source parity for `src/`, `tests/`, `README.md`; workspace-aligned `Cargo.toml` per ADR-022 fleet pattern). Source repos `<REDACTED>/Metron` and `<REDACTED>/Traceon` are left in place pending human archive confirmation (L5-105 §5).

---


All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed
- **ci(audit):** switch `.github/workflows/audit.yml` from the non-existent `rustsec/audit-action@v2` reference (returning 404; workflow was failing every run for the entire recorded history, 0/74 success on the latest sampled runs) to the SHA-pinned `rustsec/audit-check@69366f33c96575abad1ee0dba8212993eecbe998` used by `.github/workflows/cargo-audit.yml`. Also pins `actions/checkout` to a SHA per ADR-042, aligns the runner to `ubuntu-24.04`, and adds explicit `contents: read` permissions plus `workflow_dispatch` for manual triggers. Hosted verification on this PR's branch (run id `34311528488`) now resolves the action and runs cargo-audit; the workflow no longer fails on a 404. **Caveat:** the run still concludes with a real cargo-audit finding (RUSTSEC-2026-0204 `crossbeam-epoch`, RUSTSEC-2026-0258 `h2`, plus `event-listener` unsound and a yanked `chacha20` warning); remediation is out of scope for this PR and tracked as a follow-up. Unblocks required `audit` check on PR #249 from the opaque 404 failure mode.

### Security

## [phenotype-observably-macros 0.1.1] - 2026-04-26

### Added
- `async_instrumented` now emits a `compile_error!` at macro expansion when applied to an async fn whose return type is not `Result<T, E>` / `anyhow::Result<T>` (or any path ending in `Result`). Converts opaque consumer-side E0308 errors into a clear macro-time diagnostic naming the offending return type.

## 🐛 Bug Fixes
- Fix(tracingkit): resolve 6 compile errors (phenoobs precursor) (#4)

Precursor 2 of 3 for workspace dedupe (tasks #50 + #68).

Errors fixed:
- E0255 (name clash): removed stray `use super::SpanStatus` in span.rs
  that collided with the local enum definition.
- E0204 (Copy on non-Copy): removed `Copy` derive from `SpanStatus`;
  the `Error { message: String }` variant holds a `String` and cannot
  be bitwise-copied. `Clone` is retained.
- E0432 (unresolved `super::TraceId`): removed the dangling `TraceId`
  and unused `Span`, `uuid::Uuid` imports from `domain/tracer.rs`.
- E0277 (missing `SpanHandle` impl, 3 sites in tracer_provider.rs):
  introduced `SpanHandleImpl(Mutex<Span>)` in `domain/tracer.rs` and
  updated `TracerInstance` to box that wrapper. The `SpanHandle`
  contract is `&self` but mutates the span, so interior mutability is
  required; `Mutex` keeps the handle `Send`.
- Duplicate `TraceResult` re-export: removed the shadowing alias in
  `application/tracer_provider.rs`; the canonical definition now lives
  in `domain/errors`.
- Unused `TraceError` import in `adapters/exporters.rs` removed.

Additional cleanups (needed for clippy -D warnings):
- Dropped unnecessary `mut self` on two `ScopedSpan` builders.
- Added `name()` / `tracer()` / `sampler()` accessors to expose
  previously dead fields as legitimate API (no `#[allow(dead_code)]`).
- Explicit `'_` lifetime on `TracerProvider::tracer`.

Verification (scoped):
- `cargo check -p tracingkit` — clean.
- `cargo test -p tracingkit --lib` — 2/2 passing.
- `cargo clippy -p tracingkit --all-targets -- -D warnings` — clean.

Co-authored-by: Forge <forge@<REDACTED>.com> (`789dd74`)
- Fix(tracely-sentinel): remove orphan empty [workspace] stanza (resolves nested-workspace-root error) (#3)

The crate declared its own empty `[workspace]` block, making it a nested
workspace root inside the PhenoObservability root workspace. This caused
`cargo check --workspace` on main to fail with "multiple workspace roots
found".

Removing the empty stanza lets the crate be governed by the root workspace
as intended. Verified via `cargo check -p phenotype-sentinel` (passes).

Precursor #1 to PhenoObs workspace dedupe (per audit ae0fe9a3).

Co-authored-by: Forge <forge@<REDACTED>.com> (`05cf4f4`)
- Fix: add phenotype-surrealdb and fix workspace (`579669c`)
- Fix: repair workspace configuration (`d8f30f9`)
## ✨ Features
- Feat: merge tracely, Traceon into PhenoObservability

Merged crates:
- tracely-core: Core tracing infrastructure
- tracely-sentinel: Sentinel-based monitoring
- helix-logging: Structured logging framework
- tracingkit: Comprehensive tracing toolkit

PhenoObservability now contains 10 observability crates:
- pheno-dragonfly, pheno-questdb, pheno-tracing
- phenotype-llm, phenotype-mcp-server, phenotype-surrealdb
- tracely-core, tracely-sentinel, helix-logging, tracingkit

Archive tracely and Traceon after this merge. (`4da541f`)
- Feat: add phenotype-surrealdb (SurrealDB fork) (`f3123b4`)
- Feat: add fork crates (phenotype-llm, phenotype-mcp-server, phenotype-surrealdb)

Fork crates for PhenoObservability:
- phenotype-llm: litellm fork with Rust core
- phenotype-mcp-server: fastmcp fork with Rust core
- phenotype-surrealdb: SurrealDB fork (`d4350d0`)
- Feat(observability): add pheno-tracing crate

Distributed tracing utilities with tracing_subscriber integration.
Migrated from archived helix-tracing repo. (`2e184b8`)
- Feat: add Dragonfly and QuestDB storage clients

- Dragonfly: Redis-compatible cache (multi-threaded, 25x faster)
- QuestDB: Time-series storage (100x faster than InfluxDB)

These replace Redis and InfluxDB respectively. (`ad910da`)
## 🔨 Other
- Chore(deps): align tokio + serde to org baseline (phenotype-versions.toml)

- tokio: unified to 1.39
- serde: unified to 1.0
- Verified: cargo check passed

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`2ea0cbc`)
- Chore(ci): adopt phenotype-tooling workflows (wave-3) (`00a6e58`)
- Test(smoke): seed minimal smoke test (wave-2) (`3312586`)
- Chore(governance): adopt standard CLAUDE.md + AGENTS.md + worklog (wave-2) (`26156ea`)
- Chore(deps): align thiserror to v2.0 per org baseline (`5903cd8`)
- Test(obs): 75+ unit tests + FR docs + CI workflow — address P1 coverage gap (`6e31e5f`)
- Ci: add reusable phenotype workflows (#1)

Co-authored-by: Forge <forge@<REDACTED>.com> (`ef1d88d`)
- Chore(tracely): annotate 5 dead_code suppressions with kept reasons (#2)

All 5 suppressions in tracely-sentinel/src/validation.rs mark public
builder API surface (Validator::integer/min/max/validate, validate_field
helper) kept as intentional no-ops for downstream API compatibility.
Added `// kept: ...` rationale above each.

cargo build -p phenotype-sentinel: clean in 9s.

Co-authored-by: Forge <forge@<REDACTED>.com>
Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`a7667f5`)
- Chore: aggressive adoption - edition 2024 and dependency updates (`c5d0336`)
- Initial: PhenoObservability - health, logging, metrics, telemetry (`2539fa8`)
