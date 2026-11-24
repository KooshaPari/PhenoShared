# HERDR vs ACP — why this plugin exists

**TL;DR** — Herdr does not just consume ACP because they answer different questions:

| Concern | ACP | Herdr |
|---|---|---|
| Purpose | Wire protocol between agent host and agent (request/response, streaming tool calls) | Always-on observation substrate (presence, lifecycle, telemetry, multi-agent registry) |
| Lifecycle | One-shot session, terminated when the task ends | Persistent pane registry that outlives any single session |
| Direction | Bidirectional RPC over stdio / Unix socket | Outbound events to a long-lived daemon |
| Authority | Authoritative for the active tool call | Advisory for "is this agent working / idle / blocked / done" |
| Multi-agent | Single agent per ACP server | Many agents registered under one Herdr daemon |

For **ForgeCode** we don't own the ACP server, so even if we wanted to plug into ACP we'd need to fork the harness. This plugin takes the **non-invasive** path: a wrapper-binary that runs `forge` as a child process, observes its exit status and any side-channel signals, and emits `pane.report_agent` calls to Herdr. The harness binary itself stays stock; we never recompile it.

The upstream `leonardoacosta.herdr-jcode` plugin took this same approach for stock `jcode` — they did **not** fork `jcode`, they wrapped it. We're doing the same here for `forge`.

## What this plugin actually does

1. The pane-detector inside Herdr matches the running binary to `agent_id = "forgecode"` via the rules in `agent-detection/forgecode.toml`.
2. Herdr stamps the pane with `source = "herdr:forgecode"` and `agent = "forgecode"` and writes a `pane.detected` event into the pane history.
3. Lifecycle hooks (`session_start`, `turn_end`, `session_end`) call the wrapper, which invokes `herdr api call pane.report_agent ...` with the correct state mapping:
   - `session_start|start` → `working`
   - `turn_end`           → `idle`
   - `error|blocked`      → `blocked`
   - `session_end|end`    → `done`
4. Herdr's pane registry keeps the last reported state visible in the UI even after the process exits.

## What we deliberately don't do

- **No ACP client embedded in the wrapper.** Adding `agent_client_protocol` as a Rust dep would mean shipping a binary that speaks stdio JSON-RPC to a child `forge` process — which means owning `forge`'s ACP server contract. That's a fork by another name.
- **No tap on `forge`'s stdout for tool-call events.** We can scrape stdout for prompt/state heuristics if needed, but the canonical signal is the lifecycle event Herdr already tracks.
- **No shared-library preload.** No `LD_PRELOAD` / no `DYLD_INSERT_LIBRARIES` — those are forks in disguise and they break code-signing.

## When ACP would actually be the right call

If KooshaPari or someone else built an upstream ForgeCode fork whose ACP contract is open (e.g. `forge-acp-server` accepting JSON-RPC), then this plugin could be replaced with a Rust binary that speaks ACP directly. Until then, the wrapper approach is the only path that ships without a fork.

## TL;DR for the README

> ACP is for the **active tool call**. Herdr is for the **rest of the agent's life** — when it started, whether it's stuck, when it ended, what it left behind. Different questions, different plumbing.
