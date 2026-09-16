# Consolidation 20 Session Overview

Date: 2026-07-22
Spec slug: `ecosystem-consolidation-20-20260722`
Execution lane: T, with preservation sublane

## Goal

Produce an evidence-gated disposition for exactly 20 repositories without deleting, force-pushing,
rewriting history, or mutating fork remotes. All 20 repositories existed and were unarchived at
intake; docket #1 has since completed its authorized preservation transaction.

## Repository Set

1. `AgilePlus-recovery-20260714` (now `zz-archive-AgilePlus-recovery-20260714`)
2. `AgilePlus-recovery-evidence-20260714`
3. `agileplus-spec-harmonizer-tool-archive-2026-07-14`
4. `4sgm-archive`
5. `phenotype-registry-archive`
6. `phenotype-org-audits-archive2`
7. `PhenoRuntime-archive`
8. `Parpoura-archive`
9. `ResilienceKit-archive`
10. `phenoResearchEngine-archive`
11. `home-recovery-2026-07-archive`
12. `phenotype-monorepo-state-archive`
13. `phenotype-shared-archive`
14. `agent-user-status-archive`
15. `PriceyApp`
16. `Quillr`
17. `Stashly`
18. `router-docs`
19. `template-commons`
20. `phenotype-teamcomm`

## Session Outcome

Docket #1 is `ARCHIVED-PRESERVED / complete`: `AgilePlus-recovery-20260714` was renamed to
`zz-archive-AgilePlus-recovery-20260714` and archived without deletion. The remaining 19
repositories retain their HOLD or VERIFY-ONLY dispositions, preserving uncertain or absorbed
history while required evidence is completed.

Tranche 2 audited six VERIFY-ONLY candidates. The harmonizer archive is technically parity-proven
but remains on policy HOLD because the concurrent preservation ledger sets `archive=false`. The
other five remain HOLD because one or more refs or parent-boundary proofs are missing.

Tranche 3 audited six branch-heavy archives containing 49 heads. `phenotype-org-audits-archive2`
is parity-proven but joins the shared POLICY-HOLD; the other five remain HOLD with missing refs.

Tranche 4 completed deep classification for the final seven. Recovery evidence, Stashly, and
phenotype-teamcomm remain standalone; PriceyApp remains an untouched fork; Quillr, router-docs,
and template-commons remain HOLD pending complete ref mapping or additive import.
