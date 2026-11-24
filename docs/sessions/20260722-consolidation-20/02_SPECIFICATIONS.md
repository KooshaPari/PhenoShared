# Ecosystem Consolidation 20 Specification

Slug: `ecosystem-consolidation-20-20260722`

## Scope

Govern exactly the 20 repositories listed in `00_SESSION_OVERVIEW.md` through lane T and its
preservation sublane. This specification records evidence, classification, and the single completed
rename-and-archive preservation transaction authorized for docket #1.

## Functional Requirements

- FR-01: Track all and only the exact 20 repositories in the session overview.
- FR-02: Record that all 20 existed and were unarchived at intake, and that docket #1 is now
  archived under its preservation name.
- FR-03: Keep the `PriceyApp` fork untouched. Treat `router-docs` and `template-commons` as private
  non-forks whose incomplete absorption evidence blocks mutation.
- FR-04: Record that only `AgilePlus-recovery-20260714` reached READY because its sole head
  `recovery/isolated-20260714` is exact commit `0aafdf9692c11abb6e426f36857aeec7bb6cd942`, and
  canonical AgilePlus contains that exact commit and tree
  `eb82ced16353219d85aa83c925819ae48cb36c16` with the exact head.
- FR-04a: Record the completed immediate preflight, rename to
  `zz-archive-AgilePlus-recovery-20260714`, and archive; status is
  `ARCHIVED-PRESERVED / complete`, never deleted.
- FR-04b: Keep `AgilePlus-recovery-evidence-20260714` on HOLD as unique preservation evidence.
- FR-05: Place `phenotype-registry-archive`, `phenotype-org-audits-archive2`,
  `PhenoRuntime-archive`, `ResilienceKit-archive`, and `phenotype-shared-archive` on HOLD.
- FR-06: Place `Stashly` and `phenotype-teamcomm` on HOLD until their contradictions are resolved.
- FR-07: Classify `agileplus-spec-harmonizer-tool-archive-2026-07-14`, `4sgm-archive`,
  `Parpoura-archive`, `phenoResearchEngine-archive`, `home-recovery-2026-07-archive`,
  `phenotype-monorepo-state-archive`, and `agent-user-status-archive` as VERIFY-ONLY.
- FR-08: Classify `Quillr` as VERIFY-ONLY with tombstone evidence required.
- FR-09: Classify `router-docs` as VERIFY-ONLY for absorption into OmniRoute.
- FR-10: Classify `template-commons` as VERIFY-ONLY for absorption into phenokits.
- FR-11: Place `PriceyApp` on HOLD as an untouched fork.
- FR-12: Record exactly one completed READY action for `AgilePlus-recovery-20260714`; no current
  READY action remains. No other repository may become READY until SHA and content parity pass.
- FR-13: Resolve actual default branches; do not assume `main` for the eight non-`main` sources.
- FR-14: Correct Batch A placement errors before using its evidence.
- FR-15: Use partial bare clones under current disk constraints.
- FR-16: Never delete repositories, force-push, rewrite history, or mutate the PriceyApp fork.
- FR-17: Preserve the completed docket #1 metadata: private nonfork, default branch
  `recovery/isolated-20260714`, one branch, zero tags, unchanged
  `pushed_at=2026-07-16T00:20:23Z`, exact commit
  `0aafdf9692c11abb6e426f36857aeec7bb6cd942`, and exact tree
  `eb82ced16353219d85aa83c925819ae48cb36c16`; canonical exact ref/commit/tree remain unchanged and
  the old name redirects.
- FR-18: Record tranche-2 ref evidence for the six audited recovery archives; do not infer parity
  from a canonical descendant or selective content absorption.
- FR-19: Keep the harmonizer archive on POLICY-HOLD despite exact parity while the concurrent
  preservation manifest sets `archive=false`.
- FR-20: Keep the other five tranche-2 candidates on HOLD until every missing ref and parent
  boundary is preserved.
- FR-21: Treat `artifacts/tranche-2-ref-evidence.tsv` as the authoritative tranche-2 ref ledger.
- FR-22: Record all 49 heads across the six tranche-3 candidates and preserve every candidate whose
  canonical parent lacks a complete namespaced ref set.
- FR-23: Keep `phenotype-org-audits-archive2` on POLICY-HOLD despite seven-of-seven exact parity
  while the concurrent preservation manifest sets `archive=false`.
- FR-24: Treat `artifacts/tranche-3-ref-evidence.tsv` as the authoritative 49-head tranche-3 ledger.
- FR-25: Complete repository-level disposition for the final seven without mutating PriceyApp or
  any source that lacks a complete preservation map.
- FR-26: Keep recovery evidence private and standalone because raw Git evidence is sensitive by
  construction and is not reducible to canonical refs.
- FR-27: Keep Stashly and phenotype-teamcomm standalone; keep Quillr, router-docs, and
  template-commons on HOLD pending their named ref/boundary gates.

## Binary Acceptance Criteria

- [x] The governed set matches the exact 20 docket entries, with no additions or omissions.
- [x] Docket #1 has a verified post-transaction evidence record; the remaining 19 retain their
  intake evidence and HOLD or VERIFY-ONLY classifications.
- [x] Every HOLD repository remains mutation-blocked.
- [x] Every VERIFY-ONLY repository remains mutation-blocked pending its named proof.
- [x] Exactly one READY action completed for `AgilePlus-recovery-20260714`; all other repositories
  remain HOLD or VERIFY-ONLY.
- [x] The completed record includes the sole head `recovery/isolated-20260714`, exact commit
  `0aafdf9692c11abb6e426f36857aeec7bb6cd942`, and exact tree
  `eb82ced16353219d85aa83c925819ae48cb36c16` in canonical AgilePlus with the exact head.
- [x] Immediate preflight passed; the source was renamed to
  `zz-archive-AgilePlus-recovery-20260714` and archived, never deleted.
- [x] The archived source is private, nonfork, defaulted to `recovery/isolated-20260714`, with one
  branch, zero tags, unchanged `pushed_at`, and an old-name redirect.
- [x] `AgilePlus-recovery-evidence-20260714` remains HOLD as unique preservation evidence.
- [ ] SHA parity and content parity are independently recorded for any additional READY candidate.
- [x] No remote mutation occurred beyond the authorized docket #1 rename and archive; no deletion,
  force-push, or history rewrite occurred.
- [x] The PriceyApp fork was untouched; router-docs and template-commons were correctly reclassified
  as non-forks and were not mutated.
- [ ] Batch A placement errors and all eight non-`main` defaults are explicitly reconciled.
- [ ] Evidence collection stays within the partial-bare-clone disk policy.
- [x] Tranche 2 records all 16 source heads and the single source tag across its six candidates.
- [x] Exact harmonizer head/tag commit and tree parity is independently verified in AgilePlus.
- [x] No tranche-2 remote mutation occurred; the preservation manifest policy remains authoritative.
- [x] Every tranche-2 ref has an explicit commit, tree, and parent result in the TSV evidence ledger.
- [x] Tranche 3 classifies all six candidates and all 49 source heads without remote mutation.
- [x] The only tranche-3 parity-proven source remains policy-blocked; five evidence holds remain.
- [x] Every tranche-3 head has an explicit ref, commit, tree, and parent result in the TSV ledger.
- [x] All 20 docket repositories now have a deep disposition backed by current remote evidence.
- [x] The final seven were classified without remote mutation or exposure of sensitive evidence.
