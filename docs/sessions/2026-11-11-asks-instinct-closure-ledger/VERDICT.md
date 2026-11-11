# Coverage Verdict — is the 2,259-ask register a complete capture of operator intent?

Recorded (UTC): `2026-11-11T13:00Z`

**This file answers one question only.** It does not propose a migration, does not compute a
coverage percentage, and does not treat activity as evidence. Every cell below cites the
measurement it rests on. Cells that were not measured say `UNKNOWN` or `NOT_RUN`, never `PASS`.

---

## 1. The answer

**No. The register is not a complete capture of operator intent, and it cannot be made one by
inspection alone.** This is a structural finding, not a shortfall of a few percent:

> At least **9,802 distinct non-injected operator strings** have been measured across reproducible
> evidence, against **2,259 register entries**. Even under the most generous assumption — that
> every register entry uniquely corresponds to one distinct string — at most **23%** of distinct
> operator strings can be represented. The true intent count is *lower* than the string count,
> because retries and one-word nudges inflate it, so 23% is an **upper bound**, not an estimate.

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
│   └── Duplicate suppression at the *intent* level ......... NOT_RUN (no intent-level model exists)
├── Register integrity
│   ├── source_ref paths resolve ............................ FAIL  (0 of 98)
│   ├── Suspect links resolved ............................. FAIL  (118 open; ASK-000013 confirmed wrong)
│   ├── Unpromoted user utterances ......................... FAIL  (805)
│   ├── Sourceless asks .................................... FAIL  (7)
│   └── Harness join possible .............................. FAIL  (reg_provenance.source is
│                                                                   register.json for 2259/2259)
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
| codex | **405** | `evidence/CODEX-REEXTRACT.md`: 9,650 occurrences, 3,942 injected, 5,708 non-injected → 405 distinct |
| imessage | **911** | prior lane: 7,684 records, 911 substantive (975 non-substantive / one-word) |
| kcode | **196** | post-dedupe distinct (2,934 pre-dedupe, 14.97x) |
| herdr | **0** | manifest records `persists_operator_prompt_text: false`; no text recoverable |
| forge | **excluded** | authorship unresolved, see §7 |
| **Total** | **9,802** | |

Forge is deliberately excluded from the numerator rather than estimated. Including a
questionable source to strengthen a conclusion would be the same error this document exists to
correct.

`9,802 / 2,259 = 4.34` — there are at least 4.3 distinct operator strings for every register ask.

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

1. An intent-level model that groups distinct strings into intents, applied to both the register
   and the corpus. Without it, no coverage percentage is defensible in either direction.
2. Completion of the external channels, which could add unseen intent, making the shortfall larger.
3. Register provenance repair (the five `FAIL` cells in §2), without which the register cannot be
   audited at all.

None of these can make the register *complete*. They can only make the shortfall measurable.
