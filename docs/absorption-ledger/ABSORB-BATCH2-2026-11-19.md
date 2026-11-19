# Batch 2 absorption ledger, 2026-11-19

Source plan: `docs/absorption-ledger/ABSORB-PLAN-2026-11-19.md`.

Batch 2 is the six smallest repositories in the plan, 1,256 blobs total. All six were absorbed with `scripts/absorb_private.py <repo>` and independently verified with `scripts/prepare_deletion.py <repo>`, one at a time, in the order below. No repository or branch was deleted. No commits were made and nothing was pushed.

| Repository | Blobs per plan | Files absorbed | Refs | Commits | Verified N/M | DELETE-AUTHORISED | Bundle sha | Error |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| PhenoVCS | 133 | 133 exact | 1 | 1 | 133/133 files exact (registry tree) | yes | `90ad6b214889` | none |
| audit-snapshot-PhenoVCS | 133 | 133 exact | 2 | 2 | 133/133 files exact (registry tree) | yes | `0dfa7ae372c0` | none |
| phenoDesign-visual-production-v2 | 179 | 179 exact | 2 | 7 | 179/179 files | yes | `44b484ada836` | none |
| HarnessDesk | 249 | 249 exact | 80 | 145 | 249/249 files exact (registry tree) | yes | `9d2b946ef404` | none |
| Personal | 258 | 258 exact | 267 | 718 | 258/258 files exact (registry tree) | yes | `fa1ac2405daa` | none |
| zz-argis-extensions | 304 | 304 exact | 1 | 1 | 304/304 files exact (registry tree) | yes | `2d4ba373fac6` | none |

## Count agreement check

`absorb_private.py` and `prepare_deletion.py` agree on the file count for all six repositories:

- PhenoVCS: absorbed 133, verified 133/133
- audit-snapshot-PhenoVCS: absorbed 133, verified 133/133
- phenoDesign-visual-production-v2: absorbed 179, verified 179/179
- HarnessDesk: absorbed 249, verified 249/249
- Personal: absorbed 258, verified 258/258
- zz-argis-extensions: absorbed 304, verified 304/304

No disagreement between the two tools was observed. Note that the `phenoDesign-visual-production-v2` verifier line read `verified 179/179 files` without the `(registry tree)` suffix used by the other five; the numerator, denominator, and agreement with the absorbed count are unaffected.

All absorption runs ended `absorbed 1, blocked 0`. All verification runs ended `prepared 1, blocked 0`. No failures occurred, so no retries were needed. `DELETE-AUTHORISED` printed for every repository in both tools; this is a readiness signal only and no deletion was performed.

## Outcome

**6 of 6 batch 2 repositories are fully absorbed and independently verified.**

`audit-snapshot-tooling` (22,552 blobs) was not touched. It belongs to batch 4. No batch 3 or batch 4 work was started.
