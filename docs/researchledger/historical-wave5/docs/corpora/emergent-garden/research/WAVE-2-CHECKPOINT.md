# Emergent Garden Wave 2 Checkpoint

**Campaign:** `eg-nested-corpus-2026-09`  
**Checkpoint:** `wave-2-recent-window-census-and-direct-graph`  
**Recorded:** 2026-09-04  
**Canonical branch head at checkpoint input:** `67f598b96f3fe1fbcdc826bc6f02bb9462741452`  
**Status:** recent-window metadata and direct graph expanded; complete channel inventory blocked

## Gate state

| Gate                   | State                                | Evidence                                                                                                                                                                         |
| ---------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `G1_INVENTORY`         | **BLOCKED**                          | No `YOUTUBE_API_KEY` exists in repository Actions secrets or the repository's isolated Infisical `dev` environment. The official Atom feed is recent-window only.                |
| `G2_TEXT_COVERAGE`     | **PARTIAL**                          | Metadata for 15 recent uploads includes description hashes, lengths, excerpts, outbound links, and a transcript-route matrix. No transcript text was acquired.                   |
| `G3_DIRECT_GRAPH`      | **PARTIAL / RECENT WINDOW EXPANDED** | All 23 unique high-value targets found in the 15-description sample were expanded and revision- or response-pinned. Older descriptions remain outside the graph until G1 passes. |
| `G4_PROJECT_RELEVANCE` | **PARTIAL**                          | Existing Wave 1 mechanism mappings remain valid; the new direct graph strengthens provenance but does not independently clear additional portfolio fanout.                       |
| `G5_EXPERIMENT`        | **SPECIFIED, NOT RUN**               | Benchora draft PR #106 contains the first controlled coordination-topology pilot. No result claim exists.                                                                        |
| `G6_PROJECT_PR`        | **ONE DOCUMENTATION PILOT OPEN**     | Benchora PR #106 is documentation-only. No product-code implementation is authorized.                                                                                            |
| `G7_RELEASE`           | **NOT APPLICABLE**                   | No implementation or reproduced result exists to release.                                                                                                                        |

## Completed in this checkpoint

### Official-source recent-window census

- normalized 15 records exposed by the official YouTube Atom channel feed;
- preserved channel ID `UCwBhBDsqiQflTMLy2epbQVw` and uploads playlist ID `UUwBhBDsqiQflTMLy2epbQVw`;
- captured 15 non-empty description records as SHA-256, length, line count, short excerpt, parsed chapters, and outbound links;
- recorded caption availability as unknown because the Atom provider does not expose the Data API signal;
- acquired no transcript, audio, video, cookie, or undocumented endpoint response;
- committed an explicit blocked status rather than treating the 15-row window as the channel inventory.

### Description edge ledger

- 186 normalized outbound edges;
- 116 unique targets across 49 domains;
- 13 implementation-candidate occurrences;
- 10 creator-direct occurrences;
- 3 primary-paper occurrences;
- 23 unique high-value targets after deduplication.

### High-value direct-link expansion

All 23 unique high-value targets expanded successfully:

| Class                            | Unique targets | Expanded | Failed |
| -------------------------------- | -------------: | -------: | -----: |
| GitHub implementation candidates |             11 |       11 |      0 |
| Primary arXiv papers             |              3 |        3 |      0 |
| Creator-controlled web surfaces  |              9 |        9 |      0 |
| **Total**                        |         **23** |   **23** |  **0** |

The implementation frontier now directly includes:

- `MaxRobinsonTheGreat/AgentsOfEmpires`;
- `MaxRobinsonTheGreat/agent_prompts`;
- `MaxRobinsonTheGreat/fractalsearch`;
- `MaxRobinsonTheGreat/hyperdimensions`;
- `MaxRobinsonTheGreat/mandelbrotnn`;
- `MaxRobinsonTheGreat/slopcity`;
- `cabaletta/baritone`;
- `karpathy/autoresearch`;
- `mboop127/AutoDE`;
- `mindcraft-bots/mindcraft`;
- `mindcraft-ce/mindcraft-ce`.

Repository captures include current default-branch head SHAs, repository metadata, ancestry where GitHub exposes it, response hashes, and README hashes/excerpts when a README exists.

The paper frontier now revision-pins:

- `2201.05989v2`, _Instant Neural Graphics Primitives with a Multiresolution Hash Encoding_;
- `2412.17799v2`, _Automating the Search for Artificial Life with Foundation Models_;
- `2505.22954v3`, _Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents_.

The creator-direct frontier response-pins:

- Aquarium GA;
- Evoloop / Strange Loops;
- Game of Life;
- Lenia;
- Biomorphs;
- Hyperdimensional Functions;
- Picbreeder;
- Langton's Ant;
- Neural Patterns.

## Strongest new findings

### 1. The actuator is not the planner

The Minecraft evidence directly links language-agent planning systems and separate pathfinding/actuation infrastructure. Evaluating only plans hides stale state, path failure, timing, and recovery. Portfolio experiments must preserve planner, observation, actuator, and evaluator as separate interfaces.

### 2. Foreground GUI execution is an architectural constraint

The Age of Empires chain links strategy generation to screen-capture automation that depends on foreground focus, fixed resolution, timing, and mutable local game files. A benchmark that ignores those constraints measures a different system.

### 3. Shared-artifact swarms require merge governance

The Slopcity chain explicitly combines parallel agents, a shared hub, self-rendering, critique, and repeated revision. It is useful as a contention and orphan-prevention case, not as proof that ten agents outperform one agent or independent best-of-N attempts.

### 4. Open-ended search still has an evaluator

The direct paper chain contradicts a simplistic reading of open-endedness as evaluator-free autonomy. The systems use learned measures, benchmark outcomes, archives, or selection procedures. Novelty and improvement are operationalized rather than assumed.

### 5. Faster representations change the search budget, not the truth standard

Instant neural representations can make repeated evaluation feasible. They do not remove the need for controlled baselines, held-out evaluation, rollback, or independent reproduction.

## Explicit alternatives retained

- A creator-linked repository may be the creator's implementation, an upstream dependency, an external runner, a fork, or historical context.
- A reachable creator-controlled page may identify a project without proving its source repository or Git lineage.
- README and abstract claims may be accurate descriptions of intended systems while reported performance remains unreproduced.
- The Atom window may be internally correct while omitting older uploads, removed records, live streams, shorts, or playlist anomalies.
- More agents may underperform a single agent or best-of-independent attempts after equalizing total compute and tool calls.

## Open blocker

ResearchLedger issue #82 records the only operator credential action currently required for `G1_INVENTORY`: provide a key restricted to YouTube Data API v3 under the exact name `YOUTUBE_API_KEY` in repository Actions secrets or the repository's Infisical `dev` environment, then rerun **Emergent Garden YouTube Census**.

The key must not be pasted into an issue, commit, workflow input, or log. Unsupported scraping is not an acceptable substitute.

## Not complete

- exhaustive uploads-playlist pagination and reconciliation;
- complete descriptions for uploads outside the Atom recent window;
- transcript availability and permission review for the complete inventory;
- permitted transcript acquisition;
- description edit history;
- expansion of lower-priority contextual and related-video edges;
- independent reproduction of creator experiments;
- incremental refresh and impact propagation;
- additional evidence-cleared product-repository fanout.

## Publication and fanout rule

This checkpoint authorizes publication of the normalized recent-window metadata and direct-link evidence already committed to the canonical ResearchLedger branch. It does **not** authorize:

- describing 15 uploads as the complete channel;
- claiming creator experiments were reproduced;
- importing full descriptions or transcripts into downstream repositories;
- treating every outbound link as authorship or endorsement;
- opening additional product PRs solely because a repository is thematically similar;
- implementing the Benchora pilot before its repository-local review gate passes.

## Canonical artifacts

- `YOUTUBE-CENSUS-WAVE-2.md`;
- `DIRECT-LINK-EXPANSION-WAVE-2.md`;
- `../data/youtube-channel-inventory-v1.json`;
- `../data/youtube-text-coverage-v1.json`;
- `../data/youtube-description-edges-v1.json`;
- `../data/youtube-census-status-v1.json`;
- `../data/direct-link-frontier-v1.json`;
- `../../../scripts/research/collect_emergent_garden_youtube.py`;
- `../../../scripts/research/build_emergent_garden_link_frontier.py`;
- ResearchLedger issue #82.
