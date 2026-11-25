# Absorption ledger: batch 4, 2026-11-19

Batch 4 absorbed the six smallest eligible repositories outstanding after batches 1-3 and the earlier individually handled repositories. `audit-snapshot-tooling`, `audit-snapshot-OmniRoute`, and `audit-snapshot-pheno` were deliberately excluded from this batch. No repository or branch was deleted, and batch 5 was not started.

The repositories were run sequentially: `absorb_private.py <repo>` followed immediately by `prepare_deletion.py <repo>` for independent verification. The independent verifier is authoritative on pass/fail.

| Repository | Blobs in plan | Absorbed line | Verified line | Result |
| --- | ---: | --- | --- | --- |
| audit-snapshot-argis | 1,613 | `absorbed  1613 of 1613 files (0 withheld to registry, 0 excluded binary), 1 refs, 1 commits` | `verified 1613/1613 files exact (registry tree)` | pass |
| argis-extensions-preserved-20261114 | 1,628 | `absorbed  1628 of 1628 files (0 withheld to registry, 0 excluded binary), 1 refs, 1 commits` | `verified 1628/1628 files exact (registry tree)` | pass |
| audit-snapshot-agentapi | 2,605 | `absorbed  2605 of 2605 files (0 withheld to registry, 0 excluded binary), 2 refs, 2 commits` | `verified 2605/2605 files exact (registry tree)` | pass |
| audit-snapshot-AgilePlus | 2,979 | `absorbed  2979 of 2979 files (0 withheld to registry, 0 excluded binary), 2 refs, 2 commits` | `verified 2979/2979 files exact (registry tree)` | pass |
| cliproxyapi-plusplus | 3,129 | `absorbed  3083 of 3129 files (0 withheld to registry, 46 excluded binary), 2 refs, 2 commits` | `verified 3129/3129 files exact (registry tree)` | pass; absorb count was wrong |
| audit-snapshot-HexaKit | 3,308 | `absorbed  3302 of 3308 files (0 withheld to registry, 6 excluded binary), 1 refs, 1 commits` | `verified 3308/3308 files exact (registry tree)` | pass; absorb count was wrong |

For cliproxyapi-plusplus and audit-snapshot-HexaKit, the first version of the honest-count fix over-counted excluded binaries by using a filename-suffix heuristic. The independent verifier caught it: `3129/3129` and `3308/3308` exact in the registry tree prove no source file was omitted. The reported 46 and 6 excluded binaries were false counts, not real exclusions.

Counting rule for future batches: **withheld means routed to registry by the router; excluded means present in source but not written; anything else is a tool bug, and verify M/M always wins.**

`absorb_private.py` was corrected to derive counts from actual state: `withheld = set(want) & direct_paths`, `written = set(got) | withheld`, `excluded = set(want) - written`, and `covered = len(set(want) & written)`. The prior suffix list was removed.

Read-only reporting replay after the correction, against both known-bad cases:

```text
cliproxyapi-plusplus: absorbed 3129 of 3129 files (0 withheld to registry, 0 excluded binary)
audit-snapshot-HexaKit: absorbed 3308 of 3308 files (0 withheld to registry, 0 excluded binary)
```

Before/after evidence for the corrected count logic:

| Repository | Before | After |
| --- | --- | --- |
| cliproxyapi-plusplus | `3083 of 3129 files (0 withheld to registry, 46 excluded binary)` | `3129 of 3129 files (0 withheld to registry, 0 excluded binary)` |
| audit-snapshot-HexaKit | `3302 of 3308 files (0 withheld to registry, 6 excluded binary)` | `3308 of 3308 files (0 withheld to registry, 0 excluded binary)` |

## Cumulative absorbed repository count

Derived from the batch ledgers' own per-batch row counts:

| Batch | Ledger | Repositories with rows |
| --- | --- | ---: |
| 1 | `ABSORB-BATCH1-2026-11-19.md` | 5 |
| 2 | `ABSORB-BATCH2-2026-11-19.md` | 6 |
| 3 | `ABSORB-BATCH3-2026-11-19.md` | 6 |
| 4 | `ABSORB-BATCH4-2026-11-19.md` | 6 |

Total: **23 repositories absorbed, 0 deleted**.

Deleted repositories in this batch: none. Giants deferred to their own sessions: `audit-snapshot-tooling`, `audit-snapshot-OmniRoute`, `audit-snapshot-pheno`.
