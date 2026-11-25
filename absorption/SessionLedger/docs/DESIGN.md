# SessionLedger — Design (R&D)

Status: R&D / Phase 0. This document is the foundation; the code skeleton in
`src/` realizes the domain model and the port boundaries described here.

---

## 1. Problem statement

Agent sessions (Forge, Codex, Claude Code, Cursor, Factory Droid) are ephemeral,
siloed per-tool, and lossy on crash. An operator running many concurrent agents
accumulates dozens of overlapping chats; when one crashes or is abandoned, the
work, the intent, and the accumulated context are stranded across raw transcript
files with no canonical way to **resume** them in a fresh session.

SessionLedger turns every session into a durable, observable **ledger** and
distills it into an **injectable continuation bundle** — a sized, structured
artifact that a new session ingests to continue exactly where the old one left
off. Three concrete jobs:

1. **Duplicate-scoped merge** — collapse N chats over the same scope into ONE
   resumable chat (resume one, not many).
2. **Lost-work recovery** — surface crashed/abandoned sessions' unfinished work
   in a localized _in-progress / unfinished_ section.
3. **Observability + history** — a wiki/docs viewer over all sessions.

Non-goals (Phase 0): replacing any tool's native session store; real-time
in-the-loop steering of a live agent; a hosted multi-tenant service.

---

## 2. The bundle model

A **ContinuationBundle** (`src/domain/bundle.rs`) is the canonical, injectable
resume artifact: an ordered set of typed `Bundle` slices, each carrying a token
estimate so the whole bundle can be **sized to a target scope** before injection.
A bundle is _injectable_ only when it carries an `Acceptance` slice.

### Owner's four bundles

| Kind         | Answers                                     | Contents                                                                                                     |
| ------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `Acceptance` | "Is it safe to resume, and is scope sized?" | ready flag, scope-sized flag, user-turn count. The resume **gate**.                                          |
| `Contract`   | "What MUST the continuation honor?"         | invariants/constraints (style rules, do-not-touch files, success criteria) the new session must not violate. |
| `Context`    | "What state do I need to act?"              | distilled working set: cwd, open files, key decisions, environment.                                          |
| `Intent`     | "What is the operator trying to achieve?"   | the goal / intent DAG; the latest user request.                                                              |

### Proposed additional bundles (justified)

| Kind         | Why it's needed                                                                                                                                                                                                                                                      |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Provenance` | Each distilled fact needs a citation back to its origin (corpus, session id, message span) so a resumed session can **trust and audit** its inputs — without it, distillation is unverifiable and hallucination-prone. Mirrors forgecode's `intent_hash` provenance. |
| `Worklog`    | The diff/worklog of what was actually _done_ vs. _outstanding_ is distinct from `Intent` (the goal) and `Context` (the state). It is the direct feed for **lost-work localization** (use case 2): the unfinished list IS the in-progress section.                    |
| `Dedup`      | The merge key + merged-session manifest that lets **use case 1** work: it records which sessions collapsed under one scope so the merged continuation is reproducible and reversible.                                                                                |

`Contract` and `Dedup` are modeled in `BundleKind`; the Phase-1 compiler emits
`Acceptance/Intent/Context/Provenance/Worklog` and grows the rest in Phase 3.

---

## 3. Pipeline: ingest → distill → view → inject

```
                ┌──────────── ports::CorpusSource ────────────┐
 forge.db ──▶ forge adapter ─┐
 ~/.codex ──▶ codex adapter ─┤
 ~/.claude ▶ claude adapter ─┼─▶ Session (normalized) ─▶ distill::compile
 cursor   ──▶ cursor adapter ┘                                │
                                                              ├─▶ ContinuationBundle ─▶ inject into NEW session
                                                              └─▶ ports::MemoryStore (short + long term)
                                  ports::TraceSink spans every stage   viewer:: read model (wiki/history)
```

1. **Ingest** — each corpus adapter normalizes raw transcripts into `Session`
   (`domain/session.rs`), classifying user vs. subagent turns (shared with the
   curation pipeline, §6).
2. **Distill ("dream")** — `distill::compile` assembles the bundle envelope and
   (Phase 3) writes distilled facts into `MemoryStore`. Short-term = recent
   scoped facts; long-term = summarized/persisted facts (OmniRoute's two tiers).
3. **View** — `viewer::SessionSummary` projects ledger rows for the wiki/history
   surface, including the unfinished section.
4. **Inject** — the `ContinuationBundle` (sized via token estimates) is rendered
   to a prompt-injectable form and fed to a new session.

---

## 4. OKF mapping

Open Knowledge Format models knowledge as typed nodes + provenance-carrying
edges. SessionLedger maps cleanly:

| OKF concept     | SessionLedger                                                  |
| --------------- | -------------------------------------------------------------- |
| Knowledge node  | a `Bundle` slice (typed body JSON)                             |
| Node type       | `BundleKind`                                                   |
| Provenance edge | the `Provenance` bundle (origin corpus + session + span)       |
| Assertion       | a distilled fact (`MemoryStore` entry, `EPISODIC`/`SEMANTIC`)  |
| Container       | `ContinuationBundle` (a knowledge graph rooted at `source_id`) |

This makes the bundle interchangeable with other OKF-style consumers and keeps
distilled knowledge queryable, not opaque blobs.

### 4.1 OKF export implementation

Added in `feat/okf-export-v2`:

- **Port** [`src/ports/okf.rs`](src/ports/okf.rs) — defines the `OkfDocument`/`OkfEntity`/`OkfRelation`/`OkfProvenance`
  data model and the `OkfExporter` trait (`trait OkfExporter { type Output; fn export(&self, bundle: &ContinuationBundle) -> Result<Self::Output, PortError>; }`).
- **Adapter** [`src/export/okf.rs`](src/export/okf.rs) — `JsonOkfExporter` produces `serde_json::Value`, plus a
  free-standing `export_to_okf()` convenience function (the `--okf` entry point).

| Bundle kind        | OKF entity type      | Relation type                                         |
| ------------------ | -------------------- | ----------------------------------------------------- |
| `Intent` (goal)    | `intent`             | `verified_by` → acceptance, `bounded_by` → constraint |
| `Intent` (accept.) | `acceptance`         | ← `verified_by`                                       |
| `Intent` (constr.) | `constraint`         | ← `bounded_by`                                        |
| `Context`          | `resource` / `state` | `grounds`                                             |
| `Contract`         | `criteria`           | `requires`                                            |
| `Acceptance`       | `gate`               | (document-level)                                      |

---

## 5. Flows

### 5.1 Crash recovery

Adapter detects a session with no terminal/`completed` marker → `Worklog`
captures outstanding items → `viewer` files it under _in-progress / unfinished_ →
operator injects its `ContinuationBundle` into a fresh session to finish it.

### 5.2 Duplicate-scoped merge

`DedupKey::derive(session, topic_slug)` (`domain/dedup.rs`) = SHA-256 over
`(normalized cwd, topic slug)`. Sessions sharing a key are merge candidates;
their bundles fold into one `ContinuationBundle` (a `Dedup` slice records the
manifest). After a crash the operator resumes the single merged chat.

### 5.3 Lost-work localization

`Worklog.unfinished` is the canonical outstanding-work list; the viewer's
unfinished section is a projection of it across all sessions.

---

## 6. Composition map (reuse, don't reinvent)

Every external capability is a **port** (`src/ports/mod.rs`); adapters wire them
to existing Phenotype systems. Cited per the Phenotype Cross-Project Reuse Protocol.

| Capability             | Port             | Reused system (path)                                                                                                                | How                                                                                                                                                                                      |
| ---------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Corpus read            | `CorpusSource`   | forgecode `ConversationRepository` (`repos/forgecode`, `crates/forge_repo`); codex/claude/cursor JSONL                              | forge.db `conversations` (~12.9k rows) is the primary source; FTS5 `conversations_fts`, zstd `context_zstd`.                                                                             |
| Lifecycle FSM          | `domain::intent` | forgecode intent FSM + ADR-103 (`forge_repo/src/conversation/intent.rs`, `conversation_repo.rs`)                                    | `IntentState` mirrors `Pending→Extracting→Extracted→Verified→Pruned`; pruning gated on `Verified`. SessionLedger implements the currently-`NoopIntentExtractor`.                         |
| Long/short-term memory | `MemoryStore`    | OmniRoute memory (`repos/src/lib/memory/`, `docs/frameworks/MEMORY.md`)                                                             | `store.ts` + `retrieval.ts` `retrieveMemories` (FTS5 + sqlite-vec/Qdrant, RRF hybrid). Distilled facts written as `EPISODIC` scoped by `sessionId`; forgecode's `memory_id` points here. |
| Compression            | `Compressor`     | forgecode zstd codec (`forge_repo/src/codec/compression.rs`, level 3); omni-context-rtk (`repos/OmniRoute/skills/omni-context-rtk`) | reversible context compression; RTK semantic compression for summaries.                                                                                                                  |
| Search/recall          | (viewer)         | context-mode `ctx_search` (`repos/context-mode`, FTS5 BM25)                                                                         | persistent ledger-event indexing + recall without dumping raw rows into context.                                                                                                         |
| Observability          | `TraceSink`      | pheno-tracing `TracePort` (`repos/pheno-tracing`); PhenoObservability (`repos/PhenoObservability`)                                  | spans per ledger stage; op metrics + structured logs.                                                                                                                                    |

The **forgecode lifecycle is the spine**, **OmniRoute memory is the long-term
store**, and SessionLedger contributes the missing intent extractor + the
cross-corpus ingestion + the continuation-bundle compiler + the viewer.

### Cross-project reuse opportunities

- The normalized `Session` + per-corpus adapters are a candidate **shared crate**
  (`pheno-session-model`) usable by forgecode, OmniRoute, and pheno-tracing.
- The curation pipeline (`phenotype-org-audits/curation/forge/curate.py`) is
  SessionLedger's intent-extraction core; converge it onto the `IntentExtractor`
  port (forward-only migration) rather than maintaining two extractors.
  _(cross-repo ownership move — confirm destination before executing.)_

---

## 7. Phased roadmap (DAG)

Effort in agent terms (tool-call batches / parallel subagents), aggressive bounds.

| Phase                       | Work package                                                                                                                       | Depends on | Effort                                  |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------- |
| **P0 Discovery**            | DESIGN.md, domain skeleton, port traits, dedup+FSM+bundle, tests, repo+CI                                                          | —          | ✅ done                                 |
| **P1 Build: domain**        | flesh `Contract`/`Dedup` compilers, token estimator, bundle renderer (inject form)                                                 | P0         | small feature, 3–6 calls                |
| **P2 Build: ingestion**     | rusqlite forge adapter (zstd decode, user/subagent classify) + codex/claude/cursor JSONL adapters behind `sqlite`/`jsonl` features | P0         | cross-stack, 8–15 calls / 2–3 subagents |
| **P3 Build: distill**       | `MemoryStore`+`Compressor`+`TraceSink` adapters (OmniRoute HTTP, zstd, pheno-tracing); LLM intent extractor; converge curate.py    | P1, P2     | major, 15–30 calls / 3–5 subagents      |
| **P4 Viewer**               | wiki/history HTTP+TUI; FTS recall via context-mode; unfinished section                                                             | P2, P3     | cross-stack, 8–15 calls                 |
| **P5 Merge/recovery flows** | dedup merge executor; crash detector; lost-work localizer end-to-end                                                               | P3, P4     | cross-stack, 8–15 calls                 |
| **P6 Hardening**            | 85–100% coverage, property tests on FSM/dedup, fuzz adapters, perf on 12.9k corpus                                                 | all        | major, 15–30 calls                      |

**Phase-3 progress:** the deterministic distill path now writes Intent, Contract,
and Context slices as session-scoped EPISODIC facts through `MemoryStore`.
`DistillMemoryWriter` supports optional `TraceSink` notifications, while
`distill::compile_and_store` exposes the compile-and-persist path. The heuristic
intent adapter also recognizes explicit goal and constraint labels; an
LLM-backed adapter can still replace it behind `IntentExtractor`.

```
P0 ──┬─▶ P1 ─┐
     └─▶ P2 ─┼─▶ P3 ─┬─▶ P4 ─┐
              │       └─▶ P5 ─┼─▶ P6
              └───────────────┘
```

---

## 8. Quality bar

- **Coverage: 85–100%** line coverage (CI gate `--fail-under-lines 85`, ratcheting
  toward 100% as adapters land). Domain logic (FSM, dedup, bundle) targets 100%.
- **Strict gates**: `clippy::all` denied, `clippy::pedantic` warned, `RUSTFLAGS=-D
warnings` in CI, `cargo fmt --check`, `unsafe_code` forbidden.
- **TDD**: every bug fix is a failing-then-passing test first. Property tests for
  the intent FSM (no illegal transitions) and dedup-key stability.
- **CI: Linux only** (Phenotype Actions billing policy) — `.github/workflows/ci.yml`.
- **Forward-only**: extract shared code, update callers, remove duplicates; no
  legacy-compat shims.
