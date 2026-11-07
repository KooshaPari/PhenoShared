# Emergent Garden Nested-Corpus Research Plan

> **For agentic workers:** execute task-by-task in isolated worktrees. Do not merge, do not commit raw transcripts or media, and do not change product behavior merely because a research conclusion appears useful.

**Campaign:** `eg-nested-corpus-2026-09`  
**Goal:** Build a bounded, provenance-preserving, incrementally refreshable corpus rooted in Emergent Garden's YouTube channel and creator site; extract claims, concepts, implementations, contradictions, and portfolio applicability; publish canonical derived research to ResearchLedger and open only evidence-backed downstream draft PRs.

**Architecture:** ResearchLedger remains the canonical research authority and reuses its existing Markdown/SQLite document, version, chunk, FTS, provenance, claim, document-link, reference-fetch, crawl-run, and consent substrate. New work adds a documented YouTube Data API inventory adapter, permission-aware transcript/script intake, richer typed graph/provenance records, deterministic frontier scoring, synthesis artifacts, publication checks, and one-way repository projections. RepoLedger records projection state. Other repositories receive only role/tool/run references or project-specific dossiers.

**Scope:** data mining, research operations, tests for research tooling, research documents, and draft repository projections. No audiovisual mirroring, no unsupported YouTube scraping, no product-code implementation based on findings, and no merges.

---

## Existing substrate to preserve

Before editing, verify current behavior and tests for:

- `apps/desktop/src-tauri/src/storage.rs` — canonical documents, versions, chunks, provenance, claims, document links, reference jobs, crawl runs, checkpoint-like leases;
- `apps/desktop/src-tauri/src/reference_fetch.rs` — public-URL validation, DNS pinning, SSRF protection, robots policy, content-type and byte limits, retries, and raw artifact writes;
- `apps/desktop/src-tauri/src/enrichment.rs` — current URL extraction/canonicalization;
- `apps/desktop/src-tauri/src/distill.rs` — deterministic notes, claims, alternatives, questions, and source links;
- `apps/desktop/src-tauri/src/okf.rs` — permissive OKF concept boundary;
- current migrations, tests, security docs, retrieval pipeline, and AGENTS/CLAUDE instructions.

Do not create a parallel database, crawler, claim store, or source-note format when the existing boundary can be extended safely.

---

## Task 0 — Preflight, worktree, and policy lock

**Outputs:** run manifest, tool audit, policy decision, initial checkpoint, repository-state snapshot.

- [ ] Read repository `AGENTS.md`, `CLAUDE.md`, campaign README/spec/manifest, security docs, and current branch rules.
- [ ] Create an isolated branch/worktree named for `eg-nested-corpus-2026-09`; never edit protected `main` directly.
- [ ] Record current commits for ResearchLedger, RepoLedger, local-ops, thegent, SessionLedger, Tracera, AgilePlus, pheno, and initial candidate project repos.
- [ ] Record local tool versions and credential availability without printing tokens, cookies, browser profiles, or secret values.
- [ ] Set acquisition mode to `COMPLIANT_BASELINE` unless a complete permission artifact authorizes `AUTHORIZED_BULK`.
- [ ] Initialize run, session, trace, and work-package identifiers only through already-supported local integrations. Missing integrations become explicit gap records, not invented IDs.
- [ ] Create checkpoint `CP-000` with phase, branch, commits, policy mode, budgets, and known blockers.
- [ ] Fail closed when transcript acquisition or publication rights are unclear.

**Gate G0:** no unresolved authority, credential, worktree, acquisition, publication, or secret-handling ambiguity.

---

## Task 1 — Add the documented YouTube inventory adapter

**Candidate files:** resolve actual next migration/file paths before editing.

- Create or extend a YouTube provider module under `apps/desktop/src-tauri/src/`.
- Add deterministic fixtures under `tests/fixtures/youtube/`.
- Add unit/integration tests for handle resolution, uploads pagination, video batching, partial failures, quota errors, deleted/private placeholders, and key redaction.
- Add an operator-facing CLI or typed command only when it can run without exposing the API key to the renderer or persisted corpus.

- [ ] Resolve `@EmergentGarden` with documented `channels.list(forHandle=...)` behavior.
- [ ] Read the channel content-details uploads playlist.
- [ ] Enumerate all playlist items with pagination; do not use search-result counts as canonical inventory.
- [ ] Fetch video details in documented batch sizes.
- [ ] Normalize immutable video IDs, public URLs, title, publication time, duration, visibility/availability state, and temporary description metadata.
- [ ] Write a temporary raw API cache with `captured_at`, `expires_at`, endpoint, request parameters with secrets removed, response hash, and refresh/delete status.
- [ ] Write normalized long-lived video records separately from the temporary raw cache.
- [ ] Reconcile `channel.statistics.videoCount`, uploads-playlist enumeration, unique video IDs, and inaccessible placeholders without forcing equality.
- [ ] Produce `channel-coverage.json`, `video-records.jsonl`, and checkpoint `CP-100`.

**Hard rule:** no HTML scraping, undocumented transcript endpoint, media download, cookie reuse, or CAPTCHA/anti-bot bypass may be added as a fallback.

**Gate G1:** every API-enumerable public upload has a normalized record or an explicit gap; raw API cache has a maximum age of 30 days.

---

## Task 2 — Extend the corpus data model without breaking ResearchLedger

**Candidate storage additions:** use a new forward-only migration; never rewrite an already-applied migration.

- corpus campaigns and snapshots;
- typed source nodes and source versions;
- typed source edges with discovery provenance;
- acquisition/permission artifacts;
- transcript/script availability and versions;
- frontier decisions and budgets;
- concepts/aliases/occurrences;
- claim alternatives and counterevidence links;
- contradictions/supersession;
- applicability records;
- repo projections and staleness;
- checkpoints and quality reports;
- API-cache expiry/deletion audit.

- [ ] Map every proposed field onto existing `documents`, `document_versions`, `provenance`, `claims`, `document_links`, `reference_fetches`, and `reference_crawl_runs` before adding a table.
- [ ] Add only fields/tables that represent a distinct durable concept or necessary relation.
- [ ] Keep stable external identity separate from mutable source versions.
- [ ] Preserve canonical and original URIs.
- [ ] Add foreign keys/indexes for source-version evidence lookup, edge frontier queries, concept recurrence, applicability, projection staleness, and cache expiry.
- [ ] Add migration tests from an existing vault, idempotency tests, rollback/failure safety tests, and deterministic export tests.
- [ ] Define JSON Schemas or typed DTOs for source nodes, edges, video records, transcript records, claims, concepts, applicability, projections, checkpoints, and quality reports.
- [ ] Produce checkpoint `CP-200`.

**Gate:** no orphan claims, edges, source versions, applicability records, or projections; migration preserves existing data and tests.

---

## Task 3 — Implement permission-aware transcript/script intake

**Supported routes:** `creator_supplied`, `first_party_licensed`, `permissioned_export`, `manual_youtube_ui`, `operator_notes`, and `local_asr_supplied_media`.

- [ ] Build a coverage matrix for every video before acquiring text.
- [ ] Record route, provider, language, human/automatic status, timestamp confidence, permission/license artifact, captured time, source hash, normalized hash, publication class, and gap reason.
- [ ] Preserve raw permitted text locally as a source version; create normalized timestamped text as a derived version.
- [ ] Never mark operator notes as a transcript.
- [ ] Never mark local ASR as creator-supplied or human captions.
- [ ] Add importers for plain text, timestamped Markdown, WebVTT/SRT supplied by the operator, and creator-controlled repository/script files.
- [ ] Add overlap/order/duration sanity checks for timestamps.
- [ ] Quarantine text with ambiguous origin or publication rights.
- [ ] Add a publication transform that replaces non-publishable full text with metadata, hashes, locators, short necessary excerpts, and canonical links.
- [ ] Produce `transcript-coverage.json` and checkpoint `CP-300`.

**Gate G2:** every video has an honest text-availability/acquisition state; no unauthorized transcript or media is staged for Git.

---

## Task 4 — Build the direct description/source graph

- [ ] Upgrade URL extraction to retain original URL, normalized target, anchor text, surrounding context, source-version ID, and exact discovery locator.
- [ ] Canonicalize identities conservatively; strip tracking parameters only through explicit domain-aware rules; preserve the original URI.
- [ ] Detect repositories, papers/DOIs/arXiv records, creator projects, articles, demos, datasets, videos/channels, and generic pages.
- [ ] Classify each edge as `AUTHOR_DIRECT`, `IMPLEMENTATION`, `PRIMARY_SOURCE`, `DEPENDENCY`, `INFLUENCE`, `EXTENSION`, `CONTEXT`, `INCIDENTAL`, `CONTRADICTS`, `SUPERSEDES`, or `DUPLICATES`.
- [ ] Store classifier rationale, confidence, features, and review state.
- [ ] Run terms/robots/license/content-type/publication review before acquisition.
- [ ] Reuse the existing safe reference-fetch substrate; add provider-specific adapters only where generic fetch cannot preserve the required structured provenance.
- [ ] Record every denied, unsupported, missing, or failed target as a gap/quarantine result.
- [ ] Produce the direct graph, edge-class coverage report, and checkpoint `CP-400`.

**Gate G3:** no untyped direct links; every acquired direct source has an immutable version/hash and provenance chain.

---

## Task 5 — Add deterministic frontier scoring and selective recursion

Use the campaign manifest's hard budgets. Frontier scoring must be a pure, testable function over recorded features.

Suggested positive features:

- creator-owned/direct link;
- implementation/code artifact;
- explicit primary-source citation;
- repeated across multiple videos;
- central to an unresolved research question;
- needed to test a contradiction;
- strong candidate for portfolio mechanism mapping;
- recent source that changes earlier interpretation.

Suggested negative features:

- incidental/social/navigation link;
- duplicate/syndicated copy;
- unclear identity or rights;
- low-information landing page;
- already-covered dependency;
- domain/node/depth budget pressure;
- no path back to a campaign question.

- [ ] Define score weights and deterministic tie-breaking in a versioned manifest.
- [ ] Persist feature values, score, threshold, budget state, decision, and rationale.
- [ ] Expand direct implementations and explicit primary sources first.
- [ ] Select at most the configured number of bibliography references per paper.
- [ ] Add contradiction/supersession searches as explicit frontier tasks, not ad hoc browsing.
- [ ] Detect cycles, duplicate identities, and alias collisions.
- [ ] Checkpoint every 50 processed nodes and on any policy/tool failure.
- [ ] Produce frontier coverage/stop report and checkpoint `CP-500`.

**Gate G4:** graph is bounded, reproducible, connected to research questions, and not an uncontrolled web mirror.

---

## Task 6 — Distill claims, concepts, mechanisms, and contradictions

- [ ] Generate deterministic per-video and per-source notes with source-version IDs and locators.
- [ ] Extract claims as candidates, then require evidence review for high-impact claims.
- [ ] Classify evidence as `stated`, `demonstrated`, `observed_in_code`, `cited`, `inferred`, `portfolio_observed`, `hypothesis`, or `negative_result`.
- [ ] Preserve exact timestamps/pages/lines/code paths and short necessary excerpts.
- [ ] Add at least one plausible alternative interpretation to every high-impact claim.
- [ ] Search for and link counterevidence rather than merely adding a low confidence score.
- [ ] Normalize concepts and aliases independently of creator vocabulary.
- [ ] Build cross-video recurrence, evolution, contradiction, and supersession maps.
- [ ] Distinguish demonstrated mechanism from philosophical framing.
- [ ] Produce implementation-pattern catalog, unresolved-question ledger, contradiction registry, and corpus synthesis.
- [ ] Run a second-pass skeptic review that assumes the apparent philosophical unity is false or non-technical.
- [ ] Produce checkpoint `CP-600`.

**Gate G5:** every synthesis conclusion resolves to evidence, alternatives, and counterevidence status; creator statements and analyst inferences remain distinct.

---

## Task 7 — Audit and score portfolio applicability

- [ ] Inventory candidate repositories through the connected GitHub/local estate.
- [ ] Read current `README`, `AGENTS`, `CLAUDE`, specs/ADRs, status, and relevant code at a pinned commit before scoring.
- [ ] Score problem fit, mechanism fit, evidence quality, novelty, actionability, conflict risk, duplication risk, and repo authority fit.
- [ ] Treat repository names and prior memory only as search hints, never evidence.
- [ ] Generate full dossiers only above the configured project threshold.
- [ ] Keep medium-confidence research leads centrally in ResearchLedger/RepoLedger rather than opening noisy project PRs.
- [ ] Include `NOT_APPLICABLE`, `ALREADY_IMPLEMENTED`, `SUPERSEDED_BY_PORTFOLIO`, `CONTRADICTION`, and `INSUFFICIENT_EVIDENCE` results.
- [ ] For each positive recommendation, specify whether it is a documentation update, research lead, experiment, ADR input, or later implementation candidate. This campaign may not perform the implementation.
- [ ] Produce the relevance matrix and checkpoint `CP-700`.

Initial candidates include ResearchLedger, RepoLedger, local-ops, thegent, SessionLedger, Tracera, AgilePlus, Agentora, HeliosLab, helios-cli, forgecode, pheno/shared infrastructure, Civis, and other repositories discovered by the audit. They are not predetermined winners.

**Gate G6:** no project projection relies on metaphor, stale repo state, or unsupported architecture assumptions.

---

## Task 8 — Publish canonical snapshot and one-way GitHub projections

### ResearchLedger

- [ ] Freeze a canonical derived snapshot with campaign ID, source-manifest hash, source-version counts, graph/claim/concept counts, coverage, gaps, policies, generator versions, and quality result.
- [ ] Commit publishable derived notes, schemas/manifests, short excerpts, locators, and source links only.
- [ ] Keep full non-publishable text and temporary API cache in ignored local vault storage.

### RepoLedger

- [ ] Register every downstream projection as an append-only record containing campaign ID, snapshot/hash, claim IDs, destination repo/path/branch/PR, generator version, destination commit, status, and staleness.

### Other authority repos

- [ ] Add tested general local wrappers to `local-ops` only when they are reusable and contain no state/credentials.
- [ ] Add generalized role/dispatch contracts to `thegent` only when they are no longer campaign-specific.
- [ ] Add run references to SessionLedger and trace/evidence links to Tracera; do not copy the corpus.
- [ ] Add work-package/gate state to AgilePlus where supported.
- [ ] Add a pheno index entry only after canonical and downstream PRs exist.

### Project repositories

- [ ] Open draft PRs only for dossiers that passed G6.
- [ ] Include canonical snapshot/hash, claim IDs, exact evidence links, repo commit audited, alternatives, contradictions, and recommended next experiment/decision.
- [ ] Do not change product code and do not merge.

**Gate G7:** every projection is draft, reversible, publication-safe, provenance-linked, and registered centrally.

---

## Task 9 — Incremental refresh and impact propagation

- [ ] Refresh/delete temporary YouTube API cache by its deadline.
- [ ] Detect new, changed, unavailable, or deleted videos by immutable ID and source-version hash.
- [ ] Detect changed linked-source versions.
- [ ] Compute impacted edges, claims, concepts, synthesis sections, applicability records, and repo projections.
- [ ] Regenerate only affected artifacts.
- [ ] Mark downstream projections stale when their canonical inputs change.
- [ ] Resume safely from the latest checkpoint after interruption.
- [ ] Verify repeated no-change runs produce no corpus or Git diff.
- [ ] Produce final checkpoint and refresh runbook.

**Gate G8:** rerun is idempotent, cache-compliant, resumable, and impact-bounded.

---

## Verification matrix

Run repository-specific gates from current instructions. At minimum:

```bash
bun install --frozen-lockfile
bun run lint
bun run test
bun run build
RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION=1 \
  cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml --lib
cargo fmt --manifest-path apps/desktop/src-tauri/Cargo.toml --all -- --check
git diff --check
```

Add and run campaign-specific checks for:

- schema validation;
- migration from an existing vault;
- inventory pagination/batching/partial failures/key redaction;
- temporary-cache expiry/deletion;
- transcript origin and permission enforcement;
- graph foreign keys, edge typing, cycle/duplicate reporting;
- frontier score determinism and budget enforcement;
- exact claim locator and source-version resolution;
- alternative/counterevidence completeness;
- publication leak scanning for media, transcript dumps, API raw caches, secrets, cookies, local paths, and private correspondence;
- projection source/hash/staleness integrity;
- no-change idempotency.

## Final handoff

Report:

1. campaign/run/session/trace/work-package IDs;
2. branches, commits, and draft PRs;
3. public-upload and transcript/script coverage;
4. source nodes/versions, edges by class, claims by evidence type, concepts, contradictions, gaps, and quarantines;
5. source-manifest hash and snapshot ID;
6. validation/gate results with logs;
7. corpus synthesis and skeptic/alternative findings;
8. portfolio relevance matrix and rejected mappings;
9. projection registry and stale-state report;
10. cache-expiry deadlines;
11. unresolved blockers;
12. exact next operator decision.

Do not call the campaign complete when tasks merely executed. Completion requires G0–G8 to pass with evidence.
