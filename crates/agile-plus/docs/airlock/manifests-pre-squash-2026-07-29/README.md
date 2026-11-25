# Pre-Squash Branch Manifests — 2026-07-29

Generated because the user's rule *"squash the repo into one commit\1branch after your provably know the branches\and commit history hie no novel items"* allows squash **only when no novel items exist**. The re-audit on 2026-07-29 with full pagination revealed massive novelty:

| Repo | Total branches | Novel (with unique commits) | Subsumed (0 unique vs main) |
|---|---|---|---|
| `thegent` | 403 | **358** | 45 |
| `thegent-sharecli` | 18 | **14** | 4 |
| `vibeproxy-monitoring-unified` | 22 | **4** | 0 (all remote-tracking) |
| **Total** | **443** | **376** | **49** |

**Result: Squash is BLOCKED by the user's own rule.** `thegent` has 358 branches containing up to 1,394 unique commits each; `thegent-sharecli` has 14 with novel commits. Destroying these would lose real work.

## What's In This Folder

```
manifests-pre-squash-2026-07-29/
  thegent-branches-manifest.txt                        (819 lines)
  thegent-sharecli-branches-manifest.txt               (47 lines)
  vibeproxy-monitoring-unified-branches-manifest.txt   (19 lines)
  README.md                                            (this file)
```

Each manifest enumerates:
- Repo metadata (HEAD OID, subject, generation timestamp)
- Every branch (local + remote), sorted
- Per-branch novel-commit count vs `main`
- Per-branch tip OID, date, and subject

## Why Manifests Matter

Per the user's rule: *"after you provably know the branches\and commit history hie no novel items"*. These manifests are the **proof**. If we ever want to re-evaluate squashing later, these receipts document what existed at 2026-07-29.

## Path Forward

- **G1+G2 are NOT squashed.** Remote branches remain intact on `origin`.
- **No destructive action taken.** No force-push, no remote-branch deletion, no local clone deletion.
- **G3 (phenotype-omlx)** still pending — user said "C\\A\\B in that order such that you lose nothing"; will route via repo URL `https://github.com/jundot/omlx` and produce the same manifest-first pattern.
- **G4–G7 still gated** — no approval received.
- **REPOS.md** still gated — user-managed doc.

## What You Can Do Now

1. **Review the manifests** — confirm the 358 novel branches in `thegent` are real work, not junk.
2. **Decide a per-branch triage policy** — e.g., "all `feat/*` branches merged, all `wip/*` retained as branches, all `backup/*` deleted by next wave".
3. **Re-confirm squash direction** — once you've reviewed, you can either:
   - Approve per-branch triage (and I do that for each of 376 novel branches iteratively), OR
   - Approve "preserve all branches, do not squash" (and the dockets become the final state).

**No mutations will occur until you reply.**
