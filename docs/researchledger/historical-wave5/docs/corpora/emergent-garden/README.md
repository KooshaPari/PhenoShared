# Emergent Garden Nested-Corpus Campaign

**Campaign:** `eg-nested-corpus-2026-09`  
**Root:** `https://www.youtube.com/@EmergentGarden/videos`  
**Creator root:** `https://emergentgarden.io/`  
**Status:** planned / execution not yet complete

This directory defines a provenance-preserving research campaign rooted in the Emergent Garden channel. The channel is only the root node: each video, permitted transcript or script, description, project, repository, paper, article, demo, and selected downstream reference becomes part of a typed source graph.

The goal is not generic video summaries. The goal is to recover recurring mechanisms, concept evolution, implementation evidence, contradictions, and project-specific applicability across the KooshaPari/Phenotype portfolio.

## Authority

- **ResearchLedger** owns canonical research assets, source versions, claims, provenance, ontology, synthesis, and public projections.
- **RepoLedger** records one-way projection state and downstream draft PRs.
- **local-ops** may own tested machine-local acquisition wrappers, but never credentials, logs, runtime state, or corpus data.
- **thegent** may own generalized research-agent roles and dispatch contracts.
- **SessionLedger** captures replayable runs and handoffs.
- **Tracera** records trace/evidence links.
- **AgilePlus** records work packages and quality gates.
- Individual project repositories receive only evidence-backed applicability dossiers after a relevance gate. They do not receive raw transcripts or a copy of the corpus.

## Acquisition boundary

Default mode is `COMPLIANT_BASELINE`:

1. Use the documented YouTube Data API to resolve the channel handle, enumerate the uploads playlist, and maintain a temporary metadata cache.
2. Obtain transcript/script text from creator-supplied files, a licensed first-party mirror, explicit permission/export, or an operator-initiated manual copy from YouTube's transcript UI.
3. Do not run unattended YouTube scraping, undocumented transcript endpoints, cookie extraction, anti-bot or geo bypasses, member/private content access, or video/audio downloads.
4. Refresh or delete non-authorized YouTube API data within 30 days.
5. Never publish full video transcripts or audiovisual media to GitHub by default. Publish original derived research, source locators, hashes, short necessary excerpts, and links.

## Operating documents

- [`operations/CAMPAIGN_SPEC.md`](operations/CAMPAIGN_SPEC.md)
- [`operations/LOCAL_AGENT_MASTER_PROMPT.md`](operations/LOCAL_AGENT_MASTER_PROMPT.md)
- [`operations/campaign.yaml`](operations/campaign.yaml)
- [`../../superpowers/plans/2026-09-04-emergent-garden-nested-corpus.md`](../../superpowers/plans/2026-09-04-emergent-garden-nested-corpus.md)

## Completion definition

The campaign is not complete until it has:

- a reconciled public-upload inventory;
- an honest transcript/script coverage matrix;
- typed, bounded nested-source graph;
- source-version and claim/evidence chains;
- concept recurrence/evolution and contradiction records;
- a corpus-level synthesis that tests alternative interpretations;
- audited project relevance scores;
- a canonical ResearchLedger snapshot;
- RepoLedger projection records;
- evidence-backed draft PRs only in relevant repositories;
- a resumable incremental-refresh workflow.

This seed PR contains campaign contracts only. It does not claim the corpus has already been captured or analyzed.
