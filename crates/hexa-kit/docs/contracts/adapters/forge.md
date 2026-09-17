# forge adapter (v0 stub)

**Harness ID:** `forge`  
**Status:** Phase 1b stub — dispatch surface not yet wired in `hexakit harness`  
**Contract:** [Harness API](../harness-api.md)

Primary disposition harness for ecosystem relocation and wide read-audit fan-out. Implements the four adapter operations: `dispatch`, `poll`, `cancel`, `capabilities`.

## Routing

| Lane class | Worktree | Lock |
|------------|----------|------|
| `MUTATE_RELOCATE` | Required | 1/repo + global cargo |
| `READ_AUDIT` | Optional | none (up to 18-wide parallel) |

See [ADR-ECO-007 lane routing](../harness-api.md#lane-routing-adr-eco-007) in the Harness API.

## Capabilities (v0)

| Field | Value |
|-------|-------|
| `modes` | `read-only`, `write`, `full` |
| `max_parallel` | 18 |
| `supported_profiles` | `codex`, `claude`, `droid` |

## HarnessProfile mapping

At dispatch, HexaKit maps lane `harness: "forge"` to a [HarnessProfile](https://github.com/KooshaPari/thegent/blob/main/contracts/provider-bridge/schema/harness-profile.schema.json) with `defaults.intent_capability: tool_execution` and `defaults.latency_tier: interactive`. Policy overrides inherit from the lane AACP bundle when present.

## Session pattern

Fan-out sessions use `.cursor/skills/forge-fanout/SKILL.md` — detached launcher, resource-lock discipline, and 20-wide DAG recipe. HexaKit adapters wrap this surface; they do not reimplement provider routing.

## Example lane

[forge-lane.json](../../lanes/examples/forge-lane.json)
