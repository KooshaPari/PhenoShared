# Emergent Garden Nested-Corpus Campaign Specification

**Campaign ID:** `eg-nested-corpus-2026-09`  
**Status:** planned  
**Scope:** data mining, research operations, documentation, and evidence-backed repository projections only

## 1. Mission

Build a traceable, bounded, incrementally refreshable research representation of Emergent Garden's work. Start with the public YouTube channel and creator site, then follow meaningful first-party and cited links into projects, repositories, papers, articles, demos, and selected downstream references.

The unit of work is not a video summary. It is a typed source-and-claim graph that preserves what the creator stated, demonstrated, cited, implemented, or merely suggested, and distinguishes those from our own inferences.

## 2. Research questions

1. What mechanisms, abstractions, and philosophical commitments recur across the creator corpus?
2. Which ideas remain stable, and which evolve, contradict, or supersede earlier formulations?
3. Which implementations and primary sources actually support the videos?
4. Which KooshaPari/Phenotype projects have direct technical applicability?
5. Where is the resemblance only aesthetic or metaphorical?
6. Which findings justify experiments rather than immediate architecture changes?
7. What does this corpus reveal that the existing portfolio framing misses?
8. Where does the portfolio already have a stronger or incompatible formulation?
9. What remains unknown after the root corpus and high-value nested frontier are exhausted?

## 3. Scope boundaries

### In scope

- public channel inventory;
- video metadata and descriptions acquired through allowed channels;
- creator-supplied, licensed, permissioned, manually copied, or operator-authored transcript/script notes;
- creator website and project gallery;
- explicitly linked repositories, papers, articles, demos, and videos;
- selected references needed for provenance, implementation understanding, or contradiction testing;
- local machine-readable graph, source versions, claim ledger, ontology, and synthesis;
- portfolio applicability dossiers;
- research tooling tests, operational documentation, and draft GitHub projections.

### Out of scope

- audiovisual downloading or mirroring;
- member-only, private, age/geo-bypassed, or deleted content acquisition;
- unattended YouTube scraping or undocumented transcript endpoints;
- browser-cookie extraction, CAPTCHA bypass, anti-bot circumvention, or session cloning;
- public release of full transcripts without a clear license or permission;
- indiscriminate bibliography/dependency crawling;
- product-code implementation prompted by findings;
- repository creation, deletion, archival, transfer, rename, merge, or history rewrite;
- rewriting project history to force philosophical agreement.

## 4. Authority and projection model

| Concern                                                                             | Authority                      |
| ----------------------------------------------------------------------------------- | ------------------------------ |
| Canonical research assets, provenance, source versions, claims, ontology, synthesis | `KooshaPari/ResearchLedger`    |
| Fleet projection inventory and downstream PR state                                  | `KooshaPari/RepoLedger`        |
| Tested machine-local acquisition wrappers                                           | `KooshaPari/local-ops`         |
| Reusable agent roles, routing, and dispatch contracts                               | `KooshaPari/thegent`           |
| Replayable run/session capture                                                      | `KooshaPari/SessionLedger`     |
| Trace and evidence-link observability                                               | `KooshaPari/Tracera`           |
| Feature/work-package/gate state                                                     | `KooshaPari/AgilePlus`         |
| Portfolio shelf/index                                                               | `KooshaPari/pheno`             |
| Project-specific interpretation                                                     | Relevant individual repository |

ResearchLedger is the only canonical corpus authority. Other repositories receive references, run records, projection state, generalized tooling, or project-specific derived dossiers. They do not receive duplicate raw corpora.

## 5. Acquisition modes

### `COMPLIANT_BASELINE` — default

1. Resolve the channel handle and enumerate uploads using the documented YouTube Data API.
2. Treat YouTube API metadata as a temporary refreshable cache, not permanent raw source truth.
3. Acquire transcript/script text only through one of:
   - creator-supplied files;
   - clearly licensed text in a creator-controlled site/repository;
   - explicit permission plus supplied export;
   - operator-initiated manual copy from the official transcript UI;
   - operator-authored notes while viewing through the official player;
   - local ASR over media already lawfully supplied by the operator.
4. Store the acquisition route and permission artifact on every transcript record.

### `AUTHORIZED_BULK`

May be enabled only when a permission artifact explicitly authorizes the contemplated bulk operation. It must record source, grantor, scope, date, expiration, permitted storage, and publication rights.

### Forbidden

`UNSUPPORTED_SCRAPE`, `PRIVATE_OR_MEMBER_CONTENT`, and `CIRCUMVENTION` are never fallback modes.

## 6. Corpus graph

### Node classes

- channel;
- video;
- description version;
- transcript/script/note version;
- creator project;
- repository and code path;
- paper and paper section;
- article/site page;
- interactive demo;
- external video/channel;
- dataset;
- concept;
- claim;
- experiment;
- portfolio repository;
- permission artifact;
- gap/quarantine record.

Every node has a stable ID, canonical URI, original URI, source kind, acquisition route, captured time, content hash/version, license/publication class, and status.

### Edge classes

```text
AUTHOR_DIRECT
IMPLEMENTATION
PRIMARY_SOURCE
DEPENDENCY
INFLUENCE
EXTENSION
CONTEXT
INCIDENTAL
CONTRADICTS
SUPERSEDES
DUPLICATES
```

Every edge preserves discovery source, locator, original anchor/context, classifier rationale, confidence, frontier score, and expand/stop decision.

## 7. Recursion policy

The crawl is bounded by both value and hard budgets.

- default maximum depth: 4;
- total-node ceiling: 2,500;
- first deep-pass target: 250 nodes;
- maximum outbound links considered per node: 50;
- maximum selected bibliography references per paper: 20;
- maximum nodes per domain: 250;
- checkpoint interval: 50 nodes;
- minimum automatic expansion score: 12;
- mandatory review score: 20.

Prioritize creator-owned projects, direct implementations, explicit primary sources, and sources required to test contradictions. Expand dependencies, influences, and extensions selectively. Stop on incidental links unless independently promoted by a research question.

A frontier decision must be reproducible from stored features, score, rule, budget state, and agent version.

## 8. Evidence contract

Every substantive claim must contain:

- stable claim ID;
- source node and source-version IDs;
- source URI;
- exact locator: timestamp, chapter, page, line, section, or code path;
- short necessary excerpt, or a reason no excerpt may be retained;
- evidence type: `stated`, `demonstrated`, `observed_in_code`, `cited`, `inferred`, `portfolio_observed`, `hypothesis`, or `negative_result`;
- confidence;
- alternative interpretation;
- counterevidence status;
- publication class;
- affected concepts and portfolio candidates.

No inference may be rewritten as a creator claim. No recommendation may rely only on semantic similarity.

## 9. Anti-confirmation-bias protocol

For every major concept or portfolio recommendation, test at least these hypotheses:

1. the philosophical unity is real and technically useful;
2. the similarity is metaphorical rather than operational;
3. the portfolio already has a stronger or more specific formulation;
4. another source or architecture explains the overlap better;
5. the idea helps one project but harms or does not apply to another;
6. the evidence is insufficient to decide.

Contradictions, negative results, and null applicability are first-class outputs.

## 10. Required workflow

1. **Preflight:** repository/tool/policy audit; initialize run, trace, work-package, and checkpoint IDs.
2. **Root inventory:** resolve immutable channel ID, uploads playlist, every API-enumerable public upload, and explicit gaps.
3. **Text intake:** build availability matrix; ingest permitted text; preserve origin and timestamp confidence.
4. **Direct graph:** extract/canonicalize/classify description and source links; acquire approved direct sources.
5. **Recursive graph:** score and expand the high-value frontier under fixed budgets.
6. **Distillation:** produce per-video/source notes, claims, concepts, aliases, recurrence/evolution maps, contradictions, and open questions.
7. **Synthesis:** compare creator evidence with independent literature and implementation evidence.
8. **Portfolio mapping:** audit actual repository state; score mechanism/problem/evidence fit; generate dossiers above threshold.
9. **Projection:** canonical ResearchLedger snapshot first, RepoLedger projection records second, then evidence-backed draft PRs only.
10. **QA/handoff:** schema, graph, provenance, publication, duplicate, link, authority, and repository-boundary checks.

## 11. Applicability classes

```text
DIRECTLY_ADOPT
ARCHITECTURAL_ANALOGUE
EXPERIMENT
RESEARCH_LEAD
PHILOSOPHICAL_CONVERGENCE
CONTRADICTION
NOT_APPLICABLE
ALREADY_IMPLEMENTED
SUPERSEDED_BY_PORTFOLIO
INSUFFICIENT_EVIDENCE
```

A project dossier must include useful connections, contradictions, non-applicable ideas, experiments, exact source locators, confidence, and an explicit recommendation. A high score never authorizes product-code changes.

## 12. GitHub publication contract

- all changes use isolated worktrees/branches and draft PRs;
- no direct commits to protected/default branches;
- canonical source manifest hash must exist before downstream projections;
- full transcripts, media, API raw responses, credentials, private correspondence, local paths, and browser profiles must not be committed;
- individual repositories receive only project-specific derived dossiers with stable links back to canonical evidence;
- every projection records canonical campaign ID, snapshot/hash, source claim IDs, generator version, destination commit, and staleness state;
- no PR is merged by the research agent.

## 13. Completion criteria

The campaign is complete only when it has:

- reconciled public-upload inventory;
- honest transcript/script coverage matrix;
- typed and bounded nested-source graph;
- source-version and claim/evidence chains;
- recurrence/evolution and contradiction records;
- corpus synthesis that tests alternatives;
- audited project relevance matrix;
- canonical ResearchLedger snapshot and manifest hash;
- RepoLedger projection records;
- evidence-backed draft PRs only in relevant repositories;
- a tested, resumable incremental-refresh workflow;
- final quality report with unresolved gaps.

Running every task is not completion. Passing the acceptance gates is completion.
