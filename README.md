# Phenotype Forge

> CLI Task Runner and Build Orchestrator — Scaffold Only

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/phenoForge/total)](https://github.com/KooshaPari/phenoForge/releases)

> **Project status (2026-09-08):** This repository is a **scaffold-only documentation snapshot**.
> The Rust binary in this checkout (`phenotype-forge`, ~12 lines of `clap`-based `main.rs`)
> is a placeholder. It accepts a `--watch` flag and a positional `task` name and prints a
> single line. It does **not** execute tasks, does **not** resolve dependencies, does
> **not** watch files, does **not** load plugins, does **not** cache results, and does
> **not** talk to remote workers.
>
> The feature list, architecture diagram, and quick-start code samples below are
> **historical aspirational documentation**. They describe what a future implementation
> would look like, not what this checkout delivers today. See `CHANGELOG.md` for the
> `0.0.0` (2026-09-08) audit closure entry and `FUNCTIONAL_REQUIREMENTS.md` for the
> per-requirement status column.
>
> Historical note: the project was archived as a sibling product — see `ARCHIVED.md` for
> the migration record to `tools/forge/`. This checkout is preserved for provenance.

## What this checkout actually contains

- `Cargo.toml` — Rust 2021 package `phenotype-forge` v0.1.0 with deps on `clap`, `tokio`,
  `serde`, `notify`, `toml`, `thiserror`, `tracing`. No crate is actually used at runtime.
- `src/lib.rs` — empty `pub mod core {}` placeholder; doc-tests load the README.
- `src/main.rs` — 12-line clap CLI that prints `Running task: <name>` (and
  `Watching for changes...` if `--watch` is passed). The `--watch` flag is a no-op.
- `tests/integration.rs` — negative-oracle tests that lock the truthful scaffold:
  the binary's behavior matches the documented scaffold-only state.
- `docs/`, `SPEC.md`, `SOTA_RESEARCH.md`, `PRD.md` — historical design documents
  retained for provenance. They overstate implementation status and are flagged
  for future revision.

## Feature matrix (truthful status as of 2026-09-08)

| Feature | Status | Where in code |
|---------|--------|---------------|
| Parallel execution (worker pool) | **Not implemented** | — |
| Dependency graph / topological sort | **Not implemented** | — |
| Cycle detection | **Not implemented** | — |
| Hot reload / file watching | **Not implemented** (flag exists, no-op) | `src/main.rs:9` |
| Plugin system (WASM or otherwise) | **Not implemented** | — |
| Incremental builds | **Not implemented** | — |
| Caching | **Not implemented** | — |
| Remote execution | **Not implemented** | — |
| Profiling | **Not implemented** | — |
| CLI: `forge run <task>` | **Not implemented** (CLI accepts positional `task` only) | `src/main.rs:8` |
| CLI: `forge list` | **Not implemented** | — |
| CLI: `forge graph` | **Not implemented** | — |
| CLI: `forge check` | **Not implemented** | — |
| CLI: `forge --watch` | **Stub only** (flag accepted, prints line, does nothing) | `src/main.rs:9` |

> **Stable** / **Beta** badges from the previous README have been removed. No feature
> in this checkout warrants a stability claim.

## Running the placeholder

```bash
# Build
cargo build

# Run with default task name ("test" in the placeholder)
cargo run

# Run with explicit task name
cargo run -- hello

# --watch is accepted but does nothing
cargo run -- --watch hello
```

Sample output:

```text
Running task: hello
```

With `--watch`:

```text
Running task: hello
Watching for changes...
```

The "Watching for changes..." line is printed unconditionally when `--watch` is passed.
No filesystem observer is registered; the process exits immediately after printing.

## Tests

```bash
cargo test
```

The integration suite is intentionally a **negative oracle**: it locks in the truthful
scaffold by asserting (a) the binary prints a scaffold-only banner when run, (b) the
README's feature matrix contains no false "Stable" rows, and (c) `Cargo.toml`
dependencies that the scaffold does not exercise are flagged for future removal or
implementation. Future implementations flip these tests from "currently passes" to
"must pass with a positive assertion" — see `tests/integration.rs` for the
`#[ignore]`-d placeholder tests.

## Quality standards (placeholder)

```bash
cargo build          # OK — scaffold compiles
cargo test           # OK — negative-oracle tests pass
cargo clippy         # OK — minimal clippy surface
cargo fmt --check    # OK — Rust 2021 formatting
```

There is no CI gate that proves a feature is implemented. The CI gate proves only that
the scaffold compiles and the negative-oracle tests pass.

## Documentation files in this checkout (provenance)

- `AGENTS.md` — operational rules; the canonical repo's `main` branch is preserved as
  the stable checkout per the Phenotype org rule.
- `ADR.md` — historical ADRs (Rust language choice, tasks-as-traits, Tokio runtime).
  These record **decisions** made when the project was active; they do not imply the
  resulting implementation is present.
- `PRD.md`, `SPEC.md`, `FUNCTIONAL_REQUIREMENTS.md`, `SOTA_RESEARCH.md` — design
  documents retained for provenance. Each functional requirement now carries a
  `Status` column marking its actual implementation state.
- `PLAN.md` — placeholder roadmap (`Q1 2026` through `Q4 2026`); no milestones met.
- `ARCHIVED.md` — migration record to `tools/forge/`. This checkout is preserved as
  a historical scaffold; the binary in this checkout is **not** the canonical
  Phenotype CLI.
- `cliff.toml`, `renovate.json`, `deny.toml`, `pre-commit-config.yaml`,
  `.mergify.yml`, `gitleaks.toml`, `nextest.toml`, `codecov.yml`, `clippy.toml`,
  `.editorconfig` — tooling configuration retained for provenance. Tooling
  effectiveness on this scaffold-only checkout is not asserted.

## Provenance and next steps

This closure was authored on branch `closure/audit-truthful-scaffold-20260908`
from `main` HEAD `2fccbc27591aa797fd9e038a2e422b9a6636b19f` (PR #40
`docs(readme): add AI slop inside + downloads badges`). It is the narrowest
possible repair for the gap between documentation and code: it does not
implement features; it makes the gap visible so future implementers can flip
the negative-oracle tests to positive ones when each feature is actually built.

No migration, absorption, archive, deletion, or force-push was performed.
