# Recall instrument design (ask-level, denominator from the corpus)

Status: frame + blank sheet only. No labelling, no recall figure. Nothing here measures.

## Why a corpus-derived denominator

Ask-level recall needs `register-asks-that-should-have-been-found / asks-that-exist`.
The 98 declared-lost harvest documents would have supplied the denominator; they are
gone. So the denominator is built from the corpus that still exists (`chat.db`,
`~/.jcode` / `~/.codex` occurrence JSONL, `~/.kcode/sessions`), not from the lost docs.

The register is never used to build the denominator. It is used only after the
reference inventory is labelled, as the numerator.

## Unit of sampling: fixed-size transcript windows, not whole sessions

A **window is 6 consecutive operator-authored turns inside one session**, ordered by
the session's own clock (harness: `ts` then `msg_index`; iMessage: `ROWID`; kcode:
message list order). Session = `session_id` / `chat_id` / kcode session file.

Why windows and not whole sessions:

- Session length is extremely skewed (1 turn to thousands). Whole-session sampling
  gives one draw thousands of times the information of another, and a single long
  session can dominate the estimate.
- An ask is a local event. Six adjacent turns carry enough context for a blind
  labeller to judge intent, without paying for turns that cannot contain the ask.
- Windows give a mechanical, reproducible boundary and a countable population.

Eligible turn = operator-authored, not harness-injected, substantive (reuses
`recount_imessage_kcode.keep()` / `norm()`: length >= 12 after normalisation and no
noise pattern). Assistant, tool, and system-injected turns are excluded from the
frame because the reference inventory is an inventory of **operator** asks.

Trailing partial windows are dropped. Every window therefore has exactly 6 turns,
so a window is one comparable unit.

## Strata: channel

Three disjoint channels: `harness` (jcode + codex), `imessage` (`chat.db` outbound),
`kcode` (`~/.kcode/sessions`). The `phone` channel is a *subset of iMessage*
(`reg_utterances` bodies re-derived from `chat.db`), so including it would let one
ask enter the frame twice. It is excluded by construction.

Allocation: n = 60 windows, proportional to the population of full windows in each
channel, with a floor of 8 per channel, largest-remainder rounding. Proportional
allocation gives the corpus-wide rate; the floor keeps every channel estimable on
its own.

## Seed

`20261121`. Deliberately different from `20261112` (semantic probe), `20261113`
(recall probe) and `20261114` (non-ask probe), so this draw is not a re-use of any
earlier sample.

## Independent reference inventory (blind labeller)

1. The labeller receives `recall_reference_sheet.json` only. It contains no register
   ask id, no interpretation, no embedding, no score.
2. For each window it writes down **every operator ask it can see**, as
   `{turn, quote, intent}` in `reference_asks`. An ask is a request, instruction, or
   directive from the operator; a question counts, a statement of fact does not.
3. The labeller must not open `ledger.db`, `register.json`, or
   `recall_reference_key.json` while labelling. The key holds only channel/session
   metadata and is withheld purely so the frame can be reconstructed.

The reference inventory is produced from the sample alone. It is not a re-reading of
the register.

## Recall formula

```
recall = |matched register asks| / |reference asks found|
```

**Matched, defined mechanically.** A register ask counts as matched only when both
hold:

1. **Provenance:** the ask's utterance resolves to a corpus turn inside a sampled
   window (`reg_asks.utterance_id -> reg_utterances.body_sha256` / normalised body,
   joined against the same session + window ordinal range recorded in the sheet).
2. **Intent:** the reference inventory has an ask recorded for that window whose
   `intent` the adjudicating reader judges to be the same intent. An ask that the
   register places on a neighbouring turn but that the reference labels as the same
   intent still counts, because the unit of truth is the window, not the turn.

Every reference ask that no register ask matches is a miss. Unmatched register asks
(asks whose utterance falls outside every sampled window) are neither hits nor
misses; they are out of frame, and the frame rate is reported as a rate over the
sampled windows only.

## The two things that can still go wrong

1. **The reference labeller misses asks.** A human reading six turns will miss some
   operator asks, so the denominator is too small and the computed recall is a
   **lower bound**, never an over-estimate. Mitigation: a second independent labeller
   on a 20% subsample; the union of the two is the working denominator, and their
   disagreement rate is reported next to the recall figure.
2. **Window boundaries split one ask.** A turn that is part of an ask whose other
   half sits in the adjacent window can be labelled as a whole ask in one window and
   as a fragment in the other, which inflates or deflates that window's count.
   Mitigation: the labeller labels only asks whose *directive* is inside the window,
   and a fragment of an ask completed outside the window is recorded as
   `intent: "fragment"` and excluded from the denominator.

Operational note, not a third statistical limitation: each window's `text` is
truncated to 1200 characters in the sheet. Windows are 6 turns, so truncation is
rare, but where it bites the labeller sees a prefix and the same lower-bound
argument applies.

## Files

| File | Role |
|---|---|
| `recall_reference_sheet.py` | draws the sample deterministically, writes the sheet + key |
| `recall_reference_sheet.json` | the blank labeller sheet: window text, `reference_asks: []`, `matched_register_ask_ids: []` |
| `recall_reference_key.json` | channel/session/timestamp metadata, withheld from the labeller |

Matching is a separate, later step. The sheet is emitted with both ask-id fields
empty on purpose: pre-filling them would destroy the blindness.
