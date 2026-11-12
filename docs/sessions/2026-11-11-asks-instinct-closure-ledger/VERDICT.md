# Coverage Verdict — is the 2,259-ask register a complete capture of operator intent?

Recorded (UTC): `2026-11-11T13:00Z`. Revised `2026-11-12T05:55Z` (all channels mined at occurrence
level; union and coverage recomputed from one script; §3c; harness figure bounded by sampling and the
denominator's contamination measured, §3e; link integrity re-tested with namespace resolution and
reduced to zero defects, §3d; coverage re-derived at **clause granularity**, which required an
ask-classifier that failed validation and was therefore not used for the headline, §3f; the 98
`source_ref` harvest documents declared **lost** with a search record and a pointer-coherence test in
their place, §3g; a local embedding model selected by a test with a known answer, used to probe
semantic coverage, which **withholds the headline** and publishes a floor instead, §3h; and the recall
measurement that made the headline publishable, which raises union coverage from 8.0% to a lower bound
of 10.7% without changing the verdict, §3i).

**Revision history — this file has been wrong seven times, each time in the same direction (stating a
confident number from an incomplete measurement). Rev 8 is the first entry that corrects nothing: it
re-derives coverage at a finer granularity and finds the published shortfall survives the change.
Rev 9 is mixed: one withdrawn carried figure, one near-miss on schema, and one measured loss. Rev 10
adds a measurement rather than a correction, and its most important result is a refusal to publish a
number. Rev 11 is the number Rev 10 refused to publish, and it withdraws Rev 10's floor as an estimate
while keeping it as a floor, so the headline rises from 8.0% to 10.7% while the verdict does not
change.**

| Rev | Claim | What was wrong |
|---|---|---|
| 1 | "at most 23%" | counted raw strings, 31.8% of which were harness text |
| 2 | "39-43% coverage" | a volume ratio between different text populations, not coverage |
| 3 | "the register is a synthesis, not an extraction" | measured the paraphrase field against the wrong corpus; the register's source channel is phone chat, and 98.9% of its quotes anchor verbatim there |
| 4 | "harness cleaned distinct = 6,085", "register/union = 29.4%" | **6,085 is not an output of `collapse_intents.py`**; its clean set is `8,506 - 2,707 noise` = **5,799**. The 29.4% ratio rested on 6,085 and on channels that had never been mined |
| 5 | every channel mined at occurrence level; union, overlap and coverage recomputed from one committed script | — (a method upgrade, not a retraction of a number) |
| 6 | harness coverage is a floor between **1.52% and 3.35%**, and **53.3%** of the uncited harness corpus is not operator intent | Rev 5 published 1.5% as if it were an estimate; it is a strict-substring floor, and the denominator it divides by is contaminated by peer DMs and harness artifacts |
| 7 | **zero** wrong ask→message links; 0 link targets absent; 7 unlinked asks all self-flagged `source_missing` | Rev 5 blamed 3 candidate bad links and 23 unlinked targets. Both were defects in my test: `reg_ask_messages.message_id` is mixed-namespace, and Rev 5's own join note was backwards |
| 8 | clause-granularity coverage is **8.0%** of the union; harness coverage stays **1.3–1.7%** however it is cut | not a retraction — a method result. It establishes that the low figure is **not** a granularity artifact, and it rejects the ask-classifier I built to sharpen the denominator (precision 0.73, recall 0.44) |
| 9 | 0 of 98 `source_ref` harvest documents resolve (**lost**, 10 root classes searched); `source_ref` dates are harvest-date window ends, coherent for **98/98** docs; the register is **not** credential-free (2 of 8,042 rows) | two corrections carried in from earlier revisions: §8 still asserted "3 links are candidate wrong" after §3d had closed link integrity at zero, and the ledger's quote is **not** a column on `reg_asks` (it is `utterance_id` → `reg_utterances.body`); my own first pass also assumed UTC timestamps when 8,019 of 8,042 rows are PDT, and compared only 23 rows until the `uncomparable` counter caught it |
| 10 | a **true semantic** probe was run on the 8,819 uncited ask-cue clauses with `nomic-embed-text-v1.5`; it **confirms** semantic capture exists (floor **2.12%** of the sample) but its high-band precision is only **0.567** strict / **0.733** lenient, so **no semantic coverage percentage is published** | not a retraction of a number — a refusal to publish one. It also retires the earlier claim that no semantic route existed: the earlier probe found no embedding stack installed, which was true of Python packages but not of `llama.cpp`, which is present with `llama-embedding` |
| 11 | semantic capture among uncited ask-cue units is **13.3%** (8/60, 95% CI 6.9-24.2) on a **random** sample; union coverage is therefore at least **10.7%** (9.4-12.9), not 8.0% | Rev 10's 2.12% floor is withdrawn as an estimate of semantic coverage — not because it was miscalculated but because it was a floor built from a biased-high score band and could never be more. §3i measures the same quantity on a random draw. Note the trap this sets: 13.3% is a rate **within the 8,819-unit denominator**, and reading it as coverage of everything is the exact error this table exists to record |

Coverage numbers are derived from `evidence/union_channels.py`, whose machine-readable output is
`evidence/union_channels.json`; clause-granularity numbers come from `evidence/segment_units.py`
(`evidence/granularity_units.json`) and its validation `evidence/score_ask_rules.py`
(`evidence/ask_rule_validation.json`). Link-integrity numbers come from
`evidence/verify_ask_links.py` and `evidence/resolve_link_residuals.py`. Numbers below are quoted from
those files and nowhere else.

**This file answers one question only.** It does not propose a migration and does not treat activity
as evidence. Every cell below cites the measurement it rests on. Cells that were not measured say
`UNKNOWN` or `NOT_RUN`, never `PASS`.

---

## 1. The answer

**No. The register is not a complete capture of operator intent, and the reason is channel scope,
not fabrication.** Data can be read two levels down here and the two levels disagree, which is why
this section was rewritten twice:

| Reading | `ask` field | `quote` field |
|---|---|---|
| what it is | LLM interpretation, third person | operator's verbatim text |
| distinct entries | 2,255 (4 dupes in 2,259) | 2,132 |
| anchored in the register's own message store | n/a | **2,235 of 2,259 (98.9%)** |
| quoted text visible somewhere in a mined channel | n/a | **1,952 of 2,018 (96.7%)** |
| quoted text visible in the mined harness corpus | n/a | 466 of 2,018 (23.1%) |

> **The register is a verbatim extraction from a phone-chat archive that this project never mined.**
> `reg_utterances` holds 8,042 messages across 3 `phoneconv-<ULID>` conversations in 141 sessions,
> with the operator's real typos intact, and 2,252 asks are explicitly linked to a source message via
> `reg_ask_messages.relation = 'origin'`. So the register is real operator text, and my earlier
> "synthesis, not extraction" verdict is **retracted**.

**Where the shortfall actually is.** Channels, not percentages:

| Channel | Distinct substantive intents | Register captures |
|---|---:|---|
| Phone chat (the register's own source) | 2,075 | 1,733 cited (83.5%), ~87% after sampling misses |
| jcode + codex harness | 5,799 cleaned (of 8,506 distinct) | 88 members cited (1.52%); 466 of 2,018 quotes appear in it (23.1%) |
| iMessage | **6,363** (was carried as 911) | 1,674 cited (26.3%) |
| KCode | **166** (was carried as 196) | 2 cited (1.2%) |

> Both of those rows read `DEDUPED_INPUT` / `not measured` for two revisions. They are measured now
> (§3c); the corrected figures are worse than the carried ones for iMessage (911 → 6,363 distinct) and
> slightly better for KCode (196 → 166). Union coverage is **15.0%**, not `UNKNOWN` — still a count
> ratio, not an intent-level measure (§3c, §3e). The 39-43% figure below is a **volume ratio**, not
> coverage.

**Seven corrections, all mine** — each moved confidence down while the conclusion held — **plus one
structural test the conclusion passed** (item 8).

1. "At most 23%" came from 9,802 raw strings. Wrong in the pessimistic direction: 31.8% of those were
   harness text that `is_injected` missed. Intent clustering gave 5,216-5,799, i.e. 39-43%.
2. That 39-43% then had to be demoted from "coverage" to "volume ratio" once overlap was measured,
   because it assumed both sides came from the same text population.
3. "The register is synthesized, not extracted" was **wrong**. I measured the `ask` paraphrase against
   the harness corpus, got 0% overlap, and drew a provenance conclusion from it. Reading
   `reg_ask_messages` and `reg_utterances` first would have shown the register's source channel is not
   the harness at all. **Zero lexical overlap is not evidence of fabrication until channel scope is
   established.**
4. The codex distinct non-injected count is **399, not 405**. The 405 came from a worker report whose
   `is_injected` field was never persisted into the artifact. 399 is recomputed from the committed
   file.
5. **6,085 harness distinct was fabricated.** `collapse_intents.py` outputs `clean_distinct: 5799`
   (`8,506 - 2,707 noise`); 6,085 was never one of its outputs. See §3c.
6. **1.5% harness coverage is a floor, not an estimate**, and **53.3%** of the uncited harness corpus
   is not operator intent. See §3e.
7. **The 3 "candidate bad links" and the 23 "absent link targets" were defects in my own test**, not
   in the register. There are zero wrong links; the 7 unlinked asks are self-flagged
   `source_missing`. See §3d.
8. **Not a correction — a test the conclusion passed.** Re-cutting the union at clause granularity
   moved coverage from 15.0% of members to 8.0% of 43,305 clauses, and harness coverage from 1.52% to
   1.3–1.7%: the shortfall is not a units artifact. The ask-classifier built to sharpen the
   denominator was **rejected by its own validation** (precision 0.73, recall 0.44) before its 0.7%
   figure could be published. See §3f.

The previously circulated figure of 2% coverage is **withdrawn**. It was not derived from a query
that anyone can reproduce, and its numerator and denominator were both post-dedupe counts.

---

## 2. Evidence tree

Each cell is one of `PASS / FAIL / NOT_RUN / UNKNOWN`. No cell is a percentage.

```
Coverage of operator intent by the 2,259-ask register
├── Corpus construction
│   ├── Distinct non-injected operator strings measured ....... PASS  (9,802, see §3)
│   ├── Occurrence volume preserved (no global dedupe) ........ PARTIAL (2 of 6 sources, see §4)
│   ├── Compressed corpora accounted for ..................... PASS  (codex fixed, 24.1x, see §5)
│   └── All harness sources enumerated ...................... UNKNOWN (see §6)
├── Authorship separation
│   ├── Injected context separated from operator typing ...... PASS  (display_role / marker rules)
│   ├── background_task prompts excluded from operator count . PASS  (3,335 identified)
│   ├── Human vs synthetic authorship distinguishable ........ FAIL  (see §7)
│   └── Duplicate suppression at the *intent* level ......... PARTIAL (§3a collapses the corpus the
│                                                                   same way the register never was)
├── Register integrity
│   ├── source_ref paths resolve ............................ FAIL  (0 of 98; src values are harvest
│   │                                                               docs named MonthDYYYY-NN.md)
│   ├── Suspect links resolved ............................. PASS  (2,172 of 2,191 testable links
│   │                                                               verify by fold-normalised match;
│   │                                                               all 19 residuals read in full and
│   │                                                               correct (paraphrase/ASR), so 0
│   │                                                               wrong links; §3d)
│   ├── Ask -> source message link ......................... PASS  (reg_ask_messages 2,252 of 2,259,
│   │                                                               relation='origin' for all 2,252; §3b)
│   ├── Utterance store present ............................ PASS  (reg_utterances 8,042; the earlier
│   │                                                               "no user_utterances table" was a
│   │                                                               name mismatch, not an absence)
│   ├── Unpromoted user utterances ......................... UNVERIFIED (805 came from the audit that
│   │                                                               missed reg_utterances)
│   └── Sourceless asks .................................... FAIL  (7)
├── Register vs channel overlap
│   ├── Quote anchored in own message store ............... PASS  (2,235 of 2,259 = 98.9%; §3b)
│   ├── Own-channel utterance capture .................... PARTIAL (1,733 of 2,075 substantive = 83.5%;
│   │                                                               ~87% after sampling 342 uncited)
│   ├── Harness-channel capture (substring) ............... MEASURED (466 of 2,018 register
│   │                                                               quotes = 23.1% appear in harness
│   │                                                               text; supersedes 357/16.7%)
│   ├── Harness-channel capture (distributional-lexical) .. REJECTED (high band 0/12 true positives;
│   │                                                               not a usable estimator; §3b)
│   ├── Harness join possible .............................. FAIL  (reg_provenance.source is
│   │                                                               register.json for 2259/2259; the register
│   │                                                               never joined the harness)
│   └── Union coverage across all channels ................ MEASURED (15.0% citation-based;
│                                                                   1,764 of 11,752; §3c)
└── External channels
    ├── Google Takeout (Gemini) ............................ BLOCKED (0 of 68 products selected)
    ├── OpenAI conversations.json ......................... BLOCKED (identity verification)
    ├── Claude export ..................................... BLOCKED (sign-in)
    ├── Dot export (unredacted) ........................... NOT_ATTEMPTED
    └── Dot/GPT data after 2026-10-30 ..................... NOT_ATTEMPTED
```

A `BLOCKED` external channel means coverage through that channel is **unmeasured**, not zero and
not complete. The verdict in §1 does not depend on those channels, because the shortfall is already
decisive from locally measured sources alone.

---

## 3. How 9,802 is derived

Only sources where the count is reproducible from a committed artifact are summed:

| Source | Distinct non-injected operator strings | Basis |
|---|---:|---|
| jcode | **8,290** | `evidence/JCODE-REEXTRACT.md`: 30,234 human non-injected occurrences → 8,290 distinct (3.65x repeat) |
| codex | **399** | `evidence/CODEX-REEXTRACT.md` artifact, **recomputed**: 9,650 occurrences, 3,950 injected (40.9%), 5,700 non-injected → 399 distinct. Not 405; see §1 correction. |
| imessage | **6,363** | re-mined: 9,011 text-bearing outbound rows → 6,418 substantive → 6,363 distinct (`evidence/imessage_kcode_recount.json`). The carried 911 was a deduped artifact |
| kcode | **166** | re-mined: 2,457 occurrences in 1,253 session files → 166 distinct (14.8x repeat). The carried 196 was post-dedupe against a different pre-dedupe base |
| herdr | **0** | manifest records `persists_operator_prompt_text: false`; no text recoverable |
| forge | **excluded** | authorship unresolved, see §7 |
| **Total** | **15,218** | naive sum of the rows above; cross-channel overlap is **not** removed here. The de-duplicated union is 11,752 (§3c). The pre-recount total was 9,802 |

Forge is deliberately excluded from the numerator rather than estimated. Including a
questionable source to strengthen a conclusion would be the same error this document exists to
correct.

`9,796 / 2,259 = 4.34` — there are at least 4.3 distinct operator strings for every register ask.
This is a **string** ratio. It is not the coverage figure; see §3a, which collapses strings into
intents and is the only ratio this document asks you to rely on.

---

## 3a. String ratio is not intent ratio — the collapse

String counts overstate intents, because retries and rephrasings repeat one ask. Collapsing the
jcode and codex populations (`evidence/INTENT-COLLAPSE.md`) gives:

| Stage | Count | Note |
|---|---:|---|
| records kept (human, non-injected, >=12 chars) | 28,247 | from 64,772 read |
| short nudges separated, not dropped | 11,637 → 382 distinct | `go`, `continue`, `.` |
| distinct after normalization + dedupe | 8,506 | 189 cross-source duplicates removed |
| tagged harness-generated by labelled pattern pass | 2,707 (31.8%) | swarm_bee 1,453, auto_nudge 699, attached_image 248, env_context 155, internal_context 139 |
| cleaned distinct strings | **5,799** | |

Three independent collapse methods on the cleaned population, so no single threshold is
presented as truth:

| Method | Clusters | vs 2,259 |
|---|---:|---:|
| exact normalized match (most conservative) | **5,799** | 2.57x |
| token-set Jaccard >= 0.8 within prefix-40 | 5,623 | 2.49x |
| prefix-40 collapse (most aggressive) | **5,216** | 2.31x |

**Defensible range: 5,216-5,799 distinct intents.** No point estimate is offered; the three methods
differ by up to 583 clusters and every method is lexical.

Why this range is still not the true intent count:

1. **The threshold is the answer.** Exact-to-prefix-40 swings the result 38% with no change to the
data. A different Jaccard cut or prefix length moves it again.
2. **Every method is lexical, so none sees a paraphrase.** "Fix the CI failure on PR 63" and "the
   PR 63 build is red, sort it out" share almost no tokens and land in different clusters. Paraphrases
   therefore inflate the count, so the true intent count is *below* 5,216 by an unmeasured amount.
3. **The comparison is asymmetric.** The register's 2,259 entries were never normalised or deduped.
   Collapsing the register the same way would drop it below 2,259 and widen the gap.
4. **The source is not clean.** 31.8% of measured strings were harness text that `is_injected`
   missed, and `codex_user_turns_v2.jsonl` carries **no `is_injected` field at all** (0 of 9,650
   records), so that flag could not be used for codex and a pattern pass had to substitute.

Volume ratio implied: `2,259 / 5,216 = 43.3%` and `2,259 / 5,799 = 39.0%`, i.e. **39-43%**,
computed on jcode+codex only. This is **not coverage** — see §3b, which measures actual overlap and
shows the two populations barely intersect. Read this line only as "the corpus contains 2.3-2.6x as
many distinct intents as the register has entries".

---

## 3b. Channel scope: the register is a verbatim extraction from a channel we did not mine

**This section retracts an earlier verdict published in this same file.** The previous version of
~3b concluded the register was "a synthesis, not an extraction" because its text did not match the
harness corpus. That conclusion was wrong, and the error was mine: I treated zero lexical overlap as
evidence of fabrication when it was evidence that I had compared the register against the wrong
channel. The artifact itself carries the provenance tables needed to check this, and I did not read
them before publishing the claim.

### What the register's own provenance says

`ledger.db` holds the join the earlier audit declared missing:

| Table | Rows | What it is |
|---|---:|---|
| `reg_utterances` | 8,042 | the verbatim message store: `role`, `ts`, `body`, `body_sha256`, `exact_body` |
| `reg_ask_messages` | 2,252 | ask -> message link, `relation = 'origin'` for 2,252 of 2,252 |
| `reg_sessions` | 141 | sessions derived by `time-gap:45m` over 3 conversations |
| `reg_provenance` | 2,259 | per-ask `source_ref` plus `method` such as `relinked:exact:1.0` |

`reg_utterances` is **not** harness data. It is 8,042 messages across exactly 3 conversations:

| conversation_id | messages | user | register quotes anchored here |
|---|---:|---:|---:|
| `phoneconv-01M3D10S1REWYKC27825RK0JDT` | 6,616 | 2,269 | 1,891 |
| `phoneconv-01M5E89QP154YYM60H1H4CQZ6K` | 1,403 | 333 | 394 |
| `chatdb` (an iMessage store) | 23 | 23 | 49 |
| unanchored anywhere | — | — | 24 |

Counts exceed 2,259 because a few quotes appear in more than one conversation. Timestamps are in UI
form (`Friday, October 09, 2026, 06:03:06 AM UTC`), bodies keep the operator's real typos
(`"Now you're going to need you to sell yourself."`, `"br8jt up infisical yab"`), and
`exact_body = 1` for 8,037 of 8,042 rows. The register spans 38 distinct days,
`2026-09-25` to `2026-11-04`.

The builder also recorded how it linked each ask, in `reg_provenance.method`:
`relinked:exact:1.0` 1,456, `relinked:contained:1.0` 741, `relinked:alnum_exact:1.0` 45,
`relinked:token_overlap:0.8-1.0` 10, and `no-source-body-available` **7**. Those 7 are the same 7
"sourceless asks" reported as a bare `FAIL` elsewhere; the defect is real but it is documented at
source, not concealed.

### The anchoring test

Matching each register `quote` against the 2,620 user message bodies:

| Result | Count | Share |
|---|---:|---:|
| quote is an **exact** user utterance (normalized) | 1,506 | 66.7% |
| quote is a **substring** of a user utterance (mid-message excerpt) | 729 | 32.3% |
| **anchored verbatim** | **2,235** | **98.9%** |
| unanchored | 24 | 1.1% |

The 24 unanchored are visibly real harvest text carrying literal `\n` and URL-encoded filenames, so
they are harvest artifacts rather than invented entries.

### Channel coverage, measured per channel

| Channel | Distinct substantive intents | Register captures | Verdict |
|---|---:|---|---|
| **Phone chat** (the register's own source) | 2,075 | 1,733 cited (83.5%); ~87% after sampling misses | good, not complete |
| **jcode + codex harness** | 5,799 cleaned (of 8,506 distinct) | 88 members cited (1.52%); 466 of 2,018 quotes appear in it (23.1%); 440 of 33,148 clauses (1.3%) | poor |
| iMessage | **6,363** | 1,674 cited (26.3%) | poor |
| KCode | **166** | 2 cited (1.2%) | poor |

> **The "Register captures" column mixes two directions on purpose, and they are not
> interchangeable.** Member-side cells answer "what share of this channel does the register cite"
> (88 / 5,799 = 1.52%). Quote-side cells answer "what share of the register's own quotes can be found
> in this channel" (466 / 2,018 = 23.1%). A channel can score high on one and low on the other. The
> `357 (16.7%)` figure that stood in the harness row for two revisions is **superseded** by the
> measured pair above; its denominator was never recorded, so it cannot be re-derived and must not be
> quoted.

Phone-chat collapse: 2,620 messages -> 2,367 distinct strings -> 2,075 substantive (>=12 chars), and
the collapse is a no-op there (exact, prefix-40, and Jaccard-0.8 all return 2,075). Of the 342
uncited substantive utterances (16.5%), a random sample of 16 contained 3-4 genuine asks and the rest
were conversational fragments (`"was the name"`, `"and processes"`, `"desk rebooted"`), giving roughly
87% utterance-level capture of the register's own channel.

### Why the earlier fingerprint reasoning misfired

The signals I read as "synthesized" are real but they describe the `ask` field, not the register as a
whole. `ask` holds an LLM interpretation (third person, deduplicated, near-zero harness noise);
`quote` holds the operator's verbatim text. `build-asks.py` states the mapping explicitly:
`original_text` <- `quote`, `interpretation` <- `ask`. I measured the paraphrase and drew a
conclusion about the archive.

The `.md` `src` values are consistent with this too: they are harvest documents named
`MonthDYYYY-NN.md` (for example `September252026-01.md`, `October82026-02.md`), one per day-part, and
they are not on disk in the registry repo, which is why 0 of 98 resolve.

### Distributional similarity, tested and rejected

Before reading the provenance tables I built a token-level TF-IDF cosine matcher (no ML stack is
installed: no numpy, no torch, no ollama) over the 8,506 harness intents, to avoid relying on exact
matching. It scored a median of 0.32 and put 712 entries at >= 0.40. **The high band is
false-positive dominated: 0 of 12 sampled high-band pairs are the same intent.** They share
vocabulary, not meaning:

| Register | Corpus match | Same intent? |
|---|---|---|
| "why is paperclip mac only" | "state of mac works" | no |
| "switch infisical to a bright/light theme" | "infisical has the creds" | no |
| "stop directly dispatching or managing chats" | "manage the chats" | no |

So distributional-lexical scoring is **not** a usable coverage estimator here, and it is recorded as
a negative result rather than a number.

### 3c. Every channel mined; union and coverage recomputed

Rev 4 sized the union from two channels and had never mined iMessage or KCode. Both were being
reported as `DEDUPED_INPUT`, the same defect that made codex look like 401 records when it was 9,650
occurrences. They are now mined at occurrence level. Everything in this section comes from
`evidence/union_channels.py` and `evidence/union_channels.json`.

The floor counts were both wrong, and in opposite directions:

| Channel | Carried as | Actual distinct | Why |
|---|---:|---:|---|
| iMessage | 911 | **6,363** | 9,011 text-bearing outbound rows exist; the 911 was a deduped artifact |
| KCode | 196 | **166** | 2,457 occurrences genuinely collapse; 1,253 session files are mostly canary stubs |

The iMessage channel also **subsumes** the channel the register was built from: 2,049 of the 2,077
phone-chat `reg_utterances` bodies appear verbatim in iMessage. The phone conversations are an
iMessage subset, so adding iMessage does not add a second population, it widens the one the register
already drew from.

**Channel sizes and the union** (substring containment both directions, then greedy long-first
pairing):

| Quantity | Value |
|---|---:|
| iMessage distinct substantive | 6,363 |
| harness (jcode + codex) clean distinct | 5,799 |
| KCode distinct substantive | 166 |
| iMessage ∩ harness | 517 |
| KCode ∩ harness | 58 |
| KCode ∩ iMessage | 1 |
| **union** | **11,752** |

Directional containment is deliberately reported both ways because it is asymmetric: 517 iMessage
texts appear inside harness text, while only 19 harness intents appear inside iMessage text. A short
message can sit inside a long prompt; the reverse rarely happens. The union subtracts the greedy
pairing once per pair, not both directional counts.

**Register-side attribution.** This is the measure that answers "is the register real":

| Channel | register quotes whose text appears there | Share of 2,018 |
|---|---:|---:|
| phone chat (`reg_utterances`) | 1,949 | 96.6% |
| iMessage | 1,864 | 92.4% |
| harness | 466 | 23.1% |
| KCode | 2 | 0.1% |
| **any channel** | **1,952** | **96.7%** |

So 96.7% of the register's quoted text demonstrably exists in a channel that was actually mined. The
register is a faithful extraction. It also never joined the harness as a *source*: `reg_provenance`
is `register.json` for all 2,259 rows, and harness text appears in the register only as quoted
restatements of things the operator said elsewhere.

**Channel-side coverage** (a member is cited if some register quote is a substring of it):

| Channel | Distinct | Cited | Coverage |
|---|---:|---:|---:|
| iMessage | 6,363 | 1,674 | 26.3% |
| harness | 5,799 | 88 | **1.5%** (floor; ≤3.35% on sampling, §3e) |
| KCode | 166 | 2 | 1.2% |
| **union** | **11,752** | **1,764** | **15.0%** |

**This is the corrected headline, and it is worse than Rev 4's 29.4%.** Rev 4 divided the whole
register by a union it had understated, which flattered the result twice. 15.0% is a citation-based
count, so it cannot be inflated by register entries that do not correspond to anything in the union.

It is still a coarse count, and the caveats are real: it mixes granularity (a register ask is an
extracted intent, a harness member is a whole prompt that may contain several asks), a register ask
containing several harness-level requests is counted once, and 88 harness citations is a small
absolute number that a single large prompt can concentrate (466 register quotes sit inside those 88
members). It should not be read as "15% of your ideas are captured" with precision. It is the correct
order of magnitude and it is derived from one reproducible artifact.

**Reconciliation, replacing Rev 4's guess.** Rev 4 attributed the 6,085 vs 5,799 gap to "noise-pattern
pass ordering". That was wrong: `collapse_intents.py` reports `clean_distinct: 5799` and
`noise_like_distinct: 2707` against `distinct_normalized: 8506`, and 8,506 − 2,707 = 5,799. **6,085 was
never an output of the script.** The 8,488 vs 8,506 gap is still an implementation difference, but it
is now bounded and only affects the raw distinct figure, not the clean set.

### 3d. Ask → message link integrity: zero defects

The carried claim was "118 suspect ask→message links open; ASK-000013 confirmed wrong". That was a
list, not a measurement. Every one of the 2,252 links is now tested directly, and the residual has
been read message by message. **No wrong link was found.**

| Pass | Verified | Mismatched | Untestable | Fidelity |
|---|---:|---:|---:|---:|
| strict | 2,104 | 64 | 68 | 97.05% |
| fold | **2,172** | **19** | 68 | **99.13%** |
| fold, residual read in full | **2,172 + 19 correct** | **0** | 68 | **100% of testable** |

`strict` is whitespace-collapse plus lowercase. `fold` additionally undoes literal escape sequences
(`\n`, `\\`), folds curly quotes, and splits multi-part quotes on `" / "` requiring every part to be
present. The gap between the passes is quote-serialisation damage in the register, not wrong links.

**All 19 residual links are correct.** They fail substring matching because the register's
`interpretation` (or its `quote`) is a cleaned rendering of speech-to-text, so the link is right and
the text is damaged. Reading them produced two classes:

| Verdict | n | Example |
|---|---:|---|
| `CORRECT_PARAPHRASE` | 9 | `"Report the state of the Tracera Cloud/web workstream"` → `"Cloud/web state, 9:58: - Job collector: live-health failed 9:07..."` |
| `CORRECT_ASR` | 10 | `"report the state of paperclip"` → `"and apperclip"`; `"what is next"` → `"what's nxy"` |

Every row is recorded individually with its target text in `evidence/link_residual_review.json`, so
the reading can be checked rather than trusted.

**The 23 "untestable" links were a namespace defect in my own test, not in the register.**
`reg_ask_messages.message_id` is a **mixed-namespace column**: 2,229 rows hold a `phonemsg-<ULID>`
(joining `reg_utterances.message_id`) and 23 hold a `UTT-NNNNNN` (joining `reg_utterances.id`).
Resolved both ways, **zero link targets are absent** from `reg_utterances`.

**The 7 unlinked asks are self-declared, not hidden.** `reg_asks.source_missing` is `1` for exactly
those 7 and `0` for the other 2,252 — link presence and the register's own flag agree perfectly:

| | n |
|---|---:|
| asks | 2,259 |
| linked | 2,252 |
| unlinked, all flagged `source_missing = 1` | 7 |
| link targets absent from `reg_utterances` | **0** |

**Correction to the method note published in Rev 5.** Rev 5 stated that `reg_asks.utterance_id`
(`UTT-000001`) "does **not** join to `reg_utterances.id`, which looks like `phonemsg-<ULID>`". That is
backwards. `reg_utterances` has **both** columns: `id` is `UTT-NNNNNN` and `message_id` is
`phonemsg-<ULID>`. `reg_asks.utterance_id` therefore joins `reg_utterances.id` for **2,252 of 2,259**
asks. The real trap is narrower: a test that resolves links only through `message_id` will silently
mark 23 correct links untestable.

### 3e. Bounding the harness figure, and what the denominator actually contains

1.5% harness coverage is a **floor**, because a harness member is a whole prompt: a 3,000-character
prompt carrying ten asks is one member and can receive only one citation. To bound how much strict
matching hides, 45 uncited members were sampled (15 each by length, `random.seed(11)`, reproducible
via `evidence/sample_uncited_harness.py`) and classified by hand:

| Label | Count | Share |
|---|---:|---:|
| `NEW_ASK` — genuine operator request, uncited | 20 | 44.4% |
| `NOT_ASK` — background-task echo, auto-nudge, synthetic probe, protocol envelope | 12 | 26.7% |
| `NOT_OPS` — another agent's DM relayed in, or a peer's instruction quoted | 9 | 20.0% |
| `ANSWER` — a reply, not a request | 3 | 6.7% |
| `AMBIGUOUS` | 1 | 2.2% |

| Quantity | Value |
|---|---:|
| harness coverage, strict-substring **floor** | 88 / 5,799 = **1.52%** |
| implied uncited genuine asks | ≈ 2,538 |
| harness coverage if every `NEW_ASK` is one the register misses | ≈ **3.35%** |
| uncited members that are **not operator requests** | 24 / 45 = **53.3%** |

So the floor is honest: relaxing substring matching could at most lift harness coverage to ~3.4%.
Substring strictness was not hiding a large body of captured work.

**The more important finding is about the denominator, not the numerator.** More than half of the
uncited harness corpus is not operator intent at all: background-task echoes, synthetic probes such as
`reply with exactly: m3head-ok`, protocol envelopes, and — the largest single class after
`NEW_ASK` — **other agents' DMs relayed into the session** (`dm from sauropod: ...`,
`dm from giraffe: ...`). Those are peer instructions, not operator asks, so they should not sit in a
union of operator intent.

This means the 11,752 union is inflated, and 15.0% is therefore a **conservative** figure: strip the
~53% non-operator share from the harness side and genuine-intent coverage rises to roughly 20%, still
an order of magnitude short of "complete".

Two honest limits on that correction, so it is not over-claimed:

- The classification is **my judgement, single coder, no second rater**. It is an indicative bound,
  not a measured rate, and the 44.4% / 53.3% split should be read as ±a few points.
- **The iMessage side was not sampled.** Its 6,363 members are conversations with people, and whether a
  request to a human counts as "operator intent" is a definitional decision, not a measurement. Until
  that is settled, no contamination-adjusted union can be presented as a number.

### 3f. Granularity normalisation: the figure survives the change

§3e left one structural objection open. The union counts **members**, and the two sides disagree on
what a member is: a register ask is an extracted intent, usually one imperative sentence, while a
harness member is an entire prompt, median a few hundred characters and tailing past 4 KB. A prompt
carrying eight asks is one member and can earn one citation. If that mismatch were the cause of the
low figures, coverage would be a reporting artifact rather than a real shortfall. So every channel was
re-cut at **clause granularity** (`evidence/segment_units.py`, `evidence/granularity_units.json`).

The split is **structural only** — newlines, sentence terminators, semicolons, dash joins, list
markers, minimum 12 characters — and contains no semantic judgement, so the denominator is
reproducible without a model.

| Channel | Members | Distinct clauses | Clauses/member | Cited clauses | Coverage |
|---|---:|---:|---:|---:|---:|
| harness | 5,799 | 33,148 | 5.72 | 440 | **1.3%** |
| iMessage | 6,363 | 8,214 | 1.29 | 1,487 | **18.1%** |
| KCode | 166 | 2,185 | 13.16 | 2 | **0.1%** |
| phone | 2,077 | 3,697 | 1.78 | 1,534 | **41.5%** |
| **union** | 11,752 | **43,305** | — | **3,463** | **8.0%** |

(Member union 11,752 is the de-duplicated figure; the four channel member counts sum to 14,405. The
clause union subtracts 3,939 cross-channel duplications from a 47,244-clause sum.)

**The objection does not hold.** Harness coverage is 1.52% on members and 1.3% on clauses:
segmentation multiplied the numerator (88 members → 440 cited clauses) but multiplied the denominator
faster (5,799 → 33,148), so the ratio barely moved. The low harness figure is not an artifact of
counting whole prompts.

#### The ask-classifier I built to sharpen this was rejected on measurement

8.0% is a **lower bound on ask coverage**, because the denominator carries non-ask clauses: pasted
logs, status reports, metadata dumps. To tighten it, clauses were filtered by an explicit ask-cue rule
set (imperative opener, request phrasing, question mark, question opener), which selected 7,416 of
33,148 harness clauses (22.4%). That rule set gated a candidate headline of **0.7%**, so it was
validated rather than trusted: 30 predicted-ask clauses and 15 rejected clauses, seeded
(`evidence/sample_ask_rules.py`, `random.seed(23)`), labelled by hand
(`evidence/ask_rule_labels.json`), scored (`evidence/score_ask_rules.py`).

| Measure | Value |
|---|---:|
| precision — predicted asks that are asks | **0.733** (22/30) |
| ask rate in the rejected stratum — the miss rate | **0.267** (4/15) |
| estimated true ask clauses | **≈ 12,300** of 33,148 (37.1%) |
| **recall** | **0.44** |

**Recall of 0.44 means the gate misses more than half the asks**, so its denominator is not a
measurement and 0.7% was withheld. The 7,416-clause denominator understates the ask population by
~40%, which — had it been used — would have inflated coverage in my own favour. That is the same
failure mode as revs 1, 2 and 4, caught before publication this time rather than after.

Correcting numerator and denominator for the gate's measured error gives harness ask-clause coverage
of **1.4%–1.7%**. Four independent cuts now agree:

| Cut | Harness coverage |
|---|---:|
| members, strict substring (Rev 6 floor) | 1.52% |
| members, upper bound if every sampled `NEW_ASK` is missed | 3.35% |
| clauses, all (mechanical, no classifier) | 1.3% |
| clauses, ask-gated and corrected for gate error | 1.4–1.7% |

The gate's error does not widen that band much because both its false positives and its false
negatives are diluted across a large denominator. **Granularity was not the problem; recall of the
operator's asks is.** The headline is the clause-level figure: **8.0% of 43,305** on the mechanical
substring test alone, raised to **at least 10.7%** once the semantic recall measured in §3i is counted,
with 1.3–1.7% as the harness-specific one.

Two limits, stated so this is not over-claimed:

- Labels came from **one coder**, and clauses were judged without their parent message, which biases
  terse fragments toward `NOT_ASK`. A second rater would move precision and recall by several points.
  The conclusion used here — that recall is well below 0.9 — is robust to that; the exact 0.44 is not.
- **iMessage and KCode clauses were segmented but not sampled.** iMessage's 18.1% and phone's 41.5%
  are clause-count ratios with unmeasured contamination, exactly as §3e says of the iMessage member
  figures.

### Corrected statement

The register **is** a verbatim-anchored extraction of real operator utterances: 98.9% of its quotes
appear in the phone-chat message store and 96.7% appear somewhere in a mined channel. The register
**is not** a complete capture of operator intent, and the reason is now measured rather than inferred:
it draws from **one** channel. It covers 26.3% of iMessage distinct messages, 1.5% of the harness
corpus, 1.2% of KCode, and **15.0% of the 11,752-member union**. The migration gate stays closed on an
order-of-magnitude shortfall, not on a disputed ratio.

That conclusion was tested against the strongest structural objection available — that the union
compares intents to whole prompts — and **survived it**. Re-cut at clause granularity (§3f) the register
cites **3,463 of 43,305 distinct operator clauses (8.0%)**, and harness coverage moves only from 1.52%
to 1.3–1.7% depending on how the denominator is cut. The shortfall is real, not a units artifact.


### 3g. The 98 `source_ref` harvest documents are lost, and what that costs

Every ask carries a `source_ref` in `reg_provenance`, drawn from exactly **98 distinct values**. All 98
are bare filenames with no directory component (`October172026-02.md`, `October172026-p2.md`, and 8
with no index at all such as `October22026.md`). **0 of the 98 resolves.** The documents that sat
between the mined messages and the register cannot be produced.

Predicate in every case was `find <root> -maxdepth N -name '*20[0-9][0-9]-*.md'` plus
`git rev-list --all --objects` for the git tree. Roots searched, all returning zero:

| Root | Depth | Matches |
|---|---:|---:|
| `phenotype-registry` working tree | 6 | 0 |
| `phenotype-registry` all git objects, all refs, whole object DB | full | 0 |
| `phenotype-registry` deleted paths (`--diff-filter=D`) | full | 0 |
| `~/CodeProjects/Phenotype/repos` | 5 | 0 |
| `~/CodeProjects/temp` | 8 | 0 |
| `~/CodeProjects/{Exports,backups,docs,reports,infra,custody}` | 6 | 0 |
| `~/Desktop`, `~/Downloads`, `~/Documents`, `~/.Trash` | 4 | 0 |
| `~/.jcode/scratch`, `~/.hermes` | 3 | 0 |
| chat-harvest archives in the PhenoRegistry restore tree (2 archives, 1,891 entries) | n/a | 0 |
| Time Machine | n/a | no destinations configured |

**The loss is real; the provenance claim survives it.** Two things were tested instead of assumed.

*Quote-level anchoring.* The SQL ledger has **no quote column on `reg_asks`** — its text-bearing
column is `interpretation` (a cleaned rendering), and the verbatim message is reached through
`reg_asks.utterance_id`. That join resolves for **2,252 of 2,259** asks, the `reg_ask_messages`
origin link holds for the same 2,252, and the remaining **7 agree across three independent
signals**: `source_missing = 1`, `utterance_id IS NULL`, and no message link (ASK-000345,
ASK-000637, ASK-000664, ASK-001844, ASK-002254, ASK-002255, ASK-002256). Nothing fails silently.

*Pointer coherence.* With the documents gone, the `source_ref` values can still be tested against
the messages they are linked to. Two readings, both measured:

| Reading | Rule | Result |
|---|---|---:|
| A, same-day | `source_ref` date equals the linked message's date | 2,211 / 2,252 (**98.18%**) |
| B, window end | `source_ref` date equals the **latest** message date among that document's asks | 98 / 98 docs (**100%**), covering 2,252 / 2,252 asks |

Reading B is the correct model, and the measurement says why: **69 of the 98 documents are
single-day** (message span exactly 0 days), while **29 are rollups** spanning 1–27 days, and in
**29 of 29** the filename date is exactly the last message date in the rollup. The filename is the
harvest date (window end), not a per-message date. Reading A's 41 "mismatches" are all these rollup
asks, every delta negative, concentrated at −7d (6), −2d (7), −4d (4) and −1d (3). The `source_ref`
values are therefore not decorative: they are internally consistent under a single model that
predates the test.

**What is actually lost.** Two questions can no longer be answered:

1. Whether the register's 2,259 asks are the *whole* of what the harvest captured. Ask-level recall
   against the harvest cannot be measured, because the harvest no longer exists. That matters for
   the completeness question specifically: the loss removes one of the few remaining ways to test
   whether asks were dropped between mining and register.
2. Whether each register entry faithfully transcribes its harvest document, as opposed to faithfully
   transcribing the *message*. The latter is verified (§3d, 100% of testable links); the former is
   not.

Neither question is about quote fidelity, which is verified. Both are about the harvest's own
coverage. Recorded as a loss, not repaired, and not waived: the migration gate (§8) keeps it open.

**The register is not credential-free.** Because this corpus descends from a dataset whose
redaction history is not uniform, "clean" had to be tested rather than assumed. Scanning all
8,042 `reg_utterances` for JWT, bearer, `sk-`/AWS key, OTP-in-context and URL credential-parameter
shapes returns **2 rows**, both `role = assistant`, both a `?code=` callback parameter (UTT-004428 on
a local service port, UTT-004470 on a project subdomain). Zero JWT, zero OTP, zero bearer, zero
key-shaped hits. Two rows is small but not zero, so **SessionLedger ingest must scrub URL credential
parameters** rather than trust the register as clean. Hostnames are withheld here because this
repository is public; they are recoverable from the two utterance ids in `ledger.db`.

---

### 3h. A true semantic probe: capture exists, but the detector is too weak to size it

§3f measured coverage by asking whether a register ask's quote appears **verbatim** inside a clause
unit. That is a substring test, so it cannot credit "hide secrets" for "restrict private sources",
and the resulting 8.0% may be an artifact of the method rather than a property of the register. The
only way to tell is to test meaning instead of characters.

**A route existed after all.** Earlier notes recorded that no embedding route was available. That was
measured against Python packages (`numpy`, `torch`, `sentence_transformers`, `mlx`): none installed.
It was never measured against `llama.cpp`, which **is** on this host (`/opt/homebrew/bin/llama-embedding`,
build 10270) and pulls GGUF models on demand, so a real embedding model needs no Python ML stack.

**The model was chosen by a test with a known answer, not by reputation.** `evidence/probe_paraphrase.py`
embeds 17 sentences: six paraphrase pairs written to share meaning while avoiding shared wording, plus
five distractors, with chance top-1 at 6.2%. Top-1 retrieval is the metric, because min-max margin is
broken by legitimately-related non-paraphrases.

| Candidate | Top-1 | Ranks |
|---|---:|---|
| `nomic-embed-text-v1.5` f16, raw | **12/12** | all 1 |
| `nomic-embed-text-v1.5` f16, `clustering:` prefix | 10/12 | two 2s |
| `bge-small-en-v1.5` f16, raw | 9/12 | 2, 4, 3 |

nomic raw is the model of record. The probe is small: 12/12 with the rule of three implies a 95% lower
bound near 0.78, so it establishes gross separation and cannot certify accuracy to the last percent.

**The probe.** `evidence/semantic_coverage_probe.py` rebuilds the uncited population with the published
segmentation, keeping only clause units that pass the ask-cue rule, and embeds them against all 2,259
register interpretations. That population is **8,819 distinct uncited ask-cue units** (harness 7,287,
iMessage 1,012, KCode 527, phone 435) — a different and smaller denominator than the 43,305 all-unit
figure, and the two are never combined. A fixed-seed sample of 800 was scored; nearest-ask cosine ran
median **0.626**, p90 **0.707**, max **0.880**.

**Then the retrieval output was hand-labelled**, because top-1 cosine is a candidate generator, not a
verdict. The 30 highest-scoring pairs (`0.754`-`0.880`) and the 15 lowest (`0.467`-`0.518`) were read
against both the ask's interpretation and its source quote
(`evidence/semantic_label_review.json`).

| Band | M (captured) | W (adjacent) | N | Precision, strict | Precision, lenient |
|---|---:|---:|---:|---:|---:|
| High, top 30 | 17 | 5 | 8 | **0.567** | 0.733 |
| Low, bottom 15 | 0 | 0 | 15 | 0.000 | 0.000 |

The low band is uniformly transcription noise or social chatter against an unrelated ask, so the
negative side is clean. The high band is the problem: **8 of the 30 best-scoring pairs are
adjacent-but-different intents** — "do not push" against "do not force push", "list the repos you want
to delete" against "report the re-deletion path for each of the 5 repos", "is the MiniMax key
configured" against "is the MiniMax key needed". A cosine threshold therefore cannot certify capture.

**The headline is withheld, deliberately.** A semantic coverage estimate needs recall as well as
precision. Only 45 of 800 pairs were labelled, matches below the top-30 cut are uncounted, and high-band
precision is well short of certainty, so extrapolating would multiply a weak detector by an unknown miss
rate. `evidence/score_semantic_labels.py` records `semantic_coverage_pct: NOT PUBLISHED` with the
condition that would unblock it (label a random, non-stratified sample so recall is estimated on the same
distribution, or add a second rater and widen the high band).

**What can be stated is a floor, which needs no recall.** Among the 800 sampled uncited clauses, **17 are
confirmed captured** by a register ask — **2.12%** of the sample on strict labels (**2.75%** counting
adjacent-but-partial). This is a lower bound, not a rate: matches below the cut are simply not counted.
It is enough to establish two things. Semantic capture **does** exist where the substring test reported
none, so the 8.0% structural figure is genuinely a floor and not a complete miss. And it is small, so the
shortfall is **not primarily a lexical artifact** — the method explains a little, not the order of
magnitude. Compare the distributional TF-IDF probe (§3b), which found **0 of 12** high-band pairs were the
same intent: with a real embedding model the same question yields 17 of 30. Method mattered; the answer
still did not become comfortable.

**The gate is unchanged, and §3i supplies the number this section could not.** A floor of 2.12% on top
of an 8.0% structural figure closes nothing. Measured on a random sample instead of a stratified band,
the semantic share is **13.3%** of uncited ask-cue clauses, which puts union coverage at **≥10.7%**
[9.4–12.9] — larger than 8.0%, still an order-of-magnitude shortfall, and still not a complete
accounting, because the uncited non-ask-cue units were never probed. The register is incomplete, the
shortfall is real, it is not merely a substring artifact, and its size is now **bounded rather than
unknown**.

| Artifact | What it proves |
|---|---|
| `evidence/probe_paraphrase.py` + `probe_paraphrase.json` | the model choice, with the test that produced it |
| `evidence/semantic_coverage_probe.py` + `semantic_coverage_probe.json` | population, sample, scores, and the 45-pair label sheet |
| `evidence/semantic_label_review.json` | the hand labels and the reason for each |
| `evidence/score_semantic_labels.py` + `semantic_scored.json` | every figure above, recomputed from those two files |

The label sheet quotes raw corpus text, so it was scrubbed before commit: 7 email and URL matches
redacted. The scores refer to the pre-redaction strings; the scorer still reproduces identical output
from the redacted files, so the figures hold, but the artifact records a run rather than a re-runnable
corpus.

Rev 11 withdraws this section's 2.12% **as an estimate** of semantic coverage while keeping it as a
floor: it was computed from a band deliberately enriched for captures, so it could never be more than a
lower bound. The measurements below remain valid and are not superseded. §3i measures the same
quantity on a random draw.

---

## 3i. Recall, measured on a random sample: 13.3% at k=5, 0.0% at k=1

§3h could not publish a rate, and said so. The reason was structural: its 45 labelled pairs were the
top 30 by similarity plus the bottom 15. A fraction whose **numerator** comes from a band chosen for
being rich in captures, divided by the whole sample, can only be a floor. **Recall** — of all clauses,
what share the register can reach at all — was never measured, so a coverage percentage was not
computable from that design no matter how the labels fell.

The increment that fixes it is not a better model. It is a **random, unstratified sample, labelled
blind.** `evidence/recall_probe.py` draws 60 clause units with `SEED 20261113` (deliberately different
from the probe's `20261112`), retrieves **top-5** candidates for each, and asserts on every run that the
rebuilt population equals the published **8,819** (harness 7,287 / imessage 1,012 / kcode 527 / phone
435) — it refuses to sample on denominator drift.

**Blinding is structural, not asserted.** The tool writes two files. `recall_label_sheet.json` holds
the clause and its candidates **shuffled, with rank and cosine stripped**; `recall_candidates.json`
holds the same pairs *with* rank and cosine and is read only by the scorer. The labeller could not see
which candidate the model ranked first, so the model's ordering could not anchor the judgement.

| measure | k/n | rate | 95% Wilson |
|---|---|---|---|
| capture@5, strict (same intent) | 8/60 | **13.3%** | 6.9–24.2% |
| capture@5, lenient (incl. adjacent) | 10/60 | 16.7% | 9.3–28.0% |
| capture@1, strict | 0/60 | **0.0%** | 0.0–6.0% |

The capture@1 line is the most informative result here and the least convenient. All eight strict
captures landed at ranks **2, 2, 2, 3, 3, 4, 4, 5** — not one was the model's own first choice. At the
similarity levels typical of a random draw the nearest neighbour is nearly always an
adjacent-but-different intent. Two consequences follow, and they point in opposite directions:

- The register **does** hold these intents, reachable within five candidates. Semantic capture is real
  and roughly **ten times** the floor §3h could certify.
- **Top-1 lookup on this corpus is not usable.** Any design that reads one nearest neighbour and calls
  it the match will be wrong essentially every time, and would report a register far emptier than it
  is. This also explains retroactively how §3h's 17/30 was possible at all: it was measured where
  similarity is high (0.75–0.88), and precision there is a different quantity from recall here.

Candidate-level precision is reported for the same reason, because "found in 5" and "good retrieval"
are not the same claim: at most **8 of 300** retrieved candidates carried the same intent as their
clause (≤**2.7%**), treating unmarked candidates as negative. A five-candidate lookup is therefore a
recall mechanism, not a discovery mechanism. It finds the answer for one clause in eight and returns
mostly neighbours on the way — which is an argument that the register must actually *contain* intent
rather than that a better index would rescue an incomplete one.

**Projection, within its own denominator.** 8,819 × 13.3% ≈ **1,176** captured units (95% interval
610–2,131). Because those units are by construction *not* in the structural 3,463 cited units, the two
terms are disjoint and may be added:

> (3,463 structurally cited + ≈1,176 semantically captured) / 43,305 = **10.7%** [9.4–12.9%]

That figure is emitted by the scorer under a key named `derived_union_lower_bound`, and the name is the
whole caveat. It is **derived, not measured on the union**: the 31,023 uncited units that are *not*
ask-cue were never probed, so semantic capture there is unknown and this stays a lower bound. It must
never be added to, or averaged with, the 8.0% structural figure — it already contains it.

The honest revision is quantitative and does not flatter the register: published coverage rises from
**8.0%** to **at least 10.7%**, so the register holds roughly a ninth to an eighth of expressed intent
rather than a twelfth. The shortfall is still an order of magnitude, and the verdict is unchanged in
kind. **Harness coverage (1.3–1.7%) is untouched** — this probe is aggregate and per-source capture was
not measured — so the migration gate stays closed on the same evidence.

What would move it further, stated as limits rather than plans: `n=60` gives an interval spanning a
factor of 3.5, so a larger draw tightens it without changing the method; the labeller is single and is
the agent that built the retrieval, so an independent second labeller is the only real precision
control; and probing the 31,023 non-ask-cue uncited units is what would convert 10.7% from a lower
bound into coverage of everything.

Rev 10's high-band precision (0.567 strict) should not be reused as corpus precision. The corpus
figures are the ones above: **13.3% of clauses reachable at k=5, 0.0% at k=1**.

| Artifact | Carries |
|---|---|
| `evidence/recall_probe.py` | sampling, retrieval, denominator assertion, blind two-file split |
| `evidence/recall_label_sheet.json` | 60 clauses, shuffled candidates, hand labels `M`/`W`/`N` with a reason each |
| `evidence/recall_candidates.json` | the same pairs with rank and cosine; read only by the scorer |
| `evidence/recall_score.py` + `recall_scored.json` | every figure above, recomputed from those two files |

Both text-bearing files were scanned before staging and **8 matches across the two files** were redacted
(2 emails and 2 bare numeric ids per file) to typed tokens. `recall_score.py` reproduces
**byte-identical** output from the redacted files, so every figure above holds, but the artifact records
a run rather than a re-runnable corpus. This is the third time corpus text has carried contact data into
an artifact; the scan is a pipeline step now, not a review.

---

## 4. Occurrence volume is only partly recovered

`evidence/OCCURRENCE-RECOUNT.md` established that **every previously mined file has
`records == distinct`**. All of them were globally deduplicated by `text_sha256`, so no
file-level repeat factor can be recovered from them. Occurrence volume survives only where a
source was re-mined:

| Source | Occurrences | Distinct | Repeat factor | Evidence state |
|---|---:|---:|---:|---|
| jcode | 55,119 | 24,715 | 2.23x | RE-MINED |
| codex | 9,650 | 856 | 11.3x | RE-MINED |
| forge | 15,209 | 15,209 | n/a | DEDUPED_INPUT |
| imessage | 6,418 | 6,363 | 1.01x | **RE-MINED** (`evidence/imessage_kcode_recount.json`) |
| kcode | 2,457 | 166 | 14.8x | **RE-MINED** (1,253 session files) |
| herdr | 8 | 8 | n/a | NOT_RECOVERABLE |

This table previously carried imessage as `7,684 / 7,684 / DEDUPED_INPUT` and kcode as
`196 / 196 / DEDUPED_INPUT`. Both were the same defect the codex section below describes — a
carried pre-dedupe number presented as a measurement. Re-mining put iMessage at 6,418 occurrences
collapsing to **6,363** distinct (a near no-op, because outbound texts rarely repeat) and KCode at
2,457 occurrences collapsing to **166** (a 14.8x factor, because its 1,253 session files are mostly
canary stubs repeating the same prompts). The direction of the two errors was opposite.

Consequence: any statement about "how many times the operator asked something" is supportable for
jcode, codex, iMessage and KCode. Forge and herdr remain unrecoverable at occurrence level.

---

## 5. The codex correction, stated plainly

The codex lane reported 401 records. That figure was wrong by 24.1x, and the mechanism matters
more than the number:

- 2,567 files exist; only **180** are plain `.jsonl`. **2,380** are `.jsonl.zst` and **7** are
  `.jsonl.zst.zst`. The miner's `*.jsonl` glob read **7%** of the corpus.
- Counting only the 180 plain files yields **399**, which is why 401 looked self-consistent.
- The full zstd-aware pass yields **9,650** occurrences and **405 distinct non-injected** strings.

So 401 approximated *distinct vocabulary* while presenting itself as *record count*. A
distinct-string count can be internally plausible and still be the wrong quantity. The same
class of error produced kcode's 196 and the old jcode figure of 16,887.

---

## 6. What remains unmeasured

| Item | State | Why it matters |
|---|---|---|
| Other harnesses / channels | UNKNOWN | Sources not enumerated cannot be asserted absent. An absent source is not evidence of no intent. |
| Forge authorship | FAIL | 99.5% of forge bytes carry contamination flags; see §7. Forge is 169.7 MB of the 203 MB merged corpus. |
| Intent-level dedupe | NOT_RUN | No model exists for deciding that two different strings express one intent. String counts therefore overstate intents. |
| Paperclip / herdr volumes | UNKNOWN | Not probed this session. |
| iMessage substantive ratio | **MEASURED** | 9,011 text-bearing outbound rows → 6,418 substantive → 6,363 distinct; collapse is a near no-op (`evidence/imessage_kcode_recount.json`). |
| Semantic coverage | **MEASURED — 13.3% at k=5** | Random 60-clause sample, labelled blind: **8/60 = 13.3%** [6.9–24.2] of uncited ask-cue clauses are reachable within five candidates, **0/60** at k=1 (§3i). Because those units are disjoint from the 3,463 structurally cited ones, union coverage is at least **10.7%** [9.4–12.9], replacing the 8.0% structural-only headline. Still a **lower bound**: the 31,023 uncited non-ask-cue units were never probed. §3h's 2.12% survives as a floor only. |
| Semantic retrieval precision | **MEASURED — ≤2.7%** | At most 8 of 300 retrieved candidates carried the same intent as their clause, so top-1 lookup is unusable on this corpus: every strict capture sat at rank 2–5 (§3i). A better index does not fix an incomplete register. |

---

## 7. Forge is contamination-dominated by volume

`evidence/FORGE-AUTHENTICITY.md`, sample of the first 2,000 of 15,209 records:

| Flags | Records | Text bytes | byte share |
|---:|---:|---:|---:|
| 0 | 1,556 | 453,339 | **0.47%** |
| 1 | 153 | 1,549,184 | 1.60% |
| 2 | 55 | 9,060,641 | 9.35% |
| 3+ | 236 | 85,873,729 | **88.59%** |

77.8% of *records* are zero-flag, which would read as "mostly clean". Those records hold 0.47% of
the *bytes*. The 444 flagged records hold 99.5% of the text. A record-count verdict and a
byte-volume verdict point in opposite directions here, and any figure quoted from forge must say
which one it used.

The flags are evidence of contamination, not proof of it, and zero flags do not prove a record is
a single operator turn. Forge is therefore excluded from §3 rather than weighted.

---

## 8. What would change this verdict

In order of strength:

1. ~~**Mine the register's own channel and the two unmined channels.**~~ **DONE (§3c).** iMessage
   (6,363 distinct) and KCode (166 distinct) are mined at occurrence level; the phone-chat channel is
   in `reg_utterances` (2,075 substantive distinct) and is itself an iMessage subset. Union coverage is
   **15.0%**, which supersedes the earlier `UNKNOWN`. What remains open is granularity and the
   denominator's composition (§3e), not channel scope.
2. ~~**Measure cross-channel overlap.**~~ **DONE (§3c).** Register quotes overlap the harness at 23.1%
   (466 of 2,018); channel-to-channel overlap is 517 (iMessage∩harness), 58 (KCode∩harness) and 1
   (KCode∩iMessage). Summing channel counts without that subtraction would double-count 576 members.
3. **Complete the external channels** (Gemini Takeout, OpenAI, Claude, Dot), which may add channels
   not yet known to exist at all.
4. **Register provenance repair**, re-stated against what is actually open. Link integrity is **closed**
   at zero wrong links (§3d); the carried "3 links are candidate wrong" figure was stale and is
   withdrawn. What remains: 0 of 98 `source_ref` paths resolve because the harvest `.md` documents are
   lost (§3g), and 7 asks are sourceless by three agreeing signals (§3g). The first of those is the
   only one that cannot be repaired from data at hand, and it is the reason ask-level recall against
   the harvest is unmeasurable.
5. **Scrub URL credential parameters before any SessionLedger ingest.** The register is not
   credential-free: 2 of 8,042 `reg_utterances` rows carry a `?code=` callback parameter (§3g). Small,
   not zero.

Do not use **distributional** similarity as a proxy for sameness of intent: it was tested and rejected
(0 of 12 high-band pairs were the same intent, §3b). A **true embedding** model is a different
instrument and was run (§3h): the same question yields 17 of 30, so semantic capture does exist, but
the detector's precision (0.567 strict) and unmeasured recall support a floor of 2.12%, not a rate.
Neither instrument, and no combination of them, takes the register from *incomplete* to *complete*.

None of these can make the register *complete*. They can only make the shortfall measurable.
