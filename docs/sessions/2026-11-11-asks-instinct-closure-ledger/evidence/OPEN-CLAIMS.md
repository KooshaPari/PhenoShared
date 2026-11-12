# Open-Claims Ledger — asks/instinct closure (PhenoShared)

States are ordered: `change_made` < `integrated` < `workflow_validated` < `outcome_delivered` < `operator_gated` < `withdrawn`. Each row carries the highest state the cited evidence supports; operator-gated items cannot be closed by an agent and their next step is addressed to the operator. A withdrawn figure is retracted and says what replaced it (or that nothing did). Rows marked `DEFECT: no next step` have no executable closure path.

| id | claim (one line, with number if it has one) | state | evidence that supports the state | ONE next step | exact command / file check that proves it done |
|---|---|---|---|---|---|
| G1.1 | Fresh unredacted Dot export (362 of 460 human bodies redacted on disk) | operator_gated | CLOSURE-LEDGER §2 G1.1; no on-disk substitute | Operator obtains export; record MANIFEST | `test -s .../exports/dot.MANIFEST.json` |
| G1.2 | Dot/GPT records after 2026-10-30 (latest user record 2026-10-30T23:57:06Z) | operator_gated | CLOSURE-LEDGER §2 G1.2 | Operator exports; record manifest | `ls exports/` shows `.MANIFEST.json` |
| G1.3 | Official OpenAI `conversations.json` | operator_gated | CLOSURE-LEDGER §2 G1.3; none on host | Operator exports | `test -s ~/Downloads/conversations.json && python3 -c "import json;d=json.load(open('$HOME/Downloads/conversations.json'));print(len(d))"` → >0 |
| G1.4 | Gemini Google Takeout | operator_gated | CLOSURE-LEDGER §2 G1.4; no `~/.gemini` state | Operator exports | file exists, parses, count>0 |
| G2 | Occurrence preservation (every message once, no unexplained remainder) | change_made | CLOSURE-LEDGER §2 G2; mined artifacts exist; `verify_occurrences.py` missing (§2 G2 blocker) | Implement verifier, emit occurrence ledger, run it | `python3 mined/scripts/verify_occurrences.py --expect-remainder 0` → `unaccounted_occurrences=0` |
| G3 | Provenance preservation (`source_ref` resolves) | change_made | CLOSURE-LEDGER §2 G3; `reg_provenance` has no `resolved` column | Add `resolved` column; write flags | `sqlite3 "$LEDGER" "select count(*) from reg_provenance where resolved=0;"` → 0 |
| G4 | Attribution audit (`unknown=0`) | change_made | CLOSURE-LEDGER §2 G4; `occurrence_attribution` table absent (sqlite_master count 0) | Create table + classifier + `ATTRIBUTION-AUDIT.md` | `sqlite3 "$LEDGER" "select count(*) from occurrence_attribution where attribution='unknown';"` → 0 |
| G5.a | `reg_provenance.source_ref` resolves on disk (claimed 0/98) | change_made | CLOSURE-LEDGER §2 G5.a; VERDICT §3g confirms 0/98 LOST (10 roots searched) | Accept loss or recover; repair against real schema | G5 closure query all-zero |
| G5.c | Distinct operator messages behind 2,259 asks (claimed 1,843) | change_made | CLOSURE-LEDGER §2 G5.c; UNVERIFIED, no repro query | Verify against `reg_utterances` join | reproducing query quoted |
| G5.d | Unpromoted user utterances (claimed 805) | change_made | CLOSURE-LEDGER §2 G5.d; UNVERIFIED; VERDICT §2: `reg_utterances` exists (name mismatch, not absence) | Re-derive against `reg_utterances` | reproducible count |
| G5.e | Sourceless asks (7: ASK-000345, 000637, 000664, 001844, 002254, 002255, 002256) | change_made | CLOSURE-LEDGER §2 G5.e; VERDICT §3g three agreeing signals | Link to proven occurrence or mark `sourceless` | `sourceless_asks=0` in G5 query |
| G5.f | Verbatim-verified quotes baseline (claimed 2,134) | change_made | CLOSURE-LEDGER §2 G5.f; VERDICT counts 2,132 distinct quote entries; 2,235 anchored | Preserve baseline; re-measure | `verified_quotes >= 2134` |
| G6 | Coverage reconciliation matrix (one row per source) | change_made | CLOSURE-LEDGER §2 G6; `reconcile_coverage.py` missing; partial: `coverage_consistency.py` → 4.4% / 9.65% (§2 G6 partial) | Implement `reconcile_coverage.py` + `COVERAGE-MATRIX.md` | `python3 ... --expect-unexplained 0` → exit 0 |
| G7 | SessionLedger migration (doubly gated) | operator_gated | CLOSURE-LEDGER §2 G7; evidence gate + acceptance gate both NOT_RUN; `ask_research_ledger.py` lacks flags | Prepare dry-run projection; do not write until G2-G6 PASS and G8 | `cargo test -p session-ledger`; dry-run diff identical on second run |
| G8 | Human acceptance gate | operator_gated | CLOSURE-LEDGER §2 G8; no `ACCEPTANCE.md` | Operator records explicit acceptance on artifact | `grep -Eqi 'accepted by:' .../ACCEPTANCE.md` → exit 0 |
| W-2pct | "2% coverage" estimate | withdrawn | CLOSURE-LEDGER §0 warning; VERDICT §1; no replacement percentage offered | none — withdrawn | n/a |
| W-8pct | "8.0% union coverage" | withdrawn | VERDICT Rev 12/§3j: numerator double-counted 1,525 (1,484 iMessage-in-phone); superseded by 4.4% | none | n/a |
| W-10.7pct | "10.7% union coverage" | withdrawn | VERDICT Rev 12/§3j: same double count; superseded by 9.65% | none | n/a |
| W-13.3pct | "13.3% coverage" (8/60) | withdrawn | VERDICT §3i/Rev 13: rate within 8,819-unit bucket only; 0/60 at k=1; not coverage of everything | Human authorship adjudication on ask-cue sample | ask-cue authorship sample labelled |
| W-39-43 | "39-43% coverage" | withdrawn | VERDICT §3a: volume ratio of distinct intents, not coverage; 5,216-5,799 clusters | none | n/a |
| W-23pct | "at most 23%" | withdrawn | VERDICT §1 correction 1: 31.8% harness text missed by `is_injected` | none | n/a |
| W-synth | "register is synthesis, not extraction" | withdrawn | VERDICT §3b: 98.9% quotes anchor in phone-chat store; retracted | none | n/a |
| W-6085 | "6,085 harness distinct" | withdrawn | VERDICT §3c: never an output of `collapse_intents.py`; real `clean_distinct` = 5,799 | none | n/a |
| W-1.5pct | "1.5% harness coverage" as estimate | withdrawn | VERDICT §3e: strict-substring floor (88/5,799); upper bound 3.35% | none | n/a |
| W-357 | "357 (16.7%) harness quotes" | withdrawn | VERDICT §3b: superseded by 466/2,018 = 23.1%; denominator never recorded | none | n/a |
| W-911 | "911 iMessage distinct" | withdrawn | VERDICT §3c: actual 6,363 (9,011 text-bearing outbound rows) | none | n/a |
| W-196 | "196 KCode distinct" | withdrawn | VERDICT §3c: actual 166 (2,457 occurrences) | none | n/a |
| W-401 | "401/405 codex distinct" | withdrawn | VERDICT §5: actual 9,650 occurrences, 405 distinct non-injected (24.1x) | none | n/a |
| W-118 | "118 suspect links" | withdrawn | VERDICT §3d: 0 wrong links; 19 residuals all correct (9 paraphrase, 10 ASR) | none | n/a |
| W-3links | "3 candidate bad links" | withdrawn | VERDICT §3d: all 19 residuals correct; Rev 5 join note backwards | none | n/a |
| W-23abs | "23 absent link targets" | withdrawn | VERDICT §3d: mixed-namespace column; 0 absent targets | none | n/a |
| W-2.12 | "2.12% semantic floor" as estimate | withdrawn | VERDICT Rev 11: floor only, not rate; superseded by 13.3% rate | none | n/a |
| E-98lost | 98 `source_ref` harvest documents lost (0/98 resolve) | change_made | VERDICT §3g: 10 root classes searched, zero; pointer coherence 100% under window-end model | DEFECT: no next step | n/a |
| E-7srcless | 7 sourceless asks (above ids) | change_made | VERDICT §3g: three agreeing signals; CLOSURE-LEDGER §2 G5.e | Link to proven occurrence or mark `sourceless` | G5 closure query `sourceless_asks=0` |
| E-2cred | 2 `reg_utterances` rows carry `?code=` callback (UTT-004428, UTT-004470) | change_made | VERDICT §3g: 2 of 8,042 rows; zero JWT/OTP/bearer/key hits | Scrub URL credential params in SessionLedger ingest | ingest scrub test passes |
| E-805 | 805 unpromoted user utterances | change_made | CLOSURE-LEDGER §2 G5.d; VERDICT §2 UNVERIFIED (`reg_utterances` exists, name mismatch) | Re-derive against `reg_utterances` | reproducible count |
| E-ext | External channels (Gemini/OpenAI/Claude/Dot/Dot-GPT) | operator_gated | VERDICT §2 evidence tree: all BLOCKED/NOT_ATTEMPTED | Operator completes exports (G1.1-G1.4) | file exists, parses, count>0 |
| E-forge | Forge contamination (99.5% bytes flagged; 0.47% zero-flag bytes) | change_made | VERDICT §7: 15,209 records, 169.7 MB of 203 MB merged | Exclude forge or weight with stated measure | documented exclusion in matrix |
| E-herdr | herdr NOT_RECOVERABLE (`persists_operator_prompt_text=false`) | change_made | VERDICT §4: 8 records, no text recoverable | None — data limitation | n/a (not a defect) |
| E-occ | Occurrence volume only partly recovered (forge, herdr unrecoverable) | change_made | VERDICT §4: jcode/codex/iMessage/KCode re-mined; forge/herdr not | Re-mine or accept unrecoverable | occurrence ledger per source |
| E-auth | Declared-speaker attribution unusable (100% operator by construction; 27/60 agreement) | change_made | VERDICT §3k: `role` constant post-filter across 8,819 units | Human adjudication on ask-cue sample | labelled sample with authorship |
| E-nonask | 62-75% of non-ask-cue bucket is non-operator speech (47/60 from harness exports) | change_made | VERDICT §3j: two passes 45/60 and 37/60; channel composition 47/60 | Sample ask-cue bucket speaker mix | ask-cue authorship sample |
| E-nonask-adj | The 12 non-ask-cue disagreements are listed but unadjudicated (kappa `0.65` on that bucket, VERDICT §3n) | outcome_delivered | VERDICT §3p / INDEX Addendum 16: a third blind reading (key withheld) resolves `11 of 12` by majority of three (`5` to labeller 1, `6` to labeller 2; `1` three-way split, idx `59`); bucket operator count `23` / `25` / `26` of 60 (range `26` to `27`); adjudicated coverage `0.0788 [0.0591, 0.1022]`, `0.59` pp below labeller 1 and `0.19` pp below labeller 2; gate stays `WITHHOLD_RATE_AND_FLOOR`; `evidence/adjudication.json` | Operator-only if human ground truth is ever required: human adjudication of the 12 rows (idx `59` still has no majority). No agent action remains for the estimate | `~/CodeProjects/temp/npenv/bin/python adjudicate_disagreements.py` from `evidence/` → `recomputed_disagreements=12`, `sets_identical=true`, `resolved_by_majority=11`, `coverage.point=0.07881595` |
| E-union | ≈9.65% union coverage (frame A) as a coverage claim | change_made | VERDICT §3j: lower bound 6.5-17.9%; ~3/4 of attributed bucket is machine text; no operator-speech denominator | Human authorship sample on ask-cue bucket | ask-cue authorship sample labelled |
| E-16drift | 16-clause input drift (0.04%) between rebuilds | change_made | VERDICT §3j: 8,230 vs 8,214 iMessage clauses | None — recorded, no conclusion change | `coverage_consistency.json` `input_drift` |
| E-closure | Closure ledger's own checks: 9 of 11 name missing scripts/flags/columns | change_made | CLOSURE-LEDGER §1: usability FAIL | Implement named scripts/columns | scripts exist and run |
| E-index | Evidence index listed only 4 addenda while VERDICT referenced 11 | outcome_delivered | INDEX now runs to Addendum 15, including the precision and gate records | none, closed at Addendum 15 | last addendum heading = 15 |
| P-cite | Citation precision was unmeasured, so the 8.07-8.47% coverage figure could only be called an estimate | outcome_delivered | VERDICT §3o / INDEX Addendum 15: strict precision **0.780** (46/59, Wilson [0.659, 0.866]), lenient **0.966** (57/59, [0.885, 0.991]), on 60 origin links (seed `20261112`) drawn from 2,252; `evidence/precision_scored.json` | Second independent labeller on the precision sheet (one pass only so far) | `~/CodeProjects/temp/npenv/bin/python precision_score.py` from `evidence/` → `judgeable=59`, `strict=0.7797` |
| P-gate | The publication gate for the coverage rate: recall measured AND recall >= 0.9 AND strict precision >= 0.9 | outcome_delivered | VERDICT §3o: decision `WITHHOLD_RATE_AND_FLOOR`; recall `NOT_RUN` permanently (98 harvest documents lost, §3g) and strict precision 0.7797 < 0.9, so both halves fail on numbers; `evidence/rate_gate.json` | No agent action remains: a rate needs a measurable recall instrument (blocked) and strict precision >= 0.9 | `~/CodeProjects/temp/npenv/bin/python rate_gate.py` from `evidence/` → `decision=WITHHOLD_RATE_AND_FLOOR` |

## Derivative tasks with no owner

- Implement `mined/scripts/verify_occurrences.py` (G2 blocker) — no owner assigned.
- Implement `mined/scripts/reconcile_coverage.py` + `mined/COVERAGE-MATRIX.md` (G6 blocker).
- Add `resolved` column to `reg_provenance` (G3 blocker).
- Create `occurrence_attribution` table (G4 blocker).
- Create the 6 missing G5 schema objects or rewrite the query (G5 blocker).
- Add `--migrate-to-sessionledger` / `--dry-run` / `--diff-out` to `ask_research_ledger.py` (G7 blocker).
- Human authorship adjudication on 60 ask-cue clauses (VERDICT §3k): DONE, §3m (86.7% operator, 52/60).
- Second independent labeller on all three label sheets (VERDICT §3n): DONE, agreement kappa 1.00 / 1.00 / 0.65.
- Citation precision on the register's origin links (VERDICT §3o): DONE, strict 0.780 / lenient 0.966; gate decided WITHHOLD_RATE_AND_FLOOR in `rate_gate.json`.
- Second independent labeller on the PRECISION sheet (the one measurement still single-pass, §3o): not started.
- iMessage/KCode clause contamination sampling (VERDICT §3f/§3e) — not started.
- Update `evidence/INDEX.md` to cover addenda 5-15: DONE at Addendum 15.
- Prepare `ATTRIBUTION-AUDIT.md` and `ACCEPTANCE.md` evidence artifacts (G4, G8).

open=21 (change_made) operator_gated=7 withdrawn=17 defects=1 (subset of open) closed=4 (outcome_delivered) total=49
