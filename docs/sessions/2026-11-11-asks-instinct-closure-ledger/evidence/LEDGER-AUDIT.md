# LEDGER-AUDIT — CLOSURE-LEDGER.md defect audit

**Audited:** `docs/sessions/2026-11-11-asks-instinct-closure-ledger/CLOSURE-LEDGER.md`
(PhenoShared, branch `feat/researchledger-ingest-v2`, post-commit `7f6d4aa42`)
**Auditor:** jcode, 2026-11-11T12:33Z
**Method:** read the ledger, then checked each cited path / script / table on disk.
**Rule applied:** anything not checked is `UNKNOWN`, never `PASS`.

Register DB inspected: `~/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/ledger.db`
(read-only, 2,259 rows in `reg_provenance`).

---

## A. Acceptance commands naming scripts / flags / packages that do not exist — VERIFIED FAIL

| # | Ledger claim (quoted) | Verification | Verdict |
|---|---|---|---|
| A1 | G2 closure test: `python3 ~/CodeProjects/temp/asks-coverage/mined/scripts/verify_occurrences.py --manifests … --expect-remainder 0` | `ls` → `MISSING: …/mined/scripts/verify_occurrences.py`. `scripts/` contains only `merge.py`, `mine_*.py`, `repair_forge.py`, `validate_*.py`. | **FAIL** |
| A2 | G6 closure test: `python3 …/mined/scripts/reconcile_coverage.py --matrix … --expect-unexplained 0` | `ls` → `MISSING: …/mined/scripts/reconcile_coverage.py` | **FAIL** |
| A3 | G6 evidence artifact: `mined/COVERAGE-MATRIX.md` | `ls` → `MISSING: ~/CodeProjects/temp/asks-coverage/mined/COVERAGE-MATRIX.md` | **FAIL** |
| A4 | G7 closure test: `python3 researchledger/ingest/ask_research_ledger.py --migrate-to-sessionledger --dry-run --diff-out …` | File exists, but `grep -n "migrate-to-sessionledger\|diff-out\|dry-run"` returns **no matches** — none of the three flags is implemented. | **FAIL** |
| A5 | G7 closure test: `cargo test -p SessionLedger` | `absorption/SessionLedger/Cargo.toml` declares `name = "session-ledger"`. Cargo package names are exact; `-p SessionLedger` does not resolve. | **FAIL** |
| A6 | G3 closure test and §5 next-step: `select … from reg_provenance … where resolved = 0` | `pragma table_info(reg_provenance)` → `entity, entity_id, source, source_ref, method, observed_at`. **No `resolved` column.** Query errors out. | **FAIL** |
| A7 | G2/G5 closure test: `asks a join occurrence o on a.occurrence_id = o.id` | `pragma table_info(reg_asks)` has no `occurrence_id`; no `occurrence` table exists in `ledger.db`. | **FAIL** |
| A8 | G4 closure test: `select … from occurrence_attribution` | `sqlite_master` count for `occurrence_attribution` = **0**. Table does not exist. | **FAIL** |
| A9 | G5 closure test: `select … from user_utterances`, `from quotes_verified`, `asks.source_id`, `disposition` | No `user_utterances` table (it is `reg_utterances`), no `quotes_verified` table, no `reg_asks.source_id`, no `disposition` column anywhere. | **FAIL** |

**Consequence:** 9 of the 11 goal closure tests are unrunnable as written. The
evidence-cell tree's `closure test reachable by operator .... PASS` ("each goal has
one command") is therefore **wrong** — the commands exist as text but not as
executable checks.

---

## B. Zero / absence claims with no reproducing query — VERIFIED FAIL

| # | Ledger claim (quoted) | Why unsupported |
|---|---|---|
| B1 | §2 table, all seven sources: `register coverage` column = **`0 captured`** for iMessage, `~/.forge`, `~/.jcode`, `~/.codex`, `~/.kcode`, herdr, Paperclip | No query is given. `COVERAGE-REPORT.md` §1 records `reg_provenance.source = register.json` for **2,259 / 2,259** rows, i.e. the register has exactly one source value and no harness-level join key. "0 captured" is an inference from a single-value column, not a measured absence. |
| B2 | §2: `iMessage chat.db | 248,532 messages, 8,983 text-bearing outbound` | Numbers appear in `COVERAGE-REPORT.md` §2, but that report supplies no SQL either; the ledger's own §6 index points at report prose. No query text exists in the ledger. Verdict on the numbers: **UNKNOWN** (not re-derived here). |
| B3 | §2: `Paperclip Postgres | 1.5 GB, live | 0 captured` and herdr `245 MB, live` | No query; the report itself calls Paperclip counts "needs permission to query". | **UNKNOWN**, presented as a count. |
| B4 | G1.1: "whole-message redactions in **362 of 460** human bodies" | No command in the ledger reproduces this ratio; it exists only as report prose. | **UNKNOWN** |
| B5 | G5 defects: `118` suspect links, `805` unpromoted utterances, `2,134` verified quotes, `1,843` distinct messages | The G5 closure SQL that would produce these queries `quotes_verified`, `user_utterances`, `occurrence`, and `resolved` — none of which exist (A6–A9). So the baselines cannot be reproduced even in principle against the current schema. | **FAIL (unreproducible)** |
| B6 | §1 tree: `lane findings re-verified .... PASS  COVERAGE-REPORT.md 2026-11-11` | "Re-verified" is attributed to a report that itself contains no queries. No independent verification was performed. | **FAIL** (should be `UNKNOWN`) |
| B7 | §1 tree: `ledger readable without live DB .... PASS  counts cited w/ provenance` | Every numeric claim in §2/G5 depends on `~/CodeProjects/temp` lane files, i.e. it is not readable without them, and several are not reproducible even with them. | **FAIL** |

---

## C. Evidence artifacts that live only under `~/CodeProjects/temp` — VERIFIED

`~/CodeProjects/temp` is disposable by operator policy (wipeable periodically and on
reboot). The ledger itself concedes this in the header warning, then relies on it:

| # | Ledger quote | On-disk fact |
|---|---|---|
| C1 | "Companion artifacts … `~/CodeProjects/temp/asks-coverage/COVERAGE-REPORT.md`, per-lane files `A-…`–`H-…` … and `~/CodeProjects/temp/asks-coverage/mined/`" | All present **only** there; nothing is mirrored into the repo. |
| C2 | §0: "a second copy of the mined corpus … lives in `~/CodeProjects/temp/asks-coverage/mined/`" | The mined corpus is ~1.2 GB of JSONL (`forge_clean.jsonl` 185 MB, `intent.jsonl` 224 MB, `jcode.jsonl` 38 MB, …) held in volatile temp. |
| C3 | G1 evidence artifact: `~/CodeProjects/temp/asks-coverage/exports/<artifact>.MANIFEST.json` | The **only** path G1 would ever write evidence to is volatile. A `PASS` on G1 could be destroyed by a reboot. |
| C4 | G2 evidence: `mined/<source>_MANIFEST.json` | Manifests exist (`codex_`, `forge_`, `herdr_`, `imessage_`, `intent_`, `jcode_`, `kcode_`, `_MANIFEST.json`) but live only in temp. |

**Not a defect:** `ACCEPTANCE.md` is `MISSING` at
`docs/sessions/2026-11-11-asks-instinct-closure-ledger/ACCEPTANCE.md`. G8 declares
`NOT_RUN`, so absence is honest, not a false claim. (Checked, expected, `PASS` as a
state declaration.)

---

## D. Can source text hashes distinguish human from synthetic authorship? — VERIFIED **NO**

`~/CodeProjects/temp/asks-coverage/mined/SCHEMA.md`:

- `text_sha256` = "sha256 hex of `text` AFTER strip"
- rule 4: "Deduplicate by `text_sha256` WITHIN the source file. Keep the earliest ts."
- field list has `source`, `source_file`, `session_id`, `msg_id`, `ts`, `role`, `text`,
  `text_sha256`, `chars`, `substantive` — **no authorship/attribution field**, and
  `role` is fixed: "always `user`".

Reasoning, grounded in that schema:

1. A hash of the **body text** is authorship-invariant. The same sentence typed by the
   operator and emitted by a model hashes identically; conversely a human and a
   synthetic message with different bytes hash differently regardless of origin. The
   hash carries **zero** information about the producer.
2. It is computed **after strip**, and dedup keys on it, so two distinct occurrences
   with the same normalized text collapse into one record — the opposite of the
   occurrence-preservation G2 requires.
3. Because `role` is hardcoded `user`, the mining layer **asserts** operator authorship
   rather than proving it, which directly contradicts G4 rule 1 ("`PROVEN` only when a
   structural signal in the source agrees … never from phrasing alone").
4. `reg_utterances` does have `body_sha256` and a real `role`, so a proven attribution is
   *possible* there — but nothing in the ledger or the miners uses it, and no
   `occurrence_attribution` table exists (A8).

**Verdict:** text hashes cannot distinguish human from synthetic authorship. Any ledger
claim resting on `text_sha256` for attribution is unsupported.

---

## Defect summary

| id | defect | state |
|---|---|---|
| D1 | 9 closure tests reference missing scripts, missing flags, a wrong cargo package name, and 6 non-existent columns/tables | FAIL, verified |
| D2 | "closure test reachable by operator = PASS" is false | FAIL, verified |
| D3 | `0 captured` coverage cells have no reproducing query | FAIL / UNKNOWN, verified as unsupported |
| D4 | G5 baselines (118 / 805 / 2,134 / 1,843) cannot be reproduced against the actual schema | FAIL, verified |
| D5 | All primary evidence (report, lanes, 1.2 GB corpus, manifests, G1 target) lives in volatile `~/CodeProjects/temp` | FAIL, verified |
| D6 | `text_sha256` cannot establish authorship; miner hardcodes `role="user"` | FAIL, verified |
| D7 | `iMessage` / harness volume numbers (248,532 / 8,983 / ~73k) | UNKNOWN — not re-derived in this audit |
| D8 | `362 of 460` redaction ratio, Paperclip/herdr counts | UNKNOWN — no query available |

No file in the repo was modified by this audit beyond the already-committed ledger
header warning. Nothing was pushed.
