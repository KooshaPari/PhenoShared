# Absorption ledger: batch 3, 2026-11-19

Batch 3 consists of the six repositories defined by measurement in `ABSORB-PLAN-2026-11-19.md`, excluding the six already-completed batch 2 repositories. `audit-snapshot-tooling` was not in batch 3 and was not touched. No repository or branch was deleted. Batch 4 was not started.

**Real finding:** `BytePort` has a count mismatch. `absorb_private.py` reported `absorbed 680 files exact`, while `prepare_deletion.py` reported `verified 676/680 files`. Both numbers are recorded below verbatim. No bundle sha was generated for BytePort because its history was 231.8 MB, reported as too big for a bundle.

`zz-aa-dep-AirLock` first absorb attempt failed with an exact push rejection; one allowed retry succeeded. The first-attempt error is recorded below.

Total reported files absorbed across the six repositories, from absorb output: 3,056. Verified-file numerators total 3,052 because of the BytePort mismatch.

| repository | blobs per plan | files absorbed | refs | commits | verified N/M | DELETE-AUTHORISED | bundle sha | errors |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| audit-snapshot-hwLedger | 326 | 326 | 2 | 2 | verified 326/326 files exact (registry tree) | yes | `b168944a72fa` | none |
| zz-HexaKit | 358 | 358 | 1 | 1 | verified 358/358 files exact (registry tree) | yes | `e6560c54a986` | none |
| phenoreg-browser-audit | 367 | 367 | 13 | 114 | verified 367/367 files exact (registry tree) | yes | `2bdf91a93ba2` | none |
| phenotype-landing | 550 | 550 | 4 | 5 | verified 550/550 files exact (registry tree) | yes | `ea2772a1a9c9` | none |
| BytePort | 680 | 680 | 5 | 569 | **verified 676/680 files** | yes | none (history 231.8 MB, too big for a bundle) | **COUNT MISMATCH: absorb reported 680 files exact; verification reported 676/680 files** |
| zz-aa-dep-AirLock | 775 | 775 | 211 | 1017 | verified 775/775 files exact (registry tree) | yes | `1f4ff6c03827` | first absorb attempt failed: `REFUSED   push tree failed: To https://github.com/KooshaPari/PhenoRegistry.git` / ` ! [rejected]          39e3e91aac5287aad31ee66d34f3e464423c7c1e -> main (fetch first)` / `error: failed`; one retry succeeded, absorbed 775 files exact, 211 refs, 1017 commits |

## Validation performed

- `python3 -u scripts\absorb_private.py <repo>` was run once per repository, sequentially, with one allowed retry only for `zz-aa-dep-AirLock`.
- `python3 -u scripts\prepare_deletion.py <repo>` was run once per repository, sequentially, as independent verification.
- Counts agreed exactly for five repositories. The BytePort mismatch above is intentionally not smoothed over.
- No deletions, no batch 4 work, and no work on `audit-snapshot-tooling`.
