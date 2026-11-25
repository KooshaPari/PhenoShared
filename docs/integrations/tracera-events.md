# Tracera Event-Mapping — pheno ↔ Tracera wire format reference

> **Status:** authoritative for v0.12 (task 15 ac_v1).
> **Owner:** forge. **Source-of-truth:** `pheno/trace_store/tracera.py`
> (TraceraAdapter implementation, commit `9bcecc46`) + Grapheon
> `crates/tracera-server/src/store.rs` + `persistence_api.rs`
> (commit `e1f905693`).
> **Companion docs:** `tracera-api.md` (HTTP routes), `tracera-api.md`
> is the read-this-first overview; this doc is the field-by-field
> mapping reference.

## 1. Overview

`pheno.trace_store.TraceraAdapter` persists `TraceEvent` objects to the
Tracera persistent trace repository over HTTP. This document specifies:

- How a `TraceEvent` is mapped onto Tracera's `EvidenceCreate` payload
  for the **append** path.
- How a Tracera `Evidence` is reconstructed back into a `TraceEvent` for
  the **query** path.
- Which metadata keys are reserved by the adapter (cannot be safely
  shadowed by user payload).
- How legacy records (written before any of these conventions) are
  handled.

## 2. Append mapping (TraceEvent → Tracera EvidenceCreate)

`TraceraAdapter.append_event(event)` issues:

```
POST /evidence
Content-Type: application/json
Authorization: Bearer <token>     # only when TRACERA_API_TOKEN is set

{
  "artifact_id": "<event.id as str>",
  "kind": "<event.kind>",
  "url": "pheno://<event.target or 'unscoped'>/<event.id>",
  "metadata": {
    "pheno_event_id": "<event.id>",
    "pheno_event_kind": "<event.kind>",
    "pheno_event_ts": "<event.ts iso8601>",
    "actor": "<event.actor>",
    "session_id": "<event.session_id>",         # only when set
    "target": "<event.target>",                 # only when set
    ...event.payload                            # merged last
  },
  "links": [],
  "actor": "<event.actor>"
}
```

### Field-by-field table

| Tracera field | Source | Required | Notes |
|---|---|---|---|
| `artifact_id` | `str(event.id)` | yes | Tracera echoes this as `Evidence.id` |
| `kind` | `event.kind` | yes | free-form string; pheno uses `claim`, `evidence`, `trace`, `sprint`, `story` |
| `url` | constructed | yes | `"pheno://<target or 'unscoped'>/<id>"` |
| `metadata` | composite | yes | see metadata table below |
| `metadata.pheno_event_id` | `str(event.id)` | yes | duplicated so query can reconstruct without reading `artifact_id` |
| `metadata.pheno_event_kind` | `event.kind` | yes | duplicated so query can reconstruct if `kind` field shape changes |
| `metadata.pheno_event_ts` | `event.ts.isoformat()` | yes | pheno's authored timestamp (UTC) — distinct from Tracera's `created_at` |
| `metadata.actor` | `event.actor` | yes | echoed into metadata so query can reconstruct without audit side-channel |
| `metadata.session_id` | `event.session_id` | no | omitted when None (don't emit null) |
| `metadata.target` | `event.target` | no | omitted when None |
| `metadata.<payload keys>` | `event.payload` | no | merged AFTER the reserved keys — user keys with reserved names WILL be overridden |
| `links` | `[]` | yes | empty in v0.12 (single-shot append); cross-event links belong to future tasks |
| `actor` | `event.actor` | yes | top-level for Tracera's audit trail |

### Example (claim with session + target + payload)

```json
{
  "artifact_id": "b0731e98-6692-4760-a708-70a092f648df",
  "kind": "claim",
  "url": "pheno://repo/y#123/b0731e98-6692-4760-a708-70a092f648df",
  "metadata": {
    "pheno_event_id": "b0731e98-6692-4760-a708-70a092f648df",
    "pheno_event_kind": "claim",
    "pheno_event_ts": "2026-08-10T04:23:38.788293+00:00",
    "actor": "agent-x",
    "session_id": "session-abc",
    "target": "repo/y#123",
    "custom": "value",
    "score": 0.95
  },
  "links": [],
  "actor": "agent-x"
}
```

## 3. Query reconstruction (Tracera Evidence → TraceEvent)

`TraceraAdapter.query(session_id)` issues:

```
GET /evidence       # list all evidence (Tracera has no session_id filter)
```

Then filters client-side by `metadata.session_id == <session_id>` and
reconstructs each matching Evidence into a TraceEvent:

| TraceEvent field | Source on Evidence |
|---|---|
| `id` | `metadata.pheno_event_id` (fallback: `Evidence.artifact_id`) — wrapped in `UUID(...)` |
| `kind` | `metadata.pheno_event_kind` (fallback: `Evidence.kind`, "unknown" if both missing) |
| `ts` | `metadata.pheno_event_ts` (fallback: `Evidence.created_at`) — parsed via `datetime.fromisoformat` with `Z` → `+00:00` substitution |
| `actor` | `metadata.actor` (fallback: "unknown") |
| `target` | `metadata.target` (None if absent) |
| `session_id` | the query argument (always set on reconstructed events) |
| `payload` | `metadata` minus the 6 reserved keys |

Results are sorted by `(ts, id)` for stable iteration order.

### Reconstruction example

Tracera Evidence:

```json
{
  "id": "tracera-evidence-id-xyz",
  "artifact_id": "b0731e98-6692-4760-a708-70a092f648df",
  "kind": "claim",
  "url": "pheno://repo/y#123/b0731e98-6692-4760-a708-70a092f648df",
  "metadata": {
    "pheno_event_id": "b0731e98-6692-4760-a708-70a092f648df",
    "pheno_event_kind": "claim",
    "pheno_event_ts": "2026-08-10T04:23:38.788293+00:00",
    "actor": "agent-x",
    "session_id": "session-abc",
    "target": "repo/y#123",
    "custom": "value",
    "score": 0.95
  },
  "created_at": "2026-08-10T04:23:39.000000Z"
}
```

Reconstructed TraceEvent:

```python
TraceEvent(
    id=UUID("b0731e98-6692-4760-a708-70a092f648df"),
    kind="claim",
    ts=datetime.fromisoformat("2026-08-10T04:23:38.788293+00:00"),
    actor="agent-x",
    target="repo/y#123",
    session_id="session-abc",
    payload={"custom": "value", "score": 0.95},
)
```

## 4. Field reference table (all metadata keys written by `append_event`)

| Key | Source | Reserved? | Reconstructed? |
|---|---|---|---|
| `pheno_event_id` | `event.id` | yes | yes (`TraceEvent.id`) |
| `pheno_event_kind` | `event.kind` | yes | yes (`TraceEvent.kind`) |
| `pheno_event_ts` | `event.ts` | yes | yes (`TraceEvent.ts`) |
| `actor` | `event.actor` | yes | yes (`TraceEvent.actor`) |
| `session_id` | `event.session_id` (optional) | yes | yes (always the query argument) |
| `target` | `event.target` (optional) | yes | yes (`TraceEvent.target`) |
| `<user payload keys>` | `event.payload` | no | yes (`TraceEvent.payload`) |

## 5. Reserved keys

`append_event` writes the 6 reserved metadata keys BEFORE merging the
user payload. This means:

- User payload keys with reserved names are **overridden** by the
  adapter. Don't rely on `payload["actor"]` or `payload["session_id"]`
  round-tripping — the adapter's metadata wins.
- If you need to convey extra metadata, use non-reserved keys.
- The 6 reserved keys are listed in `pheno.trace_store.tracera._RESERVED_METADATA_KEYS`:

  ```python
  RESERVED_METADATA_KEYS = frozenset({
      "pheno_event_id",
      "pheno_event_kind",
      "pheno_event_ts",
      "actor",
      "session_id",
      "target",
  })
  ```

## 6. Backward compatibility

### Legacy records without `pheno_event_ts`

Records written before the `pheno_event_ts` convention (or whose
metadata was hand-edited) fall back to Tracera's `created_at` for the
`ts` field. The fallback path emits a `Z`-suffixed ISO8601 timestamp
which `datetime.fromisoformat` accepts after `Z → +00:00` substitution.

### Legacy records without `metadata.session_id`

Records with no `session_id` metadata are skipped by `query()` (they
don't belong to any session). Use a direct `GET /evidence` for
forensic recovery if needed.

### Legacy records without `metadata.actor`

`actor` falls back to the string `"unknown"`. Downstream consumers
should treat unknown actors with caution.

### Pre-rename records

Tracera was renamed from "Tracera" on 2026-07-14. Records written
under the old name still resolve correctly because the wire format
didn't change — only env var names (`TRACERA_*` legacy aliases for
`GRAPHEON_*`) and the server binary name (`tracera-server` →
`grapheon-server`) were affected.

## 7. Versioning notes

| Schema version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-10 | Initial: 6 reserved metadata keys, sort-by-(ts,id), Z-suffix fallback. |

The `pheno_event_*` keys are stable; any future change MUST be
additive (new keys) to preserve backward compatibility with v1.0
records already in production.

## 8. Examples

### Append + query round-trip

```python
from pheno.trace_store import TraceraAdapter, TraceEvent

adapter = TraceraAdapter(base_url="http://tracera.test:8080")

# Append 3 events to session "demo"
e1 = TraceEvent.make(kind="claim", actor="agent-a", session_id="demo",
                     target="repo/x#1", payload={"score": 0.9})
e2 = TraceEvent.make(kind="evidence", actor="agent-b", session_id="demo",
                     target="repo/x#2", payload={"url": "https://..."})
e3 = TraceEvent.make(kind="trace", actor="agent-c", session_id="demo",
                     target="repo/x#3", payload={"relation": "follows"})

# Either path works:
adapter.append_event(e1)           # synchronous POST
adapter.enqueue_event(e2)         # buffered
adapter.enqueue_event(e3)         # buffered
adapter.flush()                   # batched POST for e2 + e3

# Query back
results = adapter.query("demo")
assert len(results) == 3
assert [e.kind for e in results] == ["claim", "evidence", "trace"]
assert all(e.session_id == "demo" for e in results)
assert results[0].payload == {"score": 0.9}
```

### Bulk-import scenario

```python
adapter = TraceraAdapter(base_url="http://tracera.test:8080", batch_size=100)
for event in event_stream:           # thousands of events
    adapter.enqueue_event(event)
    if adapter.buffer_size() >= 100:
        adapter.flush()              # batch boundary
adapter.flush()                      # drain remainder
```

## See also

- `docs/integrations/tracera-api.md` — HTTP route reference (read first)
- `pheno/trace_store/tracera.py` — TraceraAdapter implementation
- `pheno/trace_store/protocols.py` — `TraceEvent`, `TraceStoreAdapter`, `TraceStoreError`
- `pheno/trace_store/config.py` — runtime-config loader
- Grapheon `crates/tracera-server/src/store.rs` — wire format definitions
- Grapheon `crates/tracera-server/src/persistence_api.rs` — HTTP handlers
