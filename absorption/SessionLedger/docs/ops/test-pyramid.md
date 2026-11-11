# Test pyramid (SSOT)

SessionLedger's quality evidence is organized as a **test pyramid**: many fast
unit tests at the base, fewer integration and end-to-end checks above, and
specialized load, fuzz, and race lanes at the narrow top. This page is the
single source of truth for which artifacts belong to each layer, how CI runs
them, and how to reproduce them locally.

Related: [`flake-tracker.md`](flake-tracker.md) (quarantine policy),
[`concurrency-safety.md`](concurrency-safety.md) (race lane detail),
[`cross-platform-ci.md`](cross-platform-ci.md) (OS matrix for race smoke),
[`runbook.md`](runbook.md) (operator load/chaos commands).

Browser/UI end-to-end is intentionally **out of scope** today — see
[`.qgate.toml`](../../.qgate.toml) (`not_applicable = ["e2e", …]`). In-repo
**e2e** means deterministic pipeline and golden OKF acceptance, not Playwright
or Selenium.

## Pyramid overview

```text
                    ┌─────────────┐
                    │    race     │  race_smoke + race_model · 3 OS × 3 repeats
                    ├─────────────┤
                    │    fuzz     │  cargo-fuzz okf_roundtrip + jsonl_ingest (PR smoke)
                    ├─────────────┤
                    │    load     │  load-smoke SLO · ops-load + ops-chaos-smoke
                    ├─────────────┤
                    │     e2e     │  pipeline + OKF golden/roundtrip (no browser)
                    ├─────────────┤
                    │ integration │  sl-daemon HTTP/worker · workspace contract tests
                    ├─────────────┤
                    │    unit     │  domain/distill/ports inline #[test] + crate modules
                    └─────────────┘
```

| Layer       | Primary artifacts                                                                                                                    | Default CI gate                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Unit        | `src/domain/`, `src/distill/`, `src/ports/`, `src/schema/` inline `#[test]`; `crates/sl-daemon/src/` unit modules                    | `ci.yml` → `build-test` (`cargo test --all-features --locked`)                      |
| Integration | `crates/sl-daemon/tests/integration.rs`, `sse_bridge.rs`, `completions.rs`; workspace `tests/schema_migrate.rs`, `merge_recovery.rs` | `ci.yml` → `build-test`, `schema-migrate`                                           |
| End-to-end  | `crates/sl-daemon/tests/pipeline.rs`; `tests/okf_roundtrip.rs`, `tests/okf_golden.rs`                                                | `ci.yml` → `build-test`                                                             |
| Load        | `scripts/load-smoke.ps1`; `scripts/ops-chaos-smoke.ps1` (burst + recovery)                                                           | `ops-load.yml` (weekly + dispatch); `ops-chaos-smoke.yml` (weekday cron + dispatch) |
| Fuzz        | `fuzz/fuzz_targets/okf_roundtrip.rs`, `jsonl_ingest.rs`; seeded corpus under `fuzz/corpus/`                                          | `ci.yml` → `fuzz-smoke` (10 s per target, nightly toolchain)                        |
| Race        | `tests/race_smoke.rs`, `tests/race_model.rs`                                                                                         | `race-smoke.yml` (ubuntu/windows/macos × 3 repeats)                                 |

Property tests (`tests/properties.rs`) and mutation testing
(`.github/workflows/nightly-mutants.yml`) deepen the **unit** base; they are
documented here as adjacent evidence, not separate pyramid tiers.

## Unit

Fast, hermetic tests colocated with production code.

| Area             | Location                                                             | Notes                                             |
| ---------------- | -------------------------------------------------------------------- | ------------------------------------------------- |
| Domain contracts | [`src/domain/`](../../src/domain/)                                   | dedup, merge, intent, session, bundle, acceptance |
| Distillation     | [`src/distill/`](../../src/distill/)                                 | extractors, compilers, token estimator            |
| Ports / schema   | [`src/ports/`](../../src/ports/), [`src/schema/`](../../src/schema/) | OKF adapters, sqlite memory, migrations           |
| Daemon internals | `crates/sl-daemon/src/`                                              | watcher `scan_once_*`, HTTP helpers               |
| Viewer           | `crates/sl-viewer/`                                                  | theme/export unit tests                           |

Local:

```powershell
cargo test --all-features --locked
cargo test --manifest-path crates/sl-daemon/Cargo.toml --locked
```

Or `make test` / `just test` (workspace + daemon manifest).

## Integration

Cross-module wiring without full pipeline golden lock-in.

| Artifact                                                                               | Role                                                 |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [`crates/sl-daemon/tests/integration.rs`](../../crates/sl-daemon/tests/integration.rs) | Worker pool + channel pipeline against on-disk JSONL |
| [`crates/sl-daemon/tests/sse_bridge.rs`](../../crates/sl-daemon/tests/sse_bridge.rs)   | SSE bridge HTTP surface                              |
| [`crates/sl-daemon/tests/completions.rs`](../../crates/sl-daemon/tests/completions.rs) | Shell completion generation smoke                    |
| [`tests/schema_migrate.rs`](../../tests/schema_migrate.rs)                             | Durable schema migration scaffold                    |
| [`tests/merge_recovery.rs`](../../tests/merge_recovery.rs)                             | Merge error recovery contract                        |

`ci.yml` → `schema-migrate` additionally runs `cargo test --features sqlite` for
the workspace and `sl-daemon` sqlite memory wiring.

## End-to-end

Deterministic acceptance of ingest → compile → export. No OS event timing, no
browser automation.

| Artifact                                                                         | Role                                                         |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [`crates/sl-daemon/tests/pipeline.rs`](../../crates/sl-daemon/tests/pipeline.rs) | `scan_once` sweep → bounded channel → ETL; FR-001 acceptance |
| [`tests/okf_roundtrip.rs`](../../tests/okf_roundtrip.rs)                         | Workspace OKF parse/serialize smoke                          |
| [`tests/okf_golden.rs`](../../tests/okf_golden.rs)                               | Five full-document OKF goldens under `tests/fixtures/okf/`   |

Visual golden harness (`tests/visual/`) is manual/Playwright acceptance for the
viewer chrome — tracked separately from this pyramid's **e2e** tier.

Update OKF goldens only with intent:

```powershell
$env:UPDATE_OKF_GOLDENS = "1"
cargo test --test okf_golden --locked
```

## Load

Concurrent HTTP probes against a running `sl-daemon` with success-rate and p95
SLOs.

| Artifact                                                                                         | Role                                                                                                                        |
| ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| [`scripts/load-smoke.ps1`](../../scripts/load-smoke.ps1)                                         | Headless burst across probe routes (`/healthz`, `/readyz`, `/api/metrics`, `/metrics`) or macro routes (`-RouteTier macro`) |
| [`.github/workflows/load-macro-gate-hard.yml`](../../.github/workflows/load-macro-gate-hard.yml) | Blocking PR macro-tier load smoke (C08 L73)                                                                                 |
| [`scripts/load-macro-gate-check.ps1`](../../scripts/load-macro-gate-check.ps1)                   | Hermetic SelfCheck for macro gate docs + workflow anchors                                                                   |
| [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)                         | Weekly + `workflow_dispatch`; builds daemon, waits for `/readyz`, runs probe-tier load smoke                                |
| [`scripts/ops-chaos-smoke.ps1`](../../scripts/ops-chaos-smoke.ps1)                               | Readiness fault, metrics shape, mini load, process-kill recovery                                                            |
| [`.github/workflows/ops-chaos-smoke.yml`](../../.github/workflows/ops-chaos-smoke.yml)           | Weekday cron + dispatch ops/chaos smoke                                                                                     |

Local (daemon must be listening):

```powershell
pwsh ./scripts/load-smoke.ps1 -BaseUrl http://127.0.0.1:8080
```

SLO defaults align with [`perf-baseline.json`](perf-baseline.json)
(`latency.http_load_smoke.max_p95_ms` = **500**).

## Fuzz

Structure-aware fuzzing via `cargo-fuzz` (nightly + ASAN on Linux CI).

| Target                                                                           | Corpus seed                  | Exercises                        |
| -------------------------------------------------------------------------------- | ---------------------------- | -------------------------------- |
| [`fuzz/fuzz_targets/okf_roundtrip.rs`](../../fuzz/fuzz_targets/okf_roundtrip.rs) | `fuzz/corpus/okf_roundtrip/` | OKF parse + roundtrip invariants |
| [`fuzz/fuzz_targets/jsonl_ingest.rs`](../../fuzz/fuzz_targets/jsonl_ingest.rs)   | `fuzz/corpus/jsonl_ingest/`  | JSONL ingest parse paths         |

PR smoke: `ci.yml` → `fuzz-smoke` (10 seconds per target). Sustained soft
cadence (120 s / target, crash artifact triage): [`fuzz-cadence.md`](fuzz-cadence.md)

- `.github/workflows/fuzz-cadence.yml` (`continue-on-error`; skipped on PR so
  default CI stays fast). No blocking sustained fuzz gate on every merge.

Local (nightly toolchain + `cargo-fuzz` installed):

```powershell
cargo +nightly fuzz run okf_roundtrip -- -max_total_time=30
cargo +nightly fuzz run jsonl_ingest -- -max_total_time=30
```

## Race

Concurrency determinism without sleeps or OS watcher timing.

| Artifact                                                                     | Role                                                                                           |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [`tests/race_smoke.rs`](../../tests/race_smoke.rs)                           | Threaded merge + OKF determinism across shuffled inputs                                        |
| [`tests/race_model.rs`](../../tests/race_model.rs)                           | Bounded `sync_channel` + cancel flag model (loom-lite)                                         |
| [`.github/workflows/race-smoke.yml`](../../.github/workflows/race-smoke.yml) | Both tests, `ubuntu-latest` / `windows-latest` / `macos-latest`, 3 repeats, `--test-threads=1` |

Soft Miri coverage for `race_model` only: `.github/workflows/miri-smoke.yml`
(nightly, `continue-on-error`). Operator detail: [`concurrency-safety.md`](concurrency-safety.md).

Local:

```powershell
cargo test --test race_smoke --test race_model --locked -- --test-threads=1
```

## Done gates

| Gate                   | Status   | Command                                     |
| ---------------------- | -------- | ------------------------------------------- |
| Test pyramid SelfCheck | **done** | `scripts/test-pyramid-check.ps1 -SelfCheck` |

## Machine verification (SelfCheck)

Hermetic path + doc anchor check (no `cargo test`, no daemon, no network):

```powershell
pwsh ./scripts/test-pyramid-check.ps1 -SelfCheck
```

`-SelfCheck` asserts this page documents all six pyramid layers, lists the key
artifact paths/workflows above, and that those paths still exist in-tree.
`tests/test_pyramid.rs` wraps the same command for `cargo test` proof.
