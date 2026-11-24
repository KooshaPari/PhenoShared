# ForgeCode source coverage ledger (historical evidence)

> Historical snapshot imported from `d43c060c2b24ca734864af1ad57f6eea3b7c85a4`.
> The counts and GitHub/ancestry status below are evidence captured on 2026-09-07,
> not current repository state, a backup, or a completed consolidation claim.

Integration ancestry was refreshed against `17ac2d20b6fc13f3ee3ac0d89c38746489fdae26` at the snapshot time. Source enumeration remains the dated snapshot below.

Source snapshot UTC: 2026-09-07T06:19:22.163718+00:00

| Source | Refs | Heads | Remote refs | Stashes | Worktrees |
|---|---:|---:|---:|---:|---:|
| mac:/Users/kooshapari/CodeProjects/Phenotype/repos/forgecode | 1195 | 31 | 753 | 0 | 16 |
| windows:C:/Users/koosh/forgecode | 1444 | 26 | 1027 | 0 | 5 |
| windows:C:/Users/koosh/forgecode-work | 13 | 1 | 2 | 0 | 1 |

1116 distinct tips across 2652 source/ref records; 692 duplicate tip groups and 1536 additional aliases. Counts are identities, not verified unique behavior.

| Tip disposition | Count |
|---|---:|
| CONTAINED | 477 |
| REQUIRES_PATCH_REVIEW | 625 |
| UNKNOWN_OBJECT_NOT_LOCAL_OR_NONCOMMIT | 14 |

## Missing Windows worktree paths

- `C:/Users/koosh/forgecode-auto-continue-main-20260802`
- `C:/Users/koosh/forgecode-gpu-current-20260802`
- `C:/Users/koosh/forgecode-integrity`
- `C:/Users/koosh/forgecode-v2107c-build`

## Dirty or untracked locations

- `/Users/kooshapari/CodeProjects/Phenotype/repos/forgecode`: 8 status entries; exact paths in summary JSON.
- `/Users/kooshapari/CodeProjects/Phenotype/repos/forgecode/.worktrees/h017-coverage`: 1 status entries; exact paths in summary JSON.

Windows shell startup warnings were excluded from dirty/stash counts. Failed status commands remain coverage gaps. Mac nested worktree directories appear as untracked directories in the parent checkout; each registered worktree was inspected separately. Eight annotated tag objects absent from the commit-only ancestry set were verified separately with `merge-base --is-ancestor` and counted as contained.

## Method and remaining gates (at snapshot time)

Git `for-each-ref`, `stash list`, `reflog show --all`, `worktree list --porcelain`, and status for every registered worktree captured exact identities in the local raw evidence. Remote heads were read with `ls-remote --heads`. Ancestry uses the snapshot-time integration commit graph, grouped by exact tip SHA. Non-ancestor tips still require patch-equivalence and semantic review. Unknown objects/noncommit tags need explicit object inspection. The compact summary does not replace the raw per-ref ledger.

At the snapshot time, PR #254 was OPEN and auto-merge was absent. All-source coverage was incomplete.

Snapshot next lanes: inspect unavailable Windows worktrees and unknown objects; classify non-contained tips by patch equivalence and dependency; capture dirty content with provenance before integration; reconcile arrivals since source snapshot.

- Snapshot is not a backup or preservation proof.
- Remote-tracking refs may be stale; live remote heads must be reconciled.
- Dirty/untracked content recorded by path only, not backed up.
- Only specified repositories and their registered worktrees enumerated.
- Non-ancestor does not prove unique behavior; semantic/patch review remains.
