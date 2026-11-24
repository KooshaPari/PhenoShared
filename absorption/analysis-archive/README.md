# analysis-archive — retired (2026-11-11)

This repository no longer holds records or tooling. Both moved, under the
operator directive of 2026-11-11 that shared code belongs in `PhenoShared`,
records belong in `PhenoRegistry`, and no archive or trash repository should be
created for small work.

## Where everything went

| What | Where | PR |
|---|---|---|
| Corpus write guard and its tests | `KooshaPari/PhenoShared` → `researchledger/` | #903 (merged) |
| Ingest pipeline and its tests (121 files) | `KooshaPari/PhenoShared` → `researchledger/ingest/` | #915 |
| 521 record files | `KooshaPari/PhenoRegistry` → `archives/zz-archive-analysis-archive/` | #761, #762, #764, #765 |
| Archive index | `KooshaPari/PhenoRegistry` → `archives/zz-archive-analysis-archive/README.md` | #766 |
| Incident and remediation record | `KooshaPari/PhenoRegistry` → `docs/sessions/20261111-research-ledger-corpus-hardening/` | #760 |

## What stays here

Only the corpus itself, which is git-ignored and was never in this repository:

- `research_ledger.sqlite` — 22,390,628,352 B (20.9 GiB), 5,466,462 pages of 4096,
  4,468,304 rows. SHA-256 of the sealed copy:
  `69b8c240afa3366186394a73bf56a997c6732e48ecc5cd441429fd7ebd57171f`.
- `~/CodeProjects/backups/analysis/research_ledger.sqlite.sealed-20261111` — the
  sealed local backup, `chmod 444`, verified against the live corpus on page
  count, schema fingerprint, 42 table row counts and `PRAGMA integrity_check`.
- An off-host copy lives on the desk node (`kooshapari-desk`), so the corpus
  survives the loss of this machine.

The write guard lives with the code that uses it, in `PhenoShared/researchledger/`,
and refuses any write target inside the sealed archive directory.

## Rules and checklists

- No-new-archive-repos rule: `~/.jcode/memories/global/no-new-archive-repos.md`
- Persistent closure checks and the live schedule ids:
  `~/.jcode/memories/global/closure-checks-and-goal-decomposition.md`

## Retiring the repository itself

The GitHub repository `KooshaPari/analysis-archive` is scheduled for deletion.
`gh repo delete` is policy-blocked, so the deletion needs the operator's
explicit approval; until then this repository exists but tracks nothing beyond
this pointer and `.gitignore`.
