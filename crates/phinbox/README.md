# phinbox

Native, agent-elicited prompts. One popup, one decision, back to the agent.

`phinbox` is an MCP tool, CLI, and Rust library that opens a **native OS popup window** so an AI agent can ask a human a structured question and wait for an answer. It is built for the moment an agent needs a missing decision, a missing secret, or a missing preference — and is fast enough (sub-second to first paint on a warm start) that the agent can stay in flow.

## What it does

The agent sends a JSON prompt describing one field (boolean, text, choice, integer, number, datetime, multiselect, file/path), an optional notes box, and an urgency. `phinbox` opens a small native dialog on the operator's desktop — the **exact same shape on macOS and Windows** — and blocks until the human answers, cancels, or the timeout fires. The result is returned as a structured JSON `ElicitResponse`.

It is **not** a chat UI. It is a single decision. Like `InputBox` from Visual Basic, but with a schema, a timeout, and secrets.

## Surface area

| Form             | Path                                                                |
| ---------------- | ------------------------------------------------------------------- |
| Rust library     | `phinbox::spec::*`, `phinbox::elicit()`, `phinbox::schema_json()` |
| CLI              | `phinbox ask --from-json '{...}'`                                 |
| MCP server (stdio) | `phinbox-mcp`                                                    |
| Skill            | `.phinbox/skills/phinbox/SKILL.md`                              |
| Plugin — Forgecode | `plugins/forgecode/plugin.toml`                                   |
| Plugin — Codex   | `plugins/codex/codex.toml`                                          |
| Plugin — Cursor  | `plugins/cursor/cursor-mcp.json`                                    |

## Quickstart

### As a library

```rust
use phinbox::{elicit, ElicitOptions, RendererPreference};
use phinbox::spec::*;

let spec = PromptSpec {
    title: "Rename 23 identifiers".into(),
    question: "I'll rename identifiers across 8 files. Proceed?".into(),
    field: FieldSpec::Boolean { label: "Proceed?".into(), default: Some(true) },
    notes: None,
    buttons: None,
    urgency: Urgency::Info,
    timeout_secs: 120,
    request_id: None,
};

let response = elicit(&spec, ElicitOptions {
    renderer: RendererPreference::AutoGui,
    ..Default::default()
})?;

match response {
    ElicitResponse::Answered { value, notes } => { /* use it */ }
    ElicitResponse::Cancelled { .. } => { /* user said no */ }
    ElicitResponse::TimedOut { .. } => { /* no answer */ }
    ElicitResponse::Failed { reason } => { /* surface to caller */ }
}
```

### As a CLI

```bash
# Open a popup with a literal JSON spec
phinbox ask --title "Deploy?" --question "Deploy to production?" \
    --field-kind boolean --field-label "Confirm" --field-default true

# Pipe a JSON spec via stdin
echo '{"title":"OK?","question":"","field":{"kind":"boolean","label":"OK","default":true}}' \
  | phinbox ask --from-json -

# Validate a spec without rendering
phinbox validate --from-file spec.json

# Print JSON Schema
phinbox schema

# Install the binaries + register the inbox daemon (one-shot setup)
phinbox install
# Re-run later to add / upgrade
phinbox install --prefix ~/.local/bin

# Uninstall (removes binaries + launch agent / systemd unit)
phinbox uninstall --yes
```

### Async / non-blocking workflow

When a popup would block the agent longer than you want (CI runs, long-lived
sessions, agents that should stay in flow), queue the prompt in the inbox and
answer it later — from the desktop, the browser, an iMessage, or another
shell.

```bash
# Queue the prompt — returns instantly with a request_id and an open URL
phinbox ask --async --title "Approve PR?" --question "Merge?" \
    --field-kind boolean --field-label "Yes"
# → {"status":"queued","request_id":"abc-…","open_url":"http://localhost:7117/inbox/abc-…","path":"…"}

# Open the inbox UI in the default browser (or via the deep link)
phinbox inbox --open                    # open the index
phinbox inbox --open --request-id abc-…  # open a specific form

# Poll for the answer from another shell / another agent
phinbox wait --request-id abc-…

# Submit an answer from a script (no UI required)
phinbox answer --request-id abc-… --value true --notes "ship it"
```

The inbox daemon (`phinbox daemon`) is the long-running process that:

- serves `http://127.0.0.1:7117/inbox/<id>` as a printable HTML form,
- receives `POST /answer/<id>` and persists the response, and
- on macOS / Windows shows a persistent **tray icon** (v0.4.0) with a pending
  count badge and click-to-open menu (Open inbox / Open latest / Toggle quiet /
  Quit). Build with `--features tray-native`; the default build ships a
  no-op tray everywhere.

The user can answer from any of: the tray menu, the HTML form, iMessage, or
email — whichever they happen to look at first. The agent's `wait` call
returns as soon as any of them resolves the request.

### As an MCP server

Add to `mcp_servers.json`:

```json
{
  "mcpServers": {
    "phinbox": {
      "command": "phinbox-mcp",
      "args": [],
      "transport": "stdio"
    }
  }
}
```

The server exposes a single tool, `phinbox_mcp`. It takes the same shape as `PromptSpec` and returns the same shape as `ElicitResponse`.

## Platform support

| OS      | Renderer         | Backend                                                                 |
| ------- | ---------------- | ----------------------------------------------------------------------- |
| macOS   | Native NSPanel   | AppKit via `objc2` + `cocoa` — modal sheet attached to the active app, async dispatch queue for the run-loop, lands on macOS 11+ |
| Windows | Native Win32     | `CreateWindowExW` + standard controls, `CoTaskMemFree` for COM strings, modal via `EnableWindow` on the owner, lands on Windows 10 1809+ |
| Linux   | GTK4 or TUI      | GTK4 dialog with the same layout, or fall back to the TUI renderer (`inquire`) |
| Headless | TUI / JSON     | `inquire`-based terminal UI; machine-readable `{}` on `--renderer json` |

If `phinbox` cannot show a GUI (no display, SSH session, sandbox without entitlements), it **automatically falls back** to the TUI. This is observable: run `phinbox detect` to see which path it took.

## Plugin compatibility

| Client     | Integration                                                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Forgecode  | `plugins/forgecode/plugin.toml` declares the tool; the dispatcher wraps it for the agent; `install.sh` installs the CLI and registers the skill |
| Codex      | `plugins/codex/codex.toml` registers the MCP server with the canonical transport; `install.sh` writes `~/.codex/mcp.toml`                       |
| Cursor     | `plugins/cursor/cursor-mcp.json` is the standard Cursor MCP manifest; `install.sh` merges into `~/.cursor/mcp.json`                              |

## Architecture

```
                ┌──────────────────┐
                │ Agent (any host) │
                └────────┬─────────┘
                         │ JSON-RPC over stdio
                         ▼
              ┌─────────────────────────┐
              │ phinbox-mcp (rmcp)    │
              │ validates spec, then   │
              │ dispatches              │
              └────────┬────────────────┘
                       │
                       ▼
              ┌─────────────────────────┐
              │ phinbox library       │
              │   platform/detect.rs    │──── chooses renderer
              │   render.rs             │
              │   platform/{mac,win,    │
              │     linux,tty}.rs       │
              └────────┬────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
   ┌─────────────────┐   ┌─────────────────┐
   │ Native GUI      │   │ TUI fallback    │
   │ (AppKit / Win32)│   │ (inquire)       │
   └─────────────────┘   └─────────────────┘
```

The single source of truth for the prompt and response shape is `phinbox::spec`. The CLI, the MCP server, the GUI, and the TUI all consume it.

## Safety properties

- **Process isolation.** The GUI process is launched as a separate detached process so the agent's event loop is never blocked by Cocoa/UIKit. The parent waits with `waitpid` and a wall-clock timer.
- **Bounded wait.** Every render path is bounded by `timeout_secs`. On timeout, the GUI is dismissed, the result is `TimedOut`, and the parent's deadline is honored.
- **Secret-aware rendering.** Fields with `secret: true` use `NSSecureTextField` on macOS and `ES_PASSWORD` on Windows. The value is never logged.
- **No value leakage.** `tracing` events at INFO level show only the request id and the status (Answered/Cancelled/TimedOut), never the value.

## Async inbox architecture

The "ask but don't block" pattern is what makes this useful for live agents.
Three transports cooperate:

```
   agent            phinbox ask --async      daemon (long-running)
   (mcp/CLI)   ────────────────────────────▶   http://127.0.0.1:7117
   ▲                                            │
   │                                            ├── tray notification ──┐
   │                                            ├── iMessage / SMS     ─┤── user
   │                                            └── HTML inbox form    ─┘
   │
   └───── phinbox wait ────── POST /answer/<id> ◀────────────────────┘
```

- The **inbox dir** (`~/.phinbox/inbox/` by default) is the durable queue.
  Each request is a single JSON file; the atomic rename on answer means we
  can never observe a half-written response.
- The **daemon** owns HTTP, tray, and the notifier loop. If it dies, the
  inbox dir is still the source of truth — the next daemon instance picks
  up where it left off.
- The **wait** call polls the response file with backoff. It returns as
  soon as the answer, cancel, or timeout is recorded.
- **Email / iMessage channels** are implemented as one-way notifications
  (the form link + a short prompt). The user clicks the link and the
  browser flow handles the actual response. This keeps the attack surface
  small (no inbound IMAP/SMS parser) while still giving the user a way to
  answer from their phone.

If the daemon is not running, `--async` still works — it writes the file
and returns the `open_url`. The user can paste the URL into any browser
locally. The next time the daemon starts (e.g. via the launch agent), it
will pick up the pending requests and notify the user.

## License

MIT OR Apache-2.0 (dual-licensed, matching the rest of `phenotype-tooling`).
