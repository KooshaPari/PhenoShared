# Pre-absorb gate

An absorption only adds. This gate measures the destination tree before and after an
absorb and fails when the removal count has the shape of a replacement.

It exists because the 2026-11-23/24 incident was not a bad merge, a failing test, or a
broken build. An absorb replaced the destination tree, and every file that had been in
the repository was still there in git history but no longer in the working tree.
`absorb claude-remember tree` (`66c413b73`) left 600 files where 56,728 had been. The
repair that followed, `9f951e777`, changed 72,993 files, the largest commit in the
repository's history. Recovery cost three restore commits and six hand-made safety
branches, and the only detector at the time was a person noticing.

## Relationship to the other absorption checks

- `absorption-verify.yml` asks whether an absorbed tree matches its source. That is
  completeness of what was imported.
- `scripts/pre_absorb_gate.sh` asks whether the destination repository still has what it
  had before the absorb. That is retention of what was already there.

A tree can pass the first and fail the second at the same time: absorb a correct source
over the top of the destination, and the source is complete while the destination has
lost files. Both checks are needed.

## Local use

Snapshot the tree before the absorb, then check it after.

```bash
./scripts/pre_absorb_gate.sh --snapshot --label before-absorb
# ... do the absorb ...
./scripts/pre_absorb_gate.sh --check
```

The snapshot records the HEAD commit, its tree hash, and a full `git ls-tree -r`
manifest under `<git-common-dir>/pre-absorb/`. `--check` compares that manifest against
the current tree. Point at any two refs instead, with no snapshot needed:

```bash
./scripts/pre_absorb_gate.sh --check --pre-ref origin/main --post-ref HEAD
```

The gate is read-only with respect to git state. It runs `rev-parse`, `ls-tree`,
`for-each-ref` and `cat-file`, never commits, resets, checks out, fetches or pushes, and
writes only its own report files. It reports a missing `preserve/<branch>` safety ref but
never creates one, because creating and pushing a ref is a remote mutation and belongs to
a human.

## Thresholds

The default verdict fails when removals exceed **50 files AND 0.5% of the pre-absorb
manifest**. Both halves must hold, so a small repository deleting 40 files and a large
repository deleting 200 of 73,000 files both pass, while 56,728 removals never can.
`--allow-removals N` replaces both halves with one absolute cap for a declared,
intentional deletion.

Modifications are always reported, and carry a NOTE when they exceed 30% of the pre
total. They are not gated, because a legitimate absorb rewrites little and a replacement
removes a lot; gating modifications would fail honest work while the removal count
already carries the signal.

## Exit codes

| Code | Meaning                                                                           |
| ---- | --------------------------------------------------------------------------------- |
| 0    | Additive absorb, PASS                                                             |
| 2    | Usage error                                                                       |
| 3    | Not a git worktree                                                                |
| 4    | Snapshot missing or unreadable                                                    |
| 5    | Ref cannot be resolved                                                            |
| 6    | Pre-absorb manifest is empty                                                      |
| 10   | Tree replacement suspected, FAIL                                                  |
| 13   | `--require-preserve` was requested and no `preserve/*` ref matches the pre commit |

## CI

`pre-absorb-gate.yml` runs the same check on every pull request, comparing the base
branch tree to the pull request head tree, so a replacement fails at review time instead
of after it lands on `main`. On exit 10 it emits one `TREE REPLACEMENT SUSPECTED`
annotation carrying the counts, and uploads `report.txt` and `removed.txt` so the list of
lost paths is the recovery instruction rather than something to reconstruct.

The workflow is advisory until a branch protection rule requires it. For a deliberate
bulk deletion, set the repository variable `PRE_ABSORB_ALLOW_REMOVALS` to the number of
files being removed. That is an admin action, so the override is attributable, and a pull
request cannot grant itself one.

The workflow has no `workflow_dispatch` inputs. checkov's CKV_GHA_7 requires them to be
empty, because what a workflow builds must follow from the source it was pointed at and
not from a value typed at dispatch time. A dispatch therefore re-checks the branch it was
started on against the default branch. Any other pair of refs is a local run, which is
the form that takes `--pre-ref` and `--post-ref` freely.

## Evidence from the real history

Run against this repository, on the commits that caused the incident and the commit that
repaired it:

| Pre ref      | Post ref    | Removed | Added  | Exit |
| ------------ | ----------- | ------- | ------ | ---- |
| `66c413b73^` | `66c413b73` | 56,728  | 600    | 10   |
| `2309c699c`  | `fd85e0958` | 16,259  | 770    | 10   |
| `a10ba4404`  | `66c413b73` | 55,963  | 600    | 10   |
| `9f951e777^` | `9f951e777` | 0       | 72,993 | 0    |

The last row matters as much as the first three. The repair added 72,993 files and
removed none, and the gate passes it, so the check distinguishes damage from the fix
rather than simply failing on large commits.

## Known limits

- It compares destination trees only. An absorb that deletes 40 files while silently
  replacing the contents of 4,000 others passes, and the modification NOTE is a warning,
  not a verdict.
- A rename is one removal and one addition. A large rename pass can therefore approach
  the threshold; `--allow-removals` is the intended answer.
- A submodule gitlink that changes counts as one modified entry, whatever happened
  underneath it.
- It cannot detect damage that predates the snapshot. The snapshot has to be taken
  before the absorb, which is why the CI form compares against the base branch ref
  rather than trusting a file in the pull request.
