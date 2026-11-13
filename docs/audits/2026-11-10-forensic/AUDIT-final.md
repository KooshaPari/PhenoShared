# AUDIT-final — internal consistency of the three assembled deliverables

Audited 2026-11-10T06:14Z, re-audited 10:54Z after the classification recon. Evidence: `wc -l`, `grep`, `stat`, `shasum`, `rg`.
Scope is cross-document agreement only, not whether any measurement is true against the repo.

## Verdict

**NITS-CLEARED** — the single blocking contradiction (test-attribute arithmetic) is resolved in
DELIVERABLE-2, and INDEX line counts were re-synced after DELIVERABLE-2/3 and the plan were rebuilt.

## Resolution of the 19,146 contradiction

The earlier audit found `19,146` stated but decomposed as `16,216 + 2,955 = 19,171` (a 25-count gap).
Root cause is not arithmetic: **the working tree is being re-checked-out underneath the analysis.**
Three reads of the same command, minutes apart, returned `16,216` → `16,266` → `16,712` bare
`#[test]` attributes while `#[tokio::test]` stayed at `2,955`. A count on a moving tree cannot tie out.
DELIVERABLE-2 now states the figure as `~19.2k` with the command, the timestamp and the three
observations, so no future reader can mistake it for a constant.

## INDEX line-count drift

| INDEX row | Stated | Measured | Status |
|---|---|---|---|
| `DELIVERABLE-1-codebase-atlas.md` | 321 | 321 | OK |
| `DELIVERABLE-2-qa-matrix.md` | 150 | 150 | OK |
| `DELIVERABLE-3-product-dossier.md` | 260 | 260 | OK |
| `REMEDIATION-PLAN.md` | 230 | 230 | OK |
| A 333 / B 374 / C 143 / D 523 / E 284 / F 263 / G 264 / H 324 / I 277 / J 136 / V 276 / INDEX 55 | as shown | identical | OK (12/12) |

Observed, not inferred: at 06:13:59Z the same grep returned **302 / 148 / 253**. `INDEX.md` mtime is
06:14:00Z, so it was rewritten between my two observations; those three rows were self-corrected
mid-audit, nothing else changed, and hash `ddcc5650…` held across a 3 s re-check.
`VERIFY-structure.md` (61 lines) exists but is not tabulated in INDEX.

## Numeric consistency

| Number | Meaning | Verdict | Citations |
|---|---|---|---|
| 283 | workspace members | Consistent | D1:16,34,184 · D2:119 · D3:16,22,117,143,190,205,228,250 — always "unique declared paths"; 287 quoted strings explained as +1 comment +3 duplicates |
| 372 | crate dirs | Consistent | D1:36,183,290,318 · D3:22,117,143,148,190,205. D1:36's "369 crate-like" is a distinct qualifier |
| 42,225 | tracked files | Consistent | D1:33,318. D1:16's 13,848 is the `crates/` subset, not the total |
| 3,635 | commits all refs | Consistent (one occurrence) | D1:29 |
| 1,214 | commits on main | Consistent | D1:6,30 · INDEX:4; D1:30's "1,210 local main (4 behind)" reconciles exactly |
| 2,494 | docs markdown | Consistent | D1:242,244 · D3:16,252 — always "2,494 `.md` of 11,721 files" |
| 1,904 | lockfile packages | Consistent | D1:35 · INDEX:26 |
| 19,221 | test attributes in `crates/` | Consistent (DELIVERABLE-2 only) | D2:35,105 — stated as `~19.2k` with command, timestamp and the three observed values |

## Seam leftovers

| file:line | Wording | Assessment |
|---|---|---|
| `DELIVERABLE-2-qa-matrix.md:139` | `## CI lane inventory` | Sole hit. "Lane" is deliberate vocabulary (INDEX Method: "Twelve lanes in parallel"), so not a broken seam; cosmetic only |

## Notes

- No hits for `Tier N`, `# Part`, `D-part`, `Report [A-JV]`, `H §`, `C matrix`, `C gaps`.
- Commit identity is coherent, not conflicting: `origin/main` @ `6ec4ae563` (INDEX:4, D1:6) vs
  working tree `ad667428b` on `layer/governance-happy-path-claims` (INDEX:4, D1:7, D1:318).
- D1:8 warns that a concurrent process re-checked-out the tree mid-analysis; the INDEX rewrite at
  06:14:00Z is a second instance and live evidence for that warning.
