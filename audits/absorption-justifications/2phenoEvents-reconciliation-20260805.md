# 2phenoEvents Historical Alias Reconciliation - 2026-08-05

## Scope

Reconcile the stale queued `2phenoEvents` record with current remote state and
the canonical `phenoEvents` lineage. This is registry metadata only; no source
repository, branch, worktree, or target tree is changed.

## Evidence

| Subject | Result |
| --- | --- |
| `gh api repos/KooshaPari/2phenoEvents` | not found (404) |
| `git ls-remote https://github.com/KooshaPari/2phenoEvents.git refs/heads/main` | repository not found |
| Historical source commit | `5bb0c894e44a50079035b3d5ab5d31946fc445c1` |
| Canonical repository | `KooshaPari/phenoEvents`, public and unarchived |
| Canonical source provenance | `5bb0c894...` is reachable in `phenoEvents` as its root restore commit |
| Current canonical main | `be6573c68797cc611a99533bca6dc1c3dcdb0c88` |
| Current pheno main | `81d850837848800aa7a3e6a6f007b91b6555ef07`; no claimed event-bus path |

The preserved commit proves a historical source lineage. Therefore a current
404 must not be represented as `NEVER_EXISTED`; it is a historical alias
tombstone whose source has no unique content outside canonical `phenoEvents`.

## Decision

- `2phenoEvents`: `HISTORICAL_ALIAS_TOMBSTONE`.
- `phenoEvents`: `KEEP_CANONICAL_STANDALONE`.
- `pheno`: historical and unverified target claim only.

No code lift, merge, deletion, archive operation, force-push, or GitHub setting
change is authorized by this reconciliation.
