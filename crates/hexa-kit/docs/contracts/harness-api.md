# Harness API

**Repo:** HexaKit  
**Version:** v0 (Phase 1 enabler)  
**Spec:** PhenoSpecs 004 — Zero-shot orchestration + Harness API + FSM  
**Plan:** Ecosystem Disposition DAG v3, ADR-ECO-007 (Harness routing; AgilePlus owns DAG)

The Harness API is a harness-agnostic orchestration surface for disposition lanes. AgilePlus owns the session DAG; HexaKit provides lane descriptors, adapter dispatch, and verification hooks. Primary harness is **forge**; compatible adapters include **cursor-agent**, **thegent**, and **codex-fork**.

---

## Architecture

```
AgilePlus DAG → Lane descriptor → Router → Overlap check → AACP bundle
                                    ↓
                          Adapter (dispatch | poll | cancel | capabilities)
                                    ↓
                    forge | cursor-agent | thegent | codex-fork
                                    ↓
                              Exit gate → validate → ship
```

Implementation target: `hexakit harness` subcommand + Tasken workflow hook (Phase 1b).

---

## Lane descriptor

A lane descriptor is the unit of work for one bounded disposition relocation or audit. It is validated against [lanes/schema.json](./lanes/schema.json).

### Required fields

| Field | Purpose |
|-------|---------|
| `lane_id` | Unique lane identifier (e.g. `wave-a-wp03-metron`) |
| `disposition_ids` | DISPOSITION.md row IDs this lane owns |
| `fsm_state` | Current FSM state (`pending` … `done`; see runbook) |
| `repo` | Target GitHub repo (`org/name`) |
| `worktree` | Relative worktree path under archive-migration or canonical checkout |
| `branch` | Feature branch name |
| `owns` | Glob paths this lane may mutate |
| `forbidden_paths` | Paths that must not be touched |
| `harness` | Primary harness adapter ID |
| `harness_compat` | Fallback adapters if primary unavailable |
| `aadp` | Agent context bundle metadata (session ID, bundle version, hashes) |
| `verify` | Shell commands that must pass before lane exit |
| `exit_gate` | Merge and audit predicates |

### Example

```json
{
  "lane_id": "wave-a-wp03-metron",
  "disposition_ids": [48],
  "fsm_state": "claimed",
  "repo": "<REDACTED>/PhenoObservability",
  "worktree": "PhenoObservability-wtrees/wave-a",
  "branch": "feat/obs-metron-relocate",
  "owns": ["Metron/**"],
  "forbidden_paths": [],
  "harness": "forge",
  "harness_compat": ["cursor-agent", "thegent", "codex-fork"],
  "aadp": {
    "session_id": "20260617-eco-wave-a",
    "context_bundle_version": "1.1",
    "agent_context_bundle_hashes": []
  },
  "verify": [
    "cargo test -p metron",
    "cargo test --workspace",
    "bun run tools/check-ecosystem.ts --map-only"
  ],
  "exit_gate": {
    "pr_merged": true,
    "fsm_state": "done",
    "watcher_pass": true,
    "fr_tags": ["FR-ECO-012"]
  }
}
```

---

## Harness profile (lifted from thegent)

Each adapter invocation carries a **HarnessProfile** validated against the upstream schema:

**Source:** [`thegent/contracts/provider-bridge/schema/harness-profile.schema.json`](https://github.com/<REDACTED>/thegent/blob/main/contracts/provider-bridge/schema/harness-profile.schema.json)

Local reference copy (research): `archive-migration/thegent-fresh/contracts/provider-bridge/schema/harness-profile.schema.json`

### HarnessProfile summary

| Field | Type | Values / notes |
|-------|------|----------------|
| `harness_profile` | enum | `codex`, `claude`, `droid`, `antigma`, `codex_alt` |
| `defaults.intent_capability` | enum | `chat_completion`, `embeddings`, `rerank`, `tool_execution` |
| `defaults.latency_tier` | enum | `interactive`, `batch` |
| `defaults.quality_tier` | enum | `low`, `medium`, `high` |
| `policy_overrides.max_fallbacks` | integer | ≥ 0 |
| `policy_overrides.budget_usd_max` | number | ≥ 0 |
| `tool_policy.allowed_tool_sets` | string[] | Tool set IDs permitted for this lane |
| `tool_policy.requires_confirmation_for` | string[] | Tools requiring human confirmation |

HexaKit maps lane-level `harness` to a HarnessProfile at dispatch time. Policy overrides inherit from session AACP bundle when present.

---

## Adapter interface

All harness adapters implement four operations:

| Operation | Signature (conceptual) | Purpose |
|-----------|------------------------|---------|
| **dispatch** | `(lane_descriptor, harness_profile, prompt, context) → dispatch_id` | Start agent execution in lane worktree |
| **poll** | `(dispatch_id) → LaneStatus` | Non-blocking status; includes logs pointer |
| **cancel** | `(dispatch_id) → void` | Abort in-flight execution |
| **capabilities** | `() → Capabilities` | Report supported modes, models, tool sets |

### Capabilities response

```json
{
  "harness_id": "forge",
  "modes": ["read-only", "write", "full"],
  "max_parallel": 18,
  "supported_profiles": ["codex", "claude", "droid"],
  "mcp_tools": [
    "disposition_get_row",
    "lane_dispatch",
    "lane_status",
    "registry_sync",
    "boundary_lint",
    "components_lock_pin"
  ]
}
```

### LaneStatus

```json
{
  "dispatch_id": "uuid",
  "state": "running | succeeded | failed | cancelled",
  "exit_code": 0,
  "artifacts": ["path/to/evidence.md"],
  "error": null
}
```

### thegent reference implementation

thegent exposes a Python harness surface documented at `thegent/docs/reference/api/harness_api.md`:

- `agent_executor(agent_id, prompt, context) → ExecutionResult`
- `create_agent_executor(cwd, mode, timeout, model, agent_map) → Callable`

HexaKit adapters wrap this surface; they do not reimplement provider routing.

---

## Lane routing (ADR-ECO-007)

| Class | Worktree | Harness | Lock |
|-------|----------|---------|------|
| MUTATE_RELOCATE | Required | forge / cursor-agent | 1/repo + global cargo |
| MUTATE_SCAFFOLD | Single branch | any | 1/repo |
| READ_AUDIT | Optional | forge 18-wide | none |
| LONG_VERIFY | worktree | thegent `--owner` | session |

Worktree limits: max **3/repo**; cleanup **48h** post-merge ([WORKTREES.md](../../WORKTREES.md)).

---

## MCP tools (Phase 1b)

| Tool | Purpose |
|------|---------|
| `disposition_get_row` | Fetch disposition-index row by ID |
| `lane_dispatch` | Dispatch lane with descriptor + profile |
| `lane_status` | Poll dispatch status |
| `registry_sync` | Pull latest phenotype-registry SSOT |
| `boundary_lint` | Run HexaKit boundary lint on path set |
| `components_lock_pin` | Bump components.lock entry |

---

## FSM alignment

Lane `fsm_state` follows spec-kitty FSM:

```
pending → gated → ready → claimed → in_progress → for_review → done
                              ↓                      ↓
                           blocked ←─────────────────┘
```

Stored in `phenotype-registry/registry/disposition-index.json` per row.

---

## Related artifacts

- [Lane descriptor schema](./lanes/schema.json)
- [Crate relocation runbook](../operations/crate-relocation-runbook.md)
- [DISPOSITION.md](../boundary/DISPOSITION.md)
- thegent [`harness-profile.schema.json`](https://github.com/<REDACTED>/thegent/blob/main/contracts/provider-bridge/schema/harness-profile.schema.json)
- `.cursor/skills/forge-fanout/SKILL.md` (session fan-out pattern)
