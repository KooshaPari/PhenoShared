# Emergent Garden Direct-Link Expansion — Reconciled API Snapshot

**Campaign:** `eg-nested-corpus-2026-09`

**Acquired:** 2026-09-05T05:55:02Z; direct expansion completed at 05:55:31Z.

**Acquisition commit:** `7a48a604a4ff66d65b595b0e1eb1d9cd1f00ecce`

**Original output commit:** `6b41757eb9bb85eb1842a41920770758557b3def`

**Input description-edge SHA-256:** `181bda36d25c1a325b89032761fa26a9680097ec29431d0d85ecf0bfece20c0f`

## Verdict

The input is now a reconciled official YouTube Data API snapshot of 74 public uploads, not the earlier 15-record Atom window. Two ordered playlist enumerations matched, both channel counts were 74, every public video detail resolved, and all 13 reconciliation checks passed. This closes the credential-dependent inventory gap, not the transcript or research-completeness gaps.

The extractor found 528 video-to-URL edges and 300 distinct normalized URL targets across 93 domains. It selected 54 priority target URLs under the existing classifier and retrieved metadata for 53; one fetch failed. Retrieval success does not mean full source review, endorsement, or experiment reproduction.

## Exact coverage and counting units

- Public uploads reconciled: 74.
- Non-empty descriptions observed: 62; empty descriptions observed: 12.
- Videos containing extracted links: 58.
- Description edges: 528. Repeated links within a single description are deduplicated by the current extractor.
- Distinct normalized target URLs: 300. Different URLs can still identify the same work.
- Priority target URLs attempted: 54.
- GitHub target URLs attempted: 22, all with successful repository metadata retrieval.
- arXiv target URLs attempted: 19, all with successful metadata retrieval.
- Creator-page target URLs attempted: 13; 12 successful and one failed.
- Transcript texts acquired: 0.

The 22 GitHub targets must not be described as 22 distinct repositories. The resolved rows include repeated LifeEngine and Mindcraft identities from different source URLs. Preserve every discovery edge, but reconcile stable repository IDs before counting unique implementations. A successful repository lookup also does not imply that its README was available.

## Evidence and machine-readable records

[The census status](../data/youtube-census-status-v1.json) contains the two-pass reconciliation and failure lists. [The description-edge ledger](../data/youtube-description-edges-v1.json) preserves source videos, original URLs, canonical URLs, domains, and provisional edge classes. [The direct frontier](../data/direct-link-frontier-v1.json) contains all attempted targets, source-video relationships, fetched revisions or response hashes, and per-target outcomes.

[The manifest](../data/youtube-census-manifest-v2.json) records exact output hashes. [The completed acquisition run](https://github.com/KooshaPari/ResearchLedger/actions/runs/33948427726) ran the 21 offline tests, official acquisition, bounded expansion, formatting, credential-output check, and branch-only commit.

## Recorded failure

The root URL `https://evolvecode.io/` failed during this acquisition. Several deeper pages on the same site succeeded. This is a target-specific retrieval failure, not evidence that the project or all its pages are unavailable. Preserve the failed root record and examine its exact error before selecting a recovery route; do not silently substitute a working child page as though the root succeeded.

## Newly exposed research frontier

The full inventory adds older implementation and reference links that the recent Atom window did not cover. Examples include CodeEvolver, EvolutionSimulator, LifeEngine, StableDiffEvolution, hillclimbers, turmites, NeuralPatterns, and Mineflayer. The metadata frontier also includes POET, OMNI-EPIC, Generative Agents, Project Sid, and the MineCollab paper.

These are research leads established by description edges and retrieved metadata. Their technical mechanisms and applicability require full-text or code review at the retained versions. No new claim is accepted merely because a title resembles the campaign's preferred interpretation.

## Remaining uncertainty

The current parser produced zero chapter records, and the API returned a false caption flag for every video. Neither result demonstrates that the public player has no chapters or automatic captions. Validate parser behavior and provider semantics against supported source evidence; keep chapter extraction and transcript availability separate from G1.

The priority classifier is incomplete. For example, the description ledger contains Life Engine site links and research-publisher domains outside the small automatic expansion allowlist. The 54 selected targets are not all intellectually important targets. The remaining 246 normalized URLs are not necessarily irrelevant; they need explicit relevance, identity, acquisition, and stopping decisions.

The preserved Wave 1 synthesis remains provisional. This acquisition does not reproduce its claims, run the Benchora experiment, or establish a single philosophy across every video.

## Gates and next research work

`G1_INVENTORY` passes for public uploads visible to the API at capture. `G2_TEXT_COVERAGE` remains partial because no transcript text has been acquired. `G3_DIRECT_GRAPH` remains partial because metadata retrieval, full source review, entity reconciliation, and recursive expansion are different completion criteria.

Next, reconcile aliases without discarding provenance; review the failed root and omitted high-value domains; verify the chapter and caption signals; then read the highest-value papers and implementation paths. Keep creator statements, implementation observations, reported experimental results, and analyst hypotheses distinct.

API-derived metadata has a recorded refresh-or-delete deadline of `2026-10-05T05:55:01Z`. This timestamp is a recorded obligation, not a claim that an unattended refresh or deletion job exists.

## Narrative correction

This curated report replaces inherited template language that still called the input an Atom window and called 22 GitHub URLs unique repositories. The original acquisition outputs remain recoverable at the original output commit above. The revised manifest records this report's new hash; no acquisition counts or underlying source records were changed. The current generator still needs this narrative correction incorporated before its next refresh.
