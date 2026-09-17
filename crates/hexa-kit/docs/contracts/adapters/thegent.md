# thegent adapter (v0 stub)

**Harness ID:** `thegent`  
**Status:** Phase 1b stub — dispatch surface not yet wired in `hexakit harness`  
**Contract:** [Harness API](../harness-api.md)

Python harness adapter backed by thegent provider-bridge. Wraps thegent's harness surface; HexaKit does not reimplement provider routing. Implements the four adapter operations: `dispatch`, `poll`, `cancel`, `capabilities`.

## Routing

| Lane class | Worktree | Lock |
|------------|----------|------|
| `LONG_VERIFY` | Required | session (`--owner`) |

Fallback for `MUTATE_RELOCATE` and `READ_AUDIT` when primary harness is unavailable. See [lane routing](../harness-api.md#lane-routing-adr-eco-007).

## Reference implementation

thegent exposes:

- `agent_executor(agent_id, prompt, context) → ExecutionResult`
- `create_agent_executor(cwd, mode, timeout, model, agent_map) → Callable`

Documented at `thegent/docs/reference/api/harness_api.md`.

## HarnessProfile

Each dispatch carries a [HarnessProfile](https://github.com/KooshaPari/thegent/blob/main/contracts/provider-bridge/schema/harness-profile.schema.json) validated against the upstream schema. HexaKit maps lane-level `harness: "thegent"` at dispatch time; `policy_overrides` and `tool_policy` inherit from the session AACP bundle when present.

## Capabilities (v0)

| Field | Value |
|-------|-------|
| `modes` | `read-only`, `write`, `full` |
| `max_parallel` | 4 |
| `supported_profiles` | `codex`, `claude`, `droid`, `antigma`, `codex_alt` |
