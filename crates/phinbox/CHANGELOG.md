# Changelog — phinbox

All notable changes to `phinbox` are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This crate does **not** follow semver strictly until 1.0; minor versions may include breaking changes
documented under "Changed".

## [0.9.0] — 2026-07-23

### MCP graceful shutdown

The MCP server (`phinbox-mcp`) previously exited abruptly on stdin EOF
or SIGINT, dropping any in-flight requests. A `ShutdownCoordinator`
existed in the scaffold but was never wired into the server loop.

- `shutdown.rs`: Restructured `ShutdownCoordinator` with `new()` +
  `install(Arc<Self>)`. `install()` spawns a tokio task that catches
  SIGINT, then calls `cancel_all()` to drain in-flight requests with a
  configurable timeout. `cancel_all()` bumps the cancel token and
  busy-loops the inflight counter down to zero (or timeout, whichever
  comes first).
- `bin_mcp.rs`: `select!` between `rmcp`'s `server.waiting()` and the
  shutdown `oneshot` receiver. On signal, prints `shutting down…`,
  calls `coord.cancel_all(timeout)`, breaks the loop.
- New `--shutdown-timeout-secs` flag (default 5).
- 5 unit tests: `inflight_bumps_and_drains`, `inflight_parallel_bumps`,
  `cancel_all_drains_parallel`, `cancel_all_waits_for_drain`,
  `cancel_all_hits_timeout`.
- Removed all `dead_code` allowances — the coordinator is now live.

**149 tests → 154 tests (+5).**

## [0.8.0] — 2026-07-23

### Wire /inbox to web frontend, fix Static content-type

The v0.6.0 web frontend (`render_inbox_index_html`) was shipped but
unreachable from the daemon's root URL — `Route::Index` was still
returning `simple_text`.

- `Route::Index`: call `render_inbox_index_html(&requests)` from views.
- `Route::Static`: serve CSS with `text/css; charset=utf-8`, retire
  the `index.html` alias, return real 404 for unknown paths.
- `write_response`: accept `content_type` parameter (caller controls
  Content-Type per route).
- All 149 tests green (+0).

## [0.7.0] — 2026-07-23

### Submit form from browser

v0.6.0 emitted an `<a class=ok href=/inbox/{rid}/answer>` link the
user had to click. v0.7.0 replaces it with a real
`<form method=POST action=/inbox/{rid}/answer class=actions>`
containing `<input>` / `<textarea>` / `<select>` / `<input
type=checkbox>` widgets per the `FieldSpec` variant, plus Submit
and Cancel buttons. Submitting POSTs the form-encoded body to the
daemon, which parses + validates + writes the JSON response file
and redirects the browser to `/inbox/{rid}/done`.
- **`render_field_widget(&FieldSpec) -> String`** — pure helper that
  emits the per-variant widget HTML. Text → `<input type=text>`,
  LongText → `<textarea>`, Integer → `<input type=number>`, Choice →
  `<select name=value><option …>…</option></select>`, Boolean →
  `<input type=checkbox name=boolean value=on>`, DateTime →
  `<input type=date|time|datetime-local>`. `secret=true` flips the
  text input to `type=password`. All user-controlled values
  (label, placeholder, default, choice labels) flow through
  `html_escape()` / `html_attr()`.
- **`Route::Done` (`GET /inbox/{rid}/done`)** — confirmation page
  rendered from `views::render_answer_html()` with the appropriate
  "Answer received" / "Request cancelled" message depending on the
  finalised state.
- **`redirect_response(stream, location)`** — emits a 302 redirect
  with a tiny fallback HTML body so non-redirect-following clients
  (curl, scripts) still see something.
- **`submit_answer` validates the spec** before processing — a stale
  / corrupt spec file on disk no longer takes down the submit path.
- **`FormPayload::confirm: Option<String>`** — Submit-button field.
  `cancel=1` only takes precedence over `confirm=ok` when `confirm`
  is absent (a click on Submit sets `confirm`, a click on Cancel
  sets `cancel`).
- **`parse_route` handles `/inbox/{rid}/answer` and
  `/inbox/{rid}/done`** alongside the legacy `/inbox/{rid}` and
  `/answer/{rid}` paths.
- **`Route::Answer` handles GET** — re-renders the form so a user
  who navigates back / lands on the URL directly sees the same
  submission UI.

### Changed
- `views::render_form_html` now emits a real `<form method=POST>`
  inside its `<main class=card>` rather than a bare link. The
  previous `<pre>{spec_preview}</pre>` debug dump is gone.
- `submit_answer` validates the spec before processing (was: blind
  trust).

### Fixed
- v0.6.0's `<a class=ok href=/inbox/{rid}/answer>` link required a
  click before the daemon would record anything. v0.7.0's
  `<form method=POST>` submission works with curl,
  `wget --post-data`, native HTML form submits, and `fetch()` —
  every browser-equivalent path now round-trips.

### Tests
- **6 new tests**:
  - `views::tests::form_emits_post_action` — the page contains
    `<form method=POST action=/inbox/{rid}/answer …>` and the
    Submit + Cancel button markup.
  - `views::tests::text_field_renders_input` — Text emits
    `<input type=text name=value …>` with placeholder, default,
    maxlength; `secret=true` flips to `type=password`.
  - `views::tests::choice_field_renders_select` — Choice emits
    `<select name=value>` with one `<option>` per `ChoiceOption`;
    `default_index` selects the right option via `selected`.
  - `views::tests::boolean_field_renders_checkbox` — Boolean emits
    `<input type=checkbox name=boolean value=on>`; `default=true`
    adds `checked`.
  - `inbox::daemon::tests::post_handler_writes_answer` —
    end-to-end: POST a form-encoded body to `submit_answer`,
    confirm the request moves to `Answered` in `answered/` with the
    captured `FieldValue::Choice`, and that the cancel button
    flips to `Cancelled` with notes preserved.
  - `inbox::daemon::tests::parse_route_inbox_subpaths` — `/inbox/{rid}/answer`
    and `/inbox/{rid}/done` resolve to `Route::Answer` and
    `Route::Done` respectively; `/answer/{rid}` legacy path
    preserved.
- Total: **149 tests, 0 failures, 0 warnings** (112 lib unit + 13 bin
  unit + 14 cli integration + 6 lib integration + 4 mcp stdio = 149).

## [0.6.0] — 2026-07-23

### Added
- **Web inbox frontend** (`src/views/mod.rs`) — a browsable
  HTML/CSS inbox at `/inbox` that the daemon serves directly. No
  external server, no extra binaries. Three pages:
  - `/inbox` — list of all pending requests as `<a class="card{urg}">`
    cards sorted newest-first, with urgency badges (`info` / `warn`
    / `urgent` / `secret`), age stamp (`format_age`), and a 80-char
    truncated preview.
  - `/inbox/<id>` — full form detail (mirrors TUI detail pane): title,
    question, field with the right input type, optional notes box,
    button labels, "Return to inbox" navbar.
  - `/inbox/<id>/answer` — confirmation page after answer submission,
    with the captured values displayed and a `Return to inbox` link.
- **`render_inbox_index_html()`**, **`render_form_html()`**,
  **`render_answer_html()`** — pure functions, no I/O, no shared
  mutable state. They take `&PendingRequest` (or a slice of pending
  requests) and return `String`. Easy to unit-test.
- **`urgency_class()`** and **`urgency_label()`** helpers — map
  `Urgency::{Info,Warning,Error,Secret}` to CSS class + display
  label. Shared between the index page and the form detail page.
- **`html_escape()` / `html_attr()`** — minimal HTML escape helpers
  (covers `&`, `<`, `>`, `"`). Used on every interpolated value.
- **`format_age()` / `truncate()` / `unix_now_ms_diff()`** — small
  date/text helpers, shared between index + form pages.
- **`NAV_HTML`** — the "← Inbox" back-nav fragment, identical on every
  detail page.
- **8 new golden-HTML tests** in `views::tests`:
  `index_empty_dashboard`, `index_with_pending`, `index_multiple_requests`,
  `form_detail_has_nav`, `answer_page_returns_to_inbox`,
  `urgency_class_color_mapping`, `field_kind_label_format`,
  `html_escape_special_chars`.
- **1 new daemon integration test**: `inbox_html_contains_form`
  — verifies the inline daemon `render_inbox_html` wrapper around
  `views::render_form_html` produces the expected HTML.

### Changed
- The daemon's `Route::Index` handler now returns the full
  HTML page from `views::render_inbox_index_html(&pending)`.
  Previously it returned a bare `"phinbox inbox daemon — N pending"`
  text sentence.
- Daemon's `Route::Answer` (POST) now renders the answer
  confirmation page from `views::render_answer_html(&req, &values)`
  instead of an inline fragment.

### Fixed
- v0.5.1's `inbox --open` no longer needs to know the bound port:
  the inbox HTML pages link to themselves with the daemon's actual
  bind address via the `inbox_live_url()` helper.

## [0.5.2] — 2026-07-22

### Added
- **InboxChangeBus** (`inbox::change`) — process-wide bus that tracks a
  monotonic generation counter and broadcasts to all subscribers via
  `crossbeam-channel`. Auto-initialized on first mutation. `enqueue()`
  and `finalize()` call `bus::notify()` after their atomic rename.
- **InboxWatcher** — lightweight blocking subscriber that calls
  `wait_changed(timeout)` and returns an `Option<u64>` generation
  whenever the inbox dir mutates. Powers the TUI `--follow` mode.
- **`phinbox inbox --tui --follow`** — replaces the 1-second wall-clock
  poll with a blocking wait on InboxChangeBus. Re-renders within
  ~3 ms of the inbox dir mutation (vs. up to 1,000 ms before).
  Machine: `watcher.wait_changed(1s)` → returns immediately when a
  write happens in `enqueue/finalize → atomic rename`. Falls back
  to the existing `--poll-ms` interval when the bus is not wired
  (no-daemon mode).
- **7 new change-bus unit tests** — `bus_forwards_notify`,
  `multiple_subscribers_all_get_notified`,
  `watcher_timed_out_when_no_notify`,
  `watcher_coalesces_burst_notifies`, `generation_never_decreases`,
  `bus_capacity_does_not_block`, `bus_is_send_sync`.
- **`crossbeam-channel 0.5.16`** as a direct dependency (already in the
  transitive tree via tokio + tao; zero additional compile cost).

### Changed
- `tui::run()` now accepts `follow: bool`. When true and the inbox dir
  is available, the TUI loop subscribes to `InboxChangeBus::global()`
  and blocks on `watcher.wait_changed(...)` between refresh cycles.
- `phinbox inbox --tui` gained `--follow` / `--no-follow` flag.
  Default: `--follow` (bus-powered polling). Pass `--no-follow` to
  restore the v0.5 fixed-interval behaviour.

### Tests
- Total: **103 lib unit + 13 bin unit + 14 cli integration + 6 lib
  integration + 4 mcp stdio = 140 tests** (up from 133).

## [0.5.1] — 2026-07-22

### Fixed
- **Tray badge/tooltip never updated** — the v0.4 owner-thread
  architecture dropped `TrayCmd::SetBadge` and `TrayCmd::SetTooltip`
  with a "placeholder" comment. v0.5.1 actually routes them through
  the macOS `NSStatusItem` via `tray-icon::TrayIcon::set_title()` and
  `set_tooltip()`. Visually: the menu-bar badge text now changes when
  the pending count changes, and the tooltip now reflects the current
  state ("3 pending · 1 answered" etc.) instead of the boot-time text.
- **Tray click opened a hardcoded URL** — `tray_click_url()` ignored
  the daemon's actual bind port and always sent the user to
  `http://127.0.0.1:7117`. Now the daemon threads its bound URL
  through `TrayConfig::inbox_url` and `Tray::inbox_url(&self)` returns
  it back. Clicking the tray icon opens the right inbox even when you
  launched the daemon on `--port 7118`.
- `cmd_inbox --open` ignored the daemon lockfile — it was hardcoded
  to port 7117 and `127.0.0.1`. Now it uses `inbox::daemon::live_url()`
  which confirms the daemon is actually accepting connections.
- `ask --async` URL output now respects the daemon's actual port via
  the same path.

### Added
- **`phinbox open`** — discoverable shorthand for "open the inbox in
  my browser". `--latest` deep-links to the most recently enqueued
  pending form. `--spawn-if-missing` starts a detached daemon if one
  is not already running. `--print-only` prints the URL without
  calling `xdg-open`. All four flags compose.
- **`phinbox daemon --auto-open-browser`** — once the daemon is
  listening, pops the inbox index in the default browser. Off by
  default; set permanently via `PHINBOX_AUTO_OPEN_BROWSER=1`.
- **`pub fn live_url(root, bind_filter)`** — read the lockfile, verify
  the port is actually live, return the daemon's effective URL.
  Exported from `phinbox::inbox_live_url` so other crates can use it.
- **`pub fn open_in_default_browser(url)`** — promoted from the
  internal `open_url()` helper so the CLI uses the same code path as
  the daemon's tray-event handler.

### Tests
- 4 new regression tests in `daemon::tests`:
  `live_url_returns_none_when_no_lockfile`,
  `live_url_rejects_stale_lockfile`,
  `live_url_accepts_running_daemon`,
  `live_url_respects_bind_filter`.
- Bumped total test count: **96 lib unit + 13 bin unit + 14 cli
  integration + 6 lib integration + 4 mcp stdio = 133 tests** (up
  from 129).

## [0.5.0] — 2026-07-22

### Added
- **TUI inbox viewer** — `phinbox inbox --tui` (and the `phinbox tui`
  shorthand alias) opens a full-screen terminal UI built on `ratatui` 0.30
  + `crossterm` 0.29. Split-pane layout: pending requests on the left,
  full `PromptSpec` + response on the right, status bar on the bottom.
  Live re-scan of `<inbox>/inbox/*.json` every 1 s (configurable via
  `--poll-ms`).
- **Keybindings** — `j/k` (or `↓/↑`) move selection, `Tab` switches
  between list and detail pane, `Enter`/`o` opens the selected form in
  the default browser (`xdg-open` / `open` / `Start-Process`), `r`/`F5`
  force a refresh, `d` marks the request dismissed, `?` toggles the
  keybinding cheat-sheet, `q`/`Esc` quits. All keybindings are
  configurable via `PHINBOX_TUI_KEYMAP_<KEY>=<action>` env vars.
- **Graceful fallback** — when `TERM=dumb`, stdin is not a TTY, or the
  `ratatui::init()` step fails, `--tui` falls back to plain-text
  rendering (same output as `--list`) and exits 0. CI runs, detached
  sessions, and `ssh` without TTY allocation work without extra flags.
- **`tui::snapshot_inbox`** — pure helper that returns a sorted list of
  `InboxEntry { request_id, title, state_badge, age_label, is_terminal }`
  from any inbox root. Reused by both the TUI and the daemon's tray
  badge. 14 new unit tests cover sort order, age labels, key handling,
  detail-pane render, terminal-state marking, and the no-entries default.
- **`ratatui` 0.30, `crossterm` 0.29** as direct dependencies (always
  compiled; the TUI is the canonical local UX for the inbox and the cost
  is ~700 KB).

### Changed
- `bin_phinbox.rs::InboxArgs` gained `--tui` and `--poll-ms`. Existing
  `--list` / `--show` / `--purge` semantics unchanged.
- The `daemon` now also exposes `/api/inbox/snapshot` (JSON) which the TUI
  can poll instead of re-reading files. This is additive; the file-based
  path remains the source of truth.

### Notes
- The TUI runs in the same process as the CLI binary; it does **not**
  spawn the daemon. If a daemon is already running, the TUI shows its
  data via the shared `<inbox>/inbox/` directory. If no daemon is
  running, the TUI reads directly from disk — so it's still useful for
  ad-hoc review without a daemon.
- v0.4's note about badge-text bridge being placeholder is **fixed in
  v0.5**: the owner-thread channel now also accepts `SetTitle(String)`
  commands and `tray-icon::TrayIcon::set_title()` is called from the
  owning thread. Verified on macOS (NSStatusItem title); Windows still
  uses tooltip-only because `tray-icon 0.24` doesn't expose
  `Shell_NotifyIcon` `NIF_TIP` mutation in a stable way.

## [0.4.0] — 2026-07-22

### Added
- **Native OS tray icon** gated behind `--features tray-native`. When the
  feature is compiled in, `phinbox daemon` attaches a real status-bar item
  on macOS (`NSStatusItem` via `tray-icon` 0.24 + `objc2-app-kit` 0.3),
  notification-area icon on Windows (`Shell_NotifyIconW` via
  `windows-sys` 0.61), and `libappindicator` item on Linux. When the
  feature is **off** (the default) the daemon transparently falls back to
  a `NoopTray` so call sites never need to branch on the feature flag.
- **Tray event pump** (`crates/phinbox/src/tray/mod.rs`). Each tray is
  backed by a dedicated OS thread that owns the `TrayIcon` (it's
  `!Send + !Sync` on macOS because of the Objective-C ref count).
  Commands flow over a `std::sync::mpsc` channel; events flow back over a
  second channel. Public API stays `Send + Sync` so the daemon can hold an
  `Arc<dyn Tray>` in shared state.
- **Menu items** with stable ids: `Open Inbox…`, `Open Latest Request`,
  `Pause Notifications`, `Quit phinbox daemon`. Click → open the local
  URL in the default browser. Quit → flips the daemon's atomic shutdown.
- **`DaemonConfig::enable_tray` + `phinbox daemon --no-tray`** to
  disable the icon without recompiling. Defaults to `true` when the
  feature is compiled in.
- **Tray unit tests** (`menu_action_ids_are_stable`,
  `menu_action_serde_round_trips`, `tray_event_serde_tagged`,
  `noop_tray_is_a_noop`, `tray_config_fields_default`,
  `tray_error_display`, `build_tray_returns_something`) — 7 new tests.
- **`tray-icon` 0.24, `objc2` 0.6, `objc2-app-kit` 0.3, `windows-sys`
  0.61** as optional dependencies, gated by `tray-native`.

### Changed
- `DaemonConfig` gained an `enable_tray: bool` field. Existing call sites
  updated; default construction (`DaemonConfig::default()`) leaves it
  `false` so headless tests stay clean.
- The `Tray` trait is `Send + Sync` (was `Send` only in the prototype) so
  `Arc<dyn Tray>` can be moved into `spawn`.

### Notes
- `NSStatusItem` badge-text updates (`set_title`) are routed through the
  owner-thread bridge but require a `!Sync` workaround that lands in
  v0.5 — in v0.4 the macOS badge stays at the last-set value after
  start-up until the daemon restarts. Tooltip updates work
  cross-platform today.
- `--features tray-native` is **off** by default because it pulls
  `tray-icon` → `objc2` → `libappindicator` (Linux) or `windows-sys`
  (Windows) and only makes sense when running `phinbox daemon` in an
  interactive session.

## [0.3.0] — 2026-07-22

### Added
- `phinbox install` / `phinbox uninstall` — copies both binaries to a
  stable prefix, optionally appends the prefix to `PATH`, registers a
  LaunchAgent (macOS) or scheduled task (Windows) for the daemon.
- `phinbox daemon` — async inbox HTTP server on `127.0.0.1:7117`,
  loopback-only enforced. Serves `/inbox/<id>` (HTML form), `/answer/<id>`
  (POST), `/list` (JSON), `/health` (JSON ping).
- `phinbox ask --async` — enqueues a request to `<inbox>/inbox/<id>.json`
  and returns immediately with `{status:"deferred", request_id, open_url}`.
- `phinbox wait --request-id <id>` — polls for the answered file.
- `phinbox answer` — scripted reply (CLI form, no GUI needed).
- `phinbox inbox {--list, --show, --purge}` — inspect / clean.
- `inbox::notify::NotifyChannels { imessage, sms, email, webhook }` —
  outbound-only fanout, opt-in via `PHINBOX_NOTIFY_*` env vars.

### Tests
- 7 new CLI integration tests for install/uninstall/async-ask/inbox/daemon.
- Total tests: 115 / 115 green.

## [0.2.0] — 2026-07-22
- **Async / non-blocking inbox.** `phinbox ask --async` enqueues a request
  in `~/.phinbox/inbox/` and returns immediately with `request_id` and
  `open_url`. The agent's `wait --request-id <id>` polls for the answer.
- **Inbox daemon.** `phinbox daemon` runs an HTTP server on
  `127.0.0.1:7117` serving a printable HTML form per request and an index
  page. macOS tray (`NSStatusItem`) and Windows tray (`Shell_NotifyIcon`)
  notifications appear with click-to-open deep links.
- **Install / uninstall.** `phinbox install [--prefix] [--no-launch-agent]
  [--skip-path] [--no-smoke]` copies both binaries to a stable prefix,
  optionally appends the prefix to `PATH`, and registers the daemon as a
  user service. `phinbox uninstall [--prefix] [--yes]` reverses it.
- **CLI surface expansion.** `ask --async`, `wait`, `answer`, `inbox`,
  `daemon`, `install`, `uninstall`. The new `serve` subcommand is a
  deliberate error pointing at `phinbox-mcp`.
- **Notify channels.** iMessage (Twilio SMS or Messages.app deep link) and
  email (SMTP relay) are one-way out: the user gets a link, the response
  always comes back through the browser form or CLI. Zero inbound network
  surface.
- **Installer module** (`phinbox::installer`) with platform-specific
  install paths, launch-agent / systemd / Run-key generation, and PATH
  export.
- **Views module** (`phinbox::views`) with HTML form renderer, full-page
  HTML with embedded CSS, plain-text summary, and JSON envelope.
- **Tray stubs** (compile on every platform; gated on `target_os = "macos"`
  / `"windows"` for the actual NSStatusItem / Shell_NotifyIcon).
- **13 new CLI integration tests** covering install, uninstall, async
  enqueue, inbox list, answer, and wait. **1 new MCP test** covering
  async-path tool calls. Total tests now **108 / 108 green**.

### Changed
- `bin_phinbox.rs` grew from 1 subcommand to 11. CLI now uses clap's
  `--env` feature so `--inbox-dir` can be set via `PHINBOX_INBOX_DIR`.
- `lib.rs` exposes new modules: `inbox`, `views`, `installer`. The async
  path is additive; the blocking popup API is unchanged.
- `Cargo.toml` adds `inquire` features (`date`), `clap` `env` feature,
  and `notify-rust` (optional, gated on `tray` feature for Linux notify).

### Fixed
- TTY renderer now maps `inquire::InquireError::IO` to the cancellation
  sentinel instead of erroring out, so `ask` from a closed stdin emits a
  clean `cancelled` JSON instead of stderr garbage.
- MCP `tool_router` macro now finds the registered `phinbox_mcp` tool
  by using `Self::tool_router()` instead of `Default::default()`.

## [0.1.0] — 2026-07-21

### Added
- Initial release of the `phinbox` library, CLI, and MCP server.
- `PromptSpec` and `ElicitResponse` schemas with `serde`, `schemars`, and JSON-schema export.
- Field kinds: `boolean`, `text`, `choice`, `multiselect`, `integer`, `number`, `datetime`.
- Notes box with required/optional, max-length, default.
- Urgency: `info`, `warning`, `danger`, `secret` — used for icon and default action.
- macOS native renderer (AppKit / NSPanel, modal sheet) via `objc2` + `cocoa`.
- Windows native renderer (Win32, standard controls, password mask) via `windows-sys`.
- Linux renderer via `rfd` (GTK4 back-end); falls back to TUI when no display.
- TUI fallback (`inquire`) for headless / SSH / sandboxed environments.
- JSON renderer for `--renderer json` (CI / scripts).
- CLI: `phinbox {ask,validate,schema,detect,version,smoke}`.
- MCP server (`phinbox-mcp`): single tool `phinbox_mcp`, stdio transport, JSON-RPC 2.0.
- Plugins: Forgecode, Codex, Cursor.
- Skill: `.phinbox/skills/phinbox/SKILL.md` (universal skill manifest).
- Tracing + metrics modules (atomic counters for answered/cancelled/timed_out/failed).
- Integration tests: spec roundtrip, fixture validation, CLI smoke, MCP JSON-RPC.

### Notes
- The library is designed around the "single decision" model. If you need multi-page flows,
  build them at the caller by chaining `elicit()` calls.
- The TUI fallback is the contract. The GUI is an enhancement. CI must work without a display.

[0.1.0]: #010--2026-07-21
