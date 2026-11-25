# RFC: Tracera tag-move (v0.13 task 71)

**Status:** PROPOSED
**Author:** forge (pheno-harness) <forge@phenotype.local>
**Date:** 2026-08-11

## Goal

Rehome the Tracera trace-repository code from `phenotype-registry`
into `tracera-org/tracera` once registry consumer traffic exceeds 1k
QPS sustained or once we have ≥3 separate on-call rotations using
Tracera. Until then, Tracera code lives in pheno-harness (registry
workspace) and consumes the v0.12 + v0.13 dual-write bridge.

## Current state

Tracera is implemented in:
- `pheno/trace_store/tracera.py` — `TraceraAdapter` HTTP client
- `traces/tracera_bridge.py` — dual-write sample-rate + cohort
- `traces/metrics.py` — `BridgeMetrics` + alerting ladder
- `pheno/trace_store/protocols.py` — `TraceEvent` + `TraceStoreAdapter`
- `traces/__init__.py` — bridge module entry point

Adapters (deployable artifacts):
- `bench/results/tracera_staging_integration_test.json` — stage 1
  evidence (12.4s, 8 scenarios all PASS).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| TRC-1 | Tag at `main` tip once v0.13.0 ships | One canonical release per cycle |
| TRC-2 | Bundle `tracera-python` wheel on `pypi.org/pheno` | Hermetic install for CI + downstream |
| TRC-3 | Move `pheno/trace_store/tracera.py` first | Smallest blast radius; pure HTTP client |
| TRC-4 | Move `traces/tracera_bridge.py` last (depends on adapter + protocol) | Dependency order |
| TRC-5 | Keep `pheno/trace_store/protocols.py` in pheno-harness for now | Cross-repo vocabulary still evolving |

## Migration steps

1. Confirm v0.13.0 ships cleanly (`bash scripts/forge_status.sh`,
   `bash scripts/cockpit_migrator.py --verify`).
2. Create `tracera-org/tracera-python` repo (admin task).
3. Tag `v0.13.0-tracera-pre-split` at current `main`.
4. Mirror `pheno/trace_store/tracera.py` →
   `tracera-org/tracera-python/src/tracera/client.py`.
5. Update imports in `traces/tracera_bridge.py` to consume the new
   package via `[tool.uv] dependencies = ["tracera-python>=0.1"]`.
6. Re-tag at `v0.13.0-tracera-post-split`.
7. Tag `v0.13-pheno-harness-tracera-extracted`.

## Open questions

- Q1: Does Tracera need a v0.13-era consumer wider than pheno-harness?
  → No, scope-creep beyond v0.13.1.
- Q2: Is pypi wheel publishing in scope? → No, defer to v0.14.

Refs: v0.13-task-71, RFC-TRACERA-EXTRACT.
