# PROVENANCE: tokn crates

## Source Repository

- **Original**: [KooshaPari/zz-Tokn](https://github.com/KooshaPari/zz-Tokn)
- **Absorbed into**: [KooshaPari/phenotype-tooling](https://github.com/KooshaPari/phenotype-tooling)
- **Date absorbed**: 2026-09-14
- **Original workspace version**: 0.1.5
- **License**: MIT

## Absorbed Crates

### 1. `crates/tokn-pareto-rs/` (originally `crates/pareto-rs`)

Pareto analysis helpers for tokenledger.

| File | Lines | Description |
|------|-------|-------------|
| `src/lib.rs` | 19 | Library root |
| `src/models.rs` | 436 | Pareto models and types |
| `src/concurrent.rs` | 414 | Concurrent Pareto operations |
| `src/cost.rs` | 476 | Cost analysis |
| `src/pricing.rs` | 469 | Pricing logic |
| `src/plugin.rs` | 564 | Plugin system |
| `src/event.rs` | 310 | Event handling |
| `src/metrics.rs` | 123 | Prometheus metrics |
| `src/format.rs` | 42 | Output formatting |
| `src/error.rs` | 56 | Error types |
| `src/utils.rs` | 164 | Utility functions |
| `src/bin/server.rs` | 69 | HTTP server binary |
| `tests/concurrent_integration.rs` | 309 | Integration tests |
| **Total** | **3,451** | |

### 2. `crates/tokn-tokenledger/` (originally `crates/tokenledger`)

Token management and pricing governance CLI for AI coding agents.

| File | Lines | Description |
|------|-------|-------------|
| `src/lib.rs` | 19 | Library root |
| `src/main.rs` | 36 | Binary entry point |
| `src/cli.rs` | 487 | CLI argument parsing |
| `src/models.rs` | 780 | Data models |
| `src/ingest/mod.rs` | 1,826 | Log ingestion pipeline |
| `src/ingest/aggregation.rs` | 12 | Aggregation helpers |
| `src/ingest/validation.rs` | 10 | Validation |
| `src/ingest/parser.rs` | 9 | Parser |
| `src/orchestrate.rs` | 741 | Orchestration logic |
| `src/utils.rs` | 733 | Utility functions |
| `src/bench.rs` | 698 | Benchmarking |
| `src/tenant.rs` | 684 | Multi-tenant support |
| `src/pricing.rs` | 614 | Pricing governance |
| `src/cost.rs` | 448 | Cost tracking |
| `src/cache.rs` | 416 | Caching layer |
| `src/format.rs` | 338 | Output formatting |
| `src/analytics.rs` | 217 | Analytics/reporting |
| `src/guardrails.rs` | 73 | Budget guardrails |
| `src/clap_ext.rs` | 56 | CLI extensions |
| `src/benchmarks/mod.rs` | 27 | Benchmarks module root |
| `src/benchmarks/cliproxy_metrics.rs` | 689 | Cliproxy metrics |
| `src/benchmarks/store.rs` | 316 | Benchmark store |
| `src/benchmarks/openrouter.rs` | 235 | OpenRouter benchmarks |
| `src/benchmarks/artificial_analysis.rs` | 211 | Artificial analysis |
| `src/benchmarks/overrides.rs` | 183 | Benchmark overrides |
| `src/benchmarks/thegent_adapter.rs` | 168 | TheGent adapter |
| `src/benchmarks/cli.rs` | 129 | Benchmark CLI |
| `src/routing/mod.rs` | 56 | Routing module root |
| `src/routing/pareto_frontier.rs` | 539 | Pareto frontier routing |
| `src/routing/adapters.rs` | 388 | Routing adapters |
| `src/routing/ports.rs` | 247 | Routing ports |
| `src/routing/mappings.rs` | 231 | Route mappings |
| `src/routing/pareto_router.rs` | 218 | Pareto router |
| `tests/tenant_integration_test.rs` | 327 | Tenant tests |
| `tests/cost_integration_test.rs` | 81 | Cost tests |
| `tests/budget_guardrails_integration_test.rs` | 65 | Guardrail tests |
| `tests/output_integration_test.rs` | 72 | Output tests |
| `tests/sliding_window_integration_test.rs` | 55 | Sliding window tests |
| `tests/claude_ingest_integration_test.rs` | 42 | Claude ingest tests |
| `tests/droid_ingest_integration_test.rs` | 42 | Droid ingest tests |
| `tests/cursor_ingest_integration_test.rs` | 40 | Cursor ingest tests |
| `tests/codex_ingest_integration_test.rs` | 40 | Codex ingest tests |
| `tests/ingest_checkpoint_integration_test.rs` | 25 | Ingest checkpoint tests |
| **Total** | **11,389** | |

### 3. `crates/tokn/` (root source archive)

Archived root-level source from zz-Tokn (original binary entry points). These files are preserved for historical reference.

| File | Lines | Description |
|------|-------|-------------|
| `src/main.rs` | 29 | Original binary entry |
| `src/lib.rs` | 11 | Original lib root |
| `src/ingest.rs` | 1,821 | Ingest pipeline |
| `src/orchestrate.rs` | 742 | Orchestration |
| `src/bench.rs` | 698 | Benchmarks |
| `src/utils.rs` | 643 | Utilities |
| `src/pricing.rs` | 610 | Pricing |
| `src/models.rs` | 591 | Models |
| `src/cost.rs` | 528 | Cost tracking |
| `src/cli.rs` | 411 | CLI |
| `src/format.rs` | 351 | Formatting |
| `src/cache.rs` | 346 | Cache |
| `src/analytics.rs` | 137 | Analytics |
| `src/queries.py` | — | Python queries (non-Rust) |
| **Total** | **6,918** | |

## Total Absorbed

- **56 Rust source files** across all three directories
- **~22,992 lines** of Rust code
- **1 Python file** (`queries.py`)

## Structural Changes

- zz-Tokn's `crates/pareto-rs` → phenotype-tooling's `crates/tokn-pareto-rs`
- zz-Tokn's `crates/tokenledger` → phenotype-tooling's `crates/tokn-tokenledger`
- zz-Tokn's root `src/` → phenotype-tooling's `crates/tokn/src/` (archived)
- All `workspace.*` dependency references inlined (no workspace inheritance)
- Path dependency `pareto-rs` updated to `../tokn-pareto-rs`
- Original repository URL preserved in each crate's Cargo.toml

## Git History

The original git history is preserved in the source repository:
https://github.com/KooshaPari/zz-Tokn

This absorption copies the source code snapshot as of 2026-09-14.
