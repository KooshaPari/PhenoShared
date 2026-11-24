# ADR-0012: Unified Artifact Set

## Status

Proposed

## Context

[`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) identifies **triple spec
roots** (`specs/`, `kitty-specs/`, `.planning/`) as the primary agent context fragmentation
anti-pattern. AgilePlus already uses `kitty-specs/`; Spec-Kit uses `specs/`; GSD uses
`.planning/`; OpenSpec uses `openspec/`; BMAD uses `_bmad-output/`.

ADR-0006 absorbed `agileplus-spec-harmonizer` to normalize GSD, OpenSpec, BMAD, and
Spec-Kitty formats into a unified `WorkPackage` shape — but the harmonization track did not
yet mandate a **single canonical tree** for durable artifacts.

Tracera ingests FR catalogs and builds a graph; without a canonical spec root, the same
requirement may appear under incompatible paths and ids.

## Decision

1. **Canonical feature root:** `kitty-specs/<feature-id>/` is the sole authoritative
   per-feature directory for spec, plan, tasks, `wps.yaml`, and linked deltas.
2. **Ingress, not duplication:** External framework artifacts are **imported or linked**:
   - OpenSpec: `openspec/changes/<id>/` linked from `kitty-specs/<id>/openspec-ref.yaml`
   - Spec-Kit: `constitution.md` at repo root; per-feature content merged via harmonizer
   - GSD: `.planning/STATE.md` and phase files referenced by id; REQ-XX mapped to FR-xxx
   - BMAD: `_bmad-output/` shards referenced; epics map to feature ids
3. **Harmonizer is mandatory ingress** for non-kitty formats (`agileplus-spec-harmonizer`,
   ADR-0006). No parallel hand-maintained `WorkPackage` YAML outside `wps.yaml`.
4. **FR/NFR authority:** `docs/requirements/*-frnfr.md` plus in-spec acceptance criteria;
   spine `RequirementId` is the only runtime id.
5. **Derivatives are explicit:** `traces/*.json` intent graphs and worklogs are labeled
   machine derivatives of markdown sources (ADR-0008). They are evidence inputs, not spec
   replacements.
6. **Tracera graph nodes** reference canonical paths and ids from this tree; ingest
   rejects artifacts whose `source_path` is outside the canonical set unless tagged
   `legacy-import`.

## Consequences

- Agents always start from `kitty-specs/` — predictable context window.
- Migration work for repos with `specs/` or `.planning/` as primary (scripted harmonize pass).
- OpenSpec brownfield deltas remain valuable; they nest under links, not parallel roots.
- Constitution and ADRs stay at repo governance level (`docs/adr/`, root `CONSTITUTION.md`).

## References

- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §3
- ADR-0006: spec harmonizer absorption
- ADR-0008: intent graph ontology
- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.3 anti-patterns
