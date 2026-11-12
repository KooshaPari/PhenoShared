# Recovery stores — why none of them can be deleted as redundant

The 25 `*-rb-archive-*`, `*-archive-2026*` and `*-archives-*` repositories are
the only surviving copies of several deleted upstreams. They are off-limits
without explicit per-repository confirmation.

This note exists because "off-limits" needs a reason that can be re-checked. A
future pass should not have to take the caution on faith, and should not delete
one of these believing it is a duplicate.

## The test

Three read-only checks were run.

**Ref identity.** If a store's ref names and tip shas match a live repository
exactly, the store holds nothing the live repository does not. None matched.

**Tree identity across every repository.** A tree id is a content hash of the
whole working tree, so two repositories sharing one contain the same files at the
same paths. Comparing the default-branch tree id of all 83 repositories produced
**no duplicate groups at all**, so no store's default branch duplicates any other
repository under any name, not just a similarly named one.

**Containment.** A store with only a few refs against a large live repository is
probably a snapshot of an older state, in which case its commits would all be
ancestors of the live branches. Checking whether each tip commit resolves inside
the live repository settles it.

What this does not establish: exhaustive per-branch containment between a store
and a differently named repository. The default-branch sweep and the same-name
ref comparison cover the realistic cases, but a store could in principle hold a
non-default branch duplicating another repo's branch. Nothing found so far
suggests that, and none of it is grounds for deletion either way.

## Result

Of the 24 stores matching the archive name pattern:

- **20 have no live counterpart at all.** No other repository shares their name,
  and no repository anywhere has the same default-branch tree.
- **4 share a name with a live repository, and not one of their tip commits
  exists in it.**

| Store | Live repo | Store refs | Tips found in live |
|---|---|---:|---:|
| `AgilePlus-rb-archive-20261106` | `AgilePlus` | 3 | 0 |
| `Melosviz-rb-archive-20261106` | `Melosviz` | 3 | 0 |
| `Pine-rb-archive-20261106` | `Pine` | 6 | 0 |
| `Tracera-rb-archive-20261106` | `Tracera` | 3 | 0 |

The four are not stale snapshots of work that later landed. They hold branches
that were never merged and do not exist in the live repositories:

- `AgilePlus`: `pr-1065`, `work-1065`
- `Melosviz`: `pr-237`, `work-237`
- `Pine`: `pr-58`, `pr-59`, `work-58`, `work-59`, `wrapup/pine-20261108`
- `Tracera`: `pr-1039`, `work-1039`

That is exactly the kind of content the earlier deletion batch lost forever, so
these stay.

`phenotype-archives-20261108` (1.2 GB) does not match the archive naming
pattern and was not covered by this test. It is treated as off-limits by the
same rule.

## Unrelated: exact duplicates that do exist

`zz-ref-HeliosCLI` and `zz-ref-HeliosLite` are genuine exact duplicates of
`HeliosCLI` and `HeliosLite`: 1340/1340 and 1061/1061 refs identical, same
names, same tips. Both are forks whose originals still exist, so they hold
nothing unique.

They were **not** deleted. `zz-ref-HeliosLite` was pushed at 07:25 on
2026-11-12, during an active session, so something else is creating these and
deleting one could break that process. They are recorded here as safe to remove
once whoever creates them is identified.
