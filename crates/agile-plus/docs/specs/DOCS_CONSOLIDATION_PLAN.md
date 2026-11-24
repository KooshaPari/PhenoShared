---
title: AgilePlus Docs Consolidation Plan
slug: agileplus-docs-consolidation
spec_id: plan-docs-consolidation
state: DRAFT
created: 2026-06-24
type: governance
supersedes: null
related_adrs:
  - docs/adr/0003-docs-tree-consolidation.md
  - docs/adr/0004-json-to-frontmatter-decorators.md
---

# AgilePlus Docs Consolidation Plan

> **Scope:** Plan only. This document inventories the current split across `kitty-specs/`, `specs/`, `traces/`, and `docs/`, defines the single canonical `docs/` tree, and sequences the `meta.json` / `traces/*.json` → YAML frontmatter + `#[trace_fr(...)]` decorator migration. **No file moves are executed by this spec.**

## Problem Statement

AgilePlus governance artifacts live in four parallel roots. Agents, auditors, and tooling must search multiple trees for the same artifact type. Path drift breaks traceability validators and duplicates metadata across JSON sidecars and Markdown frontmatter.

ADR-0003 and ADR-0004 accepted the target layout and metadata model, and a partial migration has already landed (`docs/specs/eco/`, redirect README stubs, archived JSON). The repo is in a **hybrid state**: canonical content coexists with legacy copies, stale path references, and tooling that still targets `kitty-specs/`.

## Goals

1. One canonical `docs/` spine for specs, ADRs, journeys, and requirements.
2. Retire hand-maintained `meta.json` and `traces/FR-*.json` in favor of YAML frontmatter.
3. Derive code↔FR coverage from `#[trace_fr(...)]` decorators (static analysis), not parallel JSON trees.
4. Preserve git history via `git mv` and archive copies under `docs/_archive/` (execution phase).
5. Leave redirect stubs at legacy top-level paths until downstream references are updated.

## Non-Goals (this plan)

- Executing moves, deletes, or archive writes.
- Implementing the `#[trace_fr]` proc-macro (follow-up crate work).
- Consolidating unrelated `docs/` subtrees (`architecture/`, `workflow/`, VitePress site, etc.) beyond path references they hold to specs/journeys.

---

## Current Inventory (origin/main baseline)

Snapshot counts and locations as of 2026-06-24.

### Top-level legacy roots

| Root | Status | Contents (approx.) |
|------|--------|-------------------|
| `kitty-specs/` | **Active + legacy** | 49 top-level feature dirs; ~50 `spec.md`; 29 `meta.json`; numbered specs (`001-*`…`022-*`), eco specs (`eco-001`…`eco-012`), fleet audits, phenosdk waves, archive subtree. README is a redirect stub. |
| `specs/` | **Mostly relocated** | `README.md` redirect stub; `issue-spec-discoverability.md` (chore doc referencing `kitty-specs`). |
| `traces/` | **Relocated** | `README.md` redirect stub only at repo root. |
| `docs/` | **Partially canonical** | See subtree inventory below. |

### `docs/` subtree (canonical targets)

| Path | Status | Contents (approx.) |
|------|--------|-------------------|
| `docs/specs/eco/` | **Canonical (partial)** | 36 eco spec dirs (`eco-001`…`eco-034`, plus `align-version-drift-2026-06-08`, `021-polyrepo-ecosystem-stabilization`). Most have `spec.md` + `plan.md` + `tasks.md`; frontmatter merged for migrated eco specs. |
| `docs/specs/crates/` | **Canonical** | 6 crate FR specs: `001-agileplus-core`, `002-agileplus-dashboard`, `011-agileplus-import`, `012-agileplus-telemetry`, `013-agileplus-grpc`, `014-agileplus-github`. |
| `docs/specs/00N-*` | **Duplicated with kitty-specs** | 9 numbered platform specs at `docs/specs/` root (`001-spec-driven-development-engine` … `007-thegent-completion`). Mirror content still under `kitty-specs/`. |
| `docs/adr/` | **Canonical** | ADR-0001…0006, task-runner/registry ADRs, `ARCHITECTURE.md`. Includes ADR-0003 (tree) and ADR-0004 (frontmatter/decorators). |
| `docs/journeys/` | **Canonical** | `FR-024-1.md`…`FR-024-8.md` with trace frontmatter; `dashboard-health-check.md`, `domain-models.md`, `assets/`. |
| `docs/requirements/` | **Canonical** | Repo-level `*-frnfr.md` files; `traceability/` (schema/matrix docs). |
| `docs/_archive/meta-json/` | **Archive** | 33 `meta.json` copies from completed eco migrations. |
| `docs/_archive/traces-json/` | **Archive** | 8 `FR-024-*.json` trace sidecars. |

### Duplication hotspots

| Artifact | Canonical location | Legacy / duplicate location | Gap |
|----------|-------------------|----------------------------|-----|
| Eco specs (eco-001…012) | `docs/specs/eco/<slug>/` | `kitty-specs/eco-*/` (still has `meta.json`) | Legacy dirs not removed; `meta.json` not archived for all |
| Numbered platform specs | `docs/specs/00N-*/` | `kitty-specs/00N-*/` | Full duplicate trees (~9 specs) |
| Portfolio / phenosdk specs | — | `kitty-specs/portfolio-audit-*`, `phenosdk-*`, etc. | Not yet under `docs/specs/` |
| Spec metadata | `spec.md` YAML frontmatter | `kitty-specs/*/meta.json` (29 remaining) | `governance_index.py` still requires `meta.json` |
| FR trace cross-refs | `docs/journeys/FR-*.md` frontmatter | `docs/_archive/traces-json/FR-*.json` | Journey bodies still reference `kitty-specs/` and `traces/` paths |
| Code coverage | `#[trace_fr(...)]` (planned) | `tests`/`code_modules` in journey frontmatter | No proc-macro or collector yet |

### Tooling still on legacy paths

| Component | Current root | Must retarget |
|-----------|-------------|---------------|
| `tooling/governance_index.py` | `kitty-specs/` | `docs/specs/eco/` (+ index generation at `docs/specs/INDEX-eco.md`) |
| `scripts/phase3-docs-consolidate.py` | reads `kitty-specs/`, `specs/`, `traces/` | idempotent re-run after execution PRs |
| CLI `specify` / `implement` workflow docs | `docs/workflow/specify.md` references `kitty-specs/` | `docs/specs/eco/` |
| `python/src/agileplus_mcp/server.py` | `file://kitty-specs/{slug}/` URIs | `docs/specs/eco/{slug}/` |
| Git adapter / SQLite rebuild (WP06) | scans `kitty-specs/*/meta.json` | frontmatter parse on `docs/specs/**/spec.md` |
| Trace validator (`tooling/trace-validator/`) | hard-coded `AgilePlus/traces/`, `kitty-specs/` strings | `docs/journeys/`, `docs/specs/eco/` |

---

## Target Canonical Tree

Single spine under `docs/` per ADR-0003:

```
docs/
├── adr/                          # Architecture Decision Records (unchanged)
├── journeys/                     # User journeys + FR trace narratives
├── requirements/                 # FR/NFR corpora + traceability schema/matrix
│   └── traceability/
├── specs/
│   ├── eco/<slug>/               # Ecosystem / operational specs
│   │   ├── spec.md               # YAML frontmatter (replaces meta.json)
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   ├── checklists/           # optional
│   │   ├── contracts/            # optional
│   │   ├── research/             # optional
│   │   └── tasks/                # optional WP files
│   ├── crates/<id>-<name>/       # Crate-level FR + BDD specs
│   └── platform/<slug>/          # Numbered platform specs (001-*, 002-*, …)
├── _archive/
│   ├── meta-json/<slug>/meta.json
│   └── traces-json/FR-*.json
└── INDEX-eco.md                  # Generated spec index (replaces kitty-specs/INDEX.md)
```

Legacy top-level stubs (post-migration):

```
kitty-specs/README.md   → redirect to docs/specs/eco/
specs/README.md         → redirect to docs/specs/crates/
traces/README.md        → redirect to docs/journeys/
```

---

## Target Mapping Table

### Spec directories

| Source pattern | Target | Slug rule | Notes |
|----------------|--------|-----------|-------|
| `kitty-specs/eco-<NN>-<name>/` | `docs/specs/eco/eco-<NN>-<name>/` | keep slug | Already migrated for eco-001…034; remove legacy copy after link sweep |
| `kitty-specs/<NNN>-<name>/` | `docs/specs/platform/<NNN>-<name>/` | keep numeric prefix | Avoid collision with `docs/specs/eco/`; alternative: keep at `docs/specs/<NNN>-<name>/` if platform subdir is deferred |
| `kitty-specs/<kebab-audit>/` (fleet-audit, portfolio-audit-*, phenosdk-*) | `docs/specs/eco/<kebab-audit>/` or `docs/specs/audits/<kebab-audit>/` | keep dirname | Classify per `type` in meta/frontmatter (`operational` → eco; one-off audits → `audits/`) |
| `kitty-specs/archive/*` | `docs/_archive/specs/<slug>/` | preserve | Retired completions (005-heliosapp, etc.) |
| `specs/issue-spec-discoverability.md` | `docs/specs/chore/issue-spec-discoverability.md` | chore | Update internal path references |
| `specs/*` (future crate FR) | `docs/specs/crates/<id>-<name>/` | id-name | README already points here |

### Trace / journey artifacts

| Source | Target | Notes |
|--------|--------|-------|
| `traces/FR-<id>.json` | Fold into `docs/journeys/FR-<id>.md` frontmatter; archive JSON | 8 files already archived; root `traces/` is stub-only |
| `docs/operations/journeys/*.md` (if any remain) | `docs/journeys/*.md` | `phase3-docs-consolidate.py` handles merge |
| `traces/SCHEMA.md`, `traces/MATRIX.md` | `docs/requirements/traceability/` | Already specified in ADR-0003 |

### Requirements

| Source | Target |
|--------|--------|
| Root / scattered `*-frnfr.md` | `docs/requirements/` (already canonical) |
| `FUNCTIONAL_REQUIREMENTS.md` references | Update anchors to `docs/specs/eco/` and `docs/journeys/` |

### ADRs

| Source | Target |
|--------|--------|
| `docs/adr/` | No move; remains canonical |
| Root `ADR.md` inline ADRs | Cross-link only; no merge required in this phase |

---

## Metadata Migration: `meta.json` → YAML Frontmatter

Per ADR-0004. Execution uses `scripts/phase3-docs-consolidate.py` (`merge_meta_into_spec`).

### Field mapping

| `meta.json` key | `spec.md` frontmatter key | Transform |
|-----------------|---------------------------|-----------|
| `spec_id` | `spec_id` | direct |
| `slug` | `slug` | direct |
| `title` | `title` | direct |
| `status` | `status` + `state` | `state` = uppercase `status` when `state` absent |
| `created_at` | `created` + `created_at` | both for backward compat during transition |
| `completed_at` | `completed_at` | direct |
| `retired_at` | `retired_at` | direct |
| `retirement_reason` | `retirement_reason` | direct |
| `superseded_by` | `superseded_by` | direct |
| `type` | `type` | `operational`, `platform`, etc. |
| `_path` | — | drop (tooling internal) |

### Per-spec execution checklist

1. Read `kitty-specs/<slug>/meta.json`.
2. Merge into `docs/specs/<area>/<slug>/spec.md` frontmatter (create target dir if missing).
3. Move `meta.json` → `docs/_archive/meta-json/<slug>/meta.json`.
4. Remove duplicate spec tree from `kitty-specs/<slug>/` after `git mv` to canonical path (or merge if both exist).
5. Regenerate `docs/specs/INDEX-eco.md` from frontmatter (not JSON).

### Acceptance criteria

- Zero `meta.json` under `kitty-specs/` (except explicit archive copies).
- `governance_index.py` validates `spec.md` + `plan.md` + `tasks.md` frontmatter, not JSON sidecars.
- SQLite/git rebuild reads frontmatter fields previously sourced from `meta.json`.

---

## Trace Migration: `traces/*.json` → Journey Frontmatter + Decorators

Per ADR-0004. Execution uses `fold_trace_into_journey` in `phase3-docs-consolidate.py`.

### JSON → frontmatter field mapping

| `FR-*.json` key | `docs/journeys/FR-*.md` frontmatter |
|---------------|--------------------------------------|
| `fr_id` | `fr_id` |
| `spec_slug` | `spec_slug` |
| `spec_anchor` | `spec_anchor` |
| `docs_pages` | `docs_pages` (list) |
| `tests` | `tests` (list) |
| `code_modules` | `code_modules` (list) |
| `journeys` | `journeys` (list; rewrite paths to `docs/journeys/`) |
| `status` | `status` |
| `last_validated` | `last_validated` |
| `schema_version` | `schema_version` |

### Journey body cleanup (post-fold)

Replace stale narrative references:

- `AgilePlus/traces/FR-*.json` → `docs/journeys/FR-*.md` (frontmatter is source of truth)
- `AgilePlus/kitty-specs/<slug>/spec.md` → `docs/specs/eco/<slug>/spec.md`
- `docs/operations/journeys/` → `docs/journeys/`

### `#[trace_fr(...)]` decorator convention (code layer)

Planned static-analysis source of truth for `tests` and `code_modules` lists. ADR-0004 locks the attribute shape:

```rust
#[trace_fr(spec = "eco-024-traceability", fr = "FR-024-1")]
fn validate_trace_required() { /* ... */ }
```

**Collector (follow-up implementation):**

1. Proc-macro or `syn` attribute parser in `agileplus-trace-validator` (or `xtask traceability`).
2. Scan `crates/**` and `tests/**` for `#[trace_fr(...)]`.
3. Emit **generated** matrix to `target/traceability/matrix.json` and `matrix.md` (not committed).
4. CI compares generated matrix against `docs/journeys/FR-*.md` frontmatter (`tests`, `code_modules`).
5. On mismatch: fail `agileplus validate-trace` (or equivalent).

**Migration order for decorators:**

1. Add attribute crate + collector (no production code changes).
2. Annotate `tooling/trace-validator/` tests first (already listed in FR-024 frontmatter).
3. Expand to `agileplus-governance`, CLI subcmds, MCP server paths cited in journeys.
4. Remove hand-maintained `tests` / `code_modules` from frontmatter once collector is authoritative (optional tightening phase).

---

## Phased Execution Plan

### Phase 0 — Governance lock (this PR)

- [x] Author `docs/specs/DOCS_CONSOLIDATION_PLAN.md` (plan only).
- [ ] Reviewer sign-off before any move PR.

### Phase 1 — Complete eco spec relocation

1. Run `phase3-docs-consolidate.py` in dry-run/report mode (add `--dry-run` flag if not present).
2. `git mv` remaining `kitty-specs/eco-*` → `docs/specs/eco/` where duplicates exist.
3. Merge remaining 29 `meta.json` files; archive to `docs/_archive/meta-json/`.
4. Replace `kitty-specs/` content with README stub only.

### Phase 2 — Platform + audit spec relocation

1. Move `kitty-specs/00N-*` → `docs/specs/platform/00N-*` (or flatten to `docs/specs/00N-*` per reviewer choice).
2. Move `kitty-specs/{portfolio-audit,phenosdk,fleet-audit}*` → `docs/specs/eco/` or `docs/specs/audits/`.
3. Move `kitty-specs/archive/*` → `docs/_archive/specs/`.

### Phase 3 — Specs root + chore docs

1. Move `specs/issue-spec-discoverability.md` → `docs/specs/chore/`.
2. Leave `specs/README.md` redirect stub.

### Phase 4 — Trace path hygiene

1. Confirm `traces/` contains only README stub.
2. Rewrite journey bodies and spec cross-links to canonical paths.
3. Update `docs/requirements/traceability/MATRIX.md` generator inputs.

### Phase 5 — Tooling retarget

| Tool | Change |
|------|--------|
| `tooling/governance_index.py` | `SPEC_ROOT = docs/specs/eco`; parse frontmatter; emit `docs/specs/INDEX-eco.md` |
| `tooling/trace-validator/` | Resolve `docs/journeys/`, `docs/specs/eco/`; drop `traces/*.json` reads |
| CLI git adapter | Scan `docs/specs/**/spec.md` frontmatter |
| MCP server URIs | `file://docs/specs/eco/{slug}/` |
| CI governance workflow | Path filters on `docs/specs/**` not `kitty-specs/**` |
| `docs/workflow/specify.md` | Update examples and created-path templates |

### Phase 6 — Decorator rollout

1. Implement `#[trace_fr]` collector crate.
2. Wire `cargo xtask traceability` (or `agileplus trace matrix`).
3. Add CI gate: generated matrix ⊆ journey frontmatter (then tighten to equality).
4. Document decorator usage in `docs/requirements/traceability/SCHEMA.md`.

### Phase 7 — Downstream + ecosystem

1. Grep <REDACTED> org for `kitty-specs/` and `AgilePlus/traces/` string refs.
2. Update agent prompts (`AGENTS.md`, `CLAUDE.md`, MCP resources).
3. Remove redirect stubs only when external refs = 0 (or after one release cycle).

---

## Validation Gates (per phase)

| Gate | Command / check |
|------|-----------------|
| Encoding | `agileplus validate-encoding --all` |
| Spec completeness | `python tooling/governance_index.py --check` (after retarget) |
| Trace closure | `tooling/trace-validator` (or successor) against `docs/journeys/FR-*.md` |
| Link sweep | `rg 'kitty-specs|/traces/FR-' --glob '!docs/_archive/**'` → zero hits in active paths |
| Frontmatter schema | JSON Schema or `taplo`/custom linter for required keys: `slug`, `spec_id`, `state`, `title` |
| No hand JSON | `find . -path './kitty-specs/*/meta.json' -o -path './traces/FR-*.json'` → empty |
| Decorator matrix | `cargo xtask traceability --check` (Phase 6+) |

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Duplicate spec dirs diverge during hybrid state | Phase 1 prioritizes eco specs with both copies; use `diff -r` before deleting legacy |
| `git mv` breaks external deep links | Keep redirect README stubs; archive copies preserve audit trail |
| Frontmatter merge loses fields | Archive original `meta.json` before delete; dry-run diff on frontmatter |
| Decorator adoption lag | Journey frontmatter remains authoritative until Phase 6 equality gate passes |
| INDEX.md consumers | Publish `docs/specs/INDEX-eco.md`; symlink or generate stub at old path for one release |

---

## Success Criteria (program complete)

1. All spec content lives under `docs/specs/{eco,crates,platform}/` with YAML frontmatter only.
2. `kitty-specs/`, `specs/`, `traces/` contain README redirect stubs (no substantive content).
3. All FR trace metadata lives in `docs/journeys/FR-*.md` frontmatter; JSON archived under `docs/_archive/traces-json/`.
4. Tooling and CI target `docs/specs/eco/` exclusively.
5. `#[trace_fr(...)]` collector produces the coverage matrix; hand-maintained trace JSON is retired.
6. `rg 'kitty-specs/'` in active code/docs (excluding `_archive` and this plan's inventory tables) returns zero.

---

## References

- [ADR-0003: Docs Tree Consolidation](../adr/0003-docs-tree-consolidation.md)
- [ADR-0004: JSON Metadata → YAML Frontmatter + Code Decorators](../adr/0004-json-to-frontmatter-decorators.md)
- Migration script: `scripts/phase3-docs-consolidate.py`
- Index generator: `tooling/governance_index.py`
- Trace schema: `docs/requirements/traceability/SCHEMA.md`
