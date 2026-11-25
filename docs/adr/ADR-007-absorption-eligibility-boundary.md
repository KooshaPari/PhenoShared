# ADR-007: Absorption Eligibility — Boundary & Scope Filters

**Status:** Accepted
**Date:** 2026-07-17
**Context:** During 2026-07-17 queue refresh waves, multiple queued entries violated
the registry's scope-boundary philosophy (large workspaces queued for single-pass
absorption, fork-bound apps marked ABSORB, primitive-repo novel work queued before
boundary stabilization). This ADR codifies the eligibility filters the queue MUST
apply before adding entries.

## Decision

### Hard-exclude categories (NEVER an ABSORB target)

A repo MAY NOT receive `disposition=ABSORB` and `fsm=active` (i.e., may not enter
the absorption queue as a code-transfer target) if any of the following apply:

1. **Too-large for clean absorption** — workspace exceeds ~50 MB **or** ≥5 member
   crates **or** ≥1 GB of bundled assets, **unless** the absorption is a documented
   boundary document only (catalog-not-consolidate). The catalog lives at
   `docs/boundary/large-workspace-repos.md`. Examples currently excluded:
   `Tracera`, `nanovms`, `Portage`, `BytePort`, `HexaKit`, `Agentora`,
   `PhenoRuntime`, `Tasken`, `Grapheon`, `PhenoCompose`, `AgilePlus`.

2. **Fork-bound** — the repo is a vendored fork of an active upstream
   (parent repo exists, `fork=true`, or README declares upstream). Absorption
   creates permanent merge-conflict debt and pins the spine to upstream
   release cadence. Examples: `cliproxyapi-plusplus`, `context-mode-plusplus`,
   `substrate-adapters-bundle` (re-export shims of upstream substrate).
   Action: `disposition=ARCHIVE_ONLY` with `archive_reason=fork-bound`
   or `disposition=DECLARE_SPINE` if already canonical.

3. **Focused primitive under active development** — novel, narrow-scope work
   that needs isolated iteration space. Absorption collides with the user's
   active development focus. Examples: `phenotype-teamcomm`. Action:
   `disposition=AFFIRM` (canonical in place) **or** leave out of queue entirely
   until the user signals convergence.

4. **Already canonical spine member** — repos declared spine in
   `BOUNDARY_OWNERS.md`, `ECOSYSTEM_MAP.md`, `docs/spine/SPINE-DEFINITION.md`,
   or any prior ADR (e.g., `phenotype-tooling`, `phenotype-apps`, `sharecli`,
   `SessionLedger`, `OmniRoute`, `phenoAI`, `phenodocs`, `AuthKit`,
   `phenokits-commons`, `substrate`, `bifrost`, `PhenoObservability`). Action:
   `disposition=DECLARE_SPINE` or leave as `AFFIRM`.

5. **404 / never existed on remote** — repos that the GitHub API returns as
   not-found. Action: `disposition=NEVER_EXISTED`/`NEVER_EXISTED_REMOTE`
   tombstone rows; do not re-queue on subsequent refreshes.

### Soft-exclude (requires user signal)

- **Experimental / pre-1.0 repos** with `core_lang` ambiguity (e.g., mix of
  Rust + Python + Go without a clear primary). Require user review before
  queueing to ensure the consumer-side fit is correct.
- **Novel-language additions** (e.g., Zig, Lua) — require user review;
  default to leaving untracked until the spine has a target language home.

### Refresh policy

- Top up the queue with fresh principled picks only when an absorbed entry
  drops the active count below 5.
- **NEVER pad the queue to "10 repos" for its own sake** — empty queue is
  healthier than artificially-queued entries.
- Skip patterns for `SKIP_PATTERNS`, `DOT_PREFIXES`, personal projects,
  non-Phenotype work, and strict-pause mirrors remain in effect.

### Account-shape target

- Total unarchived repos on the user account should remain **<75**.
- If a refresh would push past 75, do not add the entry — instead, archive
  non-spine repos first.

## Consequences

- Future queue-refresh agents MUST apply this filter before adding rows.
- Large-workspace repos get cataloged in `docs/boundary/large-workspace-repos.md`
  instead of being absorbed; downstream consumers pick specific crates when
  a real need arises.
- Fork-bound repos are archived with `archive_reason=fork-bound` rather than
  pushed to ABSORB.
- `phenotype-teamcomm` (and similar novel primitives) get AFFIRM/leave-alone
  handling until the user signals convergence.
- The active queue reflects the *minimum set of absorbable candidates*, not
  the maximum set of repo names.

## References

- `docs/boundary/large-workspace-repos.md` — triangulation catalog
- `docs/rationalization/boundary-shaping.md` — HexaKit-scaffolding-only rule
- `BOUNDARY_OWNERS.md` — canonical spine ownership
- `ADR-005-agileplus-governance-boundary.md` — spine-membership precedent
- `ADR-006-zero-loop-agent-session.md` — session protocol
- 2026-07-17 boundary-correction commit (`registry/disposition-index.json`)
