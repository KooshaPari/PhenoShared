# SPINE-DEFINITION — Phenotype Ecosystem Architecture

**Date**: 2026-07-17
**Status**: ADOPTED (ratification pending)
**Authors**: registry subagent (boundary-corrections pass)

## Purpose

The Phenotype ecosystem uses a **7-role spine** to disambiguate the responsibilities of the
top-level repositories. This ADR consolidates the previously scattered spine-role claims
into a single source of truth.

## Background

Across multiple sessions, several repos self-declared (or were declared by absorbing agents)
as "spine members" with implicit roles. By 2026-07-17, the registry had:

- 4 declared canonical roles from original spine (INDEX, ADRs/contracts, CONVENTIONS, ENFORCEMENT)
- 4 newly declared roles from queue-refresh batches 5 & 6 (IMPLEMENTATIONS, JOURNEYS, SHARED-PRIMITIVES, CONTRACTS)
- 1 retracted/duplicated role claim (PLATFORM was proposed for AgilePlus, then retracted via TOO_LARGE_RETIRE)

This ADR is the consolidating reference.

## The 7-Role Spine

| # | Role | Spine Member | Repo State | Notes |
|---|---|---|---|---|
| 1 | **INDEX** | `phenotype-registry` | LIVE (this repo) | The catalog/system-of-record |
| 2 | **ADRs / contracts-doc** | `PhenoSpecs` | LIVE upstream, physically absorbed into `phenotype-registry/docs/specs/pheno-specs/` | Spine integrity violation — see "Outstanding Issues" below |
| 3 | **CONVENTIONS** | `PhenoHandbook` | LIVE upstream, physically absorbed into `phenodocs/docs/handbook/` | Spine integrity violation — see "Outstanding Issues" below |
| 4 | **ENFORCEMENT** | `phenotype-org-governance` | LIVE (spine member) | ADRs, policies, audit enforcement |
| 5 | **IMPLEMENTATIONS** | `PhenoMCPServers` | LIVE (spine member, un-archived deliberately) | Catalog of MCP server implementations + schemas + skills + plugins + agents |
| 6 | **JOURNEYS / TRAINING-GROUND** | `phenotype-journeys` | LIVE (spine member, un-archived deliberately) | "AI-Agent-Only Repository" with intentionally generated "slop" — used as training ground for AI agents |
| 7 | **SHARED-PRIMITIVES** | `phenotype-shared` | LIVE (spine member, un-archived deliberately) | Cross-repo Phenotype primitives (manifest, port-adapter-shim, ffi_utils); adopted by BytePort, OmniRoute, NanoVMS |
| 8 | **CONTRACTS** | `phenotype-contracts` | LIVE (spine member, un-archived deliberately) | 3 JSON Schemas (provider-model, oauth-refresh-policy, resilience-policy); language-agnostic, consumed by forgecode (Rust), OmniRoute (TS), cliproxyapi-plusplus (Go) |
| 9 | **CREATIVITY / DESIGN / UX** | `phenoDesign` | LIVE (spine member, un-archived 2026-07-20) | Design tokens (`@phenotype/design`), UX patterns, art direction; peer `asset-engine` owns render pipeline |

> Note: the spine has 4 original roles + 5 operational roles = 9 total. The label "7-role spine"
> predates ratification of JOURNEYS, SHARED-PRIMITIVES, CONTRACTS, and CREATIVITY_DESIGN_UX.

## Spine Tier Classification

| Tier | Roles | Members | Mutability |
|---|---|---|---|
| **Tier 1: Foundational** | INDEX, ADRs, CONVENTIONS, ENFORCEMENT | `phenotype-registry`, `PhenoSpecs`, `PhenoHandbook`, `phenotype-org-governance` | Cannot be archived; if changes needed, spine-upgrade ADR |
| **Tier 2: Operational** | IMPLEMENTATIONS, JOURNEYS, SHARED-PRIMITIVES, CONTRACTS, CREATIVITY_DESIGN_UX | `PhenoMCPServers`, `phenotype-journeys`, `phenotype-shared`, `phenotype-contracts`, `phenoDesign` | LIVE; consume spine-protocol updates |
| **Tier 3 (proposed, retracted)** | PLATFORM (BLOCK-A) | `AgilePlus` (proposed) | RETRACTED 2026-07-17 — AgilePlus marked TOO_LARGE_RETIRE (94 crates, 27GB). PLATFORM role reopens when a smaller candidate emerges. |

## Spine Member Canonical Sources

All Tier 1 + Tier 2 members must remain **LIVE on GitHub** as the canonical source.
Absorption of any of these into another repo is a **spine integrity violation** requiring
an ADR override.

| Member | Canonical path | Mirror (if any) | Notes |
|---|---|---|---|
| `phenotype-registry` | `github.com/KooshaPari/phenotype-registry` | n/a | Self-referential |
| `PhenoSpecs` | `github.com/KooshaPari/PhenoSpecs` | `phenotype-registry/docs/specs/pheno-specs/` | **DELEGATED MIRROR** pending decision |
| `PhenoHandbook` | `github.com/KooshaPari/PhenoHandbook` | `phenodocs/docs/handbook/` | **DELEGATED MIRROR** pending decision |
| `phenotype-org-governance` | `github.com/KooshaPari/phenotype-org-governance` | n/a | — |
| `PhenoMCPServers` | `github.com/KooshaPari/PhenoMCPServers` | n/a | — |
| `phenotype-journeys` | `github.com/KooshaPari/phenotype-journeys` | n/a | — |
| `phenotype-shared` | `github.com/KooshaPari/phenotype-shared` | n/a | — |
| `phenotype-contracts` | `github.com/KooshaPari/phenotype-contracts` | n/a | — |
| `phenoDesign` | `github.com/KooshaPari/phenoDesign` | n/a | Asset pipeline peer: `github.com/KooshaPari/asset-engine` (extracted from `engine/`) |

## Outstanding Issues

### Issue 1: PhenoSpecs delegated-mirror vs upstream restoration

PhenoSpecs (the ADRs/contracts spine member) was physically absorbed into
`phenotype-registry/docs/specs/pheno-specs/` by a concurrent agent, destroying the
spine peer relationship.

Two remediation options:

**Option A: Delegated-mirror declaration** (recommended)
- Keep the physical absorption (saves disk + git maintenance)
- Declare the upstream `PhenoSpecs` as the **canonical source of truth**
- Declare `phenotype-registry/docs/specs/pheno-specs/` as a **read-only mirror**
- All consuming repos pin to the upstream URL, not the mirror
- Mirror is auto-regenerated from upstream; if drift detected, regenerate

**Option B: Upstream restoration**
- Restore `PhenoSpecs` as the standalone spine repo
- Move `phenotype-registry/docs/specs/pheno-specs/` content back to `PhenoSpecs`
- Update all references to point at `PhenoSpecs` directly

**Recommendation**: Option A. Restoration adds maintenance burden without functional
benefit; the mirror is downstream-pure (read-only), so integrity is preserved.

### Issue 2: PhenoHandbook delegated-mirror vs upstream restoration

Same pattern as PhenoSpecs. PhenoHandbook (CONVENTIONS spine) was absorbed into
`phenodocs/docs/handbook/`.

**Recommendation**: Same as Issue 1 — Option A (delegated-mirror declaration).

### Issue 3: PLATFORM (BLOCK-A) role — reopens when?

The PLATFORM role was proposed for `AgilePlus` (94 crates, 27GB), but AgilePlus was
marked TOO_LARGE_RETIRE on 2026-07-17.

**Reopening criteria**:
- A candidate repo < 100 MB total size
- Workspace structure is well-bounded (≤ 20 crates OR clear submodule boundary)
- Has at least 3 downstream consumers that would benefit from spine-membership guarantees

**Open candidates** (audit next session): none currently meet criteria.

## Ratification

This ADR is **proposed** on 2026-07-17. Ratification requires:
- Approval from at least 2 downstream consumers per spine member
- Resolution of Outstanding Issues 1 + 2 (delegated-mirror decision)
- A clean spine-member audit confirming all 8 repos are LIVE on GitHub

## Cross-references

- `docs/boundary/fleet-absorption-eligibility-2026-07-17.md` — boundary policy doc
- `registry/disposition-index.json` rows where `disposition = DECLARE_SPINE`
- `docs/spine/PhenoMCPServers.md`, `docs/spine/phenotype-journeys.md`, `docs/spine/phenotype-shared.md`, `docs/spine/phenotype-contracts.md` — Tier 2 boundary docs
- `docs/boundary/phenotype-journeys.md` — Tier 2 boundary doc
- `docs/boundary/phenotype-shared.md` — Tier 2 boundary doc
- `docs/boundary/phenotype-contracts.md` — Tier 2 boundary doc

## Changelog

- 2026-07-17: Initial draft consolidating 4 original + 4 newly-ratified spine roles
- 2026-07-20: Added CREATIVITY_DESIGN_UX spine role (`phenoDesign`); reversed 2026-07-17 absorption; peer `asset-engine` for render pipeline