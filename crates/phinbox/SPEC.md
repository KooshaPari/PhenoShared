# phinbox — Specification

## 1. Problem

AI agents frequently stall because they need a single human decision and the only way to ask is via the
chat pane. Chat is the wrong surface: it interrupts flow, the answer mixes with prior context, and
the agent has to scrape free text to recover a structured value. We need a way for an agent to pop a
single, structured, modal decision onto the operator's desktop — quickly, with a guaranteed timeout,
in the same shape every time.

## 2. Goals

- **One popup, one decision.** The shape is a single field, an optional notes box, and Confirm/Cancel.
- **Same shape everywhere.** macOS and Windows renderers produce visually equivalent dialogs.
- **Sub-second to first paint** on a warm start. The agent should not stall perceptibly.
- **Bounded by `timeout_secs`.** No prompt can hang the agent.
- **Headless-safe.** When the platform has no display, fall back to a TUI that accepts the same
  inputs and emits the same JSON output. When CI runs, the JSON renderer returns a deterministic stub.
- **Secret-aware.** A field can be marked `secret: true`; the renderer must mask input and never log
  the value.
- **Plugin-friendly.** Expose the same surface as a Rust library, a CLI, an MCP server, and a skill
  manifest so any host agent can consume it.
- **Non-blocking.** When the agent can't or shouldn't wait for the popup, it queues the request in
  a durable inbox. The user answers later from the desktop, browser, phone (via iMessage / email
  deep link), or a different shell. The wait call returns as soon as any of them responds.

## 3. Non-goals

- Multi-page wizards. (Chain `elicit()` calls at the caller.)
- Free-form chat.
- Asynchronous / multi-user flows in the same prompt. (One popup, one operator.)
- Browser-based rendering for the *initial* prompt. We deliberately use the host OS's native
  controls so the prompt feels like a system dialog, not a webpage. (The async inbox *does* render
  the form in a browser when the user opts in — that's the trade-off for the non-blocking case.)
- Inbound IMAP/SMS parsing. Notification channels are one-way out; the response always comes back
  through the local inbox surface (browser form or CLI `answer`).

## 4. Surface area

### 4.1 Library — `phinbox::*`

```rust
pub enum FieldSpec { Boolean, Text, Choice, MultiSelect, Integer, Number, DateTime }
pub struct PromptSpec { title, question, field, notes?, buttons?, urgency, timeout_secs, request_id? }
pub enum ElicitResponse { Answered { value, notes? }, Cancelled { notes? }, TimedOut { elapsed_secs }, Failed { reason } }
pub enum Urgency { Info, Warning, Danger, Secret }
pub enum FieldValue { Boolean, Text, Choice, MultiSelect, Integer, Number, DateTime, Empty }

pub fn elicit(spec: &PromptSpec, opts: ElicitOptions) -> Result<ElicitResponse>;
pub fn schema_json() -> serde_json::Value;
```

### 4.2 CLI — `phinbox`

```
phinbox ask             # open a popup (blocking) or queue it with --async
phinbox ask --async     # enqueue and return open_url + request_id instantly
phinbox wait            # poll for the answer to a previously queued request
phinbox answer          # submit an answer to a queued request (scriptable)
phinbox inbox           # list / show / open / clean the inbox
phinbox inbox --tui     # launch the ratatui-based terminal inbox viewer
phinbox tui             # shorthand for `inbox --tui`
phinbox daemon          # run the long-lived HTTP + tray + notifier server
phinbox install         # one-shot setup: copies binaries, writes PATH, registers launch agent
phinbox uninstall       # remove everything `install` added
phinbox validate        # validate a JSON spec without rendering
phinbox schema          # print JSON Schema
phinbox detect          # print platform + renderer info
phinbox version
phinbox smoke           # smoke-test the binary
phinbox serve           # explicit error: tells you to use `phinbox-mcp` instead
```

### 4.3 MCP — `phinbox-mcp`

JSON-RPC 2.0 over stdio. One tool, `phinbox_mcp`. Input is `PromptSpec`. Output is `ElicitResponse`.

### 4.4 Skill — `.phinbox/skills/phinbox/SKILL.md`

Universal skill manifest: describes when the agent should invoke the tool, what shape it must build,
and how to interpret the response.

### 4.5 Plugins

| Plugin       | Manifest                  | Install script |
| ------------ | ------------------------- | -------------- |
| Forgecode    | `plugin.toml`             | `install.sh`   |
| Codex        | `codex.toml`              | `install.sh`   |
| Cursor       | `cursor-mcp.json`         | `install.sh`   |

## 5. PromptSpec

```json
{
  "title": "string (≤ 120 chars)",
  "question": "string (≤ 1024 chars, may be empty)",
  "field": { "kind": "boolean", ... },
  "notes": { "label": "string", "default": "...", "max_length": 4096, "required": false },
  "buttons": { "cancel": "Cancel", "confirm": "OK", "default_is_cancel": false },
  "urgency": "info | warning | danger | secret",
  "timeout_secs": 60,
  "request_id": "opaque string (optional)"
}
```

`field` is a tagged union. Variants:

| Kind          | Extra                                                                 |
| ------------- | --------------------------------------------------------------------- |
| `boolean`     | `default: bool?`                                                      |
| `text`        | `default?: string`, `placeholder?: string`, `pattern?: string (regex)`, `max_length?: usize`, `multiline?: bool`, `secret?: bool` |
| `choice`      | `options: [{value, label, description?}]`, `default_index?: int`      |
| `multiselect` | same as `choice`, `min_selected?`, `max_selected?`                    |
| `integer`     | `min?: i64`, `max?: i64`, `default?: i64`                             |
| `number`      | `min?: f64`, `max?: f64`, `default?: f64`                             |
| `datetime`    | `kind: "date" | "time" | "datetime"`, `default?: ISO-8601`             |

## 6. Response

```json
{
  "status": "answered | cancelled | timed_out | failed",
  "value": { ... },        // present when status == answered
  "notes": "string",        // present when status ∈ {answered, cancelled}
  "elapsed_secs": 1.4,      // present when status == timed_out
  "reason": "string"        // present when status == failed
}
```

For `--async`, `phinbox ask` returns a different envelope:

```json
{
  "status": "queued",
  "request_id": "uuid-v4",
  "open_url": "http://127.0.0.1:7117/inbox/<id>",
  "path": "/Users/me/.phinbox/inbox/<id>.json",
  "channels": ["tray", "browser", "imessage", "email"]
}
```

## 7. Renderer selection

`render.rs::dispatch` chooses a renderer based on `ElicitOptions::renderer`:

1. `Auto` (default): detect platform → if GUI-eligible → `macos`/`windows`/`linux`; else `tty`.
2. `Gui` / `Macos` / `Windows` / `Linux`: force the chosen renderer, error if unavailable.
3. `Tty`: always `inquire`.
4. `Json`: deterministic stub used by CI tests; returns `TimedOut` after 0 ms.

The dispatch never panics. If a GUI renderer is unavailable, it returns a structured error
(`ElicitError::RendererUnavailable`) and the caller can decide to retry with `Tty`.

## 8. Concurrency model

The MCP server uses `tokio`. Each `phinbox_mcp` call runs in its own task with a `tokio::time::timeout`
wrapper. The render call itself runs on a dedicated blocking thread (renderer is synchronous,
sometimes must be on the main thread on macOS). The blocking thread is fed a crossbeam channel that
the timeout task signals with `Timeout` when the deadline fires.

## 9. Security & privacy

- **Secret fields.** `secret: true` switches to `NSSecureTextField` / `ES_PASSWORD`. The value is
  dropped after rendering returns. It is never logged, never serialized to `tracing` events,
  never echoed to the parent process's stderr.
- **Process boundary.** On macOS, the GUI runs in the same process (AppKit requires this), but the
  wait happens on a `std::thread` with a `wait`-style future so the agent's tokio runtime is not
  blocked.
- **No external network calls.** The library has zero outbound network dependencies. `Cargo.toml`
  has no `reqwest`/`hyper`/`tonic`/`surf`.
- **No value leakage in errors.** Error messages never include the prompt's content.

## 10. Async inbox

The async inbox is the non-blocking sibling of the blocking popup. It exists
because some flows simply cannot wait for the user to be at the keyboard:

- long-running agents that must keep working while the operator is in a
  meeting / on a phone / asleep,
- CI runs that surface a "what should we do about this flaky test?" prompt
  to a human channel,
- multi-agent setups where one agent delegates the decision to a human via
  a peer agent that itself is running unattended.

### 10.1 Lifecycle

```
                            enqueue        ┌── tray click ───┐
  ask --async ─────────────────────────► inbox/<id>.json ◀──┐
  (returns immediately)                   pending        │
                                                     answer ──▶ POST /answer/<id>
                                                                   │
                                              ◀─── inbox/<id>.json (renamed, atomic)
                                              answered
                                                                   │
  wait ──────────────────────────── polls file with backoff ────────┘
  (returns when file state changes)
```

The inbox directory (`~/.phinbox/inbox/` by default) is the durable store.
`enqueue` writes a single `PendingRequest` JSON; `submit_answer` does an
atomic rename to `Answered` / `Cancelled` / `TimedOut`. The wait loop polls
with exponential backoff (50ms → 2s).

### 10.2 Transport matrix

| Channel     | Direction   | Trigger                                   | Surface                         |
| ----------- | ----------- | ----------------------------------------- | ------------------------------- |
| Tray menu   | notify + RX | pending request appears / daemon starts   | NSStatusItem / Shell_NotifyIcon |
| Browser     | notify + RX | `phinbox inbox --open` / iMessage link  | HTML form served by daemon      |
| iMessage     | notify       | `phinbox-inbox.toml` has SMS gateway    | Twilio / Messages.app deep link |
| Email       | notify       | `phinbox-inbox.toml` has SMTP relay     | Sendmail / SMTP relay           |
| Local shell | RX          | `phinbox answer --request-id …`         | CLI                             |

All notify channels are **one-way out**. The user always responds through
the browser form (or the CLI). This keeps the attack surface small — there
is no inbound IMAP / SMS parser to harden.

### 10.3 Daemon responsibilities

`phinbox daemon` runs as a user service (launchd on macOS, systemd on
Linux, registry Run-key on Windows) installed by `phinbox install`. It:

1. binds `127.0.0.1:7117` (or `--port`) and serves the inbox index + per-request HTML forms,
2. watches the inbox directory for new pending requests,
3. shows a tray notification with the request title and a "Open" action,
4. (optional) forwards the request to iMessage / email per the config file,
5. persists answered / cancelled responses to disk.

If the daemon dies, the inbox directory is still the source of truth. The
next daemon instance re-reads it on startup and re-notifies any request
older than `--retry-after` that hasn't been answered.

### 10.4 Tray icon (v0.4.0)

`phinbox daemon` shows a persistent tray icon while it runs, behind the
`--features tray-native` Cargo feature. The feature is **off by default** so
the default build stays portable (no `objc2`, no `windows-sys`, no GTK).

API surface (`phinbox::tray`):

```rust
pub trait Tray: Send {
    fn update_badge(&self, pending: usize);
    fn update_tooltip(&self, text: &str);
    fn poll_menu_action(&self, timeout: Duration) -> Option<MenuAction>;
    fn shutdown(&self);
}

pub enum MenuAction { OpenInbox, OpenLatest(String), ToggleQuiet, Quit }

pub fn build_tray(cfg: &TrayConfig) -> Result<Arc<dyn Tray>, TrayError>;
```

`NoopTray` is always compiled and used when `tray-native` is not enabled.
`NativeTray` wraps `tray-icon 0.24`, which under the hood uses
`objc2-app-kit` on macOS, `windows-sys` `Shell_NotifyIconW` on Windows,
and `libappindicator` on Linux.

Why an owning-thread + channel architecture: `tray-icon`'s `TrayIcon` is
`!Sync` (it holds `NSStatusItem` on macOS). The trait is therefore
`Send`-only (not `Sync`); the `TrayIcon` lives on a dedicated OS thread
that owns it for its lifetime, and `poll_menu_action` does a non-blocking
`try_recv` on a `crossbeam_channel` from any other thread.

Daemon CLI additions for v0.4.0:

- `phinbox daemon --no-tray` — skip tray initialization (silently
  no-ops if the feature isn't compiled in).
- The tray badge updates whenever the inbox transitions
  (`enqueue` / `answer` / `purge`) via a `NotifierHandle` callback
  wired into `run_notifier_loop`.

### 10.5 Install

`phinbox install` is a one-shot setup that:

1. copies `phinbox` and `phinbox-mcp` to `--prefix` (default
   `~/.local/bin` on Linux, `~/Library/Application Support/phinbox/bin`
   on macOS, `%LOCALAPPDATA%\phinbox\bin` on Windows),
2. adds that prefix to the user's PATH in `.zshrc` / `.bashrc`
   (or PowerShell profile on Windows),
3. installs the inbox daemon as a user service (launch agent / systemd
   unit / registry Run key),
4. runs `phinbox smoke` to verify the renderer works.

`phinbox install --no-launch-agent` skips step 3. `phinbox install
--skip-path` skips step 2. `phinbox uninstall --yes` reverses everything
without prompting.

### 10.6 Terminal inbox viewer (TUI)

`phinbox inbox --tui` opens a full-screen terminal interface on top of
the same `<inbox>/inbox/*.json` files the daemon reads. It is the
canonical local UX for the inbox: no daemon required, no browser
required.

Library API (`phinbox::tui`):

```rust
pub struct ViewerConfig { inbox_dir: PathBuf, poll_ms: u64, focus_on_list: bool }
pub struct InboxEntry { request_id: String, title: String, state_badge: String, age_label: String, is_terminal: bool }
pub fn snapshot_inbox(root: &Path) -> Vec<InboxEntry>;
pub fn run_tui(cfg: ViewerConfig) -> Result<(), TuiError>;
```

Layout — split pane:
- Left pane: list of pending requests, newest first. Each row shows
  request id (cyan), title (white), state badge `[pending]`, `[seen]`,
  `[answered]`, `[cancelled]`, `[expired]` (yellow for live, dark-gray
  for terminal), age label (e.g. `12s`, `3m`, `1h`).
- Right pane: full `PromptSpec` of the selected request — title,
  question, field spec with kind + label + (for `Choice`) option list,
  urgency, origin (CLI / MCP / notify), and the recorded response if
  one exists.
- Bottom status bar: row count, refresh interval, current keymap hint.

Keybindings (default; rebindable via `PHINBOX_TUI_KEYMAP_*` env vars):

| Key            | Action                          |
|----------------|---------------------------------|
| `j` / `↓`      | move selection down             |
| `k` / `↑`      | move selection up               |
| `g` / `G`      | jump to first / last            |
| `Tab`          | switch focus between list & detail |
| `Enter` / `o`  | open selected form in default browser |
| `r` / `F5`     | force refresh                   |
| `d`            | mark request dismissed          |
| `?`            | toggle keybinding cheat-sheet   |
| `q` / `Esc`    | quit                            |

Graceful fallback — when `TERM=dumb`, stdin is not a TTY, or
`ratatui::init()` fails, `--tui` falls back to plain-text rendering
(same output as `--list`) and exits 0. This is the contract: CI,
detached sessions, and `ssh` without TTY allocation must work without
extra flags.

The TUI does **not** spawn the daemon. It is a thin client over the
shared `<inbox>/inbox/` directory; it works with or without a daemon
running.

## 11. Acceptance criteria

A reviewer should be able to:

1. `cargo build -p phinbox` and see binaries `phinbox` and `phinbox-mcp`.
2. Run `phinbox schema` and see valid JSON Schema.
3. Run `phinbox detect` and see the detected platform + renderer.
4. Run `phinbox ask --title T --question Q --field-kind boolean --field-label "?" --renderer tty`
   and observe a TUI prompt. Press Enter. Observe a JSON response on stdout.
5. Run the MCP server under `mcp-client` and see `phinbox_mcp` listed with the correct schema.
6. Run `cargo test -p phinbox` and see green.
7. Run `phinbox-mcp` and pipe in a `tools/call` request with an invalid `title`. See a structured
   error response.
8. Run `phinbox ask --async --title T --field-kind boolean` and see a `queued` JSON envelope
   within ~20ms. Verify `<inbox>/<id>.json` was created.
9. Run `phinbox inbox --list --inbox-dir <dir>` and see the pending request in the index.
10. Run `phinbox answer --request-id <id> --value true --inbox-dir <dir>` and observe the JSON
    file move to the answered state. Run `phinbox wait --request-id <id>` from another shell
    in parallel and confirm it returned the answered value.
11. Run `phinbox install --prefix /tmp/test --no-launch-agent --skip-path --no-smoke` and
    confirm both binaries are at `/tmp/test/{phinbox,phinbox-mcp}`. Run
    `phinbox uninstall --prefix /tmp/test --yes` and confirm they're gone.
12. Run `phinbox daemon --inbox-dir /tmp/test --port 0` (random port) and confirm it serves
    `GET /health` returning 200.
13. With `cargo build -p phinbox --features tray-native`, run
    `phinbox daemon --port 0 --inbox-dir /tmp/test` on macOS / Windows and verify
    a tray icon appears with a pending count badge. The badge increments when
    `phinbox ask --async` enqueues a request and decrements when
    `phinbox answer` resolves it.
14. `cargo test -p phinbox --features tray-native` and `cargo test -p phinbox`
    (default features) both pass — same test count, same test IDs.
15. Run `phinbox ask --async --inbox-dir <dir> --from-file spec.json` to enqueue
    a request, then run `phinbox inbox --tui --inbox-dir <dir>` in a TTY.
    Observe the request in the left pane with `[pending]` badge, the full
    `PromptSpec` in the right pane, and `j`/`k` moves selection. Press `Enter`
    to open the form URL in the default browser, or `q` to quit cleanly.
    Repeat with `TERM=dumb` and observe the same `--tui` invocation exits 0
    and prints a plain-text summary instead of entering raw mode.
16. Run `phinbox open` (no daemon running) and observe the command
    printing a clear "no daemon running on port 7117" error and a
    one-line `did you mean: phinbox daemon --auto-open-browser`
    hint. With `--spawn-if-missing`, observe a detached daemon being
    spawned and the URL opening in the default browser within 1 s.
17. With a daemon already running on `--port 8118`, run
    `phinbox open` and observe the URL printed / opened points at
    `http://127.0.0.1:8118/inbox`, **not** the hardcoded `:7117`.
    The same applies to `phinbox inbox --open`, `phinbox inbox --tui`
    (auto-opens if `--auto-open` is set), and the tray-icon left-click
    handler.
18. After enqueuing 3 requests via `phinbox ask --async`, with the
    tray-native feature compiled in and `phinbox daemon` running on
    macOS / Windows, observe the menu-bar badge shows "3" (or "3+"
    if over the display threshold). After running
    `phinbox answer --request-id <id>` for one of them, observe the
    badge decrements to "2" within the poll interval (≤ 1 s by
    default).
19. Tooltip on the tray icon reflects the live state: hover the
    tray icon after a request is enqueued and observe
    `phinbox · 3 pending · 0 answered` (or similar). After all
    requests are answered, observe
    `phinbox · 0 pending · 3 answered`.
20. `cargo test -p phinbox` reports **133 tests, 0 failures** across
    both the default feature set and `--features tray-native`. The 4
    new v0.5.1 regression tests (`live_url_*`) all pass.

## 12. Out of scope (v0.5.x)

Deferred to v0.6+:

- **macOS native notifications** via `objc2` + `NSUserNotification` /
  `UNUserNotificationCenter`. v0.5 currently uses a generic
  `osascript` shell-out; the native binding gets a richer UI (actions,
  replies inline).
- **Windows Action Center** notifications via `windows-sys` +
  `Shell_NotifyIconGetRect` / toast APIs.
- **Linux D-Bus StatusNotifierItem** — currently routes through
  `tray-icon`'s GTK backend. A direct D-Bus binding removes the
  GTK dependency for headless servers.
- **`$EDITOR` integration** for the TUI's `a` (answer) action — open
  the response YAML in `$VISUAL` and parse on save.
- **Per-crate distribution** — `phinbox` is not yet published to
  crates.io. Publishing is gated on a stable 1.0 API, which requires
  locking down the `FieldSpec` enum, the `ElicitResponse` wire format,
  and the `Tray` trait.
- **Code-signing + notarization** for `phinbox-mcp` so it can be
  whitelisted in MCP clients that require signed bundles.

### 10.7 Open-in-box (v0.5.1)

The user's experience of "open the inbox" is split across four
surfaces, all of which must be discoverable from `phinbox --help`:

1. **Standalone CLI** — `phinbox open [--latest] [--spawn-if-missing] [--print-only] [--inbox-dir DIR] [--port N]`.
   - `--latest` deep-links to the most recently enqueued pending form
     (vs. the inbox index if omitted).
   - `--spawn-if-missing` launches a detached `phinbox daemon` if
     no daemon is running on the requested port (saves the user one
     command).
   - `--print-only` skips the platform `xdg-open` / `open` call and
     just prints the URL — useful for piping into other tools.
2. **Inbox subcommand** — `phinbox inbox --open` and
   `phinbox inbox --show <id>` now use the live daemon URL
   (`inbox::daemon::live_url`) instead of a hardcoded port, so they
   work with `phinbox daemon --port 8118` etc.
3. **Daemon auto-open** — `phinbox daemon --auto-open-browser`
   (off by default, override via `PHINBOX_AUTO_OPEN_BROWSER=1`)
   pops the inbox index in the default browser as soon as the
   daemon is listening.
4. **Tray icon left-click** — the macOS `NSStatusItem` (or Windows
   `Shell_NotifyIcon`) opens the inbox index. The right-click menu
   adds `Open inbox` / `Open latest` / `Quit` items.

The shared code path is `phinbox::open_in_default_browser(url)`,
which routes through `mac::open` / `cmd /c start ""` /
`xdg-open` depending on the platform — same helper as the v0.3
notify fanout, now exported for CLI reuse.
