# Containment: scoped daemon change

Status: **design only, nothing implemented, build NOT RUN.** 2026-11-06.
Supersedes the incorrect mechanism claim in `docs/ACP-CONTAINMENT-DESIGN.md` §2.3.

## Correction: the design doc is wrong about observability

`ACP-CONTAINMENT-DESIGN.md` §2.3 says `map_event` is "referenced only by its
definition and one unit test" and "not wired into the live prompt path". **Both are
false.**

`map_event` is called at `jcode-acp-native:src/cli/acp/live.rs:106`, inside the pump
task spawned by `AcpRuntime::register_session` (`live.rs:88-124`). That pump is the
**sole reader** of the daemon socket (`read_raw_event`, `live.rs:91` ->
`acp.rs:267-277`) and runs for the whole session lifetime. Per raw event it calls
`mapper.map_event()` and `write_notification("session/update", ...)`
(`live.rs:106-117`), which writes to the ACP client's stdout (`acp.rs:1270-1301`).

So tool lifecycle (`ToolStart` -> `ToolExec` -> `ToolDone`) **is** emitted to the
client as `session/update` `tool_call` / `tool_call_update` notifications during a
prompt. The earlier review inspected `run_prompt` and missed the concurrent pump.

**The conclusion survives the correction**, and it matters more than the mistake:
there is still no approval mechanism. `ToolStart` already emits a `pending` state,
but the daemon proceeds to execution immediately, and the daemon `Request` enum
(`wire.rs:38-756`) has **no** tool-permission, deny or hold variant. The only stop
lever is `Cancel`, which aborts the entire prompt.

## What has to change

> **CORRECTION (2026-11-08, read-only inspection).** The premise below is wrong in one
> specific way, and it changes the effort estimate rather than the goal.
>
> The hold does **not** need a new wire variant. It already exists out-of-band inside the
> daemon: `crates/jcode-app-core/src/tool/interaction.rs` holds the pending operation in a
> process-local map with a `oneshot::Sender`, the tool path awaits that oneshot (so the tool
> is genuinely not executed while held), and approval travels over a separate local Unix
> socket, `<daemon socket>.interactions`, mode 0600, not over the ACP JSON-RPC channel.
>
> The `Request` enum is the daemon's own control channel; tool approval never needed to be on
> it. Adding `ServerEvent::ToolPermissionRequest` / `Request::ToolPermissionResponse` as
> described below would create a **second, parallel mechanism** rather than fill the missing
> piece.
>
> The plan is still right that the ACP front end has no client-pushable policy, and right that
> `map_event` is wired.
>
> **The real gap is different:** a client that never answers stalls for the 600 s interaction
> timeout and then receives a tool error, not a clean denial. Fail-closed is preserved, but a
> non-answering client costs ten minutes per held tool call instead of failing fast. That is
> the thing to fix first.

**Daemon** (`jcode-acp-native`)
- `wire.rs`: add `ServerEvent::ToolPermissionRequest` (emitted between `ToolStart`
  and `ToolExec`) and `Request::ToolPermissionResponse { id, tool_id, allow }`.
- Tool path: when a policy is active, **hold** before `ToolExec` until the response
  arrives.

**Front end**
- Pump (`live.rs:106-117`): intercept `ToolPermissionRequest` and emit a
  `session/update` `permission_request` to the client.
- Inbound: add `session/request_permission` to `handle_message`
  (`acp.rs:350-432`) and translate it into `ToolPermissionResponse`.

The new `awaiting-approval` state blocks **between** `ToolStart` and `ToolExec`, so a
client refuses *before* execution rather than being told after the fact.

## Failure semantics

| Condition | Behaviour |
|---|---|
| `allow=true` | resume, tool executes |
| `allow=false` | deny: skip the tool, emit an error result |
| client timeout / malformed reply | fail closed (`allow:false`); must not deadlock the prompt |
| client does not implement the method | gate must be **opt-in** (the client pushes a policy first), or legacy prompts stall |
| daemon cannot hold | fallback is `Cancel` on an unapproved `ToolStart` - coarse, aborts the prompt |

Blast radius is zero for clients that never set a policy. Critically,
`require_interaction_ownership` must **not** re-gate the permission response:
validate the response against the existing owner, or the approval deadlocks the
in-flight prompt it is trying to protect.

## Effort and the riskiest assumption

**Revised: materially less than ~3-5 days**, because the hold mechanism already exists (see the
correction above). The remaining work is front-end reach and fail-fast behaviour, not building a
pause primitive.

The original riskiest assumption — "the daemon can hold tool execution mid-prompt without
corrupting its streaming/turn state" — is **already answered in the affirmative** by the existing
`interaction.rs` oneshot path. The assumption that remains untested is narrower: whether a
non-answering client can be failed fast instead of stalling 600 s.

## Why nothing was implemented

No slice satisfied all three conditions required to land safely: behaviour-preserving
for clients that ignore it, covered by tests in the fork, and small enough to stand
alone. The observational half is already wired; the enforcement half is not
behaviour-preserving without the daemon hold. Shipping the front end alone would
produce a permission prompt that cannot actually stop a tool - exactly the fake
enforcement this repository refuses.

Until the daemon change lands, the shim's `-32012` prompt refusal remains the only
real containment, and that is what the code already does.
