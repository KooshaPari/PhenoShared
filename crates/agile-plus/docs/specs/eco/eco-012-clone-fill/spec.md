---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05
slug: eco-012-clone-fill
spec_id: eco-012
state: PENDING
status: active
superseded_by: null
title: Clone Fill
type: operational
---
# eco-012: Clone Fill

## Problem

The <REDACTED> canonical-fleet baseline tracks all non-archived public/private repos under the <REDACTED> GitHub org as local clones under `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`. The worklog snapshot `worklogs/oldest-<REDACTED>-20260605.json` enumerates 9 oldest non-archived repos that have no local clone present:

- kmobile
- KWatch
- phenotype-postfx
- Eventra
- phenotype-water
- phenotype-terrain
- KaskMan
- Apisync
- Pyron

Without local clones, agent sweeps, governance audits, and cross-project reuse scans silently skip these projects, breaking the canonical-fleet baseline and the Phenotype Org Cross-Project Reuse Protocol.

## Target Users

- **Phenotype agents** — need a complete local fleet to perform cross-repo audits, governance checks, and reuse discovery.
- **Repo stewards** — need every <REDACTED> repo locally available for branch discipline, worktree management, and integration passes.

## Functional Requirements

FR-1. For each of the 9 repos listed above, run `gh repo clone <name> <local-path> -- --depth 50` into `/Users/<REDACTED>/CodeProjects/Phenotype/repos/<name>`.

FR-2. Use `--depth 50` to bound disk usage; full history is not required for fleet-baseline parity.

FR-3. If a target directory already exists and is a valid clone, skip with status `present`.

FR-4. If `gh repo clone` fails due to access (private repo, missing token scope, 404, archive), record status `skipped: <reason>`.

FR-5. Persist a per-repo outcome table (name, status, path, reason-if-skipped) as `kitty-specs/eco-012-clone-fill/clone-results.md`.

## Acceptance Criteria

AC-1. 9 of 9 repos have a documented outcome in `clone-results.md`.

AC-2. All `cloned` repos exist on disk at `/Users/<REDACTED>/CodeProjects/Phenotype/repos/<name>` and report a valid HEAD.

AC-3. All `skipped` repos include a concrete `reason` (e.g. `skipped: private — no token scope`, `skipped: 404 not found`, `skipped: archived`).

AC-4. No silent failures: every repo yields exactly one of `cloned | present | skipped`.

## Constraints

- **Disk floor**: respect the disk-budget policy (`repos/docs/governance/target_budget_policy.md`); abort and report if free space drops below 20 GB during the run.
- **No git, no worktrees**: this spec performs only `gh repo clone` and writes a results file. It does not initialize worktrees or run quality gates.
- **Private/failed repos** are not blockers — they are recorded as `skipped: <reason>` and do not fail the spec.
- **Single-batch execution**: do not parallelize clones (sequential keeps the gh API rate-limit window predictable and disk I/O steady).
