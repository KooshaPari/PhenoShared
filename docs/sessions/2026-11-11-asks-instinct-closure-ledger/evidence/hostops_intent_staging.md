# host-ops intent staging — asks-instinct closure ledger (I15)
# Staging file only. DO NOT apply while host-ops working tree is dirty.

## A. NEXT INTENT NUMBER
I15. Evidence: highest existing heading in closure/INTENTS.md is `## I14` (line 241); next is I15.

## B. INTENT ENTRY (paste verbatim into closure/INTENTS.md)

## I15 — Asks register coverage is measured, not asserted

**Intent.** From the 2026-11-11 asks-instinct verdict: structural coverage, semantic capture
(ask-cue and non-ask-cue), the union frame, and ask-cue authorship are each a measured quantity
with a committed artifact and an executable check, not a carried number; ask-level recall is
acknowledged as permanently unmeasurable and the operator-gated items stay open.

| ID | Deliverable | Closed when |
|----|-------------|-------------|
| D15.1 | Structural coverage is a consistent count ratio | evidence/coverage_consistency.json frame_a_set_union reports cited 1938 and denominator 43648 |
| D15.2 | Ask-cue semantic capture is measured on a random sample | evidence/recall_scored.json reproduces capture_at_5 = 8/60 |
| D15.3 | Non-ask-cue semantic capture is measured on a random sample | evidence/nonask_scored.json reproduces 2/60 strict |
| D15.4 | Union frame A is derived in ONE frame | evidence/nonask_scored.json emits union.frame_a with numerator ~4210 and denominator 43648 and explicitly no joint CI claim |
| D15.5 | Ask-cue authorship is measured, not assumed | evidence/askcue_speaker_scored.json exists with a Wilson interval and single_labeller=true caveat, and the verdict cites the interval rather than a point value |
| D15.6 | Independent second labeller on both sheets | a second labels file exists for BOTH sheets and an inter-labeller agreement figure is committed |

NOTE (operator-gated, no agent can close):
- 98/98 harvest docs lost (October*.md); ask-level recall permanently unmeasurable.
- 2 rows with a URL credential parameter (UTT-004428, UTT-004470) await a scrub ruling.
- Unredacted-history commits e77430b5, f8321714, 4b1f2eb2 await a decision.

## C. ROW CALLS (add to closure/scripts/closure-check; STATE = NOT_RUN until artifact committed)

row D15.1 I15 NOT_RUN "coverage_consistency.json frame_a_set_union cited=1938 denom=43648 not yet wired as a check" "evidence/coverage_consistency.json"
row D15.2 I15 NOT_RUN "recall_scored.json capture_at_5=8/60 not yet wired as a check" "evidence/recall_scored.json"
row D15.3 I15 NOT_RUN "nonask_scored.json capture_at_5 strict=2/60 not yet wired as a check" "evidence/nonask_scored.json"
row D15.4 I15 NOT_RUN "nonask_scored.json union.frame_a ~4210/43648 not yet wired as a check" "evidence/nonask_scored.json"
row D15.5 I15 NOT_RUN "askcue_speaker_scored.json exists (operator 52/60, Wilson 75.8-93.1) but is not committed and not wired as a check" "evidence/askcue_speaker_scored.json"
row D15.6 I15 NOT_RUN "no second-labeller file for either sheet" "evidence/*_speaker_sheet.json"

## D. config.sh CHANGE

In closure/scripts/config.sh, intent_title(), add before the `*)` line:
    I15) echo "Asks register coverage is measured, not asserted" ;;

## E. APPLY ORDER

1. Verify host-ops working tree is clean: `git -C ~/CodeProjects/host-ops status --porcelain` must be empty.
2. Append the I15 intent entry (Section B) to closure/INTENTS.md.
3. Add the six row calls (Section C) to closure/scripts/closure-check.
4. Add the I15 case to closure/scripts/config.sh intent_title() (Section D).
5. Run `closure/scripts/closure-check` (regenerates closure/TREE.md + closure/STATE.json).
6. Commit INTENTS.md + closure-check + config.sh + TREE.md + STATE.json together.
7. NEVER run a second scheduler (one ledger, one evaluator).

## F. GUARD LINE

DO NOT APPLY while closure/INTENTS.md, closure/STATE.json, closure/TREE.md, closure/scripts/closure-check or closure/scripts/desk-probe.sh are modified -- that is another actor's in-flight D11.4 watchdog work.
file_path">
/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared-space/feat/researchledger-ingest-v2/wtree/docs/sessions/2026-11-11-asks-instinct-closure-ledger/evidence/hostops_intent_staging.md