# Why Herdr doesn't just consume ACP — HeliosLite

> **TL;DR** — Herdr does not just consume ACP because they answer different
> questions:
>
> | Concern | ACP | Herdr |
> |---|---|---|
> | Purpose | Wire protocol between agent host and agent (request/response, streaming tool calls) | Always-on observation substrate (presence, lifecycle, telemetry, multi-agent registry) |
> | Lifecycle | One-shot session, terminated when the task ends | Persistent pane registry that outlives any single session |
> | Direction | Bidirectional RPC over stdio / Unix socket | Outbound events to a long-lived daemon |
> | Authority | Authoritative for the active tool call | Advisory for "is this agent working / idle / blocked / done" |
> | Multi-agent | Single agent per ACP server | Many agents registered under one Herdr daemon |
>
> For HeliosLite we **don't** own the ACP server, so even if we wanted to
> plug into ACP we'd need to fork the harness. This plugin takes the
> **non-invasive** path: a wrapper-binary that runs `helioslite` as a child
> process, observes its exit status and any side-channel signals, and emits
> `pane.report_agent` calls to Herdr. The harness binary itself stays
> stock; we never recompile it.
>
> The upstream `leonardoacosta.herdr-jcode` plugin took this same approach
> for stock jcode — they did **not** fork jcode, just wrapped it. We're
> doing the same here.

## Why ACP alone is not enough

ACP (Agent Communication Protocol) was designed to solve a focused problem:
let an agent host drive an arbitrary agent process with structured
request/response, streaming, and tool-call framing. It is by design
**session-scoped** — the agent spawns, answers one round of work, and the
host tears it down.

Herdr's question is broader. The Herdr daemon keeps a long-lived registry of
"what agents exist right now, in what panes, doing what". A pane can outlive
several ACP sessions (user closes HeliosLite, reopens an hour later). A pane
can host multiple agents in sequence (HeliosLite, then jcode, then forge).
A pane can be **idle** for hours — which is itself information the host
needs ("is Koosha working right now?").

If Herdr tried to model that purely on top of ACP it would have to either:

1. Run an ACP host for every pane forever (wasteful, and ACP sessions
   shouldn't outlive a task by design), or
2. Treat ACP as one of several signal sources alongside exit codes, screen
   scrapes, and CLI hooks (which is exactly what this plugin does).

Today the answer is #2 — Herdr is signal-agnostic, this plugin happens to
emit `pane.report_agent` via the daemon's `herdr api call` shim, and we
get lifecycle telemetry without touching the upstream HeliosLite source.

## Why the wrapper approach

The alternative is forking HeliosLite and adding an `--herdr-report` flag
that calls `pane.report_agent` directly. That gives stronger guarantees
(more reliable state, structured events) but costs:

- Permanent maintenance burden whenever HeliosLite moves
- Divergence from upstream features (anyone using this fork can't use stock
  HeliosLite changes until they're ported)
- A second binary users must keep in sync with the upstream

The wrapper costs:

- One more process boundary (trivial, <2ms)
- Slightly weaker state signal (we infer "working" from
  `helioslite`'s exit-code / child-alive status, not from internal hooks)
- A `~/.local/bin/herdr-helioslite-report` symlink to manage

For an observation-only tool the wrapper trade is correct. HeliosLite is a
closed-form TUI bound by `helioslite` semantics; the Herdr plugin lives
happily in userland.

## When to revisit

If HeliosLite ever ships an official `--report` flag (or an ACP server of
its own), the wrapper becomes the lowest-tier adapter and we should
supersede it with a direct hook. Until then, this plugin is the smallest
honest implementation that meets the Herdr contract: presence + lifecycle
+ telemetry, no fork.
