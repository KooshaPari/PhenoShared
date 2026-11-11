# OKF — Open Knowledge Format

> **Status:** v1.0 dialect (stable; see §13 for changelog rules).
> **Scope:** raw-artifact format emitted by SessionLedger's compile pipeline and consumed by the Dioxus viewer, downstream agents, and CI tooling.
> **Implementation reference:** `crates/sl-daemon/src/worker.rs` (writer), `crates/sl-viewer` (consumer), `src/ports/okf.rs` (port trait).

---

## Table of Contents

1. [Purpose & Design Goals](#1-purpose--design-goals)
2. [Format Identifier](#2-format-identifier)
3. [Top-Level Shape](#3-top-level-shape)
4. [Entities](#4-entities)
5. [Relations](#5-relations)
6. [Provenance](#6-provenance)
7. [Bundle → OKF Mapping](#7-bundle--okf-mapping)
8. [Message Roles](#8-message-roles)
9. [Tool-Use Trace](#9-tool-use-trace)
10. [Session Boundaries](#10-session-boundaries)
11. [Retry Semantics](#11-retry-semantics)
12. [Model Routing](#12-model-routing)
13. [Versioning & Compatibility](#13-versioning--compatibility)
14. [Concrete Examples](#14-concrete-examples)
15. [Consumer Guidance](#15-consumer-guidance)
16. [Security & Sanitization](#16-security--sanitization)
17. [Open Questions](#17-open-questions)

---

## 1. Purpose & Design Goals

OKF (Open Knowledge Format) is the wire format that SessionLedger writes
when it compiles an agent session into a knowledge graph. It is the artifact
that travels between three stages of the pipeline:

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  JSONL /     │    │   SessionLedger  │    │  OKF document    │
│  SQLite      │───▶│   compile pipeline│───▶│  (this format)   │
│  (raw input) │    │                  │    │                  │
└──────────────┘    └──────────────────┘    └────────┬─────────┘
                                                     │
                                  ┌──────────────────┼──────────────────┐
                                  ▼                  ▼                  ▼
                            ┌──────────┐      ┌──────────┐       ┌──────────┐
                            │  sl-viewer │      │  CI gates │       │  Other    │
                            │  (Dioxus) │      │           │       │  agents   │
                            └──────────┘      └──────────┘       └──────────┘
```

### Design goals

1. **Self-contained** — every document identifies its source corpus and session
   id, so a folder of `.okf.json` files is queryable without external metadata.
2. **Graph-shaped** — knowledge is a directed graph of typed entities and
   relations, not a flat record. This lets downstream consumers ask
   graph-shape questions ("which intents are bounded by this constraint?")
   rather than parsing nested JSON.
3. **Provenance first** — every entity and relation carries or inherits a
   provenance record. No anonymous nodes.
4. **Lossy on purpose** — OKF is a _distilled_ view. Raw transcripts, raw tool
   I/O, raw retry envelopes are intentionally absent; they live in the source
   session store, not in the OKF.
5. **Round-trippable** — `serde::Serialize` / `Deserialize` produces a
   byte-identical document for a given input bundle.
6. **Stable across major versions** — adding new entity or relation types is a
   **minor** version bump; changing the meaning of an existing type is a
   **major** version bump (see §13).

### Non-goals

- **Not a transcript** — full message text is in the source corpus; OKF holds
  extracted _facts_, not raw turns.
- **Not a vector store** — embedding indices live in Qdrant / OmniRoute memory,
  not in OKF.
- **Not a query language** — OKF is data, not a DSL. Consumers may build
  indexes over OKF (the viewer does this for the in-memory list view).

---

## 2. Format Identifier

Every OKF document begins with a top-level `okf` string that identifies the
dialect. Consumers MUST refuse to parse a document whose `okf` value they do
not recognize, with one exception: a consumer that supports v1.x SHOULD accept
any v1.x document (minor-version tolerant within v1).

```json
{ "okf": "1.0", ... }
```

The version string follows `[major].[minor]` semantics. There is no patch
component: bugs are fixed by bumping minor and adding migration notes.

---

## 3. Top-Level Shape

A v1.x OKF document is a single JSON object with the following required and
optional keys:

| Key          | Type            | Required | Notes                                       |
| ------------ | --------------- | -------- | ------------------------------------------- |
| `okf`        | string          | yes      | Format version (e.g. `"1.0"`).              |
| `source_id`  | string          | yes      | Session id this document was compiled from. |
| `entities`   | `OkfEntity[]`   | yes      | Knowledge graph nodes. May be empty.        |
| `relations`  | `OkfRelation[]` | no       | Typed edges. Omitted when empty.            |
| `provenance` | `OkfProvenance` | yes      | Document-level provenance.                  |

`entities` MUST appear in the order they were emitted by the compiler (this
matters for human readers and for replay determinism).

### Strict-mode additions (forward-compatible)

Future versions MAY add new top-level keys. v1.x consumers MUST ignore
unknown keys rather than failing.

---

## 4. Entities

An `OkfEntity` is a typed node in the knowledge graph.

```rust
struct OkfEntity {
    id: String,                    // unique within document
    type: String,                  // entity type (see §7)
    label: String,                 // human-readable label
    properties: serde_json::Value, // structured, may be null
}
```

### 4.1 `id`

- MUST be unique within the document.
- SHOULD follow `<type>-<N>` where `<type>` is the entity type and `<N>` is a
  monotonically increasing integer starting at 0. The compiler guarantees this
  shape; downstream tools MAY rely on it for sorting and de-duplication.
- Examples: `intent-0`, `acceptance-1`, `constraint-2`, `resource-0`,
  `state-0`, `criteria-0`, `gate-0`.

### 4.2 `type`

A short, lowercase string that classifies the node. The v1 dialect defines
seven canonical types (see §7). Consumers SHOULD treat unknown types as opaque
and render them generically ("{type}: {label}").

| Type         | Source bundle | Meaning                                          |
| ------------ | ------------- | ------------------------------------------------ |
| `intent`     | Intent        | The user's stated goal.                          |
| `acceptance` | Intent        | An acceptance signal (a "looks good" criterion). |
| `constraint` | Intent        | A do-not-cross constraint string.                |
| `resource`   | Context       | A working resource (cwd, file, URL).             |
| `state`      | Context       | A named piece of session state (title, env var). |
| `criteria`   | Contract      | A success criterion (test, watch-file, gate).    |
| `gate`       | Acceptance    | The document-level resume gate (ready / scope).  |

### 4.3 `label`

A short human-readable string. Should be safe to render as plain text.

- `intent` label is the user's goal sentence.
- `acceptance` label is the acceptance signal string.
- `constraint` label is the constraint string.
- `resource` label is the resource kind (e.g. `"working-directory"`).
- `state` label is the state name (e.g. `"session-title"`).
- `criteria` label is the criterion string.
- `gate` label is conventionally `"resume-gate"`.

### 4.4 `properties`

An open `serde_json::Value`. The compiler MAY attach structured metadata. Known
property keys are listed per type in §7. Consumers MUST tolerate unknown keys.

`properties` is serialized as `null` when empty (not `{}`), to keep documents
compact.

---

## 5. Relations

An `OkfRelation` is a typed directed edge between two entities.

```rust
struct OkfRelation {
    source: String,                // entity id (must exist in entities[])
    target: String,                // entity id (must exist in entities[])
    type: String,                  // relation type (see §5.2)
    provenance: OkfProvenance,     // edge-level provenance
}
```

### 5.1 Edge semantics

- Edges are directed. The compiler always emits them from the "origin" node to
  the "satellite" node (e.g. `intent → acceptance`, not the reverse).
- A relation MAY be reflexive only if a future minor version adds a "self-loop"
  semantic; v1.0 emits no self-loops.
- The compiler does NOT guarantee that the source/target ids appear before the
  relation in document order. Consumers MUST build an id index first.

### 5.2 Relation types

| Type          | Source   | Target             | Meaning                                    |
| ------------- | -------- | ------------------ | ------------------------------------------ |
| `verified_by` | `intent` | `acceptance`       | This intent is verified by this signal.    |
| `bounded_by`  | `intent` | `constraint`       | This intent is bounded by this constraint. |
| `grounds`     | `intent` | `resource`/`state` | This intent operates in this context.      |
| `requires`    | `intent` | `criteria`         | This intent requires this criterion.       |
| `asserts`     | `intent` | `gate`             | This intent asserts resume-gate readiness. |

These are the only five relation types in v1.0. Downstream tools SHOULD treat
unknown relation types as edges but flag them for review.

### 5.3 Relation provenance

Each relation carries its own `OkfProvenance` (see §6). In v1.0 the compiler
clones the document-level provenance onto every relation. Future versions MAY
add per-relation provenance fields (e.g. message index, turn number) — see §11
for retry semantics and §17 for open questions.

---

## 6. Provenance

`OkfProvenance` traces an entity or relation back to its origin.

```rust
struct OkfProvenance {
    corpus: String,    // source corpus (forge, codex, claude-code, cursor, ...)
    source_id: String, // session id
}
```

### 6.1 `corpus`

A short lowercase identifier for the source agent corpus. Defined values in v1.0:

| Corpus          | Meaning                       |
| --------------- | ----------------------------- |
| `forge`         | Forge session store (SQLite). |
| `codex`         | Codex session store.          |
| `claude-code`   | Claude Code session store.    |
| `cursor`        | Cursor session store.         |
| `factory-droid` | Factory Droid session store.  |

Consumers SHOULD treat unknown corpora as opaque strings and not crash.

### 6.2 `source_id`

The session id within the corpus. MUST be globally unique within the corpus
but MAY collide across corpora (the `(corpus, source_id)` pair is the
canonical identity).

### 6.3 Inherited vs explicit provenance

- **Document-level provenance** at the top of the document is the _default_.
- **Relation provenance** is always explicit (the compiler clones the default
  per edge).
- **Entity provenance** is INHERITED from the document level in v1.0 —
  individual entities do not carry a `provenance` field. This is a deliberate
  simplification; see §17 for whether v1.1 should add per-entity provenance.

---

## 7. Bundle → OKF Mapping

SessionLedger compiles sessions into `ContinuationBundle`s, which contain
typed `Bundle` entries (Intent, Context, Contract, Acceptance, Provenance,
Worklog, Dedup). OKF maps each bundle kind to entities and relations as
follows.

| Bundle kind  | OKF entity(ies) emitted                              | Relations emitted                                                                  |
| ------------ | ---------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `Intent`     | `intent` (1) + `acceptance*` (N) + `constraint*` (M) | `verified_by` (intent → each acceptance) + `bounded_by` (intent → each constraint) |
| `Context`    | `resource` (if `cwd`) + `state` (if `title`)         | `grounds` (intent → resource/state) [implicit; see §7.2]                           |
| `Contract`   | `criteria` (1)                                       | `requires` (intent → criteria)                                                     |
| `Acceptance` | `gate` (1)                                           | `asserts` (intent → gate)                                                          |
| `Provenance` | — (folded into document / relation provenance)       | —                                                                                  |
| `Worklog`    | — (not represented in OKF v1.0)                      | —                                                                                  |
| `Dedup`      | — (not represented in OKF v1.0)                      | —                                                                                  |

### 7.1 Intent translation

```text
Intent body = {
  "goal": "ship the auth fix",
  "acceptance_signals": ["tests pass", "deploy succeeds"],
  "constraints": ["no MFA removal"],
  "user_turn_count": 4,
}
```

becomes:

```json
[
  {
    "id": "intent-0",
    "type": "intent",
    "label": "ship the auth fix",
    "properties": { "user_turn_count": 4 }
  },
  {
    "id": "acceptance-0",
    "type": "acceptance",
    "label": "tests pass",
    "properties": null
  },
  {
    "id": "acceptance-1",
    "type": "acceptance",
    "label": "deploy succeeds",
    "properties": null
  },
  {
    "id": "constraint-0",
    "type": "constraint",
    "label": "no MFA removal",
    "properties": null
  }
]
```

with relations:

```json
[
  { "source": "intent-0", "target": "acceptance-0", "type": "verified_by", ... },
  { "source": "intent-0", "target": "acceptance-1", "type": "verified_by", ... },
  { "source": "intent-0", "target": "constraint-0", "type": "bounded_by", ... }
]
```

### 7.2 Context translation — known issue

`translate_context` in the current implementation emits the `resource` and
`state` entities but does NOT emit the `grounds` relations to the intent.
This is a known gap (tracked for v1.1, see §17). Consumers that need
"context attachment" must currently link via `corpus + source_id` and
assume the most-recent intent is the operative one. The spec documents the
intended behavior (`grounds` edges from intent to context entities) so that
future versions are conformant.

### 7.3 Contract translation

```text
Contract body = { "watch_files": ["src/auth.rs"], "skipped_by": ["test-suite-A"] }
```

becomes a single `criteria` entity whose `label` is the first string in
`criteria` (or empty) and whose `properties` is the entire body. The current
implementation looks at `criteria` only; downstream agents that need
`watch_files`/`skipped_by` semantics MUST inspect the `properties` blob.

### 7.4 Acceptance translation

```text
Acceptance body = { "ready": true, "scope_sized": true, "user_turns": 5 }
```

becomes:

```json
{
  "id": "gate-0",
  "type": "gate",
  "label": "resume-gate",
  "properties": { "ready": true, "scope_sized": true, "user_turns": 5 }
}
```

with an `asserts` relation from the intent to the gate.

---

## 8. Message Roles

OKF v1.0 does NOT carry raw message transcripts. However, downstream consumers
frequently need to reason about which `Role` produced a given fact (e.g. was
the goal stated by a user or inferred by an assistant?). This section
specifies how roles are surfaced in v1.0 and reserves extension points for
v1.1.

### 8.1 The five roles

Session recognizes five `Role` values:

| Role        | Glyph | Meaning                                        |
| ----------- | ----- | ---------------------------------------------- |
| `User`      | 🧑    | The human operator.                            |
| `Assistant` | 🤖    | The primary model under the user.              |
| `Subagent`  | ⚙️    | A delegated sub-task (sub-agent, sub-process). |
| `Tool`      | 🔧    | A tool result / tool message.                  |
| `System`    | 💻    | System / environment messages (rare).          |

### 8.2 Where roles appear in OKF v1.0

- **Intent goal** (`intent.label`) is sourced from a `User` message by the
  heuristic extractor. There is no explicit role tag in v1.0.
- **Acceptance signals** (`acceptance.label`) are typically sourced from
  `User` messages ("looks good", "ship it"). Some are sourced from
  `Assistant` self-reports; the compiler does not currently distinguish.
- **Constraints** (`constraint.label`) are typically `User`-stated
  prohibitions.
- **Resource / state entities** (`resource`, `state`) are sourced from
  `System` context (cwd, title) injected by the harness.

### 8.3 Reserved extension: `provenance.role`

v1.1 (proposed) adds an optional `role` field to `OkfProvenance` carrying the
`Role` of the message that sourced this entity. v1.0 consumers MUST ignore this
field if present.

---

## 9. Tool-Use Trace

Tool invocations appear in raw sessions as `Tool`-role messages. OKF v1.0
**does not** store the tool I/O itself. It does carry a few categories of
tool-derived facts:

### 9.1 What OKF v1.0 carries

- **Files mentioned** in any `Tool` message — folded into `context.key_decisions`
  in the source Session and NOT currently propagated to OKF. This is a known
  gap; consumers needing file lists must re-run the session's
  `context_extractor`.
- **Watch files / skipped-by** — these live in the `Contract` bundle and
  reach OKF as the `criteria` entity's `properties` blob.
- **Tool errors** — NOT in OKF. They live in the source session's tool
  messages; downstream tooling that needs tool-error rates must read source
  corpora, not OKF.

### 9.2 Reserved extension: `tool_call` entity type

v1.1 (proposed) adds a `tool_call` entity type that surfaces each tool
invocation as an entity with:

```json
{
  "id": "tool-call-0",
  "type": "tool_call",
  "label": "Read /code/auth/src/session.rs",
  "properties": {
    "tool": "Read",
    "args_summary": "...",
    "result_summary": "...",
    "ok": true,
    "latency_ms": 42
  }
}
```

with `invoked_by` relations from the assistant message index to each
`tool_call`. v1.0 consumers ignore this entity type.

---

## 10. Session Boundaries

A `ContinuationBundle` is bounded by a session. OKF v1.0 encodes this via the
`(corpus, source_id)` provenance pair (§6) and the top-level `source_id` key.

### 10.1 What is and is not a boundary

- **Hard boundary** — `(corpus, source_id)` is unique. Two OKF documents with
  different `source_id` describe two different sessions.
- **Soft boundary** — within a single session, a user may switch topics or
  restart. The compiler does NOT currently split a single session into multiple
  OKF documents; the entire session is one OKF.
- **Cross-session boundary** — two OKF documents with the same `corpus` but
  different `source_id` may still share entities (e.g. the same `cwd`). OKF
  v1.0 does not deduplicate across documents; consumers that need
  cross-session linking MUST do so externally.

### 10.2 Session start / end markers

The source `Session` struct has `started_at` and `ended_at` timestamps. These
are NOT currently emitted into OKF. v1.1 (proposed) adds optional
`session.started_at` and `session.ended_at` keys at the document top level.

### 10.3 File-naming convention

SessionLedger writes one OKF document per session with the filename
`<source_id>.okf.json`. This is the convention adopted by `sl-daemon`:

```
output_dir/
  forge-session-001.okf.json
  codex-session-003.okf.json
  claude-session-007.okf.json
```

Filenames MUST match the document's `source_id` (sanity check enforced by
`sl-daemon`).

---

## 11. Retry Semantics

The compiler is **idempotent over a single session** — running it twice on the
same input JSONL produces byte-identical OKF documents. Retries that occur at
_runtime_ (model calls that fail and re-issue) are NOT currently visible in
OKF; the OKF describes the FINAL state of the session, not the path to it.

### 11.1 What OKF v1.0 carries about retries

- Nothing directly. The compiler runs after the session ends, so retry counts,
  backoff levels, and circuit-breaker state are erased.

### 11.2 Why this is the right trade-off

- The viewer's purpose is to summarize "what was the user trying to do" and
  "is the result accepted" — both of which are post-retry facts.
- Retry noise pollutes the graph and would make acceptance/constraint nodes
  ambiguous.

### 11.3 Reserved extension: `retry_envelope` provenance

v1.1 (proposed) adds a `retry_envelope` block at the document level:

```json
{
  "retry_envelope": {
    "attempts": 3,
    "backoff_levels": [0, 1, 2],
    "final_outcome": "success",
    "circuit_breaker_state": "closed"
  }
}
```

v1.0 consumers ignore this block.

---

## 12. Model Routing

When a session involves model fallback (e.g. OmniRoute's combo routing
selects a different upstream provider), OKF v1.0 records the **final** model
that produced the assistant content. Intermediate fallbacks are not retained.

### 12.1 Where model info appears

- **Document-level provenance** does NOT currently include model id. This is
  a v1.0 limitation; consumers needing model attribution must read the source
  session.
- **Per-message model attribution** is also out of scope for v1.0.

### 12.2 Reserved extension: `model` provenance field

v1.1 (proposed) adds an optional `model` field to `OkfProvenance`:

```json
{
  "corpus": "forge",
  "source_id": "sess-abc",
  "model": {
    "provider": "openai",
    "model": "gpt-5",
    "fallback_chain": ["anthropic/claude-sonnet-4-6", "google/gemini-2.5-pro"]
  }
}
```

When this field is present, the FINAL model is the one that produced the
content; the fallback chain is informational.

### 12.3 Why this is deferred

- Model attribution belongs in the source session, not in the distilled view.
  Carrying it in OKF risks leaking provider details into a format meant to be
  long-lived and portable.
- Downstream consumers that need per-attempt model traces should use the
  source corpus + their own routing logs.

---

## 13. Versioning & Compatibility

### 13.1 Version tuple

`okf` field carries `[major].[minor]`. There is no patch level.

### 13.2 Compatibility rules

| Change kind                                | Bump  | Consumer behavior                             |
| ------------------------------------------ | ----- | --------------------------------------------- |
| Add new entity type                        | minor | Existing consumers ignore; new consumers see. |
| Add new relation type                      | minor | Existing consumers ignore; new consumers see. |
| Add optional top-level key                 | minor | Existing consumers ignore; new consumers see. |
| Add optional field to entity/relation      | minor | Existing consumers ignore; new consumers see. |
| Rename an entity or relation type          | major | Existing consumers MUST reject.               |
| Change semantic of an existing entity type | major | Existing consumers MUST reject.               |
| Change the meaning of `properties` keys    | major | Existing consumers MUST reject.               |
| Remove a type or relation                  | major | Existing consumers MUST reject.               |

### 13.3 Rejection policy

A consumer that does not recognize the major version MUST refuse the document.
A consumer that recognizes the major but not the minor version SHOULD accept
the document but emit a warning. A consumer that recognizes both MUST parse
strictly (no partial parses).

### 13.4 Migration notes

Any minor-version bump MUST be accompanied by a `CHANGELOG.md` entry in
SessionLedger that lists:

- The new types / fields added
- Any _semantic_ clarification of existing fields (clarifications are
  minor-level; semantic changes are major-level and require a migration guide)

---

## 14. Concrete Examples

### 14.1 Minimal session

Input session: a single user/assistant exchange about fixing a login bug.

OKF:

```json
{
  "okf": "1.0",
  "source_id": "forge-session-001",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Fix login timeout regression after auth refactor",
      "properties": { "user_turn_count": 5 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "all existing auth tests pass",
      "properties": null
    },
    {
      "id": "acceptance-1",
      "type": "acceptance",
      "label": "session expiry extends beyond 30 min",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "must not touch password reset flow",
      "properties": null
    },
    {
      "id": "resource-0",
      "type": "resource",
      "label": "working-directory",
      "properties": { "cwd": "/home/dev/auth-service" }
    },
    {
      "id": "state-0",
      "type": "state",
      "label": "session-title",
      "properties": { "title": "Login timeout fix" }
    },
    {
      "id": "gate-0",
      "type": "gate",
      "label": "resume-gate",
      "properties": { "ready": true, "scope_sized": true, "user_turns": 5 }
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "acceptance-1",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "gate-0",
      "type": "asserts",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
}
```

### 14.2 Edge case: missing intent

A session with no detectable goal produces an empty `intent` entity:

```json
{
  "okf": "1.0",
  "source_id": "forge-empty-002",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "",
      "properties": { "user_turn_count": 0 }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-empty-002" }
}
```

Consumers MUST tolerate empty `label` strings and zero-turn intents.

### 14.3 Edge case: multiple intents

A session that contains two distinct goals (e.g. "fix the bug AND update the
docs") produces TWO `intent` entities, each with their own acceptance and
constraint satellites:

```json
{
  "okf": "1.0",
  "source_id": "forge-multi-003",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Fix login timeout regression",
      "properties": { "user_turn_count": 3 }
    },
    {
      "id": "intent-1",
      "type": "intent",
      "label": "Update auth documentation",
      "properties": { "user_turn_count": 2 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "tests pass",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "do not change public API",
      "properties": null
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-multi-003" }
    },
    {
      "source": "intent-1",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": { "corpus": "forge", "source_id": "forge-multi-003" }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-multi-003" }
}
```

Consumers MUST NOT assume exactly one `intent` entity per document.

---

## 15. Consumer Guidance

### 15.1 Building an index

```rust
// pseudo-code
let doc: OkfDocument = serde_json::from_str(&text)?;
let mut by_id: HashMap<String, &OkfEntity> =
    doc.entities.iter().map(|e| (e.id.clone(), e)).collect();
let outgoing: HashMap<&str, Vec<&OkfRelation>> =
    doc.relations.iter().group_by(|r| r.source.as_str());
```

### 15.2 Detecting resume-gate readiness

```rust
let ready = doc.entities.iter().any(|e| {
    e.type == "gate"
        && e.properties.get("ready").and_then(|v| v.as_bool()) == Some(true)
});
```

### 15.3 Walking acceptance signals

```rust
let intent_id = "intent-0";
let acceptance_ids: Vec<&str> = doc.relations.iter()
    .filter(|r| r.source == intent_id && r.type == "verified_by")
    .map(|r| r.target.as_str())
    .collect();
let acceptance_labels: Vec<&str> = acceptance_ids.iter()
    .filter_map(|id| by_id.get(*id).map(|e| e.label.as_str()))
    .collect();
```

### 15.4 Round-trip test

Any consumer that mutates an OKF document SHOULD round-trip through
`serde_json` before writing it back:

```rust
let serialized = serde_json::to_string(&doc)?;
let parsed: OkfDocument = serde_json::from_str(&serialized)?;
assert_eq!(doc, parsed);
```

---

## 16. Security & Sanitization

### 16.1 Source content is untrusted

`label` and `properties` strings originate from raw agent sessions. They MAY
contain:

- Arbitrary user text, including shell fragments or URLs.
- Code snippets (legitimate use case).
- Adversarial content if the upstream agent was prompt-injected.

### 16.2 Renderer rules

- Render `label` as plain text, never as HTML. The viewer uses `{label}`
  interpolation, which Dioxus escapes by default.
- Do NOT render `properties` directly. Inspect keys you recognize; ignore
  unknown keys.
- Cap `label` rendering length at, e.g., 240 characters to bound the rendered
  DOM.

### 16.3 Storage rules

- File-system writer (`sl-daemon`) MUST reject `source_id` values containing
  `/`, `..`, or null bytes. Filename collisions MUST be reported, not
  silently overwritten.
- Output directory SHOULD be created with mode `0700` if it contains session
  provenance.

### 16.4 Provenance leakage

`(corpus, source_id)` MAY be sensitive (it identifies which developer ran
which session). Downstream tools that ship OKF documents to external systems
SHOULD redact `provenance` first.

---

## 17. Open Questions

These are unresolved design decisions that may affect v1.1:

1. **Per-entity provenance** — should `OkfEntity` carry its own provenance
   record? Current decision: no, inherit from document. Revisit if multi-source
   documents ever become a thing.
2. **`grounds` edges from intent to context** — `translate_context` does not
   currently emit these. Tracked for v1.1; v1.0 consumers must walk
   `(corpus, source_id)` to attach context.
3. **Model routing in provenance** — defer to v1.1 (see §12.3). Coordinate
   with OmniRoute team on the field shape.
4. **Retry envelopes** — defer to v1.1 (see §11.3).
5. **Tool-call entities** — defer to v1.1 (see §9.2).
6. **Cross-session linking** — out of scope. Consumers that need a knowledge
   graph across sessions must build one externally.
7. **Binary serialization** — v1.0 is JSON only. If a future version adds CBOR
   or MessagePack, it MUST be opt-in (a top-level `encoding` key) so existing
   JSON consumers do not break.
8. **Streaming writes** — v1.0 requires the document to be complete before
   write. A future version MAY add NDJSON-style streaming for very large
   sessions; deferred.

---

## Appendix A — Quick Reference Card

```
TOP-LEVEL:  okf, source_id, entities[], relations?, provenance
ENTITY:     id, type, label, properties?
RELATION:   source, target, type, provenance
PROVENANCE: corpus, source_id

TYPES:      intent | acceptance | constraint | resource | state | criteria | gate
RELATIONS:  verified_by | bounded_by | grounds | requires | asserts

FILENAME:   <source_id>.okf.json
VERSION:    "1.0"  (forward-compatible with 1.x)
```

---

_End of OKF v1.0 specification._
