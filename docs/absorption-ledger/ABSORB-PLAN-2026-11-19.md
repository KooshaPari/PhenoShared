# Absorption plan sizing, 2026-11-19

This plan sizes the 22 private repositories still awaiting absorption. The five already handled or in progress (`cvp-fixture`, `StealthStartup`, `harness-ops`, `dagrun`, `audit-system`) are excluded.

## Method

Measurements were taken on 2026-11-19 from GitHub metadata only:

- `gh api repos/KooshaPari/<repo> --jq ".default_branch, .size"` supplied the default branch and repository size in KB.
- `gh api repos/KooshaPari/<repo>/git/trees/<branch>?recursive=1 --jq "[.tree[] | select(.type==\"blob\")] | length"` supplied the blob count.
- Every recursive tree response reported `truncated: false`, so all blob counts below are complete rather than partial.

No repository was cloned, no absorption or deletion scripts were run, and no registry or Git state was changed.

## Repositories sorted by blob count ascending

| Repository | Blobs | Repo size KB | Default branch | Truncated |
| --- | ---: | ---: | --- | --- |
| PhenoVCS | 133 | 122 | main | no |
| audit-snapshot-PhenoVCS | 133 | 166 | main | no |
| phenoDesign-visual-production-v2 | 179 | 2,823 | main | no |
| HarnessDesk | 249 | 778 | main | no |
| Personal | 258 | 15,100 | main | no |
| zz-argis-extensions | 304 | 1,226 | audit/snapshot-20260916 | no |
| audit-snapshot-hwLedger | 326 | 691 | main | no |
| zz-HexaKit | 358 | 1,652 | audit/snapshot-20260916 | no |
| phenoreg-browser-audit | 367 | 1,659 | main | no |
| phenotype-landing | 550 | 2,522 | main | no |
| BytePort | 680 | 237,377 | main | no |
| zz-aa-dep-AirLock | 775 | 43,121 | main | no |
| audit-snapshot-argis | 1,613 | 9,413 | main | no |
| argis-extensions-preserved-20261114 | 1,628 | 9,406 | main | no |
| audit-snapshot-agentapi | 2,605 | 11,706 | main | no |
| audit-snapshot-AgilePlus | 2,979 | 8,261 | main | no |
| cliproxyapi-plusplus | 3,129 | 11,802 | main | no |
| audit-snapshot-HexaKit | 3,308 | 12,526 | main | no |
| chatta | 4,521 | 69,998 | main | no |
| audit-snapshot-pheno | 8,876 | 27,402 | main | no |
| audit-snapshot-OmniRoute | 13,989 | 89,650 | main | no |
| audit-snapshot-tooling | 22,552 | 218,859 | main | no |

## Total and dominant repository

Across the 22 repositories the blob counts sum to **69,512**. `audit-snapshot-tooling` dominates that total with **22,552 blobs**, about **32.44%** of all files; the next largest, `audit-snapshot-OmniRoute`, has 13,989 blobs.

The combined GitHub repository size is 776,260 KB. BytePort has the largest reported size (237,377 KB) despite having only 680 blobs, which reinforces that file count and storage size are different measures.

## Proposed batching

Batches are ordered strictly by blob count ascending, using the table above.

- **Batch 2, next 6 smallest (1,256 blobs total):** PhenoVCS, audit-snapshot-PhenoVCS, phenoDesign-visual-production-v2, HarnessDesk, Personal, zz-argis-extensions.
- **Batch 3, following 6 (3,056 blobs total):** audit-snapshot-hwLedger, zz-HexaKit, phenoreg-browser-audit, phenotype-landing, BytePort, zz-aa-dep-AirLock.
- **Batch 4, remainder (65,200 blobs total):** audit-snapshot-argis, argis-extensions-preserved-20261114, audit-snapshot-agentapi, audit-snapshot-AgilePlus, cliproxyapi-plusplus, audit-snapshot-HexaKit, chatta, audit-snapshot-pheno, audit-snapshot-OmniRoute, audit-snapshot-tooling.

## Caveat

**Blob count measures files, not difficulty.** A repository with one huge binary and a repository with 20,000 small text files can cost very different amounts to absorb, so these batches are a first-order ordering by file count rather than a forecast of effort. Repository size, content type, conflict density, history, and target placement also affect absorption cost and should be checked before execution.
