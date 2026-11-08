# Current Repo-State Ledger - 2026-04-26

## Purpose

This is the first SUNSET-001 ledger for the local Phenotype shelf. It records
current maturity state from cheap, reproducible evidence instead of relying on
archive labels, old plans, or PR queue status.

## Evidence Sources

- Local shelf path: `/Users/<REDACTED>/CodeProjects/Phenotype/repos`
- Snapshot command: top-level `.git` directories, `git status --short --branch`,
  tracked dirty count, untracked count, branch, and origin URL.
- GitHub queue command: `gh search prs --owner <REDACTED> --state open --limit 200`
- Read-only subagent inventory for top-level repo maturity classes.
- Read-only subagent P0 branch-tip manifest for known P0 repos.

## Current Open PR Queue

The org open PR queue is not empty. All visible open PRs are in `phenoShared`
and are blocked by the intentionally tightened review rule.

| PR | Title | Gate |
|---|---|---|
| `phenoShared#110` | `fix(config): restore config core validation` | `REVIEW_REQUIRED` |
| `phenoShared#109` | `feat(errors): add dual-interface contracts` | `REVIEW_REQUIRED` |
| `phenoShared#108` | `chore(gitignore): add .worktrees/ + .claude/worktrees/ entries` | `REVIEW_REQUIRED` |
| `phenoShared#107` | `fix(crates): add missing description fields to error-core/event-sourcing/health` | `REVIEW_REQUIRED` |
| `phenoShared#106` | `fix(readme): document all 16 workspace members` | `REVIEW_REQUIRED` |

Merge order after approval remains: `#110`, `#109`, `#108`, `#107`, `#106`.

## Snapshot Counts

Two scans were used because they answer different questions:

| Scan | Scope | ACTIVE | MAINTENANCE | SUNSET_READY | ARCHIVED | QUARANTINE |
|---|---:|---:|---:|---:|---:|---:|
| Top-level git-only status scan | 112 repos | 14 | 24 | 1 | 0 | 73 |
| Shelf inventory scan including non-git containers | 179 entries | 95 | 12 | 33 | 36 | 3 |

Interpretation:

- The git-only scan is conservative and marks any dirty, ahead/behind, detached,
  or branch-work repo as `QUARANTINE` unless it is already a known active repo.
- The shelf inventory scan is broader and counts non-git policy/doc/template
  directories plus archive/worktree containers.
- Neither scan authorizes deletion. These are routing states for follow-up work.

## Priority Repo-State Ledger

| Repo / Container | State | Evidence | Next action |
|---|---|---|---|
| `phenoShared` | `ACTIVE` | Canonical shared-source repo; open PRs `#106-#110`, all review-gated. | Get one write-access approval, merge in documented order. |
| `PhenoKits` | `ACTIVE` | Governance/control-plane docs continue from clean clones; shelf root checkout remains quarantined. | Continue docs PRs from fresh clones. |
| `AgilePlus` | `ACTIVE` | Clean local main in git-only scan; canonical project truth still under `.agileplus/*`. | Keep as active runtime/spec owner; avoid shelf contamination. |
| `thegent` | `ACTIVE` | Worktree branch `chore/gitignore-worktrees-2026-04-26`; small untracked count. | Keep active; avoid broad legacy-stack rebases. |
| `Tracera-recovered` | `ACTIVE` | Branch `fix/main-workflow-syntax`; remote `<REDACTED>/Tracera`; dirty but is the recovered live source. | Resolve with `Tracera` routing under SUNSET-011. |
| `Tracera` | `SUNSET_READY` candidate | Non-git/docs-only container in shelf inventory; recovered source is elsewhere. | Do not delete; compare against `Tracera-recovered` before successor note. |
| `agentapi-plusplus` | `MAINTENANCE` / P0 salvage | Clean and synced on `main`; P0 subagent recommends `salvage`. | Keep as current manifest source; no wholesale recovery needed. |
| `Dino` | `MAINTENANCE` / P0 salvage | Clean and synced on `main`; P0 subagent recommends `salvage`. | Keep; verify ruleset/readme state before sunset claims. |
| `PhenoSpecs` | `MAINTENANCE` / P0 salvage | Clean local main, behind remote-tracking by 1; no dirt. | Fast-forward/validate in a dedicated lane. |
| `PhenoProc` | `QUARANTINE` | `31` tracked changes, `490` untracked, ahead 1 / behind 1. | Split salvageable workspace artifacts from unrelated dirt. |
| `phenoSDK` | `QUARANTINE` | `2189` tracked changes, mostly deletions, branch behind remote by 11. | Do not land wholesale; create deletion manifest before any salvage. |
| Shelf root | `QUARANTINE` | Root checkout points at project remotes rather than neutral shelf manifest; prior object-store corruption observed. | Do not treat shelf root as project truth; use fresh per-repo clones. |
| `AuthKit/go` | `QUARANTINE` / split | Nested clean git repo with no remote/upstream; parent sees `go` as modified. | Decide submodule vs vendored nested repo vs flattened directory under SUNSET-003. |
| `.worktrees`, `*-wtrees`, `*-wtr` containers | `ARCHIVED` / quarantine containers | Inventory scan found many nested branch worktrees. | Keep until row-level disposition; no deletion. |
| `PhenoSchema` | `QUARANTINE` | No top-level git, nested `pheno-xdd` and `pheno-xdd-lib`. | Already routed by migration proposals; verify no unique source before deletion. |

## Highest-Risk Dirty Repos

| Repo | Evidence | Required disposition |
|---|---|---|
| `phenoSDK` | `2189` tracked changes, `11` untracked, behind remote. | Quarantine, deletion manifest, split-only salvage. |
| `PhenoProc` | `31` tracked changes, `490` untracked, ahead/behind. | Split salvage branches by coherent crate/workspace lane. |
| `phench` | `149` tracked changes; status scan timeout in inventory pass. | Treat as Tracera-related quarantine until timed scan succeeds. |
| `ResilienceKit` | `137` untracked on worktree branch. | Preserve; do not prune worktree branch without artifact manifest. |
| `PhenoDevOps` | `94` untracked. | Manifest before cleanup. |
| `TestingKit` | `80` untracked. | Manifest before cleanup. |
| `PhenoVCS` | `3` tracked, `28` untracked on sync branch. | Inspect for salvageable sync state. |
| `Tracely` | `9` tracked, `18` untracked, branch ahead. | Continue dead-code phase lane or close with branch ledger. |

## Classification Rules

- `ACTIVE`: canonical project/source repo with current product, platform, or governance role.
- `MAINTENANCE`: clean or low-churn repo with durable value but no current heavy feature lane.
- `SUNSET_READY`: candidate only; requires no open PRs, no local unmerged work, no Dependabot emitters, and successor/canonical-home note before archive.
- `ARCHIVED`: archive/worktree container; no deletion without row-level disposition.
- `QUARANTINE`: dirty, diverged, detached, ambiguous, corrupted, or nested repo state requiring written disposition before mutation.

## Next Work Packages

1. `SUNSET-003`: decide `AuthKit/go` ownership model.
2. `SUNSET-011`: resolve `Tracera` vs `Tracera-recovered` canonical routing.
3. `P0-DRIFT-001`: create detailed branch-tip manifests for `phenoSDK` and `PhenoProc`.
4. `P0-DRIFT-002`: create row-level manifests for `.worktrees` and `*-wtrees` containers.
5. `GATE-001`: obtain review for `phenoShared#110` and `#109` before any shared-crate consumer migration claims.
