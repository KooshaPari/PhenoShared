# Evidence Index — asks/instinct coverage corpus

Copy date (UTC): `2026-11-11T12:36:26Z`
Source root: `~/CodeProjects/temp/asks-coverage/`
Destination root: `docs/sessions/2026-11-11-asks-instinct-closure-ledger/evidence/`

## Why this directory exists

The entire evidence base for this work previously lived only under
`~/CodeProjects/temp/asks-coverage`, which is a **volatile scratch path**: it may be
wiped periodically and on reboot. This directory makes the *derivable* parts of that
corpus durable and repo-tracked.

**The full mined corpus is NOT copied.** It is roughly 612 MB on disk across the
`mined/*.jsonl` files (the largest are `intent.jsonl` ~224 MB, `forge_clean.jsonl`
~186 MB, `forge.jsonl` ~186 MB, `jcode.jsonl` ~39 MB). Those remain volatile and are
not recoverable from this repo. What is preserved here is the **schema, the per-source
manifests, and the human-readable analysis reports**, which are sufficient to describe,
re-validate and re-derive the corpus from the original local sources.

## Copied files (21)

### From `~/CodeProjects/temp/asks-coverage/mined/`

| File | Bytes |
| --- | --- |
| `SCHEMA.md` | 1487 |
| `KCODE-VERDICT.md` | 8986 |
| `_MANIFEST.json` | 2294 |
| `_MANIFEST.backup.forge.json` | 2243 |
| `codex_MANIFEST.json` | 888 |
| `forge_MANIFEST.json` | 2294 |
| `forge_clean_MANIFEST.json` | 7530 |
| `herdr_MANIFEST.json` | 8484 |
| `imessage_MANIFEST.json` | 1794 |
| `intent_MANIFEST.json` | 3268 |
| `jcode_MANIFEST.json` | 354 |
| `kcode_MANIFEST.json` | 3961 |

### From `~/CodeProjects/temp/asks-coverage/`

| File | Bytes |
| --- | --- |
| `A-gpt-full.md` | 7747 |
| `B-gpt-partial.md` | 4991 |
| `C-claude-gemini.md` | 5332 |
| `COVERAGE-REPORT.md` | 5448 |
| `D-harness.md` | 3579 |
| `E-imessage-register.md` | 10016 |
| `G-provenance.md` | 6737 |
| `H-other-channels.md` | 8465 |
| `LEDGER-AUDIT.md` | 9358 |

Total copied: 105,256 bytes (0.10 MB) across 21 files, measured with `stat -f%z`.

## Deliberately NOT copied

| Path | Bytes | Reason |
| --- | --- | --- |
| `mined/intent.jsonl` | 224,242,675 | Large corpus; volatile by policy |
| `mined/forge_clean.jsonl` | 185,831,404 | Large corpus |
| `mined/forge.jsonl` | 185,704,748 | Large corpus |
| `mined/jcode.jsonl` | 38,693,298 | Large corpus |
| `mined/imessage.jsonl` | 3,651,550 | Large corpus |
| `mined/codex.jsonl` | 1,868,115 | Large corpus |
| `mined/kcode.jsonl` | 511,971 | Large corpus |
| `mined/forge_recovered_prompts.jsonl` | 563,349 | Corpus extract, not a manifest/report |
| `mined/herdr.jsonl` | 2,675 | Corpus extract |
| `mined/scripts/` | (dir) | Regenerable tooling, not evidence |
| `B-preserved-human-messages.json` | 18,075 | Data extract, not a manifest/report |
| `analyze_exports.py`, `chatgpt.py`, `chatgpt2.py`, `final.py`, `probe.py`, `sample_codex.py`, `stats.py` | 410-6126 | Scripts; regenerable tooling |
| `chat.txt`, `chat2.txt`, `ledger2.txt`-`ledger5.txt`, `probe.txt` | 227-7358 | Ad-hoc console captures, superseded by the reports |

## Note on the manifests

`_MANIFEST.json` and `_MANIFEST.backup.forge.json` are byte-identical in intent but the
backup was written before the `forge_clean` pass. `forge_MANIFEST.json` is likewise the
pre-clean version. All three are retained so the clean/raw distinction stays auditable.

## Reproducing the corpus

Regeneration depends on local source artifacts at their original locations (jcode/kcode
session stores, Codex rollouts, Forge/Herdr/iMessage exports). Those sources are outside
this repo and unchanged by this copy. If the volatile JSONL is lost, it can be re-mined
from those sources; the manifests here record what the previous run contained.

## Addendum — corrected counts (2026-11-11T12:59Z)

These four artifacts supersede every per-source record count in the earlier manifests.
They are copied verbatim from `~/CodeProjects/temp/asks-coverage/` and are the only
durable record of the following measurements.

| Artifact | What it establishes |
|---|---|
| `CODEX-VERIFY.md` | 2,567 `~/.codex/sessions` files: 180 plain `.jsonl`, 2,380 `.jsonl.zst`, 7 `.jsonl.zst.zst`. A `*.jsonl` glob reads 7% of the corpus. |
| `CODEX-REEXTRACT.md` | Full zstd-aware pass: **9,650** user-turn occurrences, not 401 (24.1x). 3,942 are injected context, leaving **5,708** genuine, **405** distinct non-injected. |
| `JCODE-REEXTRACT.md` | **55,119** user-role occurrences, 24,715 distinct, **2.23x** repeat factor. Injected share 38.44%. Human non-injected: **30,234** occurrences, **8,290** distinct. `messages[].display_role` is the decisive field. |
| `OCCURRENCE-RECOUNT.md` | Every previously mined file has `records == distinct`, i.e. all were globally deduped. No file-level repeat factor is recoverable; jcode/herdr have no pre-dedupe evidence. |

Corrections to earlier figures in this directory:

- The jcode sessions directory is **2.9 GB / 8,667 files**, not the ~38.7 MB previously stated.
- `16,887` (old jcode count) is a deduped, partially-filtered figure and is not reproducible
  from either distinct count; it must not be used as a volume baseline.
- herdr cannot be recovered at occurrence level: its manifest records
  `persists_operator_prompt_text: false`, so the 8 records are a data limitation, not a bug.

## Addendum 2 — every channel mined, union and coverage (2026-11-12T02:52Z)

Rev 4 of `VERDICT.md` sized the union from two channels and had never mined iMessage or KCode.
Both are now mined at occurrence level. These artifacts are the only durable record.

| Artifact | What it establishes |
|---|---|
| `recount_imessage_kcode.py` | Occurrence-level miners for both channels. iMessage is opened `mode=ro` with `PRAGMA query_only=1`; **chat.db is never copied**. KCode `content` is a list of typed blocks and `display_role == 'system'` marks injected context — both facts were needed before it would parse. |
| `imessage_kcode_recount.json` | iMessage **6,363** distinct substantive (9,011 text-bearing outbound rows). KCode **2,457** occurrences collapsing to **166** distinct across 1,253 session files. |
| `union_channels.py` | The single script behind every figure in `VERDICT.md` §3c: channel sizes, both-direction containment, greedy long-first overlap, citation counts, union. |
| `union_channels.json` | harness 5,799 · iMessage 6,363 · KCode 166 · overlaps 517/58/1 · **union 11,752** · cited 1,764 · **coverage 15.0%**. |
| `register_channel_attribution.json` | Register-side proof: of 2,018 distinct quotes, 1,952 (**96.7%**) appear in a mined channel — phone 96.6%, iMessage 92.4%, harness 23.1%, KCode 0.1%. |

Corrections to figures this directory previously carried:

- **6,085 was never an output of `collapse_intents.py`.** Its `clean_distinct` is **5,799**
  (`8,506 − 2,707 noise`). Rev 4 attributed the gap to noise-pass ordering; that explanation
  was wrong.
- **iMessage "911" was a deduped artifact**, not the channel size. The channel has 9,011
  text-bearing outbound rows.
- **KCode "196" was roughly right** (166 actual distinct). Its 2,457 occurrences genuinely
  collapse because most sessions are canary stubs that repeat the same prompts.
- The phone channel is **not a separate channel**: 2,049 of 2,077 of its bodies appear verbatim
  in iMessage. It is an iMessage subset.
- `29.4%` register/union is superseded by **15.0%** citation-based coverage over a union that is
  11,752, not 7,661.

## Addendum 3 — ask→message link verification (2026-11-12T02:58Z)

The carried claim was "118 suspect ask→message links open". Every link is now tested.

| Artifact | What it establishes |
|---|---|
| `verify_ask_links.py` | Tests each `reg_ask_messages` link: does the ask's quoted text appear in the message it names? Two normalisation passes (strict / fold) so quote-serialisation damage is separated from wrong links. |
| `ask_link_verification.json` | strict 2,107 verified / 62 mismatched (97.14%); fold 2,151 / 18 (**99.17%**). Residual 18 = 6 sharing 60 chars, 3 at 40, 6 at 25, and **3 sharing nothing** — the only candidate genuinely wrong links. |

Method corrections recorded here:

- `reg_asks.utterance_id` (`UTT-000001`) does **not** join to `reg_utterances.id` (`phonemsg-<ULID>`).
  Comparing them yields a spurious "2,229 disagree". The working join is
  `reg_ask_messages.message_id` → `reg_utterances.message_id`.
- The 5-point strict→fold gap is the register storing escaped `\n` where the source message has a
  space, plus `" / "`-joined multi-part quotes. It is a defect in quote serialisation, not in linkage.

---

## Addendum 4 — harness coverage bounded, and the denominator's contamination measured

Rev 5's 1.5% harness figure was published as if it were an estimate. It is a strict-substring **floor**:
a harness member is a whole prompt, so a 3,000-character prompt carrying ten asks is one member and can
receive at most one citation. 45 uncited members were sampled (15 per length stratum, `random.seed(11)`,
reproducible) and classified by hand.

| Label | n | Share |
|---|---:|---:|
| `NEW_ASK` — genuine operator request, uncited | 20 | 44.4% |
| `NOT_ASK` — bg-task echo, auto-nudge, synthetic probe, protocol envelope | 12 | 26.7% |
| `NOT_OPS` — another agent's DM relayed in, or a peer instruction quoted | 9 | 20.0% |
| `ANSWER` | 3 | 6.7% |
| `AMBIGUOUS` | 1 | 2.2% |

| Artifact | What it establishes |
|---|---|
| `sample_uncited_harness.py` | Reproduces the identical 45-member sample from seed 11 and applies the classification; emits floor and upper bound. |
| `harness_uncited_sample.json` | `coverage_floor_pct` 1.52, `coverage_upper_pct` 3.35, `new_ask_share_pct` 44.4, `contamination_pct` 53.3, plus all 45 rows with excerpts. |

Two results:

1. **The floor is honest.** Even if every sampled `NEW_ASK` is one the register misses, harness coverage
   reaches only ~**3.35%**. Relaxing substring strictness was not hiding a large body of captured work.
2. **The denominator is contaminated.** **53.3%** of uncited harness members are not operator requests at
   all. The largest non-ask class is *other agents' DMs relayed into the session* (`dm from sauropod`,
   `dm from giraffe`, `dm from t-rex`), plus background-task echoes and synthetic probes such as
   `reply with exactly: m3head-ok`. Those belong in no union of operator intent, so 11,752 is inflated
   and 15.0% is a conservative figure.

Recorded limits, so the correction is not over-claimed:

- Classification is **my judgement, single coder, no second rater**. Read 44.4% / 53.3% as ±a few points,
  not as a measured rate.
- **iMessage was not sampled.** Whether a request to a *human* counts as operator intent is a
  definitional decision, not a measurement, and no contamination-adjusted union is published until it
  is settled.

---

## Addendum 5 — link integrity reduced to zero defects, and a Rev 5 method note retracted

Re-running `verify_ask_links.py` with namespace resolution, then reading every residual against the
full source message, closes the link question:

| | n |
|---|---:|
| asks | 2,259 |
| linked (`relation='origin'`) | 2,252 |
| unlinked, **all** flagged `reg_asks.source_missing = 1` | 7 |
| link targets absent from `reg_utterances` | **0** |
| fold-normalised mismatches | 19 |
| of those, read in full and judged correct | **19** |
| **wrong links** | **0** |

| Artifact | What it establishes |
|---|---|
| `verify_ask_links.py` (patched) | Adds a `resolve()` that tries `reg_utterances.message_id` then `reg_utterances.id`, and records `link_resolution` counts. Untestable drops 90 → 68 and verified rises 2,151 → 2,172. |
| `resolve_link_residuals.py` | Reads all 19 residual pairs against their full source bodies and writes a per-row verdict, plus the namespace split and the unlinked set. |
| `link_residual_review.json` | 9 `CORRECT_PARAPHRASE`, 10 `CORRECT_ASR`, `wrong_links_found: 0`; per-row interpretation and body excerpt for independent checking. |

Two errors of mine, both recorded rather than quietly fixed:

1. **`reg_ask_messages.message_id` is a mixed-namespace column** — 2,229 `phonemsg-<ULID>` plus 23
   `UTT-NNNNNN`. A test resolving only via `message_id` marks 23 *correct* links untestable. There are
   zero absent targets.
2. **Rev 5's join note was backwards.** It said `reg_asks.utterance_id` (`UTT-000001`) does not join
   `reg_utterances.id`. `reg_utterances` has both columns: `id` is `UTT-NNNNNN`, `message_id` is
   `phonemsg-<ULID>`. The join `reg_asks.utterance_id → reg_utterances.id` succeeds for **2,252 of
   2,259**.

The 19 residual mismatches are not defects in the register; they are speech-to-text damage. Two
readings, unchanged from the earlier review but now recorded row by row: `"report the state of
paperclip"` ← `"and apperclip"`, and `"what is next"` ← `"what's nxy"`.

---

## Addendum 6 — clause granularity, and an ask-classifier rejected by its own validation
(2026-11-12T04:50Z)

Files: `segment_units.py`, `granularity_units.json`, `sample_ask_rules.py`, `ask_rule_sample.json`,
`ask_rule_labels.json`, `score_ask_rules.py`, `ask_rule_validation.json`.

**Question.** The union compares two different units: a register ask is one extracted intent, a harness
member is a whole prompt. If that mismatch caused the low coverage figures, the shortfall would be a
reporting artifact. §3f tests it.

**Method.** `segment_units.py` splits every channel member on structure only — newlines, sentence
terminators, semicolons, dash joins, list markers, min 12 chars — with no semantic judgement, so the
denominator is reproducible without a model. Citation is unchanged: a register quote appearing as a
substring of the clause.

| Channel | Members | Clauses | Clauses/member | Cited | Coverage |
|---|---:|---:|---:|---:|---:|
| harness | 5,799 | 33,148 | 5.72 | 440 | 1.3% |
| iMessage | 6,363 | 8,214 | 1.29 | 1,487 | 18.1% |
| KCode | 166 | 2,185 | 13.16 | 2 | 0.1% |
| phone | 2,077 | 3,697 | 1.78 | 1,534 | 41.5% |
| union | 11,752 | 43,305 | — | 3,463 | **8.0%** |

**Result: the objection does not hold.** The numerator and the denominator both grew
(88 members → 440 cited clauses; 5,799 → 33,148 clauses), so harness coverage barely moved, 1.52% →
1.3%. Granularity was not suppressing the figure.

**A candidate headline was withheld.** Filtering clauses by ask cues selected 7,416 of 33,148 (22.4%)
and would have produced a 0.7% headline. That filter was validated instead of trusted: 30 predicted-ask
and 15 rejected clauses, `random.seed(23)`, hand-labelled, scored.

| Measure | Value |
|---|---:|
| precision | 0.733 (22/30) |
| ask rate in the rejected stratum | 0.267 (4/15) |
| estimated true ask clauses | ≈ 12,300 (37.1%) |
| **recall** | **0.44** |

Recall 0.44 means the gate misses more than half the asks, so its denominator understates the ask
population by ~40% and would have **inflated** coverage in the author's favour. It was rejected, and
0.7% was not published. Correcting both sides for the measured error gives 1.4–1.7%, which agrees with
the two member-level cuts and the mechanical clause-level 1.3%.

**Limits.** One coder; clauses judged without parent message (biases terse fragments to `NOT_ASK`); a
second rater would move precision and recall by several points. The finding used here — recall well
below 0.9 — is robust to that; the exact 0.44 is not. iMessage and KCode clauses were segmented but not
sampled, so their 18.1% and 41.5% carry unmeasured contamination.

## Addendum 7 — the 98 harvest documents are lost; two readings tested, one model confirmed
(2026-11-12T05:55Z)

Files: `audit_harvest_sources.py`, `harvest_source_audit.json`.

**Question.** All 2,259 asks cite one of 98 `source_ref` harvest documents, and none of the 98
resolves. Is that a search failure, a relocation, or a real loss — and what does it cost?

**Search.** Ten root classes, all zero: the registry working tree, the registry's whole git object DB
(all refs, plus `--diff-filter=D` deleted paths), all Phenotype repos, `~/CodeProjects/temp` to depth
8, six sibling trees under `~/CodeProjects`, Desktop/Downloads/Documents/Trash, `~/.jcode/scratch`
and `~/.hermes`, and both chat-harvest archives in the PhenoRegistry restore tree (1,891 entries).
Time Machine has no destinations configured. **Verdict: LOST**, not misplaced.

**Two schema corrections found while doing this, both my own errors.**

1. `reg_asks` has **no quote column**. Its columns are `id, utterance_id, interpretation,
   first_asked_at, day, time, area, kind, category_id, reported_state, verified_state, reviewed,
   reconciled_at, evidence_json, theme_key, issue_ref, issue_level, source_missing, updated_at`. The
   quoted text is `original_text` in the `asks.json` export and `reg_utterances.body` in SQL, reached
   via `utterance_id`. Any statement that "the register stores its quotes in `reg_asks`" is wrong.
2. Timestamps are stored **local (PDT)**, not UTC: 8,019 PDT rows against 23 UTC. A first pass of
   this script assumed UTC and silently compared only the 23 UTC rows, reporting "18 compared,
   2,229 uncomparable". Caught by the `uncomparable` counter, not by the headline, which looked
   plausible.

**Coherence test.** The documents are gone, so what can be tested is whether the remaining pointers
agree with the messages they point at.

| Reading | Rule | Result |
|---|---|---:|
| A, same-day | `source_ref` date = linked message's date | 2,211 / 2,252 (**98.18%**) |
| B, window end | `source_ref` date = latest message date in that document | 98 / 98 docs (**100%**), all 2,252 asks |

Reading B is correct, and the split says why: **69 docs are single-day** (span 0), **29 are rollups**
(span 1–27 days), and in **29 of 29** the filename date is exactly the rollup's last message date. The
filename is the harvest date, not a per-message date. Reading A's 41 mismatches are all rollup asks,
all deltas negative (mode −2d at 7, then −7d at 6, −4d at 4, −1d at 3).

**Provenance baseline, measured.** `reg_asks.utterance_id` resolves to `reg_utterances` for 2,252 of
2,259; `reg_ask_messages` origin links hold for the same 2,252. The remaining 7 agree across three
independent signals — `source_missing = 1`, `utterance_id IS NULL`, no message link — the same ids
(ASK-000345, -000637, -000664, -001844, -002254, -002255, -002256). No silent failure.

**Credential scan.** Prompted by the corpus's descent from a dataset whose redaction history is not
uniform. All 8,042 `reg_utterances` scanned for JWT, bearer, `sk-`, AWS-key, OTP-in-context and URL
credential-parameter shapes: **2 rows match**, both assistant, both `?code=` (UTT-004428 on a local
service port; UTT-004470 on a project subdomain). Zero JWT, OTP, bearer or key hits. Recorded as an
ingest scrub requirement, not as a clean bill. Hostnames withheld because this repository is public;
they are recoverable from the two utterance ids in `ledger.db`.

**What the loss costs.** Ask-level recall against the harvest is now unmeasurable, so "did the harvest
miss asks?" cannot be answered. Quote fidelity is unaffected and stays verified (§3d). The loss
constrains the *completeness* question, which is the question this whole programme is about.

---

## Addendum 8 — a true semantic probe, and a withheld headline (2026-11-12T08:30Z)

Four new artifacts, all replayable: `probe_paraphrase.py`, `semantic_coverage_probe.py`,
`semantic_label_review.json`, `score_semantic_labels.py`. Their outputs are the four sibling `.json`
files. VERDICT §3h carries the prose.

**A route existed that earlier notes said did not.** The "no embedding route" finding was measured
against Python packages (`numpy`, `torch`, `sentence_transformers`, `mlx`) — all absent, then and now.
It was never measured against `llama.cpp`, which is installed on this host with `llama-embedding`
(build 10270) and fetches GGUF models itself. No Python ML stack is needed. That is a probe-scope
error, recorded rather than quietly fixed.

**Selection used a test with a known answer.** 17 sentences: six paraphrase pairs with deliberately
low lexical overlap plus five distractors, chance top-1 at 6.2%. Minimum-maximum cosine margin was
rejected as the metric mid-test — legitimately related non-paraphrases inflate it, which is how my
first three-sentence probe appeared to show a *negative* margin while the model was in fact fine.
Top-1 retrieval: nomic f16 raw **12/12**, nomic `clustering:` 10/12, bge-small f16 9/12 (ranks 2, 4, 3).
Twelve pairs is small: rule of three puts the 95% lower bound near 0.78.

**Population is smaller than the published denominator, and the two are never combined.** Uncited
ask-cue clause units, rebuilt with `segment_units.py`: **8,819** distinct (harness 7,287, iMessage
1,012, KCode 527, phone 435). Sample of 800, seed 20261112. Nearest-ask cosine median 0.626, p90 0.707,
max 0.880.

**Hand labels, single labeller.** High band top 30 (`0.754`–`0.880`): **17 captured, 5 adjacent,
8 not**. Low band bottom 15 (`0.467`–`0.518`): **0 captured**. High-band precision is therefore
**0.567 strict, 0.733 lenient** — a cosine threshold cannot certify capture, because 8 of the 30
best-scoring pairs are adjacent-but-different intents.

**No semantic coverage percentage is published.** Recall is unmeasured (45 of 800 pairs labelled,
matches below the cut uncounted), so extrapolation would compound a weak detector with an unknown miss
rate. `semantic_scored.json` records `semantic_coverage_pct: NOT PUBLISHED` and names the condition
that would unblock it.

**What is published is a floor, because a floor needs no recall.** 17 of 800 sampled uncited clauses
are confirmed captured: **2.12%** strict, 2.75% lenient. Two consequences follow, and neither is
comfortable. Semantic capture does exist where the substring test reported none, so the 8.0%
structural figure is a genuine floor. And it is small, so the shortfall is not primarily a lexical
artifact. The distributional TF-IDF probe (§3b) found 0 of 12 high-band pairs were the same intent; a
real embedding model finds 17 of 30 on the same question. The method mattered, and the answer still
did not improve enough to close anything.

**Redaction, applied before commit.** The label sheet carries 45 verbatim clause/quote pairs — raw
corpus text, in a public repository. Scanned for emails, IP literals, URL credential parameters, key
shapes and whole URLs: **7 matches, all emails or URLs, all redacted** to `<EMAIL-REDACTED>` /
`<URL-REDACTED>`. Two consequences. The redaction edited text that had already been embedded, so the
`scores` in the JSON refer to the pre-redaction strings — the numbers are unchanged and
`semantic_scored.py` reproduces byte-identical output from the redacted files, but the artifact is a
record of a run, not a re-runnable corpus. And this is the second time corpus text introduced contact
addresses into an artifact, which is a scrub step that belongs in the pipeline rather than in a
review.
