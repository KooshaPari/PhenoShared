# Session Artifact Standard — Survey & Two-Layer Model

**Status:** Research / Recommendation  
**Date:** 2026-07-03  
**Scope:** Does an existing open standard cover the _raw_ agent-session artifact/contract (the transcript itself), distinct from OKF which covers the _distilled_ knowledge items?

---

## 1. Two-Layer Model

SessionLedger operates on two distinct layers of the same data. They serve different consumers and should be governed by different standards.

```
┌─────────────────────────────────────────────────────────────────┐
│  RAW SESSION CONTRACT (this document)                            │
│                                                                  │
│  The verbatim transcript: turns, tool calls, file artifacts,     │
│  model responses. Lossless replay of what happened.              │
│                                                                  │
│  Schema: JSONL + JSON Schema (session-contract)                  │
│  Ingestion: forge.sqlite, ~/.codex/*.jsonl, ~/.claude/*.jsonl   │
│                                                                  │
│  Consumer: SessionLedger ingest → normalize → Session domain     │
│                    ↓ compile & distill                            │
├─────────────────────────────────────────────────────────────────┤
│  DISTILLED KNOWLEDGE ITEMS (OKF — Open Knowledge Format)         │
│                                                                  │
│  Typed knowledge graph: entities, relations, provenance.         │
│  Intent, context, contract, acceptance, worklog, dedup.         │
│  What was learned / decided, not what was said.                  │
│                                                                  │
│  Schema: OKF (Entity/Relation/Provenance) per ports/okf.rs      │
│  Consumer: Resume injection, memory store, wiki/history viewer   │
└─────────────────────────────────────────────────────────────────┘
```

The raw layer feeds the distilled layer. The two-layer split mirrors how
SessionLedger's pipeline works: `ingest → normalize (raw) → compile →
distill (OKF)`. Different standards are appropriate for each layer.

---

## 2. Candidate Standards Survey

### 2.1 OpenTelemetry GenAI / LLM Semantic Conventions

**What it covers:**
The OpenTelemetry semantic conventions define attributes for LLM spans:
`gen_ai.request.model`, `gen_ai.response.finish_reason`,
`gen_ai.prompt`, `gen_ai.completion`, token counts, and — via the newer
GenAI/LLM conventions (in experimental since 2024) — structured
attributes for chat messages, tool calls, and embeddings. These are
span-level attributes attached to OpenTelemetry traces.

**URL:** https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

**Raw-session fit:** Partial. The semantic conventions can model individual
LLM calls (prompt → completion) as spans with message/tool attributes,
but they are designed for _observability of production AI systems_, not for
archival of agent sessions. Key gaps:

- No notion of a "session" as a durable artifact with an id, corpus, cwd.
- No support for file artifacts (patches, diffs) that agents produce.
- No provenance chains linking multiple turns.
- Spans are ephemeral, not designed for crash recovery or resume injection.
- Agent-tool interactions are flattened into LLM span attributes rather than
  modeled as first-class artifacts.

**Distilled-knowledge fit:** Poor. OKF's entity/relation/provenance graph
is a different data model from OTel's span tree. One could _map_ OKF
entities into OTel span attributes, but there is no direct standard for
distilled knowledge items.

**Recommendation:** Do **not** adopt as the raw session contract. OTel
semantic conventions are a good serialization target for _live monitoring_
(e.g., streaming spans to a tracing backend) but unsuitable as a durable,
resumable session artifact format. SessionLedger's `TraceSink` port may
emit OTel spans for observability, but the raw session contract should be
a self-contained JSONL document.

---

### 2.2 OpenInference / AI-SDK Span Schema (Arize)

**What it covers:**
OpenInference (from Arize AI) extends OpenTelemetry with a richer span
schema specifically for LLM applications. Span kinds: `LLM`, `CHAIN`,
`RETRIEVER`, `TOOL`, `AGENT`, `GUARDRAIL`, `EVALUATOR`, `EMBEDDING`,
`RERANKER`, `PROMPT`. It defines detailed attributes for messages
(`llm.input_messages`, `llm.output_messages`), tool calls, token counts,
embeddings, documents, and cost tracking. The Vercel AI SDK uses a
similar schema internally for its `ai/tool-call` and `ai/response`
telemetry.

**URL:** https://github.com/Arize-AI/open-inference

**Raw-session fit:** Better than raw OTel, but still observability-focused.
OpenInference's `AGENT` span kind and structured message/tool attributes
can model a multi-turn session as nested spans. OpenLLMetry (an
OpenInference-compatible SDK) even has `llm.input_messages` and
`llm.output_messages` arrays that loosely resemble a conversation log.
However:

- No canonical session ID / corpus / workspace concept.
- No artifact storage (diffs, patches, file writes).
- Designed for backends like Phoenix/Arize, not for session resume.
- Retention is opaque (how long do traces live?).

**Distilled-knowledge fit:** Poor for the same reasons as OTel. OKF's
graph model does not map naturally to OpenInference span kinds.

**Recommendation:** Do **not** adopt as the raw session contract. The
message schema (role, content, tool_calls) is useful as inspiration for
a turn-level model, but the container (traces/spans) is wrong for
SessionLedger's use cases.

---

### 2.3 W3C PROV (Provenance)

**What it covers:**
The W3C PROV family (PROV-DM, PROV-O, PROV-N) defines a data model for
provenance: entities, activities, agents, and the relationships between
them (`wasGeneratedBy`, `used`, `wasAttributedTo`, `wasDerivedFrom`,
etc.). It is a conceptual data model with multiple serializations (RDF,
XML, JSON).

**URL:** https://www.w3.org/TR/prov-overview/

**Raw-session fit:** Poor. PROV models _provenance of things_ — who did
what to produce a result. It does not model conversation turns, tool
calls, or agent-level artifacts. A session transcript cannot be
naturally expressed as PROV entities and activities.

**Distilled-knowledge fit:** Good! PROV's entity/activity/agent model is
structurally similar to OKF's entity/relation/provenance model. In fact,
OKF could be serialized as PROV-O RDF without loss. The `OkfProvenance`
type in SessionLedger (`ports/okf.rs:96-102`) mirrors PROV's notion of
attribution. A future bridge could emit OKF documents as PROV-JSON.

**Recommendation:** Adopt PROV concepts as a semantic backbone for OKF,
not for the raw session. Consider a future `ProvOkfExporter` that emits
PROV-O RDF for interoperability with scholarly/knowledge provenance tools.

---

### 2.4 MLCommons / Croissant

**What it covers:**
Croissant is a metadata format for machine learning datasets, developed by
MLCommons. It wraps datasets (Parquet, CSV, JSONL, images) with structured
metadata: schema, field descriptions, splits, preprocessing, and citations.
It uses schema.org and JSON-LD.

**URL:** https://github.com/mlcommons/croissant

**Raw-session fit:** Marginal. Croissant describes _static datasets_ (e.g.,
"this Parquet file has columns 'prompt' and 'completion'"). A growing
session transcript is not a static dataset. Croissant could wrap a
frozen snapshot of sessions (e.g., "SessionLedger corpus v1") for ML
training, but it does not model the interactive turn structure.

**Distilled-knowledge fit:** Poor. OKF is a knowledge graph, not a dataset
with typed columns.

**Recommendation:** Not suitable for either layer. Croissant is for ML
dataset distribution, not session contracts or knowledge graphs.

---

### 2.5 ActivityStreams 2.0 (W3C)

**What it covers:**
ActivityStreams 2.0 is a W3C standard for modeling activity feeds: "Alice
posted a photo", "Bob liked the photo". Core types: `Activity`, `Actor`,
`Object`, `Target`, `Collection`. Extended types include `Create`,
`Update`, `Delete`, `Follow`, `Like`. Serialized as JSON-LD.

**URL:** https://www.w3.org/TR/activitystreams-core/

**Raw-session fit:** Interesting, but indirect. An agent session _could_ be
modeled as an ordered `Collection` of `Activities` (turns), where each
turn's Actor is the User or Agent and the Object is the message content.
Tool calls could be `Activities` with `type: "Apply"` or a custom extension.
However:

- No first-class support for tool calls, artifacts, or agent sessions.
- No provenance or resume semantics.
- Would require significant extension (AS2's extension mechanism is
  inherited from JSON-LD and is verbose).

**Distilled-knowledge fit:** Poor. OKF's entity-relation graph
fundamentally differs from AS2's activity feed model.

**Recommendation:** Do not adopt. AS2 is a good fit for social feeds (its
intended use case) but requires too much extension to model agent
sessions.

---

### 2.6 OCSF (Open Cybersecurity Schema Framework)

**What it covers:**
OCSF defines a vendor-agnostic schema for security events: network
activity, file events, process events, authentication, etc. It uses a
normalized JSON structure with `category_uid`, `type_uid`, and
`severity_id`.

**URL:** https://schema.ocsf.io/

**Raw-session fit:** Very poor. OCSF is purpose-built for security
telemetry (SIEM, EDR, audit logs). An agent session transcript shares
no common structure with a firewall log or a file access audit.

**Distilled-knowledge fit:** Poor for the same reasons.

**Recommendation:** Not suitable. OCSF is in a different domain entirely.

---

### 2.7 Claude Code / Codex / Forge Session-JSONL Shapes

**What it covers:**
These are the _de facto_ session formats produced by the major coding
agents. They are not standardized but share a common pattern. From
SessionLedger's ingestion adapter analysis:

| Agent             | Format                         | Key fields                                                                                       |
| ----------------- | ------------------------------ | ------------------------------------------------------------------------------------------------ |
| **Claude Code**   | JSONL per session              | `{ "role": "...", "content": "...", "tool_use": {...}, "tool_result": {...}, "ts": ... }`        |
| **Codex**         | JSONL per session              | `{ "id": "...", "messages": [...], "model": "...", "timestamp": ... }`                           |
| **Forge**         | SQLite (`conversations` table) | zstd-compressed `context_zstd` → JSONL `{ "role", "content", "tool_calls", "results", "ts_ms" }` |
| **Cursor**        | JSONL per session              | Similar to Claude Code structure                                                                 |
| **Factory Droid** | JSONL                          | Per-agent variant of the above                                                                   |

The shared de facto shape is a **JSONL stream** where each line is a
conversation turn with: role, content, optional tool_calls, optional
tool_results, and a timestamp. This is the closest thing to a "standard"
that exists today.

**URL:** See `src/ingestion/` in SessionLedger; also
`~/.claude/projects/*.jsonl`, `~/.codex/sessions/*.jsonl`,
`~/.forge/.forge.db`.

**Raw-session fit:** Excellent for ingestion — this is what SessionLedger
already consumes. The de facto JSONL-per-turn format is the raw session
contract in practice. The problem is it is _implicit_ and _ad-hoc_: each
agent has a slightly different JSONL shape, and there is no shared schema.

**Distilled-knowledge fit:** N/A (these are raw formats, not distilled).

**Recommendation:** Formalize this de facto shape as the SessionLedger
session-contract. The next section provides a concrete JSON Schema.

---

### 2.8 JSONL + JSON Schema

**What it covers:**
[JSONL](https://jsonlines.org/) (JSON Lines) is a de facto standard for
streaming structured data: one JSON object per line, newline-delimited.
[JSON Schema](https://json-schema.org/) is a standard for annotating and
validating JSON documents. Together, they are the natural container for
a session transcript: each line = one turn/event, and the schema defines
the valid shapes.

**Raw-session fit:** Excellent. JSONL is already the de facto raw session
format (see §2.7). Adding a JSON Schema to validate the turn structure
is the minimal, natural standardization step.

**Distilled-knowledge fit:** OKF documents are JSON already; they could
also be validated by a JSON Schema.

**Recommendation:** Adopt JSONL + JSON Schema as the raw session contract's
serialization format. Define a SessionLedger `session-contract.json`
schema (see §4).

---

### 2.9 AI-SDK / Vercel AI SDK Telemetry Schema

**What it covers:**
The Vercel AI SDK defines structured telemetry events for LLM calls,
tool calls, and responses. Schema includes: `ai.prompt`, `ai.completion`,
`ai.toolCall`, `ai.toolResult`, `ai.operation`. It is designed for
observability and debugging of AI SDK-based applications.

**URL:** https://sdk.vercel.ai/docs/ai-sdk-core/telemetry

**Raw-session fit:** Similar to OpenInference — observability-focused,
not archival-focused. The flat event structure (prompt/completion/toolCall
as separate events) is less natural for reconstructing a session
transcript than a per-turn JSONL model.

**Distilled-knowledge fit:** Poor.

**Recommendation:** Do not adopt. The schema is narrower than the raw
session contract need.

---

## 3. Candidate Summary Matrix

| Standard                           | Raw-session fit                                | Distilled fit         | Recommendation                    |
| ---------------------------------- | ---------------------------------------------- | --------------------- | --------------------------------- |
| OpenTelemetry GenAI semantic conv. | Partial (span model ≠ session)                 | Poor                  | Skip. Use TraceSink port only.    |
| OpenInference / AI-SDK             | Partial (message schema good, container wrong) | Poor                  | Borrow message schema ideas.      |
| W3C PROV                           | Poor (provenance-only)                         | **Excellent** (≈ OKF) | Adopt as OKF's semantic backbone. |
| MLCommons/Croissant                | Poor (static dataset)                          | Poor                  | Skip.                             |
| ActivityStreams 2.0                | Weak (needs heavy extension)                   | Poor                  | Skip.                             |
| OCSF                               | Very poor (security domain)                    | Poor                  | Skip.                             |
| Claude/Codex/Forge JSONL           | **Excellent** (de facto)                       | N/A                   | Formalize as session-contract.    |
| JSONL + JSON Schema                | **Excellent** (container+validation)           | OK                    | Adopt as the serialization.       |
| AI-SDK Telemetry                   | Weak (event ≠ turn)                            | Poor                  | Skip.                             |

---

## 4. Recommendation: Minimal SessionLedger "Session-Contract" JSON Schema

**Adopt the de facto JSONL-turn format as a formal SessionLedger
session-contract, validated by a shared JSON Schema.**

This is the minimal, highest-value step: the raw format already exists
in the wild; we write it down and validate it. It does not require
coordination with upstream tool vendors (Claude Code, Codex, etc.),
because SessionLedger already normalizes their divergent formats through
its ingestion adapters. The schema describes the _output_ of the
normalization pipeline — the `Session` domain model — which is the
canonical raw contract that SessionLedger works with internally and that
downstream consumers (the viewer, the bundle compiler, the OKF exporter)
depend on.

### 4.1 Schema Sketch (`session-contract.json`)

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schema.phenotype.dev/session-contract/v1",
  "title": "SessionLedger Session Contract",
  "description": "Canonical raw session artifact: a lossless, replayable transcript of an agent session.",

  "definitions": {
    "corpus": {
      "type": "string",
      "enum": ["forge", "codex", "claude-code", "cursor", "factory-droid"],
    },
    "role": {
      "type": "string",
      "enum": ["user", "assistant", "subagent", "tool", "system"],
    },
    "tool_call": {
      "type": "object",
      "required": ["id", "name", "arguments"],
      "properties": {
        "id": {
          "type": "string",
          "description": "Provider-assigned tool call id.",
        },
        "name": { "type": "string", "description": "Tool/function name." },
        "arguments": {
          "type": "object",
          "description": "Tool arguments as a JSON object.",
        },
      },
    },
    "tool_result": {
      "type": "object",
      "required": ["id", "content"],
      "properties": {
        "id": { "type": "string" },
        "content": { "type": "string" },
        "is_error": { "type": "boolean", "default": false },
      },
    },
    "turn": {
      "type": "object",
      "required": ["role", "content"],
      "properties": {
        "role": { "$ref": "#/definitions/role" },
        "content": { "type": "string", "description": "Message body text." },
        "ts_ms": {
          "type": "integer",
          "description": "Unix millisecond timestamp.",
        },
        "model": {
          "type": "string",
          "description": "Model id used for this turn (assistant-only).",
        },
        "tool_calls": {
          "type": "array",
          "items": { "$ref": "#/definitions/tool_call" },
        },
        "tool_results": {
          "type": "array",
          "items": { "$ref": "#/definitions/tool_result" },
        },
        "artifacts": {
          "type": "array",
          "items": { "$ref": "#/definitions/artifact" },
        },
        "provenance": { "$ref": "#/definitions/provenance_ref" },
      },
    },
    "artifact": {
      "type": "object",
      "required": ["path", "content"],
      "properties": {
        "path": {
          "type": "string",
          "description": "File path relative to session cwd.",
        },
        "content": { "type": "string", "description": "Full content or diff." },
        "action": {
          "type": "string",
          "enum": ["create", "edit", "delete", "read"],
        },
        "language": {
          "type": "string",
          "description": "Detected language for syntax highlight.",
        },
      },
    },
    "provenance_ref": {
      "type": "object",
      "properties": {
        "corpus": { "$ref": "#/definitions/corpus" },
        "session_id": { "type": "string" },
        "turn_index": { "type": "integer" },
      },
    },
  },

  "type": "object",
  "required": ["id", "corpus", "turns"],
  "properties": {
    "format": {
      "type": "string",
      "const": "sessionledger-session-contract",
      "description": "Format identifier for future compatibility.",
    },
    "version": {
      "type": "string",
      "const": "1",
    },
    "id": {
      "type": "string",
      "description": "Unique session id (UUID or corpus-assigned).",
    },
    "corpus": {
      "$ref": "#/definitions/corpus",
      "description": "Origin tool / corpus.",
    },
    "agent": {
      "type": "string",
      "description": "Agent tool name (e.g. 'claude-code', 'codex', 'forge').",
    },
    "model": {
      "type": "string",
      "description": "Default model id for the session (overridable per turn).",
    },
    "cwd": {
      "type": "string",
      "description": "Working directory / project scope.",
    },
    "title": {
      "type": "string",
      "description": "Session title or topic, when known.",
    },
    "started_at": {
      "type": "integer",
      "description": "Session start time (Unix millis).",
    },
    "ended_at": {
      "type": "integer",
      "description": "Session end time (Unix millis).",
    },
    "metadata": {
      "type": "object",
      "description": "Arbitrary key-value metadata from ingestion.",
    },
    "turns": {
      "type": "array",
      "items": { "$ref": "#/definitions/turn" },
      "description": "Ordered session turns. Each line in JSONL = 1 turn.",
    },
  },
}
```

### 4.2 JSONL Serialization

Each line of the JSONL file is a `turn` object. The session-level fields
(`id`, `corpus`, `agent`, `model`, `cwd`, `title`, `started_at`,
`ended_at`, `metadata`) are carried as a header / first line or as a
separate metadata file. When streaming, writers SHOULD emit a first turn
with `role: "system"` carrying the session metadata.

```jsonl
{"role":"system","content":"","session_id":"sess-abc123","corpus":"claude-code","model":"claude-sonnet-4-20250514","cwd":"/home/user/proj"}
{"role":"user","content":"fix the pagination bug","ts_ms":1719878400000}
{"role":"assistant","content":"Let me look at the pagination code.","model":"claude-sonnet-4-20250514","tool_calls":[{"id":"call_1","name":"read_file","arguments":{"path":"src/pagination.rs"}}],"ts_ms":1719878401000}
{"role":"tool","content":"// pagination.rs\n...","tool_results":[{"id":"call_1","content":"// pagination.rs\n..."}],"ts_ms":1719878402000}
{"role":"assistant","content":"I see the issue: the offset calculation is wrong.","model":"claude-sonnet-4-20250514","ts_ms":1719878403000,"artifacts":[{"path":"src/pagination.rs","content":"...fixed code...","action":"edit","language":"rust"}]}
```

### 4.3 Relationship to OKF

| Layer              | Format                                        | Schema                                | Consumer                                                    |
| ------------------ | --------------------------------------------- | ------------------------------------- | ----------------------------------------------------------- |
| **Raw** (this doc) | JSONL per session                             | `session-contract.json` (draft above) | `SessionLedger` ingest → normalize → `Session` domain model |
| **Distilled**      | JSON document (entities+relations+provenance) | `OkfDocument` per `ports/okf.rs`      | Resume injection, memory store, wiki viewer                 |

The raw layer is the _input_ to distillation. SessionLedger ingests
raw session-contract JSONL, normalizes to `Session`, compiles into
`ContinuationBundle`, and exports as OKF. The two schemas are versioned
independently. A raw session-contract v1 can produce OKF v1 content.

### 4.4 Adoption Cost

| Task                                                                 | Effort     | Notes                                                        |
| -------------------------------------------------------------------- | ---------- | ------------------------------------------------------------ |
| Add `session-contract.json` to `docs/`                               | Low        | What this PR does                                            |
| Add JSON Schema validation to ingestion                              | Low-Medium | `jsonschema` crate or `serde_json::Value` + manual check     |
| Backfill ingestion adapters to emit schema-conformant JSONL          | Medium     | Each adapter normalizes to `Turn` struct; serialize as JSONL |
| Add `--to-session-contract` CLI flag                                 | Low        | Reuse existing `Session` serialization                       |
| Publish schema at `https://schema.phenotype.dev/session-contract/v1` | Low        | GitHub Pages or Phenotype registry                           |

---

## 5. References

1. SessionLedger domain model: `src/domain/session.rs`
2. OKF port definition: `src/ports/okf.rs`
3. OKF export adapter: `src/export/okf.rs`
4. Ingestion adapter specs: `src/ingestion/forge.rs`, `src/ingestion/codex.rs`,
   `src/ingestion/claude_code.rs`, `src/ingestion/cursor.rs`
5. OpenTelemetry GenAI semantic conventions:
   https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
6. OpenInference span schema:
   https://github.com/Arize-AI/open-inference
7. OpenLLMetry message attributes:
   https://github.com/Arize-AI/open-inference/blob/main/spec/semantic_conventions.md
8. W3C PROV:
   https://www.w3.org/TR/prov-overview/
9. MLCommons Croissant:
   https://github.com/mlcommons/croissant
10. ActivityStreams 2.0:
    https://www.w3.org/TR/activitystreams-core/
11. OCSF:
    https://schema.ocsf.io/
12. JSON Lines:
    https://jsonlines.org/
13. JSON Schema:
    https://json-schema.org/
14. Vercel AI SDK Telemetry:
    https://sdk.vercel.ai/docs/ai-sdk-core/telemetry
15. Claude Code on-disk format: `~/.claude/projects/` (JSONL sessions)
16. Codex session store: `~/.codex/sessions/` (JSONL sessions)
17. Forge conversation DB: `~/.forge/.forge.db` → zstd → JSONL
18. Phenotype Design doc: `docs/DESIGN.md`
