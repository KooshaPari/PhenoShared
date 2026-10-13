# Emergent Garden research index

Campaign `eg-nested-corpus-2026-09`. Current unit: **Wave 5 source methods, Git lineage and evidence-admission checks**. Campaign completion remains partial.

## Current entry points

- [Wave 5 source review](WAVE-5-SOURCE-REVIEW.md): OMNI-EPIC methods, MineRL comparison controls, Picbreeder, timestep and historical Mindcraft.
- [Repository identity and ancestry](WAVE-5-LINEAGE-AND-TRANSFER.md): exact observed IDs and Git evidence, not inferred authorship or behavioral equivalence.
- [Execution checkpoint](WAVE-5-EXECUTION-CHECKPOINT.md): executed work, scope and unresolved evidence.
- [Direct-paper coverage](../data/primary-paper-coverage-v5.json): 19 selected-method records, not 19 reproductions.
- [Capture receipts](../data/wave-5-intake-receipts.json) and [synthetic admission results](../data/wave-5-admission-results.json).

## Preserved evidence

The [official census](2026-09-04-official-census-checkpoint.md) reconciled 74 public uploads: 62 non-empty descriptions, 528 description edges, 300 normalized target URLs and 93 domains. The [description ledger](../data/youtube-description-edges-v1.json) and [direct frontier](../data/direct-link-frontier-v1.json) preserve source locators and retrieved revisions. URL counts do not equal distinct works or full reviews.

[Wave 3 comments and synthesis](WAVE-3-COMMENTS-AND-SYNTHESIS.md), its [primary-source depth](WAVE-3-PRIMARY-SOURCES.md) and [receipt](../data/wave-3-execution-receipt.json) remain available. They reported 203 creator records reviewed and a chapter-parser correction. Missing private input is not silently replaced with invented evidence.

[Wave 4 checkpoint](WAVE-4-EXECUTION-CHECKPOINT.md), [method reviews](WAVE-4-METHODS-REVIEW.md), [transfer boundaries](WAVE-4-TRANSFER-BOUNDARIES.md), [transcript-route audit](../data/transcript-route-audit-v4.json) and [comment revalidation](../data/comment-revalidation-v4.json) preserve the previous unit. The actual Wave 4 package corrected the earlier three-file status stub.

The [anchor synthesis](WAVE-1-ANCHOR-CORPUS.md), [chronology](CREATOR-CHRONOLOGY-WAVE-1.md), [project identities](PROJECT-GALLERY-WAVE-1.md), [claim ledger](CLAIM-LEDGER-WAVE-1.md), [ontology](CONCEPT-ONTOLOGY-WAVE-1.md) and [portfolio mapping](PORTFOLIO-APPLICABILITY-WAVE-1.md) remain historical. Later corrections qualify their claims.

## Tools and validation

The [v2 collector](../../../../scripts/research/collect_emergent_garden_youtube_v2.py) checks public-upload reconciliation. [Comment intake](../../../../scripts/research/collect_emergent_garden_comments.py) accounts for incomplete reply sets. [Offline comment analysis](../../../../scripts/research/analyze_comment_corpus.py) requires the actual private inputs. The [new evidence checker](../../../../scripts/research/assess_research_evidence.py) checks record sufficiency and declared comparison controls; it is not a truth oracle. [Bundle verification](../../../../scripts/research/verify_research_bundle.py) checks required payloads and bytes without executing source material.

Wave 5 adds 12 tests to the 58-test suite. All 70 passed locally, and all 32 synthetic admission cases matched their expectations. A publication-run result, application-wide CI and live benchmark outcomes must be reported separately.

## Remaining limits

Full transcripts remain unacquired. The one-comment discrepancy, exhaustive audience review, broad recursive-source closure and historical behavior reconstruction remain open. The live Benchora experiment remains proposed. No source findings automatically authorize product-code changes.

The corpus supports family resemblance across different generative and adaptive systems, not a universal architecture or a rule that more agents are better. ResearchLedger stays canonical; RepoLedger stores append-only projection state; project drafts contain bounded proposals only.

Recorded API-data refresh-or-delete deadline: `2026-10-05T05:55:01Z`. No unattended service or release is claimed.
