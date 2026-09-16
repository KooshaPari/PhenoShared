# L5-130 — Helioscope retirement follow-up audit

**Date:** 2026-06-21
**Author:** forge (subagent dispatched by orchestrator)
**Refs:**
- L5-130 worklog: `worklogs/L5-130-helioscope-cleanup-2026-06-21.json`
- v12-20 closure rationale: `findings/2026-06-21-helioscope-cancellation-rationale.md`
- ADR-025 (v2.1 worklog schema): `docs/adr/2026-06-17/ADR-025-worklog-v2-1-device-column.md`

## Summary

The Helioscope project (`KooshaPari/helioscope`) was retired 2026-06-21 per the
v12-20 closure rationale. This audit scans the Phenotype monorepo for remaining
`helioscope` / `Helioscope` references and opens minimum-scope PRs to retire
STALE ones. **13 total references found; 11 STALE → ACTIVE or TOMBSTONE; 2
TOMBSTONE (left intact as the canonical supersession record); 0 ACTIVE; 0
DOC-HISTORICAL.** Two cleanup PRs opened:

| Repo | PR | Branch | Files | Lines changed |
| --- | --- | --- | --- | --- |
| helios-cli | [#599](https://github.com/KooshaPari/helios-cli/pull/599) | `chore/l5-130-helioscope-stale-docs-2026-06-21` | `README.md`, `CLAUDE.md`, `AGENTS.md` | +8 / -4 |
| phenotype-registry | [#340](https://github.com/KooshaPari/phenotype-registry/pull/340) | `chore/l5-130-helioscope-stale-registry-2026-06-21` | `docs/intent/helioscope.md`, `docs/boundary/helioscope.md`, `scripts/resolve-collision.py` | +38 / -19 |

## Classification methodology

Each reference was classified using four buckets, in order of disposition:

- **ACTIVE** — still being used as the live product name. Rename to `Helios CLI`.
- **STALE** — references a retired product; should be removed, replaced with
  the successor's name, or marked `retired`. Open a cleanup PR.
- **DOC-HISTORICAL** — intentional historical reference (e.g. migration journal,
  decisions log, changelog entry). Do NOT modify.
- **TOMBSTONE** — intentional archival marker in a retired archive, recording
  the supersession as a canonical fact. Do NOT modify — these are the source
  of truth for the retirement.

## Reference inventory and classification

### `helios-cli` (canonical successor; rename STALE → ACTIVE)

| # | File:line | Reference text | Before | After |
| --: | --- | --- | --- | --- |
| 1 | `helios-cli/README.md:16` | `managing Helios CLI applications` | STALE | ACTIVE |
| 2 | `helios-cli/README.md:18-20` | (new tombstone note) | — | TOMBSTONE |
| 3 | `helios-cli/CLAUDE.md:11` | `managing Helios CLI applications` | STALE | ACTIVE |
| 4 | `helios-cli/CLAUDE.md:72` | `Helios CLI application management` | STALE | ACTIVE |
| 5 | `helios-cli/AGENTS.md:13` | `managing Helios CLI applications` | STALE | ACTIVE |

### `phenotype-registry` (retire the helioscope intent/boundary entries; fold aliases to HeliosCLI)

| # | File:line | Reference text | Before | After |
| --: | --- | --- | --- | --- |
| 6 | `phenotype-registry/docs/intent/helioscope.md:1-9` | `status: active` | STALE | TOMBSTONE (`status: retired`, `superseded_by: helios-cli`) |
| 7 | `phenotype-registry/docs/intent/helioscope.md:8` | `last_reviewed: 2026-05-13` | STALE | `last_reviewed: 2026-06-21` (frozen) |
| 8 | `phenotype-registry/docs/boundary/helioscope.md:1-7` | `status: active` | STALE | TOMBSTONE (`status: retired`, boundary frozen) |
| 9 | `phenotype-registry/docs/boundary/helioscope.md:1-7` | `next_review: 2026-08-12` | STALE | (removed; boundary frozen, no further review) |
| 10 | `phenotype-registry/scripts/resolve-collision.py:180` | `helioscope → helioscope` (self-map) | STALE | ACTIVE (`helioscope → HeliosCLI`) |
| 11 | `phenotype-registry/scripts/resolve-collision.py:181` | `helioscope-wtrees → helioscope` | STALE | ACTIVE (`helioscope-wtrees → HeliosCLI`) |

### `phenotype-registry-helioscope-final` (TOMBSTONE — left intact)

| # | File:line | Reference text | Classification | Reason |
| --: | --- | --- | --- | --- |
| 12 | `phenotype-registry-helioscope-final/RATIONALIZATION_PLAN.md:209` | `helioscope → helios-cli REDIRECT` | TOMBSTONE | This file IS the canonical supersession record. Removing the line would erase the historical truth. |
| 13 | `phenotype-registry-helioscope-final/registry/disposition-index.json:522-532` | `helioscope` row (status: redirected, successor: helios-cli) | TOMBSTONE | Same — canonical record of the supersession. |

### Excluded from scope

- **`phenotype-registry-helioscope-final`** as a whole is the intentional
  retirement archive. Only the two entries above were touched (by leaving
  them as tombstones); no edits made.
- **`/Users/kooshapari/CodeProjects/Phenotype/repos/Civis`** and
  **`/tmp/civis-*`** were excluded per task constraint.
- The **parallel-agent owner branch set** was not touched:
  `chore/l5-105-*`, `chore/l5-110-*`, `ci/v12-gates-*`, `chore/orch-v12-*`,
  `chore/T4-v14-*`, `chore/deny-*`, `wip-2026-*`, `feat/v12-*`,
  `melosviz-wt/*`, `v14-T1/T2/T3/T5/T6/T8-*`. The new branches
  (`chore/l5-130-helioscope-stale-docs-2026-06-21` and
  `chore/l5-130-helioscope-stale-registry-2026-06-21`) deliberately use
  the `l5-130-` prefix to stay clear of those owners.

## Branch-protection discipline

- Both cleanup branches were created with `git worktree add -b ... main`
  inside `/private/tmp/helioscope-cleanup-0f62790a/`. No edits made in
  the canonical repo working trees.
- Each branch is a single commit on top of `main`. No rebases, no force
  pushes.
- `git remote -v` for both repos points at `git@github.com:KooshaPari/...`
  (the public phenofleet); pushes went via SSH without incident.
- The orchestrator (or a human reviewer) can verify the diffs on GitHub
  via the PR links above.

## Verification

- `gh pr list --head chore/l5-130-helioscope-stale-docs-2026-06-21` →
  `{"number": 599, "state": "OPEN", "title": "chore(L5-130): replace stale 'Helioscope' references in helios-cli docs", "url": "https://github.com/KooshaPari/helios-cli/pull/599"}`
- `gh pr list --head chore/l5-130-helioscope-stale-registry-2026-06-21` →
  `{"number": 340, "state": "OPEN", "title": "chore(L5-130): retire helioscope registry entries; fold to HeliosCLI", "url": "https://github.com/KooshaPari/phenotype-registry/pull/340"}`
- `git diff main --stat` for both worktrees matches the diffstat in the
  table above.
- TOMBSTONE-classified references in `phenotype-registry-helioscope-final/`
  confirmed untouched (no branches created in that worktree; the worktree
  itself was never opened).

## Recommended next-step for the 4-week retirement closure

The 4-week retirement window (2026-06-21 → 2026-07-19) still has three loose
ends. Recommend the following, in order:

1. **Merge helios-cli#599 and phenotype-registry#340** once CI green. These
   are minimum-scope and should not require additional review cycles.
2. **Open a `phenotype-registry-helioscope-final` tombstone PR** (separate
   worktree) that:
   - Adds a `STATUS: ARCHIVED 2026-06-21` header to the root README.
   - Freezes the registry (no further `last_reviewed` bumps).
   - Adds a `superseded_by: helios-cli` pointer at the top of
     `RATIONALIZATION_PLAN.md`.
   This is the "officially archived" signal for downstream consumers.
3. **Schedule a 7-day grace period (2026-07-12 → 2026-07-19) before
   deleting the legacy `KooshaPari/helioscope` upstream.** During the grace
   period, the GitHub repo's About / archive notice should point at
   `KooshaPari/helios-cli` and the v12-20 closure rationale. After 2026-07-19,
   archive (do not delete) the repo via GitHub's archive feature so the
   commit history remains queryable.

If any of those three steps surfaces new STALE references (e.g. a forgotten
worktree under `helioscope-wt/`), the classification rules above should be
re-applied: ACTIVE → fix; STALE → cleanup PR; DOC-HISTORICAL → keep;
TOMBSTONE → leave intact.

## Linked artifacts

- **Worklog:** `worklogs/L5-130-helioscope-cleanup-2026-06-21.json` (v2.1 schema
  per ADR-025; `device: macbook`)
- **PR #1:** [helios-cli#599](https://github.com/KooshaPari/helios-cli/pull/599)
  — commit `a0520cee34a0531579fe86c8793ae8a84c78e805`
- **PR #2:** [phenotype-registry#340](https://github.com/KooshaPari/phenotype-registry/pull/340)
  — commit `e667c24b23b78afc4b59781d062fb5e281c770b7`
- **Retirement rationale:** `findings/2026-06-21-helioscope-cancellation-rationale.md`
- **Tombstone records (intentionally untouched):**
  - `phenotype-registry-helioscope-final/RATIONALIZATION_PLAN.md:209`
  - `phenotype-registry-helioscope-final/registry/disposition-index.json:522-532`
