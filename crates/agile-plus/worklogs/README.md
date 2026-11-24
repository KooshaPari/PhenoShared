# Worklogs Index

This directory contains the auditable worklog entries for the AgilePlus repository.

## Layout

- `dag-*.json` — DAG topology entries for each work package, showing dependencies, layers, and unlocks.
- `worklog-*-canonical.json` — Canonical 8-field worklog entries (status, task_id, agent_id, files_changed, commit_sha, verification_result, started_at, completed_at).
- `worklog-*.json` — Legacy/extended worklog entries (being migrated to canonical format).
- `build-triage-*.json` — Build triage reports.
- `autograde-*.json` — CI autograder output reports.
- `worktree-hygiene-*.json` — Stale/dirty worktree audit reports.

## Conventions

- Every entry is UTF-8, no BOM.
- Every entry contains a `generated_at` or `started_at` ISO 8601 timestamp.
- DAG entries reference the spec ID that motivated the work (e.g., `eco-028`, `eco-030`).
- Worklog entries are immutable once completed; corrections are appended as new entries.

## Fleet Readiness

This repo is part of the Phenotype ecosystem. The worklog coverage spec (`eco-010`) requires every active repo to maintain a `worklogs/` directory with at least one dated entry. AgilePlus satisfies this with continuous worklog entries for each DAG work package.
