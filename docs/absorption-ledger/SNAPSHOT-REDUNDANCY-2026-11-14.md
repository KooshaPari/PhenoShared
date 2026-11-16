# Are the snapshot repositories redundant?

Date: 2026-11-14
Question: the twelve `Snapshot import` repositories hold between 17 and 22,552
files each. Deleting them requires proving the content exists elsewhere.

## Two tests, because the obvious one is not enough

Comparing the snapshot's tree against the live repository's default branch
answers "is this the same right now". Four of the five pairs differ, but that
proves nothing on its own: a snapshot taken months ago differs from today's tip
while holding nothing that is not an earlier state of existing work.

The test that decides a deletion is blob reachability. Every blob id that appears
on any ref of the live repository is collected, and each snapshot blob that does
not match the live tip is checked against that set. A blob absent from the entire
live history is content that would be lost.

`rev-list --objects` is the obvious way to collect that set and it is the wrong
way: on a blobless clone git lazily fetches every blob it names, which turned
this into 40 minutes of single-object round trips. `ls-tree` reads only tree
objects, which a blobless clone holds in full, and answers the same question in
about 17 seconds.

## Results

| Snapshot                   | Live counterpart   |  Files | Differ from tip | Unique blobs | Verdict                       |
| -------------------------- | ------------------ | -----: | --------------: | -----------: | ----------------------------- |
| `audit-snapshot-PhenoVCS`  | `PhenoVCS`         |    133 |               0 |            0 | **byte-identical, redundant** |
| `audit-snapshot-AgilePlus` | `AgilePlus`        |  2,979 |           1,602 |            1 | not redundant                 |
| `audit-snapshot-tooling`   | `PhenoTooling`     | 22,552 |              83 |            2 | not redundant                 |
| `audit-snapshot-argis`     | `argis-extensions` |  1,613 |               8 |            3 | not redundant                 |
| `audit-snapshot-OmniRoute` | `OmniRoute`        | 13,989 |           5,157 |           43 | not redundant                 |

The scale of "unique" differs from the scale of "differing" by orders of
magnitude, which is the whole point. `OmniRoute`'s snapshot differs from the live
tip in 5,157 files, but only 43 of those blobs are absent from the live history;
the other 5,114 are earlier states that the live repository still contains.

Those 43 are real work. They include the `open-sse/executors/` reasoning and
identity test files, `chatCore` retry and error-identifier handling, SRE scripts,
provider-onboarding helpers and a compression replay route. Content like that is
what "probably duplicated" would have discarded.

## Consequences

1. **Do not bulk-delete the snapshot imports.** Four of the five comparable ones
   hold content that exists nowhere in the live repository's history.
2. **`audit-snapshot-PhenoVCS` and `PhenoVCS` are byte-identical.** One of the two
   can go with nothing lost. Which one is a naming decision, not an evidence one.
3. **`OmniRoute`'s 43 unique blobs are worth recovering**, not just preserving.
   They may be a branch or a working tree that never reached the live repository.
4. **Six snapshots have no live counterpart** (`audit-snapshot-pheno`,
   `-HexaKit`, `-hwLedger`, `-agentapi`, `phenotype-landing`, `cvp-fixture`).
   Redundancy cannot be claimed for them at all, so they stay.

## Reproducing

```
python scripts/tree_compare.py audit-snapshot-PhenoVCS:PhenoVCS
python scripts/blob_reach.py audit-snapshot-OmniRoute OmniRoute
```

`tree_compare.py` compares default-branch trees by blob id.
`blob_reach.py` collects every blob on every ref of the live repository using
`ls-tree` and reports the snapshot blobs that appear nowhere in it.

## Recovering the unique blobs: attempted, and stopped

The next step after identifying OmniRoute's 43 unique blobs was to put them back
into the live repository. That was attempted and deliberately stopped, because
the direction of the divergence cannot be established.

All 41 file blobs classify as **CHANGED**, not **NEW**. Every path still exists
on OmniRoute's default branch; the snapshot simply holds different bytes. So this
is not lost work being restored to an empty space, it is two versions of the same
file with no hash-level way to tell which is later.

Dating the two sides looks promising and is not sufficient:

| Path                                          | Live last changed | Reading                        |
| --------------------------------------------- | ----------------- | ------------------------------ |
| `open-sse/executors/userAgentHeader.ts`       | 2026-09-14        | live changed before the import |
| `open-sse/executors/reasoningEffortMaps.ts`   | 2026-07-02        | live changed before the import |
| `open-sse/executors/vertexMedia.ts`           | 2026-09-14        | live changed before the import |
| `open-sse/services/autoCombo/speedRanking.ts` | 2026-09-14        | live changed before the import |
| `scripts/sre/oncall-rotation.mjs`             | 2026-07-02        | live changed before the import |
| `src/app/api/compression/replay/route.ts`     | 2026-09-20        | live changed before the import |
| `src/lib/skills/containerProvider.ts`         | 2026-08-11        | live changed before the import |
| `tests/unit/vertex-media.test.ts`             | 2026-09-16        | live changed before the import |

Every live version predates the import, which reads as "the snapshot may be
newer". But the snapshot's commit is the _import_ commit, dated
2026-11-14 with the message "import committed tree of audit-snapshot-OmniRoute".
That date records when the copy was taken, not when the code was written, so a
months-old state copied yesterday produces the same reading as genuinely newer
work. The two cases are indistinguishable from dates and hashes alone.

Restoring on that evidence would be a coin flip against a live product: forward,
and unreviewed local work lands on OmniRoute; backward, and it reverts five
months of changes made after the snapshot's content was authored.

So no branch was pushed. `recover_blobs.py` builds one locally on request and
pushes nothing by default.

## What was done instead

All eight snapshots that hold content no live repository has are now preserved
under `refs/preserved/` in the registry, each verified ref-for-ref:

`audit-snapshot-OmniRoute`, `-AgilePlus`, `-tooling`, `-argis`, `-pheno`,
`-HexaKit`, `-hwLedger`, `-agentapi`.

`audit-snapshot-PhenoVCS` was not preserved because it is byte-identical to
`PhenoVCS`, which already is.

The divergent content is therefore durable and the decision is deferred rather
than guessed. Settling it needs one of:

- an author's recollection of whether that work was pushed;
- a bisect over OmniRoute's history for a commit whose tree contained these blob
  ids, which would date them exactly;
- a content review of 41 files, which is small enough to read.
