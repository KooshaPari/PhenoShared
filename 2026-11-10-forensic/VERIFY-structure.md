# VERIFY-structure.md

Structural audit of DELIVERABLE-1/2/3 (read-only). Scope: structure only. No file was modified except this report.

## Verdict

COMPLETE-WITH-FIXES

14 findings. Checks 1, 2, 4 and 6 pass clean. Check 3 passes with two verified-benign raw-pipe artifacts. Check 5 fails: internal analysis-lane, part-numbering and source-report vocabulary leaks into all three deliverables, and DELIVERABLE-3 embeds an unresolved internal adjudication that contradicts its own headline number.

## Findings

| Check | File | Line | Problem | Fix |
|---|---|---|---|---|
| 5 seam leakage | DELIVERABLE-1-codebase-atlas.md | 10 | Method row exposes internal parallel-lane structure: `12 parallel forensic lanes + independent claim verification` | Rewrite harness-agnostically, e.g. `static structural inspection + independent claim re-measurement` |
| 5 seam leakage | DELIVERABLE-1-codebase-atlas.md | 11 | `counts verified by an independent lane` exposes the analysis-lane structure | Rewrite as `counts independently re-measured from the working tree` |
| 5 seam leakage | DELIVERABLE-2-qa-matrix.md | 22 | `Not counted in part 1 (see PII sweep / cosign rows in C source)` leaks internal part numbering plus an internal source-file id (`C`) | Restate self-contained: `Not counted above (see PII sweep and cosign rows in the control matrix)` |
| 5 seam leakage | DELIVERABLE-2-qa-matrix.md | 51 | `No CI run was executed in either source lane` leaks the source-lane structure | Rewrite as `No CI run was executed for this matrix` |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 7 | Front matter confidence field says `no build was run in this lane` | Rewrite as `no build was run for this dossier` |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 21 | `no build ran in this lane` | Rewrite as `no build was run` |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 222 | `no build was run in lane D` names an internal lane id outright | Rewrite as `no build was run for this dossier` |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 186 | Evidence cell cites an internal report instead of the repo: `287 declared workspace members (V measured 239)` | Cite the repo path (`Cargo.toml` workspace `members`) rather than an internal report id |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 187 | Evidence cell cites internal reports: `V (B)` | Cite repo-relative paths (`Cargo.toml`, `ls crates`, `README.md:17`) |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 231-238 | Section `## Appendix: source map` names internal artifacts `D-product-dossier.md`, `V-verification.md`, `Reports A, B, C, E, F, G, H, I, J`, and `evidence base for D` | Delete the section, or replace the Input column with repo-relative paths only |
| 5 seam leakage | DELIVERABLE-3-product-dossier.md | 239-243 | Section `## Verification note` narrates internal adjudication: `V confirmed`, `V mismatched / corrects D`, `H's 287 rejected, J's 239 upheld`, `must not be propagated` | Remove the section; fold any surviving correction into the body text |
| 3/5 content conflict | DELIVERABLE-3-product-dossier.md | 186 vs 241-243 | The dossier leads with `287 declared workspace members` while its own note says that number is contradicted (239) and `must not be propagated`. The deliverable ships a number it flags as unusable | Reconcile to one cited value; if unverifiable from the repo, mark the cell `UNKNOWN` rather than stating 287 |
| 3/4 undefined taxonomy | DELIVERABLE-1-codebase-atlas.md | 106, 116, 170 | LOC-tier ids `Tier 3` and `Tier 5` are used with no legend anywhere in the file. The bands live only in an internal source report, so a reader of D1 alone cannot resolve them | Add a one-line tier legend (e.g. `Tier 3 = 5k-10k LOC, Tier 5 = <2.5k LOC`), or inline the LOC band |
| 3/4 undefined taxonomy | DELIVERABLE-3-product-dossier.md | 18, 57 | `Tier 0 dispatch spine` / `Tier 0 dispatch facade` uses a tier id that has no definition in this file and does not exist in the internal source it appears to come from | Add a legend or replace with a descriptive phrase (`the foundation dispatch spine`) |

### Check 5 hit triage (every hit, with file:line)

Real leak (fix required): DELIVERABLE-1:10, DELIVERABLE-1:11, DELIVERABLE-2:22, DELIVERABLE-2:51, DELIVERABLE-3:7, DELIVERABLE-3:21, DELIVERABLE-3:222, DELIVERABLE-3:186, DELIVERABLE-3:187, DELIVERABLE-3:231-238, DELIVERABLE-3:239-243.

False positive (repo-domain vocabulary, no change): DELIVERABLE-1:208 and DELIVERABLE-1:263 (matched `D-part` inside `third-party`), DELIVERABLE-2:95 and DELIVERABLE-2:137 (`scanner lanes` / `CI lane inventory` refer to PhenoShared's own CI workflows), DELIVERABLE-3:91, DELIVERABLE-3:100, DELIVERABLE-3:158 (matched `lane` inside `plane`, i.e. PhenoFabric plane).

No hits for `worker` or `seam` in any of the three files.

## Passed

- Check 1, code fences balanced: DELIVERABLE-1, DELIVERABLE-2 and DELIVERABLE-3 each contain exactly 2 fence markers (1 opener, 1 closer), all even. The unanchored backtick-fence count equals the anchored count in each file (2 = 2), so no indented fence was missed by the `^```' test.
- Check 2, mermaid blocks closed: DELIVERABLE-1 opens ` ```mermaid ` at line 211 and it is closed by the fence at line 235. DELIVERABLE-3 opens ` ```mermaid ` at line 93 and it is closed by the fence at line 109. DELIVERABLE-2 contains no mermaid block; its only fenced region is a plain ASCII tree opened at line 92 and closed at line 109.
- Check 3, table column consistency: zero real mismatches across all tables in all three files. Two rows showed a raw pipe count of 5 against a header count of 4 (DELIVERABLE-3:33 and DELIVERABLE-3:140); both were traced to a single escaped pipe inside a cell (`git log --reverse \| head -1` and `PhenoShared\|KooshaPari/PhenoShared`). Re-running the check with escaped pipes stripped reported no mismatch, so all tables are structurally 3-column consistent.
- Check 4, duplicate headings: none. No heading text repeats within DELIVERABLE-1, DELIVERABLE-2 or DELIVERABLE-3.
- Check 6, front matter: DELIVERABLE-2 is fenced by `---` at lines 1 and 6; DELIVERABLE-3 is fenced by `---` at lines 1 and 8. DELIVERABLE-1 has no front matter (starts at the H1), which is in scope only as a not-applicable case. The `commit:` field is byte-identical where present: DELIVERABLE-2:3 and DELIVERABLE-3:4 both read `commit: origin/main@6ec4ae563 (working tree observed at ad667428b)`. DELIVERABLE-1 carries the same pair of SHAs in its metadata table (`6ec4ae563`, `ad667428b`), so the commit reference is consistent across all three files.

## Commands run

1. `ls -la` + per-file `grep -c '^```'` fence counts + `wc -l` on the three deliverables.
2. `head -12` on each deliverable (front matter inspection).
3. `grep -n '^```'` and `grep -n '```mermaid'` on each deliverable (fence and mermaid line positions).
4. `grep -n -i -E 'part [0-9]|^# Part|LANE|D-part|worker|seam'` across the three deliverables (check 5, first pass).
5. `grep -n -i -o -E 'part [0-9]+|D-part|[a-z]*lane[a-z]*|[a-z]*seam[a-z]*|[a-z]*worker[a-z]*'` to identify which alternative matched each hit, plus `grep -n '^commit:'` and `head -3` front-matter delimiters.
6. `awk` table-block pipe-count comparison with fence-region skipping across all three files (reported global `NR`; re-derived as per-file `FNR` in step 7).
7. `awk` duplicate-heading detector (heading text -> count + line numbers) per file, plus `grep -n '^#\{1,6\}[ \t]'` full heading listing for all three files.
8. `awk` mismatch-detail pass emitting the header line and offending row for each table mismatch, plus `sed -n '90,94p;106,110p'` on DELIVERABLE-2 to confirm fence orientation.
9. `grep -o '```' | wc -l` (unanchored fence parity), an `awk` escaped-pipe-stripped table recheck, and `sed -n '89,92p'` on DELIVERABLE-2.
10. `grep -n -E 'A-git-history|...|part [0-9]'` for internal source-file and lane references, plus `sed -n '231,243p'` (DELIVERABLE-3 appendix) and `sed -n '10,11p'` (DELIVERABLE-1 method rows).
11. `grep -n 'Tier'` on DELIVERABLE-1/DELIVERABLE-3 and on the internal source report, plus a broad `\bV\b|\bD\b|Reports A` scan of DELIVERABLE-3.
12. `grep -n 'Tier 0'` and a legend/definition search in DELIVERABLE-1 to confirm the tier taxonomy is undefined in the deliverable.

All commands were read-only. No git command was run. No file other than this report was created or modified.
