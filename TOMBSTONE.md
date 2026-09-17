# TOMBSTONE: DataKit (`datakit` Rust crate)

This file records the deprecation of this repository. It exists because
`README.md` and prior commit history referenced it, and the reference was
dangling until now.

## Status

| Field | Value |
|---|---|
| Decision | **Deprecated. Archive recommended.** |
| Recorded | 2026-09-17 |
| Crate | `datakit` v0.1.0, edition 2021, MIT |
| Successor | `phenotype-python-sdk/packages/data-kit` |
| Successor verification | **Verified absent (2026-09-17).** `gh api repos/KooshaPari/phenotype-python-sdk` and `repos/phenotype-python-sdk` both return HTTP 404, and `gh search repos phenotype-python-sdk` returns nothing. The successor path is unverified and unreachable. |
| This repo on GitHub | **Absent.** `git remote -v` points at `https://github.com/KooshaPari/DataKit.git`, but `gh api repos/KooshaPari/DataKit` returns 404, `git ls-remote origin` reports "Repository not found", and DataKit is not among the 46 repos returned by `gh repo list KooshaPari`. The authenticated account is `KooshaPari`. |

Both the deprecation target and this repository's own remote are currently
unreachable on GitHub. Anyone arriving here through git history or a stale link
should treat the supersession claim as unconfirmed until a reachable successor
is identified.

## Why it was deprecated

The repository was created as a planning placeholder for a unified data
transformation and ETL framework. The framework was never built here. What
exists is a two-type sketch, and the direction moved to the Python SDK
monorepo.

## What was actually built here

The crate compiles, lints, and passes all tests. It is small but not empty.

| Artifact | State |
|---|---|
| `DataStream<T>` | Implemented, `src/lib.rs` |
| `Pipeline<T, U>` with `new` and `run` | Implemented, `src/lib.rs` |
| Unit tests | 4, passing |
| Integration tests | 5, passing, `tests/pipeline_test.rs` |
| Doc test | 1, passing |
| Criterion benchmarks | Scaffolded, `benches/criterion_bench.rs` |
| `cargo-fuzz` target | Scaffolded, `fuzz/fuzz_target.rs` |
| Streaming, connectors, plugins, I/O, error handling | Never implemented |

Verified 2026-09-17 with `cargo test --all`: 4 + 5 + 1 tests pass, 0 fail.

## Why this looked more complete than it was

Repository scaffolding was added ahead of implementation. This includes CI
workflows, scorecard configs, Docker files, community docs, and empty
integration/e2e test placeholders. Those files are real but they do not
represent implemented functionality. `audit_scorecard.json` remains
unpopulated (`overall_score: 0`, empty pillar scores).

## Migration guidance

If you reached this repository looking for data transformation tooling:

1. Use the successor package (`phenotype-python-sdk/packages/data-kit`) for
   new work.
2. Do not add features here. There is no active development path.
3. The only reusable idea in this crate is the `DataStream<T>` plus
   `Pipeline<T, U>` sketch, documented faithfully in
   [docs/API_REFERENCE.md](docs/API_REFERENCE.md). It has no production
   semantics: the transform is infallible, execution is batch-only, and there
   is no I/O.

## What this repository is still good for

- A minimal worked example of a generic, boxed-closure transform pipeline in
  Rust.
- A reference for the repository scaffolding conventions used across the
  Phenotype org.

## Discrepancies recorded at deprecation time

- `CLAUDE.md` claims edition 2024 and license MIT; `Cargo.toml` is edition 2021
  with no `license` field, though `LICENSE` is MIT.
- `CONTRIBUTING.md` cites `anyhow`, `thiserror`, and `pretty_assertions`, which
  are not dependencies.
- `tests/integration/` and `tests/e2e/` contain one-line README placeholders
  with no tests.
- MSRV is not pinned.
