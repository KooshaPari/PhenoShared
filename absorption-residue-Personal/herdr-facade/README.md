# herdr-facade (MVP, Windows-first)

Authored by Instinct. Review only. Nothing here is installed anywhere yet.

A small loopback HTTP API in front of the `herdr` CLI, so the owner (and Instinct on his behalf) can read panes and type into a scoped set of panes from any tailnet device, with an audit trail. One file, no dependencies, Node 20+.

## Why not only the third-party relay
The Mac runs benkraus/herdr-plugin-mobile-relay (linux/macos only, no Windows). The desk is Windows, so this facade is the owned equivalent: same shape (loopback + Tailscale Serve identity), but small enough to read in five minutes.

## Design
- **Bind:** 127.0.0.1 only. The port is configurable, the host is not.
- **Auth:** every request needs `Tailscale-User-Login` equal to `FACADE_TRUSTED_USER`. Tailscale Serve injects that header for tailnet users and strips client-supplied copies. Missing or wrong identity: 403, audited.
- **Read:** any pane (`GET /v1/panes`, `/v1/workspaces`, `/v1/panes/<id>/read`).
- **Write:** `POST /v1/panes/<id>/text` and `/keys` work only for panes in a workspace whose label matches `FACADE_WRITE_SCOPE` (default `^instinct\b`, case-insensitive). Everything else: 403. Max 4000 chars per text, 30 writes/minute.
- **Audit:** append-only JSONL (`audit.jsonl`): time, method, path, identity, pane, workspace, outcome, size and an 80-char preview of typed text. Denials are logged too.
- **Layout rule:** `GET /v1/workspaces` flags `full: true` at 9 panes (3x3). Callers open a new space instead of adding a tenth pane.
- **Naming:** panes and chats are named `Proj - Intent`, just `Intent` when no project applies, just `Proj` when the pane owns a project indefinitely. Grouped by project so he can answer down the line with minimal context rebuild.

## Adapters
`herdrAdapter` is the primary, durable surface (list, read, send-text, send-keys). Interface for others: `workspaces() panes() read(id) sendText(id,t) sendKeys(id,k[])`.

**jcode adapter (planned, not in this PR).** On the Windows desk, jcode inside herdr makes input unusable, so the desk's jcode sessions run in native Windows Terminal panes and herdr cannot reach them. For those, the only control path is jcode's own `jcode serve` / `--resume` surface. I have only enumerated the processes (8 `jcode --resume` sessions plus one shared `jcode serve`). The serve socket protocol is not yet verified, so the adapter is deliberately not written. Next step is reading jcode's protocol and adding it behind the same identity, scope and audit gates.

**Mac note.** Mac agents mostly live outside herdr today (codex app-server, jcode serve). The Mac already has the relay; this facade is Windows-first.

## Run (do not do this until the PR is approved)
```
set FACADE_TRUSTED_USER=user@example.com
node facade.mjs
tailscale serve --bg --https=8787 http://127.0.0.1:8787
```
Port 8443 on the desk is already used by another Serve mapping; leave it alone. `install-windows.ps1` registers a per-user Scheduled Task (no admin, runs at logon) and prints the Serve command; it does not run it.

## Tested
Against a fake `herdr` binary: 403 without or with a wrong identity, read allowed, write refused outside scope, write allowed inside scope, audit lines for each. Not yet run against a real herdr on the desk.

## Watch list (alternatives, no deep dive yet)
- **honeymux** and **crux**: other terminal-multiplexer tools the owner is evaluating. Maturity versus herdr not yet assessed. If one is adopted, it is a new adapter behind the same interface.

## Presentation-layer model (long-term target)
Direction from the owner: one independent agent session process, many parallel presentations of it. Clients remote into the process; the client is never the process.
1. **Raw view.** The exact terminal / herdr session, remoted to another client. This is what the MVP does today (read pane, type into pane).
2. **Rich view.** A React-driven chat UI (ChatGPT/Claude-app richness, custom components) rendered from rich machine-readable output of the same session, live-synced in real time, while the TUI/CLI agent keeps running untouched as its own process.
Both views attach to the same session at the same time; closing a view never ends the session. For the rich view, each adapter must emit structured events (turns, tool calls, diffs, status) beside the raw bytes, so the UI does not scrape a terminal. The facade API would grow an event stream (SSE or WebSocket) per session, behind the same identity, scope and audit gates. Not built yet; the MVP is raw view only.

## ACP (Agent Client Protocol, e.g. Zed): eval note
On the eval list, not tried. Owner caveat: ACP owns the session, so the session lives and dies with the ACP connection. To fit the model above it would need to be made ephemeral/dynamic, i.e. a long-lived session process with ACP as one attachable front end rather than the owner. Next step is trying an ACP client (the owner plans to try it through Zed) and checking whether a session can be detached and re-attached.

## Open question: task management
The cockpit's task tracking is hand-rolled. The owner suspects it will not keep up and is weighing Linear or Jira. Recorded only as an open question; nothing here builds toward either.
# herdr-facade (MVP, Windows-first)

Authored by Instinct. Review only. Nothing here is installed anywhere yet.

A small loopback HTTP API in front of the `herdr` CLI, so the owner (and Instinct on his behalf) can read panes and type into a scoped set of panes from any tailnet device, with an audit trail. One file, no dependencies, Node 20+.

## Why not only the third-party relay
The Mac runs benkraus/herdr-plugin-mobile-relay (linux/macos only, no Windows). The desk is Windows, so this facade is the owned equivalent: same shape (loopback + Tailscale Serve identity), but small enough to read in five minutes.

## Design
- **Bind:** 127.0.0.1 only. The port is configurable, the host is not.
- **Auth:** every request needs `Tailscale-User-Login` equal to `FACADE_TRUSTED_USER`. Tailscale Serve injects that header for tailnet users and strips client-supplied copies. Missing or wrong identity: 403, audited.
- **Read:** any pane (`GET /v1/panes`, `/v1/workspaces`, `/v1/panes/<id>/read`).
- **Write:** `POST /v1/panes/<id>/text` and `/keys` work only for panes in a workspace whose label matches `FACADE_WRITE_SCOPE` (default `^instinct\b`, case-insensitive). Everything else: 403. Max 4000 chars per text, 30 writes/minute.
- **Audit:** append-only JSONL (`audit.jsonl`): time, method, path, identity, pane, workspace, outcome, size and an 80-char preview of typed text. Denials are logged too.
- **Layout rule:** `GET /v1/workspaces` flags `full: true` at 9 panes (3x3). Callers open a new space instead of adding a tenth pane.
- **Naming:** panes and chats are named `Proj - Intent`, just `Intent` when no project applies, just `Proj` when the pane owns a project indefinitely. Grouped by project so he can answer down the line with minimal context rebuild.

## Adapters
`herdrAdapter` is the primary, durable surface (list, read, send-text, send-keys). Interface for others: `workspaces() panes() read(id) sendText(id,t) sendKeys(id,k[])`.

**jcode adapter (planned, not in this PR).** On the Windows desk, jcode inside herdr makes input unusable, so the desk's jcode sessions run in native Windows Terminal panes and herdr cannot reach them. For those, the only control path is jcode's own `jcode serve` / `--resume` surface. I have only enumerated the processes (8 `jcode --resume` sessions plus one shared `jcode serve`). The serve socket protocol is not yet verified, so the adapter is deliberately not written. Next step is reading jcode's protocol and adding it behind the same identity, scope and audit gates.

**Mac note.** Mac agents mostly live outside herdr today (codex app-server, jcode serve). The Mac already has the relay; this facade is Windows-first.

## Run (do not do this until the PR is approved)
```
set FACADE_TRUSTED_USER=user@example.com
node facade.mjs
tailscale serve --bg --https=8787 http://127.0.0.1:8787
```
Port 8443 on the desk is already used by another Serve mapping; leave it alone. `install-windows.ps1` registers a per-user Scheduled Task (no admin, runs at logon) and prints the Serve command; it does not run it.

## Tested
Against a fake `herdr` binary: 403 without or with a wrong identity, read allowed, write refused outside scope, write allowed inside scope, audit lines for each. Not yet run against a real herdr on the desk.

## Watch list (alternatives, no deep dive yet)
- **honeymux** and **crux**: other terminal-multiplexer tools the owner is evaluating. Maturity versus herdr not yet assessed. If one is adopted, it is a new adapter behind the same interface.
