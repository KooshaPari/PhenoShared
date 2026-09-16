# Depletion Audit Batch 1 (2026-07-17)

Per ADR-007 (absorption eligibility boundary), every active fleet member must
either be AFFIRM-canonical, absorbable into a target home, or a **depletion
candidate** (retire + archive + relocate).

This document records **batch 1** of 10 depletion proposals based on the
systematic audit of every KooshaPari repo.

## Boundary Policy Recap (ADR-007)

- **TOO_LARGE_RETIRE** — size > 500MB, retire + archive
- **TOO_BOUND_UPSTREAM** — 5/5 OWNERS = upstream maintainers
- **TOO_INCOMPLETE / TOO_INCOMPLETE_RETIRE** — no committed external contract
- **TOO_NOVEL** — < 14 days old, needs stabilization time
- **KEEP_LOCAL_PRIMITIVE** — focus locally while primitive
- **KEEP_LOCAL_CORE** — never delete (registry, spine repos)
- **LEGACY_POLYGLOT** — pre-ADR multi-crate legacy
- **NEVER_EXISTED_REMOTE** — phantom 404 GitHub refs
- **LOCAL_RETIRE_CANDIDATE** — local-only reflection drops

## Batch 1 Proposals

| # | Repo | Disposition | Size | Action | ADR Ref |
|---|---|---|---|---|---|
| 1 | phenotype-apps | TOO_INCOMPLETE_RETIRE | 1.7GB | `gh repo archive` + relocate local | §3 |
| 2 | OmniRoute | TOO_BOUND_UPSTREAM | 453MB | Relocate local to `_retire/` | §4 |
| 3 | portage | TOO_BOUND_UPSTREAM | 156MB | Relocate local to `_retire/` | §4 |
| 4 | heliosApp | TOO_INCOMPLETE | 13MB | Relocate local to `_retire/` | §3 |
| 5 | phenotype-teamcomm | KEEP_LOCAL_PRIMITIVE | 372MB | Relocate out of active fleet | §5 |
| 6 | phenotype-registry | KEEP_LOCAL_CORE | 181MB | **Keep at canonical location** | — |
| 7 | AgilePlus | LEGACY_POLYGLOT | 27GB (ghost) | Relocate to `_retire/` | §6 |
| 8 | phantom-dist-sbom | NEVER_EXISTED_REMOTE | 0KB | Update registry row to NEVER_EXISTED_REMOTE | §7 |
| 9 | phantom-phenotype-teamcomm-archive | NEVER_EXISTED_REMOTE | 0KB | Verify content present, fix FOCUSED_PRIMITIVE claim | §7 |
| 10 | spectra-worktrees | LOCAL_RETIRE_CANDIDATE | 5KB | Relocate to `_retire/` | §6 |

## Net Fleet Reduction

If all 10 batch1 actions are executed:
- **GitHub archives**: +2 (phenotype-apps, phantom-dist-sbom cannot be archived since 404)
- **Local clones relocated to `_retire/`**: 8 (total ~3GB freed from active fleet root)
- **Registry row updates**: 2 (phantom rows → NEVER_EXISTED_REMOTE)

## Standing Rule

After batch1 completion, continue auditing remaining repos. Queue next
batch (batch2) of 10 in: `2026-07-17-depletion-batch2`.

**Total repos to audit**: ~109 KooshaPari repos
**Batches planned**: ~11 batches × 10 each

## Execution Order

1. First: `phenotype-apps` (1.7GB — biggest impact)
2. Phantom registry rows (pure bookkeeping, no I/O)
3. Bound upstream clones (OmniRoute, portage — pure relocate)
4. Incomplete apps (heliosApp)
5. KEEP_LOCAL_PRIMITIVE: phenotype-teamcomm (focus locally)
6. KEEP_LOCAL_CORE: skip (phenotype-registry)
7. Legacy polyglot: AgilePlus ghost clone
8. Local retire candidates: spectra-worktrees
