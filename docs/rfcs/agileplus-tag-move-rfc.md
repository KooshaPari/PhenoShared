# RFC: AgilePlus tag-move (v0.13 task 72)

**Status:** PROPOSED
**Author:** forge (pheno-harness) <forge@phenotype.local>
**Date:** 2026-08-11

## Goal

Rehome the AgilePlus adapter from `beads/agileplus_adapter/` (within
pheno-harness) into a dedicated `agileplus-org/agileplus-python` repo
once ≥2 pheno-* projects consume AgilePlus as a shared work-tracking
backend.

## Current state

AgilePlus client lives in:
- `beads/agileplus_adapter/agileplus_adapter.py` — `AgilePlusBeadStore`
  (`append`, `query`, `dedup_check`, `stats`, `health`, `bulk_append`).
- `beads/agileplus_adapter/__init__.py` — re-exports.
- `tests/test_agileplus_adapter.py` + `tests/test_agileplus_adapter_bulk.py`
  (56 + 9 = 65 hermetic tests pass).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| AP-1 | Extract when consumer count ≥ 2 OR ≥ 1 external (non-pheno) consumer | Premature extraction is YAGNI |
| AP-2 | Tag `v0.13.0-agileplus-pre-split` at current `main` tip | One canonical pre-extract snapshot |
| AP-3 | Preserve `BeadStoreAdapter` Protocol in pheno-harness | Cross-repo vocabulary |
| AP-4 | Move CLI bits first, then HTTP bits | CLI is pure stdlib, less risky |
| AP-5 | Wheel name `agileplus-python` | Same as Tracera |
| AP-6 | Pin to agileplus REST `v1` (current); no v2 plans in v0.13 | Avoid churn |

## Migration steps

1. Confirm v0.13.0 ships cleanly.
2. Create `agileplus-org/agileplus-python` repo (admin task).
3. Tag `v0.13.0-agileplus-pre-split` at current `main`.
4. Mirror `beads/agileplus_adapter/agileplus_adapter.py` →
   `agileplus-org/agileplus-python/src/agileplus/client.py`.
5. Add a thin stub at `beads/agileplus_adapter/agileplus_adapter.py`
   that re-exports from the new package (deprecation shim).
6. Re-tag at `v0.13.0-agileplus-post-split`.
7. Tag `v0.13-pheno-harness-agileplus-extracted`.

## Open questions

- Q1: Is the deprecation shim necessary, or do we force-cut
  consumers? → Force-cut; only 2 consumers in pheno-harness.
- Q2: Does the wheel need entry points (CLI scripts)? → No;
  consumers call `BeadStoreAdapter.append()` from their own CLIs.

Refs: v0.13-task-72, RFC-AGILEPLUS-EXTRACT.
