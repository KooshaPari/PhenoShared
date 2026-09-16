# AgilePlus Event-Mapping — Bead ↔ AgilePlus wire-format reference

> **Status:** authoritative for v0.12 (task 33 ac_v1).
> **Owner:** forge. **Source-of-truth:** `pheno-harness/beads/
> agileplus_adapter/agileplus_adapter.py` + `traces/tracera_bridge.py`
> + `AgilePlus/crates/agileplus-api/src/routes/`.
> **Companion docs:** `agileplus-api.md` (HTTP routes, task 21),
> `tracera-events.md` (parallel Tracera reference, task 15).

## 1. Overview

`beads.agileplus_adapter.AgilePlusBeadStore` persists `Bead` objects
to AgilePlus by mapping them onto **work-package transitions**. Each
bead becomes one transition entry; the bead's `kind` becomes the
target state, `text` becomes the transition reason, and the
`RESERVED_METADATA_FIELDS` are surfaced in the transition payload as
a metadata block so `query()` can reconstruct the Bead on read-back.

This document specifies:

- How a `Bead` is mapped onto AgilePlus's transition POST body for
  the **append** path.
- How AgilePlus `events` are reconstructed back into a `Bead` for
  the **query** path.
- Which metadata keys are reserved by the adapter (cannot be safely
  shadowed by user payload).
- How legacy records (written before any of these conventions) are
  handled.

## 2. Append mapping (Bead → AgilePlus transition POST)

`AgilePlusBeadStore.append(bead)` issues:

```
POST /api/v1/work-packages/{wp_id}/transition
Content-Type: application/json
Authorization: Bearer <token>     # only when AGILEPLUS_API_TOKEN is set

{
  "target_state": "<bead.kind>",
  "reason": "<bead.text>",
  "metadata": {
    "bead_id": "<bead.id>",
    "bead_ts": "<bead.ts iso8601>",
    "bead_agent": "<bead.agent>",
    "bead_kind": "<bead.kind>",
    "bead_target": "<bead.target>",
    "bead_hash": "<bead.hash>",
    "host": "<bead.host>",
    ...bead.metadata                   # merged AFTER reserved keys (reserved keys WIN)
  }
}
```

### Field-by-field table

| AgilePlus field | Source | Required | Notes |
|---|---|---|---|
| `target_state` | `bead.kind` | yes | AgilePlus uses this as the WP transition target |
| `reason` | `bead.text` | yes | Human-readable transition rationale |
| `metadata.bead_id` | `bead.id` | yes | 8-char hash; client-assigned identity |
| `metadata.bead_ts` | `bead.ts` | yes | pheno's authored timestamp (UTC) |
| `metadata.bead_agent` | `bead.agent` | yes | 8-char agent hash |
| `metadata.bead_kind` | `bead.kind` | yes | Duplicated into metadata for query() reconstruction |
| `metadata.bead_target` | `bead.target` | yes | Filter key for query() |
| `metadata.bead_hash` | `bead.hash` | yes | dedup_check() key |
| `metadata.host` | `bead.host` | yes | hostname of the writing agent |
| `metadata.<payload keys>` | `bead.metadata` | no | merged AFTER the 6 reserved fields + host; user keys with reserved names are overridden |

### Why this mapping?

AgilePlus's API has no dedicated "bead store" endpoint. The closest
surface is the **work-package transition** POST handler, which
already accepts a `metadata` block in its payload. By routing every
bead through a single WP, we:

1. Get a stable query surface (`GET /api/v1/events?entity_type=
   work_package&entity_id={wp_id}`) without needing new server code.
2. Preserve bead identity (client-assigned `bead.id` round-trips).
3. Keep dedup working (`dedup_check()` only needs to scan events
   with `bead_hash` matching the incoming bead's hash).

## 3. Query reconstruction (AgilePlus event → Bead)

`AgilePlusBeadStore.query(target)` issues:

```
GET /api/v1/events?entity_type=work_package&entity_id={wp_id}&limit=10000
```

Then filters client-side by `metadata.bead_target == <target>` and
reconstructs each matching event into a Bead.

Each event in the response has the shape::

    {
      "id": <wp_transition_id>,
      "entity_type": "work_package",
      "entity_id": <wp_id>,
      "type": "transition",
      "actor": <agent_name>,
      "occurred_at": <iso8601>,
      "metadata": {
        "bead_id": "<8-char hash>",
        "bead_ts": "<iso8601>",
        "bead_agent": "<8-char>",
        "bead_kind": "<kind>",
        "bead_target": "<target>",
        "bead_hash": "<8-char>",
        "host": "<host>",
        ...<user metadata>...
      }
    }

Reconstruction reads `metadata.bead_*` fields with sensible
fallbacks to top-level event fields. The user `metadata` payload is
rebuilt by stripping the 6 reserved fields + `host`.

Results are sorted by `(ts, id)` for stable iteration order.

### Reconstruction example

AgilePlus event:

```json
{
  "id": 12345,
  "entity_type": "work_package",
  "entity_id": 42,
  "type": "transition",
  "actor": "agent-x",
  "occurred_at": "2026-08-10T07:30:00Z",
  "metadata": {
    "bead_id": "abc12345",
    "bead_ts": "2026-08-10T07:30:00Z",
    "bead_agent": "agent-x",
    "bead_kind": "claim",
    "bead_target": "pheno-harness",
    "bead_hash": "hash0001",
    "host": "m1",
    "session_id": "s1",
    "score": 0.95
  }
}
```

Reconstructed Bead:

```python
Bead(
    id="abc12345",
    ts="2026-08-10T07:30:00Z",
    agent="agent-x",
    kind="claim",
    target="pheno-harness",
    text="<from event.reason — not in this example>",
    hash="hash0001",
    host="m1",
    metadata={"session_id": "s1", "score": 0.95},
)
```

### Fallback chain (legacy events)

For events written before the `bead_*` metadata convention:

| Bead field | Fallback chain |
|---|---|
| `id` | `metadata.bead_id` → `event.id` |
| `ts` | `metadata.bead_ts` → `event.occurred_at` |
| `agent` | `metadata.bead_agent` → `event.actor` → `"unknown"` |
| `kind` | `metadata.bead_kind` → `event.type` → `"unknown"` |
| `target` | `metadata.bead_target` → `""` |
| `text` | `event.reason` → `""` |
| `hash` | `metadata.bead_hash` → `""` |
| `host` | `metadata.host` → `""` |

## 4. Field reference table (all metadata keys written by `append`)

| Key | Source | Reserved? | Reconstructed? |
|---|---|---|---|
| `bead_id` | `bead.id` | yes | yes (`Bead.id`) |
| `bead_ts` | `bead.ts` | yes | yes (`Bead.ts`) |
| `bead_agent` | `bead.agent` | yes | yes (`Bead.agent`) |
| `bead_kind` | `bead.kind` | yes | yes (`Bead.kind`) |
| `bead_target` | `bead.target` | yes | yes (`Bead.target`) |
| `bead_hash` | `bead.hash` | yes | yes (`Bead.hash`) |
| `host` | `bead.host` | yes | yes (`Bead.host`) |
| `<user payload keys>` | `bead.metadata` | no | yes (`Bead.metadata`) |

## 5. Reserved keys

`append()` writes the 6 reserved metadata keys + `host` BEFORE
merging the user payload. In Python dict construction, later keys
win — so the reserved keys override any user payload keys with the
same name. Don't rely on `metadata["agent"]` or `metadata["target"]`
round-tripping — the adapter's reserved values win.

If you need to convey extra metadata, use non-reserved keys. The 7
reserved keys are listed in
`pheno-harness/beads/agileplus_adapter/agileplus_adapter.py` as:

```python
RESERVED_METADATA_FIELDS = frozenset({
    "bead_id",
    "bead_ts",
    "bead_agent",
    "bead_kind",
    "bead_target",
    "bead_hash",
})
# + "host" (treated as reserved by append/query but not in the frozenset)
```

## 6. Backward compatibility

### Legacy records without `metadata.bead_*` fields

Records written before the `bead_*` metadata convention (or hand-
edited events) are reconstructed using the top-level event fields
with sensible fallbacks. The reconstruction is lossy — `kind` falls
back to `event.type`, `agent` falls back to `event.actor`, `text`
falls back to `event.reason` — but every field round-trips through
some path.

### Legacy records without `metadata.bead_target`

Records with no `bead_target` metadata are skipped by `query()`
(they don't belong to any target). Use a direct `GET /api/v1/events`
for forensic recovery if needed.

### Pre-rename records

Tracera was renamed from "Tracera" on 2026-07-14. Records written
under the old name still resolve correctly because the wire format
didn't change — only env var names (`TRACERA_*` legacy aliases for
`GRAPHEON_*`) and the server binary name were affected. (AgilePlus
has not had a rename event.)

## 7. Versioning notes

| Schema version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-10 | Initial: 6 reserved metadata fields + `host`, sort-by-(ts,id), WP-based routing |

The `bead_*` keys are stable; any future change MUST be additive
(new keys) to preserve backward compatibility with v1.0 records
already in production.

## 8. Examples

### Append + query round-trip

```python
from beads.agileplus_adapter import AgilePlusBeadStore, Bead

store = AgilePlusBeadStore(work_package_id=42)

# Append 3 beads to target "demo"
e1 = Bead.make(kind="claim", target="demo", text="claim #1",
               agent="agent-a", host="m1",
               metadata={"session_id": "demo", "score": 0.9})
e2 = Bead.make(kind="complete", target="demo", text="done",
               agent="agent-b", host="m1")
e3 = Bead.make(kind="warn", target="demo", text="warning",
               agent="agent-c", host="m1")

store.append(e1)
store.append(e2)
store.append(e3)

# Query back
results = store.query("demo")
assert len(results) == 3
assert [b.kind for b in results] == ["claim", "complete", "warn"]
assert all(b.target == "demo" for b in results)
assert results[0].metadata == {"session_id": "demo", "score": 0.9}
```

### Dedup check

```python
# Before appending, check if a bead with the same hash exists.
b = Bead.make(kind="claim", target="demo", text="hello",
              agent="agent-x", host="m1")
if not store.dedup_check(b):
    store.append(b)
else:
    print("duplicate — skipping")
```

### Migrate from JSONL (task 29)

```bash
$ bead-ctl migrate --from-jsonl --dry-run --limit 3
  [dry-run] would import 0ed71cbd claim phenoAI/65
  [dry-run] would import a4036009 warn OmniRoute/493
  [dry-run] would import 5803bec7 ctl pheno/272

Migration summary: total=4 imported=0 skipped=0 failed=0
```

## See also

- `docs/integrations/agileplus-api.md` — HTTP route reference (task 21)
- `docs/integrations/tracera-events.md` — Tracera parallel (task 15)
- `pheno-harness/beads/agileplus_adapter/agileplus_adapter.py` — implementation
- `pheno-harness/beads/agileplus_adapter/config.py` — config loader (task 27)
- `pheno-harness/beads/bead-ctl.sh` — CLI dual-write (tasks 28-31)
- `AgilePlus/crates/agileplus-api/src/routes/work_packages.rs` — wire format
- `AgilePlus/crates/agileplus-api/src/routes/events.rs` — query endpoint
