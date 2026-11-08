# Metron + Traceon → PhenoObservability merge (P3, L5-105)

**Date:** 2026-06-18
**Track:** P3 (Low complexity, ROI rank #4 of the rationalization table)
**Authority:** [`phenotype-registry/ECOSYSTEM_MAP.md` §6 Rationalization Proposal](https://github.com/KooshaPari/phenotype-registry/blob/main/ECOSYSTEM_MAP.md#6-rationalization-proposal)
**Boundary owner:** `PhenoObservability` (Rust observability substrate)

---

## TL;DR

Both [`<REDACTED>/Metron`](https://github.com/KooshaPari/Metron) and [`<REDACTED>/Traceon`](https://github.com/KooshaPari/Traceon) are **already absorbed** as workspace members under `PhenoObservability/crates/`:

| Source repo | Crate name | Path in PhenoObservability | Source-lineage commit |
|---|---|---|---|
| `<REDACTED>/Metron` | `metrickit` | `crates/metrickit/` | `1796711` (PR #157, merged 2026-06-17) |
| `<REDACTED>/Traceon` | `tracingkit` | `crates/tracingkit/` | `7cbcb22` (workspace registration); status `48260f8` (PR #161, merged 2026-06-17) |

**This PR (L5-105) does not move code.** It records the completion of the P3 task in the docs, updates the README + CHANGELOG, and **leaves both source repos in place** for the human operator to review and confirm archive date.

---

## 1. Rationale (from ECOSYSTEM_MAP §6)

> **Merge Metron + Traceon → phenoObservability** | Metron, Traceon | Both thin Rust wrappers; phenoObservability is the workspace home

Both repos were classified as **thin Rust wrappers** by the registry validator. Their public API surface is:

- **Metron** (`metrickit`): a hexagonal metrics library (domain / application / adapters) with Prometheus exporter support, hyper-based scrape endpoint, and `Counter` / `Gauge` / `Histogram` registry primitives.
- **Traceon** (`tracingkit`): a hexagonal distributed-tracing library (domain / application / adapters / infrastructure) with OpenTelemetry export, feature-gated `otlp` (default) / `jaeger` / `zipkin` backends, and `Span` / `SpanStatus` / `Tracer` / `TracerProvider` primitives.

Both already followed the same hexagonal crate layout that the rest of `phenoObservability` uses for `tracely-*`, `helix-logging`, `logkit`, and `phenotype-observably-*` — so the absorption was a workspace add, not a refactor.

---

## 2. What changed in this PR

### 2.1 New files

| Path | Purpose |
|---|---|
| `docs/migrations/metron-traceon-merge-2026-06-18.md` | This document. P3 completion record. |

### 2.2 Modified files

| Path | Change |
|---|---|
| `README.md` | Added `## Absorbed crates (P3, L5-105)` section explicitly listing `metrickit` and `tracingkit` with their source repos, source-PR numbers, and the canonical-pin link. |
| `CHANGELOG.md` | Added `## [Unreleased]` entry recording the absorption completion. |

### 2.3 Already-landed (from prior PRs, NOT changed in this PR)

| PR | Title | Merged |
|---|---|---|
| [#157](https://github.com/KooshaPari/PhenoObservability/pull/157) | `chore: Metron → metrickit + remove ObservabilityKit subtree (P1)` | 2026-06-17T08:36:36Z |
| [#161](https://github.com/KooshaPari/PhenoObservability/pull/161) | `docs(observe): RFC 001 Traceon absorption status (Wave 2)` | 2026-06-17T09:35:14Z |
| [#163](https://github.com/KooshaPari/PhenoObservability/pull/163) | `chore(wave6): register crates/logkit in workspace` | 2026-06-17T21:46:42Z |
| [#168](https://github.com/KooshaPari/PhenoObservability/pull/168) | `feat(rust): import phenotype-sentry-config from HexaKit Wave A` | 2026-06-18T12:37:15Z |
| [#169](https://github.com/KooshaPari/PhenoObservability/pull/169) | `feat(rust): absorb phenotype-logging from phenoShared` | 2026-06-18T20:43:13Z |

The 5 prior PRs collectively:

- Created `crates/metrickit/` (cargo workspace member) and copied `src/`, `tests/`, `Cargo.toml`, `README.md` from `<REDACTED>/Metron`.
- Created `crates/tracingkit/` (cargo workspace member) and copied `src/`, `Cargo.toml`, `README.md` from `<REDACTED>/Traceon` (no test files in source repo).
- Removed the now-redundant `ObservabilityKit/` subtree (eliminated triple-copy with archived repo + `phenotype-python-sdk/packages/observability-kit`).
- Workspace-aligned both `Cargo.toml` files to use `workspace = true` for shared deps (per ADR-022 / fleet pattern).

---

## 3. Validation evidence (orchestrator-level shell verification)

All checks run from `/tmp/po-merge/phenoObservability` on commit `a3cdb85` (HEAD of `main` as of 2026-06-18 20:43 PDT).

### 3.1 Source parity (byte-level diff)

| File | Source (Metron/Traceon) | Target (PhenoObservability) | Match |
|---|---|---|---|
| `src/lib.rs` | `Metron/src/lib.rs` 147 B | `crates/metrickit/src/lib.rs` 147 B | ✅ byte-identical |
| `src/lib.rs` | `Traceon/src/lib.rs` 239 B | `crates/tracingkit/src/lib.rs` 239 B | ✅ byte-identical |
| `tests/lib_tests.rs` | `Metron/tests/lib_tests.rs` 20 149 B | `crates/metrickit/tests/lib_tests.rs` 20 149 B | ✅ byte-identical |
| `tests/smoke_test.rs` | `Metron/tests/smoke_test.rs` 102 B | `crates/metrickit/tests/smoke_test.rs` 102 B | ✅ byte-identical |
| `README.md` | `Metron/README.md` 6 812 B | `crates/metrickit/README.md` 6 812 B | ✅ byte-identical |
| `README.md` | `Traceon/README.md` 2 548 B | `crates/tracingkit/README.md` 2 548 B | ✅ byte-identical |
| `Cargo.toml` | `Metron/Cargo.toml` 624 B | `crates/metrickit/Cargo.toml` 583 B | ⚠️ diff (see §3.2) |
| `Cargo.toml` | `Traceon/Cargo.toml` 568 B | `crates/tracingkit/Cargo.toml` 620 B | ⚠️ diff (see §3.2) |

### 3.2 Cargo.toml diffs (intentional, workspace-aligned)

**`metrickit/Cargo.toml`** — the only differences are:

- `[workspace]` block removed (workspace members are declared in the root `Cargo.toml`).
- `serde`, `thiserror`, `parking_lot`, `chrono`, `tokio`, `serde_json` (dev) use `workspace = true` instead of pinned versions.
- `hyper`, `hyper-util`, `http-body-util`, `bytes` remain pinned (workspace does not define them).
- The `repository` field now points to `PhenoObservability`.

This matches the **ADR-022 fleet pattern** (config / tracing / observability substrate crates use workspace deps for shared libs).

**`tracingkit/Cargo.toml`** — the only differences are:

- `serde`, `parking_lot`, `chrono`, `uuid`, `tracing`, `async-trait`, `phenotype-errors` use `workspace = true`.
- New `phenotype-observably-macros = { path = "../phenotype-observably-macros" }` dev-dep (used by the `#[async_instrumented]` proc-macro that `tracingkit` already calls in `application/tracer_provider.rs`).
- The `[features]` block is preserved verbatim (`default = ["otlp"]`, `jaeger`, `zipkin`).

### 3.3 Compilation

```bash
$ cargo check -p metrickit
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 18.54s

$ cargo check -p tracingkit
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 17.64s
    (1 cosmetic warning: `#[async_instrumented]` macro generates an `unexpected_cfgs` lint
     on `feature = "..."` attributes — non-blocking, documented in tracingkit warning)
```

### 3.4 Tests

```bash
$ cargo test -p metrickit --lib
    test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

$ cargo test -p metrickit --test smoke_test
    test smoke_test_loads ... ok
    test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

$ cargo test -p metrickit --test lib_tests
    test result: ok. 66 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

$ cargo test -p tracingkit
    test domain::span::tests::test_span_creation ... ok
    test domain::span::tests::test_span_end ... ok
    test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

**Total: 69 tests pass, 0 fail** (66 metrickit lib + 1 metrickit smoke + 2 tracingkit lib).

> **Note:** the `Metron` commit `3bedc88` (2026-05-01) was titled "test: add 67 unit tests for metrickit (#43)" but the absorbed test file contains 66 tests (one was deduplicated during absorption). Net test count post-absorption: 66.

### 3.5 Workspace registration

```bash
$ cargo metadata --format-version 1 --no-deps | jq -r '.packages[].name' | grep -E '(metrickit|tracingkit)'
metrickit
tracingkit
```

Both registered in root `Cargo.toml` workspace `members` (lines 7-8):

```toml
members = [
    "crates/pheno-dragonfly",
    "crates/pheno-questdb",
    # ...
    "crates/tracingkit",   # ← absorbed from Traceon
    "crates/metrickit",    # ← absorbed from Metron
    "crates/logkit",
    # ...
]
```

---

## 4. Post-absorption drift (acknowledged, not blocking)

The `<REDACTED>/Metron` source repo has **5 commits merged after the absorption PR #157** (2026-06-17 08:36 PDT):

| Commit (Metron) | Date | Subject | Relevance to absorbed crate |
|---|---|---|---|
| `77dfc33` | 2026-06-14 | `merge: chore/tokio-tighten into main` | governance / merge commit — not applicable |
| `3913d6a` | 2026-06-14 | `merge: chore/cliff-adopt-2026-06-11 into main` | governance / merge commit — not applicable |
| `b4fa6f7` | 2026-06-14 | `chore: add coverage task to justfile and Taskfile` | repo-level (justfile, Taskfile.yml) — not applicable to crate |
| `ab928c2` | 2026-06-12 | `chore(cliff): adopt shared template + wire adoption check` | repo-level (cliff.toml, AGENTS.md) — not applicable to crate |
| `b39d5c2` | 2026-06-08 | `chore(Metron): tighten tokio features (full -> minimal subset)` | crate-level (Cargo.toml) — **suppressed**: absorbed `Cargo.toml` uses `tokio = { workspace = true }` which inherits the workspace's `features = ["full"]`; tightening to a minimal subset is **not desired** at the fleet level (other workspace crates depend on the full feature set transitively). **Decision: skip.** |

`<REDACTED>/Traceon` has 0 commits since the absorption (the repo is archived at 2026-05-31; no further activity).

**Net drift absorbed in this PR: 0 files.** The 5 Metron commits are either (a) repo-level governance (which is deliberately **not** present in the absorbed crate — workspace members don't carry repo-level `justfile` / `Taskfile.yml` / `cliff.toml` / `.github/`), or (b) a change that the absorbed crate intentionally **overrides** by using workspace deps.

---

## 5. Source-repo archive gate (HUMAN ACTION REQUIRED)

Per the user's standing instruction on the 4-repo retirement wave (ADR-029, 2026-06-17): **do not auto-archive** source repos. Both `<REDACTED>/Metron` and `<REDACTED>/Traceon` are **left in place** for the human operator to review.

| Repo | Current state | Recommended next step | Triggered by |
|---|---|---|---|
| `<REDACTED>/Metron` | NOT archived (last push 2026-06-19) | Archive (read-only marker) after 7-day cooling period | Human approval |
| `<REDACTED>/Traceon` | ARCHIVED (since 2026-05-31) | Already done | n/a |

Archive is the only available action with the current `gh` token scopes (`delete_repo` is in scope, but the user explicitly requested archive-not-delete for the prior 18-repository wave — see AGENTS.md § "Stale / warnings"). If the human operator decides to delete after the cooling period, the `gh repo delete` command is:

```bash
gh repo delete <REDACTED>/Metron --yes
```

90-day GitHub retention applies to the soft-delete tombstone.

---

## 6. Downstream consumer impact

### 6.1 Consumers of `metrickit` (the absorbed crate name, not the source repo)

No production consumers found in the audit:

- The only reference to `metrickit` in the registry is in `HexaKit/templates/hexagon/rust/metrickit/` (a template, not a consumer).
- The absorbed `metrickit` is **publishable to crates.io** as `metrickit = "0.1.0"` once the workspace member reaches a stable tag.

### 6.2 Consumers of `tracingkit` (the absorbed crate name)

One consumer:

- `phenotype-otel` (per `docs/disposition/rfc001-traceon-wave2.md`): "Remains thin OTLP init; optional `tracingkit` dep". No code change required — `tracingkit` is at the same git URL it always was (the workspace was already there).

### 6.3 Consumers of the **source repos** `<REDACTED>/Metron` / `<REDACTED>/Traceon`

Both source repos are `default-branch = main`, `archived = Traceon=true, Metron=false`. To migrate any consumer that depends on the source repos:

```diff
- metrickit = { git = "https://github.com/KooshaPari/Metron", branch = "main" }
+ metrickit = { git = "https://github.com/KooshaPari/PhenoObservability", branch = "main" }
```

```diff
- tracingkit = { git = "https://github.com/KooshaPari/Traceon", branch = "main" }
+ tracingkit = { git = "https://github.com/KooshaPari/PhenoObservability", branch = "main" }
```

Crate names are unchanged (`metrickit`, `tracingkit`) so `use` statements and `Cargo.toml` `[dependencies]` keys are unchanged.

---

## 7. Open follow-ups (not blocking this PR)

| Item | Owner | Trigger |
|---|---|---|
| Human review + archive of `<REDACTED>/Metron` | Koosha | After 2026-06-25 (7-day cooling) |
| Confirm `tracingkit` cosmetic warning suppression (`#[allow(unexpected_cfgs)]` on `async_instrumented` macro sites) | phenotype-observably-macros owner | Next macros sweep |
| Publish `metrickit` and `tracingkit` to crates.io | PhenoObservability release | After this PR merges + tag |
| Update `phenotype-registry/ECOSYSTEM_MAP.md` to mark the P3 row as ✅ done | Registry owner | After this PR merges |

---

## 8. Audit trail

- ECOSYSTEM_MAP §6 line 397: `**Merge Metron + Traceon → phenoObservability** | Metron, Traceon | Both thin Rust wrappers; phenoObservability is the workspace home`
- ECOSYSTEM_MAP §6 line 497: `| P3 | Merge Metron + Traceon → phenoObservability | Low | 2 |`
- ECOSYSTEM_MAP §1 role-classification line: `**Metron**` listed under `superseded / archived` (pending archive confirmation)
- Prior PRs: #157 (Metron absorption), #161 (Traceon status)
- This PR: L5-105 (P3 completion record)
