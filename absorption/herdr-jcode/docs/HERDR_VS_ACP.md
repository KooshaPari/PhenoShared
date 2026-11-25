# HERDR vs ACP — why this plugin exists

**TL;DR** — Herdr does not just consume ACP because they answer different questions:

| Concern | ACP | Herdr |
|---|---|---|
| Purpose | Wire protocol between agent host and agent (request/response, streaming tool calls) | Always-on observation substrate (presence, lifecycle, telemetry, multi-agent registry) |
| Lifecycle | One-shot session, terminated when the task ends | Persistent pane registry that outlives any single session |
| Direction | Bidirectional RPC over stdio / Unix socket | Outbound events to a long-lived daemon |
| Authority | Authoritative for the active tool call | Advisory for "is this agent working / idle / blocked / done" |
| Multi-agent | Single agent per ACP server | Many agents registered under one Herdr daemon |

## Jcode is special: it *does* speak ACP

Unlike ForgeCode or HeliosLite, Jcode ships a full ACP server (`src/cli/acp.rs` in
the fork, exposed via `jcode acp`). So the obvious question is fair: *why doesn't
Herdr just talk ACP to Jcode and skip this plugin?*

Because the two are not substitutes:

1. **ACP is a session host contract, not an observer.** To drive Jcode over ACP,
   Herdr would have to *own* the session: spawn the ACP server, hold the
   request/response stream, and keep it alive per pane. Herdr's model is the
   opposite — it observes a pane whose lifecycle the *shell* already owns.
   Turning Herdr into an ACP host would make it responsible for every agent's
   session, and it would still need a separate path for every agent that has no
   ACP server (ForgeCode, HeliosLite, Cursor, …).

2. **ACP is scoped to one active turn.** ACP tells you what happened *inside* a
   tool call. Herdr answers *across* turns and *across* panes: which pane is
   blocked on a prompt right now, which workspace has three agents running, what
   ran and finished while you were away. That state must outlive any single ACP
   session, because the whole point is to still show it after the session ends.

3. **ACP is one agent per server; Herdr is many agents per daemon.** The Herdr
   sidebar is a multi-pane rollup. ACP has no notion of "my neighbours".

4. **The non-invasive path ships today.** This plugin wraps the stock `jcode`
   binary, watches its lifecycle, and emits `pane.report_agent` /
   `pane.report_agent_session`. Zero fork, zero shared-library preload, zero
   ownership of Jcode's ACP contract.

The fork *also* reports natively through the `jcode-herdr` crate (socket
`pane.report_agent`), which is the same signal this wrapper produces — just
emitted in-process. Both are lifecycle reports to Herdr; neither replaces ACP,
and ACP does not replace either.

## What this plugin actually does

1. The pane-detector inside Herdr matches the running binary to `agent = "jcode"`
   via the rules in `agent-detection/jcode.toml`.
2. Herdr stamps the pane with `source = "herdr:jcode"` and `agent = "jcode"` and
   writes a `pane.detected` event into the pane history.
3. Lifecycle hooks (`session_start`, `turn_start`, `turn_end`, `session_end`)
   call the wrapper, which invokes `herdr pane report-agent ...` with the correct
   state mapping:
   - `session_start|turn_start` → `working`
   - `turn_end`                → `idle`
   - `error|blocked`           → `blocked`
   - `session_end|end`         → `done`
   - `session <id>`            → `pane.report_agent_session` (native restore id)
4. Herdr's pane registry keeps the last reported state visible in the UI even
   after the process exits.

## What we deliberately don't do

- **No ACP client embedded in the wrapper.** Adding `agent_client_protocol` as a
  dependency would mean shipping a binary that speaks stdio JSON-RPC to a child
  `jcode` process — i.e. owning Jcode's ACP server contract. That is a fork by
  another name, and it duplicates the ACP server Jcode already has.
- **No tap on `jcode`'s stdout for tool-call events.** The canonical signal is the
  lifecycle event Herdr already tracks.
- **No shared-library preload.** No `LD_PRELOAD` / `DYLD_INSERT_LIBRARIES` —
  those are forks in disguise and they break code-signing.

## When ACP-to-Herdr *would* be the right call

If Herdr ever grows a first-class "spawn and own an ACP session per pane" mode,
then a Jcode pane could be driven entirely over ACP. Even then, Herdr would still
need this plugin's lifecycle channel for the agents that have no ACP server, and
for the post-session registry that ACP cannot express.

## TL;DR for the README

> ACP is for the **active tool call**. Herdr is for the **rest of the agent's
> life** — when it started, whether it's stuck, when it ended, what it left
> behind. Different questions, different plumbing.
