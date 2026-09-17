# cursor-agent adapter (v0 stub)

**Harness ID:** `cursor-agent`  
**Status:** Phase 1b stub — dispatch surface not yet wired in `hexakit harness`  
**Contract:** [Harness API](../harness-api.md)

Compatible fallback harness for bounded lane work inside Cursor IDE agent sessions. Implements the four adapter operations: `dispatch`, `poll`, `cancel`, `capabilities`.

## Routing

| Lane class | Worktree | Lock |
|------------|----------|------|
| `MUTATE_RELOCATE` | Required | 1/repo + global cargo |
| `MUTATE_SCAFFOLD` | Single branch | 1/repo |

Used when `forge` is unavailable or when a lane is scoped to IDE-native agent tooling. See [lane routing](../harness-api.md#lane-routing-adr-eco-007).

## Capabilities (v0)

| Field | Value |
|-------|-------|
| `modes` | `read-only`, `write` |
| `max_parallel` | 1 (per lane) |
| `supported_profiles` | `codex`, `claude` |

## HarnessProfile mapping

At dispatch, HexaKit maps lane `harness: "cursor-agent"` to a [HarnessProfile](https://github.com/KooshaPari/thegent/blob/main/contracts/provider-bridge/schema/harness-profile.schema.json) with `defaults.intent_capability: tool_execution` and `defaults.latency_tier: interactive`. Tool policy inherits from session AACP bundle when present.

## Example lane

[cursor-lane.json](../../lanes/examples/cursor-lane.json)
