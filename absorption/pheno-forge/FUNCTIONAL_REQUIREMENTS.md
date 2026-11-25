# Functional Requirements — phenotype-forge

> **Status key** — every `SHALL` is annotated with its actual implementation state
> in this checkout as of 2026-09-08. The status column is the source of truth;
> the `SHALL` text is the original aspirational requirement.

| Status | Meaning |
|--------|---------|
| **Not implemented** | No code path delivers this requirement today. |
| **Stub only** | A CLI flag or symbol exists but does not perform the requirement. |
| **Scaffold only** | Required infrastructure is partially in place (e.g., a `clap` arg or a `Cargo.toml` dep) but the behavior is not wired up. |
| **Implemented** | The requirement is delivered by a unit or integration test. |

> Any `SHALL` that does **not** carry an explicit `Status: Implemented` row is
> not delivered by this checkout. See `tests/integration.rs` for the
> negative-oracle tests that lock these gaps.

## FR-TASK — Task Definition

| ID | Requirement | Status | Where (if any) |
|----|-------------|--------|----------------|
| FR-TASK-001 | The system SHALL allow tasks to be defined as Rust structs implementing a Task trait. | Not implemented | — |
| FR-TASK-002 | The system SHALL support declaring task dependencies as a directed acyclic graph. | Not implemented | — |
| FR-TASK-003 | The system SHALL validate the task graph for cycles at startup and exit with an error if found. | Not implemented | — |
| FR-TASK-004 | The system SHALL support environment variable injection per task. | Not implemented | — |
| FR-TASK-005 | The system SHALL support secret resolution from environment or vault per task. | Not implemented | — |

## FR-EXEC — Execution

| ID | Requirement | Status | Where (if any) |
|----|-------------|--------|----------------|
| FR-EXEC-001 | The system SHALL execute tasks in topological dependency order. | Not implemented | — |
| FR-EXEC-002 | The system SHALL execute independent tasks in parallel up to a configurable concurrency limit. | Not implemented | — |
| FR-EXEC-003 | The system SHALL stream stdout/stderr to the terminal with task-labeled prefixes. | Not implemented | — |
| FR-EXEC-004 | The system SHALL fail fast on first error by default. | Not implemented | — |
| FR-EXEC-005 | The system SHALL support --continue-on-error to execute remaining independent tasks after a failure. | Not implemented | — |

## FR-CLI — CLI

| ID | Requirement | Status | Where (if any) |
|----|-------------|--------|----------------|
| FR-CLI-001 | The system SHALL provide a `forge run <task>` command. | Not implemented | CLI accepts a positional `task` argument only (`src/main.rs:8`); there is no `forge run` subcommand. |
| FR-CLI-002 | The system SHALL provide a `forge list` command showing all tasks with descriptions. | Not implemented | — |
| FR-CLI-003 | The system SHALL provide a `forge graph` command rendering the task DAG. | Not implemented | — |
| FR-CLI-004 | The system SHALL provide a `forge check` command validating the task graph. | Not implemented | — |

## FR-DIST — Distribution

| ID | Requirement | Status | Where (if any) |
|----|-------------|--------|----------------|
| FR-DIST-001 | The system SHALL ship as a statically linked binary for Linux, macOS, and Windows. | Scaffold only | `Cargo.toml` declares a `[[bin]]` named `phenotype-forge`; no release pipeline or cross-compile artifact is present in this checkout. |
| FR-DIST-002 | The system SHALL read project configuration from `.forge/config.toml`. | Not implemented | The `toml` crate is in `Cargo.toml` but no config-loading code exists. |

## FR-OBS — Observability (informational; not previously in this document)

The original document did not enumerate observability requirements. They are added here so that the negative-oracle suite has a place to record the truthful scaffold status for them.

| ID | Requirement | Status | Where (if any) |
|----|-------------|--------|----------------|
| FR-OBS-001 | The system SHALL emit a scaffold-only banner on stdout when the binary is invoked. | Implemented | `src/main.rs:18` prints `Running task: <name>` (the banner is the literal "Running task:" line; see `tests/integration.rs::test_binary_prints_running_task_banner`). |
| FR-OBS-002 | The system SHALL accept a `--watch` flag without crashing. | Implemented | `src/main.rs:7` clap arg parses successfully; the flag is a documented no-op. |
| FR-OBS-003 | The system SHALL register a filesystem observer when `--watch` is passed. | Not implemented | The `notify` crate is in `Cargo.toml` but `main.rs` does not import or call it. |

## Provenance

This file was extended with the `Status` and `Where` columns and the
FR-OBS section in commit `closure/audit-truthful-scaffold-20260908`
(branched from `main` HEAD `2fccbc27591aa797fd9e038a2e422b9a6636b19f`).
No requirement text was deleted; only columns were added and statuses were
recorded from direct code inspection.
