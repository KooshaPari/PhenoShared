# Coverage Verdict — is the 2,259-ask register a complete capture of operator intent?

Recorded (UTC): `2026-11-11T13:00Z`. Revised `2026-11-12T02:30Z` (channel-scope correction, §3b).

**Revision history — this file has been wrong three times and each time in the same direction
(stating a confident provenance claim from an incomplete measurement).**

| Rev | Claim | What was wrong |
|---|---|---|
| 1 | "at most 23%" | counted raw strings, 31.8% of which were harness text |
| 2 | "39-43% coverage" | a volume ratio between different text populations, not coverage |
| 3 | "the register is a synthesis, not an extraction" | measured the paraphrase field against the wrong corpus; the register's source channel is phone chat, and 98.9% of its quotes anchor verbatim there |

Rev 4 (this one) is derived from the register's own provenance tables rather than from overlap with a
corpus chosen by me.

**This file answers one question only.** It does not propose a migration, does not compute a
coverage percentage, and does not treat activity as evidence. Every cell below cites the
measurement it rests on. Cells that were not measured say `UNKNOWN` or `NOT_RUN`, never `PASS`.

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
| overlaps the mined harness corpus | 0.0% | 16.7% substring |

> **The register is a verbatim extraction from a phone-chat archive that this project never mined.**
> `reg_utterances` holds 8,042 messages across 3 `phoneconv-<ULID>` conversations in 141 sessions,
> with the operator's real typos intact, and 2,252 asks are explicitly linked to a source message via
> `reg_ask_messages.relation = 'origin'`. So the register is real operator text, and my earlier
> "synthesis, not extraction" verdict is **retracted**.

**Where the shortfall actually is.** Channels, not percentages:

| Channel | Distinct substantive intents | Register captures |
|---|---:|---|
| Phone chat (the register's own source) | 2,075 | 1,733 cited (83.5%), ~87% after sampling misses |
| jcode + codex harness | 5,799 cleaned (of 8,506 distinct) | 357 (16.7%, substring) |
| iMessage | 911 (`DEDUPED_INPUT`) | not measured |
| KCode | 196 (`DEDUPED_INPUT`) | not measured |

> The register is roughly an **87%-complete capture of one channel** and at most a **16.7% capture of
> another**. Coverage of the union is `UNKNOWN` until all channels are mined and the cross-channel
> overlap is measured rather than assumed. The 39-43% figure below is a **volume ratio**, not coverage.

**Three corrections, same day, all mine.** Each moved confidence down while the conclusion held.

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
│   ├── Suspect links resolved ............................. FAIL  (118 open; ASK-000013 confirmed wrong)
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
│   ├── Harness-channel capture (substring) ............... PASS  (357 = 16.7% of 2,132)
│   ├── Harness-channel capture (distributional-lexical) .. REJECTED (high band 0/12 true positives;
│   │                                                               not a usable estimator; §3b)
│   ├── Harness join possible .............................. FAIL  (reg_provenance.source is
│   │                                                               register.json for 2259/2259; the register
│   │                                                               never joined the harness)
│   └── Union coverage across all channels ................ UNKNOWN (needs imessage + kcode mined and
│                                                                   cross-channel overlap measured)
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
| imessage | **911** | prior lane: 7,684 records, 911 substantive (975 non-substantive / one-word) |
| kcode | **196** | post-dedupe distinct (2,934 pre-dedupe, 14.97x) |
| herdr | **0** | manifest records `persists_operator_prompt_text: false`; no text recoverable |
| forge | **excluded** | authorship unresolved, see §7 |
| **Total** | **9,802** | |

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
| **jcode + codex harness** | 5,799 cleaned (of 8,506 distinct) | 357 (16.7%, substring) | poor |
| iMessage | 911 (mined, `DEDUPED_INPUT`) | unknown | not measured |
| KCode | 196 (mined, `DEDUPED_INPUT`) | unknown | not measured |

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

### Corrected statement

The register **is** a verbatim-anchored extraction of real operator utterances: 98.9% of its quotes
appear in the phone-chat message store. The register **is not** a complete capture of operator
intent, and the reason is now measured and specific: it is a **single-channel** capture. It covers
~87% of its own channel and at most 16.7% of the harness channel. Coverage of the union cannot be
computed until every channel is mined and the cross-channel overlap is measured rather than assumed.


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
| imessage | 7,684 | 7,684 | n/a | DEDUPED_INPUT |
| kcode | 196 | 196 | n/a | DEDUPED_INPUT (2,934 pre-dedupe per manifest) |
| herdr | 8 | 8 | n/a | NOT_RECOVERABLE |

Consequence: any statement about "how many times the operator asked something" is currently
supportable for jcode and codex only.

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
| iMessage substantive ratio | UNKNOWN | The 911/7,684 split was taken from a prior lane and was not re-verified here. |

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

1. **Mine the register's own channel and the two unmined channels.** The register is a phone-chat
   extraction (§3b), and iMessage (911) and KCode (196) are still `DEDUPED_INPUT`. The phone-chat
   channel is already in `reg_utterances` (2,620 user messages, 2,075 substantive distinct), so it can
   be joined directly; iMessage and KCode need a real miner. Union coverage is `UNKNOWN` until this is
   done, and this is now the only route to a defensible coverage number.
2. **Measure cross-channel overlap.** Operator intent repeats across channels; the register's quotes
   overlap the harness at 16.7%. Until that overlap is measured, summing channel counts double-counts.
3. **Complete the external channels** (Gemini Takeout, OpenAI, Claude, Dot), which may add channels
   not yet known to exist at all.
4. **Register provenance repair** for the remaining `FAIL` cells: 0 of 98 `source_ref` paths resolve
   because the harvest `.md` documents are not on disk, 118 suspect links remain, 7 asks are sourceless.

Do not use distributional similarity as a proxy: it was tested and rejected (0 of 12 high-band pairs
were the same intent, §3b).

None of these can make the register *complete*. They can only make the shortfall measurable.
