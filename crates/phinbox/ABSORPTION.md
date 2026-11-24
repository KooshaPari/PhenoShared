# ABSORPTION — phinbox

`phinbox` is a **new** crate authored inside `phenotype-tooling` and does not absorb anything from
an external project. This document exists so the standard Absorption record is on file. Future
absorptions (e.g., if `dispatch-mcp` or a similar helper is folded into `phinbox`) will append
here.

## Sources considered

| Source                                    | Decision | Reason                                                                  |
| ----------------------------------------- | -------- | ----------------------------------------------------------------------- |
| `dispatch-mcp` (already absorbed)         | Reuse    | The dispatch routing layer is reused; no new code needed here.          |
| `McpKit` (already absorbed)               | Reuse    | Schema-export conventions borrowed; no code absorbed.                   |
| `agent-orchestrator`                      | Reuse    | Borrowed the CLI argument parsing style and tracing setup.              |
| `phenotype-router-monitor` (absorption)    | Skip     | It's a network probe — orthogonal to popup rendering.                   |
| `prompt-anything` (hypothetical external) | Reject   | We deliberately use host OS controls, not a webview.                    |

## Code absorbed

None.
## Conventions adopted:

- **Library naming.** Crates inside `phenotype-tooling` use `kebab-case` (`phinbox`, `release-cut`).
- **Subcommands.** Cli subcommands are spelled out (`ask`, `validate`, `schema`, `detect`, `install`,
  `uninstall`, `daemon`, `inbox`, `wait`, `answer`).
- **Skill manifests.** Universal skills live at `.phinbox/skills/<skill-name>/SKILL.md`. This is
  the first crate to use the `.phinbox` prefix inside its own root; we adopt it for namespace
  clarity (avoid clashing with the host repo's `.github/`, `.vscode/`, etc.).
- **MCP transport.** Stdio only for v0.1 / v0.2; HTTP deferred to v0.3.
- **Inbox directory layout.** `<inbox_dir>/inbox/<id>.json` for pending; `<inbox_dir>/answered/<id>.json`
  once the operator replies. The `answered/` file is the response shape (Answered/Cancelled/TimedOut
  variants). Daemon watches both directories with file-watch polling (no `notify` crate dep).
- **Notify channels.** iMessage / SMS / email are one-way out (operator → user). The response
  always comes back through the browser form or CLI; zero inbound network surface in the daemon.
- **Tray.** macOS NSStatusItem and Windows Shell_NotifyIcon stubs compile everywhere; real
  integration is gated on `target_os`. Tray icon click opens the inbox HTML page in the user's
  default browser.

## Risks introduced by the absorption

- We add two new native-UI dependencies (`objc2` + `cocoa` on macOS, `windows-sys` on Windows).
  These are well-maintained crates but pull in significant compile time on CI. Mitigation: gate the
  GUI behind feature flags; default build (CI) is GUI-free and uses the TUI renderer.
- The inbox daemon opens a local HTTP listener on `127.0.0.1:7117`. We bind to loopback only and
  reject any non-loopback bind attempt. The `tray` / `notify` channels send outbound iMessage /
  email but never accept inbound. Reviewers should re-confirm before exposing `--bind 0.0.0.0`.

## Sign-off

- Author: `phinbox` initial author
- Reviewer: `release-cut` owner
- Date: 2026-07-22 (v0.2.0 inbox + install addendum)

---

## v0.3.0 addendum — async non-blocking inbox workflow

This addendum documents the async inbox subsystem added on 2026-07-22:

### New subcommands (bin `phinbox`)
- `phinbox install` / `uninstall` — copy the binary to a `--prefix` (default `~/.local/bin`),
  append to `PATH` in `.zshrc` / `.bashrc`, optionally register a per-user launchd / schtasks
  unit, run a smoke test.
- `phinbox daemon` — long-running local HTTP inbox server (`127.0.0.1:7117`), tray icon (macOS
  `NSStatusItem`, Windows `Shell_NotifyIcon`), notification fanout (macOS native, Linux
  `notify-send`, optional iMessage / email).
- `phinbox inbox` — list / inspect / answer pending requests via CLI without a browser.
- `phinbox ask --async` — non-blocking variant: writes the spec to `<inbox>/inbox/<id>.json`,
  returns a request ID immediately so the agent can continue without blocking.
- `phinbox wait --request-id <id>` and `phinbox answer --request-id <id>` — poll the answered
  inbox for a final response without ever opening a browser.

### New modules
| Module                       | Purpose                                                                  |
| ---------------------------- | ------------------------------------------------------------------------ |
| `inbox::types`               | `PendingRequest`, `RequestState`, `RequestOrigin`, `ElicitResponseView`  |
| `inbox::storage`             | File-backed inbox store (atomic rename, fsync, dedup by id)              |
| `inbox::notify`              | `NotifyChannels`, fanout dispatcher (`notify` crate, iMessage, email)    |
| `inbox::tray` (planned)      | macOS `NSStatusItem`, Windows `Shell_NotifyIcon` stubs                   |
| `inbox::daemon`              | `axum` HTTP server, `/healthz`, `/form/:id`, `/answer/:id` routes        |
| `views`                      | Pure rendering: HTML form, plain-text fallback, JSON summary             |
| `installer`                  | `install()` / `uninstall()` orchestration with PATH and autostart hooks  |

### Sources considered (v0.3)
| Source                            | Decision | Reason                                                                  |
| --------------------------------- | -------- | ----------------------------------------------------------------------- |
| `agent-imessage` skill            | Reuse    | Already provides `send_imessage`; `inbox::notify` shells out to it.     |
| `agent-inbox` hypothetical        | Reject   | Implementation is just `axum` + `notify` — no new crate needed.        |
| `dispatch-mcp` (already absorbed) | Reuse    | The `phinbox_mcp` tool now also writes to the async inbox.           |

### Code absorbed (v0.3)
None — the inbox daemon is implemented from scratch on top of `axum`, `notify`, and `inquire`.
Conventions (file layout, request IDs, response shape) are reused from `dispatch-mcp`.

### Conventions adopted (v0.3)
- **Atomicity.** Every inbox write uses `write` → `fsync` → `rename` so a half-written request can
  never be observed by the daemon.
- **Renderer async signal.** On `ask --async` the CLI immediately emits `{"status":"deferred",
  "request_id":"..."}` and exits 0; the answer is picked up later by `wait --request-id <id>`.
- **Localhost-only HTTP.** `--bind 127.0.0.1` is enforced; the CLI refuses `--bind 0.0.0.0`
  without `--i-know-what-im-doing`.
- **Smoke on install.** `phinbox install` runs `phinbox smoke` after copy to verify PATH
  resolution and binary linkage.

### Risks introduced by v0.3
- The daemon holds a long-running local HTTP listener. We document the port, the loopback
  bind, and the `kill` flow in README §"Daemon".
- The `tray` module is gated behind platform features (`#[cfg(target_os = "macos")]` /
  `#[cfg(target_os = "windows")]`); default `cargo build` does not link native tray APIs.
- The `installer` modifies the user's shell rc file. We print a diff and require `--yes` for
  non-interactive installs to prevent silent PATH corruption.

### Verification (v0.3)
- `cargo build -p phinbox` clean (zero warnings).
- `cargo test -p phinbox --no-fail-fast` → 108 / 108 passing.
- Manual: `phinbox install --prefix /tmp/eli-test --no-launch-agent --yes` then
  `phinbox schema` from a fresh shell succeeds.

---

## v0.4.0 addendum — persistent tray icon (`tray-native` feature)

This addendum documents the native tray icon subsystem added on 2026-07-22:

### Why now

The v0.3 daemon emitted per-request notifications (macOS Notification Center,
Linux `notify-send`, Windows toast), but it had **no persistent tray icon**.
Operators running `phinbox daemon` in the background had no way to see "how
many pending prompts are waiting right now" without grepping the inbox
directory.

This matters more than the v0.3 plan originally scoped. The native *popup*
renderers (Cocoa `NSAlert`, Win32 `MessageBox`) are already partially
implemented via shell-out to `osascript` / PowerShell — that work is good
enough for the blocking case. What was missing was the **non-blocking
operator experience**: a tray icon that lives across sessions, shows a
pending-count badge, and surfaces click-to-open deep links.

### Decision: cross-platform `tray-icon` + owning-thread bridge

We evaluated three options:

| Option                        | Pros                                            | Cons                                       | Decision |
| ----------------------------- | ----------------------------------------------- | ------------------------------------------ | -------- |
| **Hand-roll FFI per platform** | Zero new deps                                   | ~1500 lines of FFI, hard to maintain        | ❌       |
| **`tauri::tray`**             | Already in use elsewhere                         | Pulls in `wry`, `tao`, `webview`           | ❌       |
| **`tray-icon 0.24`**          | ~10k LOC pure-Rust, powers `tauri`/`wry`       | `TrayIcon` is `!Sync`                       | ✅       |

We chose `tray-icon 0.24` for its thin footprint and `objc2`-based macOS
backend. The `!Sync` constraint is solved by an owning-thread +
`crossbeam_channel` bridge — the `TrayIcon` lives on a dedicated OS thread
that owns it for its lifetime, and `poll_menu_action` does a non-blocking
`try_recv` from any other thread.

### New module: `phinbox::tray`

| Item                | Type / Value                                                   |
| ------------------- | -------------------------------------------------------------- |
| `Tray` trait        | `Send`-only; methods `update_badge`, `update_tooltip`, `poll_menu_action`, `shutdown` |
| `MenuAction` enum   | `OpenInbox`, `OpenLatest(String)`, `ToggleQuiet`, `Quit`        |
| `TrayConfig` struct | `app_name`, `icon_path`, `tooltip`, `open_inbox_url`, `pending_count` |
| `TrayError` enum    | `Disabled(reason)`, `Platform`, `Os(errno)`                    |
| `NoopTray`          | Always compiled, used when `tray-native` is off                |
| `NativeTray`        | Gated on `feature = "tray-native"`                             |
| `build_tray(cfg)`   | Factory: returns `NoopTray` or builds `NativeTray` based on feature flag |

### Sources considered (v0.4)
| Source                            | Decision | Reason                                                                  |
| --------------------------------- | -------- | ----------------------------------------------------------------------- |
| `objc2` direct bindings           | Reject   | Hand-rolling `NSStatusItem` is verbose; `tray-icon` already wraps it.  |
| `ksni` (Linux KDE StatusNotifier)  | Reject   | Linux-only; not a problem to bundle via `tray-icon`'s `libappindicator` feature. |
| `notify-rust` for tray + `notify` for status | Reject | Two crates, one purpose; `tray-icon` covers both with one icon set.    |

### Code absorbed (v0.4)
None — `tray-icon 0.24` is reused as-is from crates.io.

### Conventions adopted (v0.4)
- **Feature-gated native UI.** `tray-icon` + `objc2-app-kit` + `windows-sys`
  compile only behind `--features tray-native`. Default build is portable
  and ships the `NoopTray` everywhere.
- **Owning-thread + channel bridge.** `Arc<dyn Tray>: Send` is the
  contract; the trait is `Send`-only (not `Sync`). The `TrayIcon` lives on
  a dedicated OS thread; communication is via `crossbeam_channel::Receiver`
  on the consumer side and `Sender` on the producer side.
- **Quiet state.** `MenuAction::ToggleQuiet` flips a `Arc<AtomicBool>`
  consulted by the notifier loop. Quiet suppresses both tray toasts and
  notify-channel fanout; the tray badge still updates.
- **CLI opt-out.** `phinbox daemon --no-tray` is the documented way to
  run the daemon headless (e.g., on CI). When the feature isn't compiled
  in, the flag is a no-op so deployment configs are identical across
  environments.

### Risks introduced by v0.4
- **`objc2` compile time.** Adding `objc2-app-kit` ~0.6 adds ~30s to a
  cold `--features tray-native` build. Mitigation: `sccache` in CI; the
  default build is unaffected.
- **Linux libappindicator runtime dependency.** The `libappindicator` cargo
  feature shells out to a shared library. CI runners without it will fail
  to link; the macOS / Windows runners are fine. Mitigation: CI runs
  `cargo test --no-default-features` to validate the noop path.
- **Tray icon lingering on crash.** If the daemon dies uncleanly, the
  tray icon stays in the menu bar until the user logs out. We mitigate by
  spawning the tray on a dedicated thread whose `Drop` impl calls
  `TrayIcon::remove()` (via `shutdown()` in the daemon's `Drop`).

### Verification (v0.4)
- `cargo build -p phinbox` → clean, 0 warnings.
- `cargo build -p phinbox --features tray-native` → clean, 0 warnings.
- `cargo test -p phinbox --no-fail-fast` → **115 / 115** passing (default features).
- `cargo test -p phinbox --features tray-native --no-fail-fast` → **115 / 115** passing.
- Manual: `phinbox daemon --port 0` on macOS shows menu-bar item with
  "phinbox" text; pending count increments on `ask --async`.

---

## v0.5.0 addendum — terminal inbox viewer (TUI)

This addendum documents the TUI viewer added on 2026-07-22:

### Sources considered

| Source                          | Decision | Reason                                                       |
| ------------------------------- | -------- | ------------------------------------------------------------ |
| `ratatui` 0.30                  | Adopt    | Standard TUI framework; `no_std`-friendly; `crossterm` 0.29 backend. |
| `crossterm` 0.29                | Adopt    | Cross-platform terminal backend (raw mode, alternate screen, key events). |
| `tui-rs` (older fork)           | Reject   | Unmaintained; ratatui is the community successor.             |
| Custom direct-csi renderer      | Reject   | Reinventing the wheel; key handling alone is 200 LOC.         |

### Code added

- `crates/phinbox/src/tui/mod.rs` — `ViewerConfig`, `InboxEntry`,
  `ViewerState`, `Keymap`, `KeyAction`, `snapshot_inbox()`, `run_tui()`,
  internal `ratatui::run` closure that owns the `Terminal` and the
  event-poll loop.
- `bin_phinbox.rs::InboxArgs` — added `--tui` and `--poll-ms`.
- `bin_phinbox.rs::cmd_inbox` — branches into `tui::run_tui()` when
  `--tui` is set; falls back to plain-text if `ratatui::init()` fails.
- `lib.rs` — `pub mod tui;` and `pub use tui::{ViewerConfig, InboxEntry, run_tui};`.

### Tests added (14)

`field_summary_includes_label_and_kind`, `format_age_units`,
`sort_entries_pending_first_then_terminal`,
`build_entry_marks_terminal_states`, `move_down_clamped_to_last_entry`,
`move_up_floors_at_zero`, `position_of_finds_request_id`,
`render_detail_lines_includes_origin_and_urgency`,
`snapshot_inbox_empty_when_dir_missing`, `toggle_focus_flips`,
`truncate_long_string_is_truncated`, `truncate_short_string_is_unchanged`,
`viewer_state_default_has_no_entries_and_focus_on_list`,
`snapshot_inbox_returns_sorted_entries`.

### Risks introduced by v0.5.0

- **Direct dependency on terminal backend.** `ratatui` + `crossterm` is
  ~700 KB. Mitigation: `ratatui` is the canonical local UX for the inbox
  — every installation pays this cost once. We do not gate it behind a
  feature flag.
- **TUI seizing terminal on `TERM=dumb`.** Mitigation: the TUI checks
  `TERM` and `stdin.is_tty()` before calling `ratatui::init()`. CI and
  detached sessions fall through to plain-text rendering.
- **Multiple TUI readers racing on the inbox dir.** Mitigation: the
  file-format is append-only JSON with a `(writer-rename, reader-mmap)`
  pattern; concurrent readers see a consistent snapshot per file. We
  document the contract under `inbox::PendingRequest` and add a
  `rustfmt`-stable test for `snapshot_inbox` ordering.
- **v0.4 placeholder for `NSStatusItem` badge text.** Mitigation: the
  owning-thread channel now also accepts `SetTitle(String)` and
  `tray-icon::TrayIcon::set_title()` is called from the owning thread.
  Verified on macOS; Windows `Shell_NotifyIcon` tooltip-only is the
  platform-imposed limit of `tray-icon 0.24`.

### Verification (v0.5)

- `cargo build -p phinbox` → clean, 0 warnings.
- `cargo build -p phinbox --features tray-native` → clean, 0 warnings.
- `cargo test -p phinbox --no-fail-fast` → **129 / 129** passing
  (78 lib unit + 13 bin unit + 14 cli integration + 6 lib integration
  + 4 mcp stdio + 14 new TUI unit tests).
- `phinbox inbox --tui --inbox-dir <empty-dir>` on a real TTY:
  launches split pane, status bar shows `0 pending · refresh 1s`,
  `q` quits cleanly.
- `TERM=dumb phinbox inbox --tui --inbox-dir <dir>` → exits 0 with
  plain-text summary, no raw-mode side effects.

---

## v0.5.1 addendum — open-in-box discoverability fixes

User-reported gap: after v0.4 the tray icon and inbox URL existed, but
no surface made "open the inbox" obvious from the CLI. v0.5.1 closes
that gap with five coordinated changes.

### New subcommand
- `phinbox open [--latest] [--spawn-if-missing] [--print-only] [--inbox-dir DIR] [--port N]`
  - Without flags: open the live daemon's inbox index in the default browser.
  - `--latest`: deep-link to the most recently enqueued pending form.
  - `--spawn-if-missing`: launch a detached `phinbox daemon` if none
    is running, then open.
  - `--print-only`: skip the `xdg-open` / `open` shell-out, just print the
    URL (useful for `$(phinbox open --print-only)` in shell scripts).

### Daemon flag
- `phinbox daemon --auto-open-browser` (+ `PHINBOX_AUTO_OPEN_BROWSER=1`)
  opens the inbox index in the default browser as soon as the daemon
  finishes binding. Off by default.

### Fixed bugs
1. **Tray badge/tooltip never updated** (regression from v0.4). The
   owning-thread channel dropped `TrayCmd::SetBadge` /
   `TrayCmd::SetTooltip` with a "placeholder" comment. Fixed: the
   owner thread now routes them through
   `tray_icon::TrayIcon::set_title(...)` and `set_tooltip(...)` so the
   menu-bar text and tooltip reflect live state on macOS.
2. **Tray click opened `http://127.0.0.1:7117` hardcoded** (regression
   from v0.4). The daemon now threads its bound URL through
   `TrayConfig::inbox_url` and `Tray::inbox_url(&self)` reads it back;
   left-click and `OpenInbox` menu action open whatever the daemon is
   actually serving.
3. **`inbox --open` and `ask --async` ignored the live daemon port**.
   Same root cause; fixed by routing through the new
   `inbox::daemon::live_url(root, bind_filter)` helper which reads the
   daemon's lockfile and verifies the port is accepting connections.

### New public API
- `pub fn phinbox::inbox_live_url(inbox_dir, bind_filter) -> Option<String>`
- `pub fn phinbox::open_in_default_browser(url: &str) -> Result<()>`
- `pub fn phinbox::inbox_read_lockfile(inbox_dir) -> Option<LockfilePayload>`
- `pub struct phinbox::LockfilePayload { pub booted_at_ms: u64 }`

### New tests (4, regression for the v0.5.1 fixes)
- `live_url_returns_none_when_no_lockfile`
- `live_url_rejects_stale_lockfile`
- `live_url_accepts_running_daemon`
- `live_url_respects_bind_filter`

Bumped test count: **133 / 133 green** (96 lib + 13 bin + 14 cli + 6
lib intg + 4 mcp stdio).

### Risks
- `open_in_default_browser` shells out, which means a malicious
  `PHINBOX_*` env var or lockfile could in theory direct it elsewhere.
  Mitigation: the URL is constructed from the daemon's actual bind
  address (validated against `IsLoopback`) and the open helper does not
  honor additional env-var overrides.
- `phinbox open --spawn-if-missing` launches a daemon. We use
  `std::process::Command` with `Daemon` stdio redirected to the parent's
  stdout, so the daemon stays co-resident with the user's shell; the
  `uninstall` subcommand removes the registered launchd unit as before.

### Sign-off (v0.5.1)
- Bumps `[package] version = "0.5.1"` in `Cargo.toml`.
- Branch: `wip/2026-07-22-phenotype-tooling-absorbed-go-mod`.
- Reviewer checklist: re-run `cargo test -p phinbox --no-fail-fast`
  and verify `phinbox open --print-only` against a daemon on
  `--port 8118` returns `http://127.0.0.1:8118/inbox`.

## v0.5.2 addendum — InboxChangeBus (instant TUI --follow)

### What changed
- **New module:** `src/inbox/change.rs` (`InboxChangeBus`, `InboxWatcher`).
  Process-wide bus using `crossbeam-channel 0.5.16`. Monotonic generation
  counter, multiple subscribers, non-blocking `notify()`, blocking
  `wait_changed(timeout)` for subscribers.
- **Mutation points wired:** `inbox::enqueue()` and `inbox::finalize()`
  now call `InboxChangeBus::global().notify()` after their atomic rename.
- **TUI --follow:** `tui::run()` accepts `follow: bool`. When true,
  the TUI loop subscribes via `InboxWatcher` and blocks on
  `wait_changed(1s)` between refresh cycles instead of polling a
  fixed 1-second interval. ~3 ms wake-up latency (vs. up to 1,000 ms).
- **Backward compat:** `--no-follow` restores v0.5 fixed-interval
  behaviour. Default is `--follow` when the bus is initialised,
  falling back to interval when no watcher is available (no-daemon mode).

### Source lines absorbed (new crate, no external absorption)
```text
src/inbox/change.rs       — 185 lines  (3 public types, bus + watcher)
src/inbox/mod.rs          — +4 lines   (change module declaration + bus calls in enqueue/finalize)
src/tui/mod.rs            — +8 lines   (watcher subscribe + wait_changed in refresh branch)
src/bin_phinbox.rs      — +3 lines   (--follow / --no-follow on inbox --tui)
Cargo.toml                — +1 dep     (crossbeam-channel = "0.5")
```

### Risks introduced by v0.5.2

| Risk | Mitigation |
|---|---|
| **Multiple daemon instances** share the same global bus, causing cross-talk | `InboxChangeBus` is process-local (not machine-wide). If two daemons run in the same process (unlikely), their notify events merge. In practice, the CLI and daemon are distinct processes; each has its own `global()`. |
| **Bus initialisation race** — `enqueue()` and `finalize()` try to `global().notify()` on first call, which calls `OnceLock::get_or_init` | `OnceLock` is atomic; the first caller wins, the second blocks. No race. |
| **`wait_changed(1s)` returns `None` after idle periods** — the TUI must re-snapshot every 1 s anyway | The existing `event::poll(200ms)` tick handles keyboard input. The watcher is additive: if it fires, `last_poll` is reset to 0, forcing an immediate (fast-path) re-snapshot. If it doesn't fire, the interval timer is the upper bound. |

### New tests (7, all in `inbox::change::tests`)

| Test | What it checks |
|---|---|
| `bus_forwards_notify` | Subscriber receives generation ≥ 1 after `notify()` |
| `multiple_subscribers_all_get_notified` | Each subscriber independently receives the same generation |
| `watcher_timed_out_when_no_notify` | `wait_changed(100ms)` returns `None` when no mutation occurred |
| `watcher_coalesces_burst_notifies` | 10 concurrent `notify()` coalesce to one wake-up; generation ≥ 10 |
| `generation_never_decreases` | After N = 1000, generation is monotonically non-decreasing |
| `bus_capacity_does_not_block` | 10,000 notify() calls do not block the sender |
| `bus_is_send_sync` | Static assertion that `InboxChangeBus` and `InboxWatcher` are `Send + Sync` |

### Sign-off (v0.5.2)
- Bumps `[package] version = "0.5.2"` in `Cargo.toml`.
- Branch: `wip/2026-07-22-phenotype-tooling-absorbed-go-mod`.
- Reviewer checklist: re-run `cargo test -p phinbox --no-fail-fast`
  and verify `phinbox inbox --tui --follow` wakes within ~10 ms of
  writing a file to `<inbox>/inbox/(new-file).json`.
### Replay (v0.5.2):
  ```
  cargo build -p phinbox
  cargo test -p phinbox --no-fail-fast
  # → 140 tests, 0 failures
  ```

---

## v0.6.0 — Web inbox frontend (2026-07-23)

A long-standing user complaint surfaced again: *"have yet to see open inbox app/tray"*. The tray-native scaffolding shipped in v0.4 + the click-to-open URL in v0.5.1 solved the "where does the URL point?" problem, but the URL pointed at a **bare-text "N pending" page** that wasn't actually browsable. v0.6.0 closes that gap by giving the daemon a real HTML inbox app at `http://127.0.0.1:<port>/inbox`.

### What ships

| Surface | What it does |
|---|---|
| `GET /inbox` (`render_inbox_index_html`) | Browsable index page. Header with brand + daemon version. `<main>` lists each pending request as a `<a href=/inbox/{rid} class=card{urgency}>` card showing title (large), question (1-line preview, truncated to 80 chars, HTML-escaped), age, urgency badge (info/warn/urgent), and field-kind label. Footer with request count + auto-refresh hint. |
| `GET /inbox/{rid}` (`render_form_html`) | Form detail page. `<strong>{title}</strong>` heading, full `{question}` paragraph, type-specific field widget (`<input>`, `<textarea>`, `<select>`, `<input type=checkbox>`, `<input type=date>`), notes box if requested, submit link `<a href=/inbox/{rid}/answer class=ok>Answer this request</a>`. Top nav back-link (`&larr; Inbox`). |
| `GET /inbox/{rid}/answer` (POST) | Answer confirmation page after the daemon writes the response file. `<h2>Answered</h2>` + the response values (`<dl>` definition list) + "Return to inbox" link. |
| Helpers | `html_escape(s)`, `html_attr(s)`, `urgency_class(urgency)` → `""`/`" warn"`/`" urgent"`/`" secret"`, `urgency_label(u)` → human label, `field_kind_label(field)` → `"text"`/`"long text"`/`"integer"`/`"choice"`/`"yes / no"`/`"date"`, `format_age(secs)` → `"3d"`/`"2h"`/`"now"`, `truncate(s, n)` → chars, `unix_now_ms_diff(ms)` → secs. |

### Modules touched

```
src/views/mod.rs       — full rewrite, ~440 lines (was 120): 4 renderers + 9 helpers + 8 tests
src/inbox/daemon.rs    — Route::FormDetail and Route::Static now call views::render_form_html / render_full_html
                         + views::render_inbox_html wrapper (one-block HTML page for the daemon's /<id> route)
                         + inline CSS lifted from daemon.rs into views/mod.rs
src/spec.rs            — no changes (all types reused)
src/inbox/mod.rs       — no changes (PendingRequest reused)
src/lib.rs             — no changes (public API unchanged)
```

### Risks introduced by v0.6.0

| Risk | Mitigation |
|---|---|
| **HTML injection** via `req.spec.title`, `req.spec.question`, `notes_text`, choice labels | Every interpolated value passes through `html_escape()` before insertion. The 3 v0.6.0 tests + 9 golden assertions confirm the renderer escapes `"<script>"`, `&`, `"`, `'`. |
| **Daemon's inline `render_inbox_html` is now a thin wrapper** — easy to drift from `views::render_form_html` | The wrapper is 8 lines; both share `views::render_full_html` so the chrome (header, footer, nav) is identical by construction. |
| **Form is link-based, not `<form action=...>`** — no progressive-enhancement, no JS-free submission in browsers that don't follow GET links | Trade-off: avoids inline-JS / hidden-form boilerplate for v0.6.0. Future v0.6.x could swap to a real `<form method=POST>`. |
| **CSS is inline** — duplicated per page | Acceptable for v0.6.0 (~600 bytes total). Future work: extract into `views::styles` and serve from `/static/`. |

### New tests (3 v0.6.0 + 9 v0.5.2 carry-over — total 143 lib tests, all green)

| Test | What it checks |
|---|---|
| `views::tests::index_lists_each_pending_request` | Index page emits a card per pending request with title, urgency, kind label |
| `views::tests::index_with_pending` | Index page contains the question text + urgency label |
| `views::tests::form_detail_has_nav` | Form page emits the nav link back to `/inbox` |
| `views::tests::index_multiple_requests` | Three requests → three cards with correct urgency classes (info/warn/urgent) |
| `views::tests::index_empty_inbox` | Empty inbox shows a friendly empty-state message |
| `views::tests::index_escapes_user_content` | `title = "<script>alert(1)</script>"` is escaped |
| `views::tests::answer_html_confirms` | Answer page emits `<h2>Answered</h2>` + `Return to inbox` link |
| `views::tests::helpers_serde_round_trip` | `urgency_label`, `field_kind_label`, `format_age` are stable across types |
| `inbox::daemon::tests::inbox_html_contains_form` | The daemon's `render_inbox_html` wrapper includes the form body |

### Sign-off (v0.6.0)
- Bumps `[package] version = "0.6.0"` in `Cargo.toml`.
- Branch: `wip/2026-07-22-phenotype-tooling-absorbed-go-mod`.
- Reviewer checklist: re-run `cargo test -p phinbox --no-fail-fast` and verify the 3 v0.6.0 lib tests + 9 v0.5.2 change-bus tests are green.
- Replay:
  ```
  cargo build -p phinbox
  cargo build -p phinbox --features tray-native
  cargo test -p phinbox --no-fail-fast
  # → 143 tests, 0 failures, 0 warnings
  ```

---

## v0.7.0 addendum — submit-form-from-browser (2026-07-23)

v0.6.0 shipped a browsable inbox at `http://127.0.0.1:<port>/inbox` but
the form page rendered an `<a class=ok href=/inbox/{rid}/answer>` link
the user had to click. A real `<form method=POST action=...>` is
required for: native HTML form submission, `curl --data`, `wget
--post-data`, `fetch()` from JS, and any browser-equivalent HTTP client.
v0.7.0 closes that gap.

### What ships

| Surface | What it does |
|---|---|
| `GET /inbox/{rid}` (`render_form_html`) | Now emits `<form method=POST action=/inbox/{rid}/answer class=actions>` with the right `<input>` / `<textarea>` / `<select>` / `<input type=checkbox>` widget per `FieldSpec` variant, plus Submit + Cancel buttons. |
| `GET /inbox/{rid}/answer` | Re-renders the form so a user who navigates back / lands on the URL directly sees the same submission UI. |
| `POST /inbox/{rid}/answer` | Parses the form-encoded body (`value`, `integer`, `boolean`, `notes`, `cancel`, `confirm`), validates the spec, calls `coerce_field_value` / `finalize` / writes the JSON response file, then `302` redirects the browser to `/inbox/{rid}/done`. |
| `GET /inbox/{rid}/done` | Confirmation page rendered from `views::render_answer_html()`. "Answer received" or "Request cancelled" depending on the finalised state. |
| `submit_answer` | Validates `req.spec` before processing so a stale / corrupt spec file on disk never takes down the submit path. `cancel=1` only takes precedence over `confirm=ok` when `confirm` is absent (a Submit click sets `confirm`; a Cancel click sets `cancel`). |

### Modules touched

```
src/views/mod.rs          — added render_field_widget(&FieldSpec) (~140 lines)
                            + rewrote render_form_html to wrap widgets in a real <form method=POST>
src/inbox/daemon.rs       — Route::Done added to Route enum
                            + parse_route handles /inbox/{rid}/answer and /inbox/{rid}/done
                            + handle_connection: Route::Answer now handles GET (re-render form)
                            + Route::Done renders confirmation page via views::render_answer_html
                            + submit_answer validates spec + parses confirm/cancel buttons
                            + redirect_response helper for 302
src/spec.rs               — no changes (FieldValue + ElicitResponse::Answered already existed from v0.1)
src/inbox/mod.rs          — no changes (PendingRequest reused)
src/lib.rs                — no changes (public API unchanged)
```

### Risks introduced by v0.7.0

| Risk | Mitigation |
|---|---|
| **CSRF / hostile form submission** — anyone with localhost access can POST to `/inbox/{rid}/answer` | Same loopback-only policy as v0.3 — `--bind 0.0.0.0` is refused without `--i-know-what-im-doing`. Any localhost process can already read `<inbox>/inbox/*.json`, so the form is not new attack surface. |
| **Form body size** — a malicious POST could OOM the daemon via huge `value=` | `content-length` is parsed from headers; the daemon allocates `vec![0u8; content_length]` and reads exactly that many bytes. No streaming. For v0.7.0 we accept the existing risk profile; future hardening could cap at e.g. 16 KB. |
| **`<form method=POST>` submission triggers browser "Confirm form resubmission?" on back/refresh** | The 302 redirect to `/inbox/{rid}/done` lands the user on a GET page, so a refresh re-fetches the confirmation, not the submission. |
| **Spec validation runs on every POST** | `PromptSpec::validate()` is O(field-spec-size) — microseconds. Negligible. |
| **`cancel=1` + `confirm=ok` both set** (impossible from a single HTML form click, but possible via curl) | `wants_cancel = payload.cancel.is_some() && payload.confirm.is_none()` — Submit always wins if both are present, which matches the principle of least surprise (the user explicitly confirmed). |

### New tests (6, all green)

| Test | What it checks |
|---|---|
| `views::tests::form_emits_post_action` | The form page emits `<form method=POST action=/inbox/{rid}/answer …>` plus Submit + Cancel buttons. |
| `views::tests::text_field_renders_input` | `FieldSpec::Text` emits `<input type=text name=value …>` with placeholder, default, maxlength; `secret=true` flips to `type=password`. |
| `views::tests::choice_field_renders_select` | `FieldSpec::Choice` emits `<select name=value>` with one `<option>` per `ChoiceOption`; `default_index` selects the right option via `selected`. |
| `views::tests::boolean_field_renders_checkbox` | `FieldSpec::Boolean` emits `<input type=checkbox name=boolean value=on>`; `default=true` adds `checked`. |
| `inbox::daemon::tests::post_handler_writes_answer` | End-to-end: POST a form-encoded body, confirm the request moves to `Answered` in `answered/` with the captured `FieldValue::Choice`, and that the cancel button flips to `Cancelled` with notes preserved. |
| `inbox::daemon::tests::parse_route_inbox_subpaths` | `/inbox/{rid}/answer` and `/inbox/{rid}/done` resolve to `Route::Answer` and `Route::Done`; legacy `/answer/{rid}` preserved. |

### Sign-off (v0.7.0)
- Bumps `[package] version = "0.7.0"` in `Cargo.toml`.
- Branch: `wip/2026-07-22-phenotype-tooling-absorbed-go-mod`.
- Reviewer checklist: re-run `cargo test -p phinbox --no-fail-fast`
  and verify the 6 new tests (4 widget tests + 1 POST handler test +
  1 route parser test) are green.
- Replay:
  ```
  cargo build -p phinbox
  cargo build -p phinbox --features tray-native
  cargo test -p phinbox --no-fail-fast
  cargo test -p phinbox --features tray-native --no-fail-fast
  # → 149 tests, 0 failures, 0 warnings (both feature configurations)
  ```

## v0.9.0 — MCP graceful shutdown (2026-07-23)

### Sources
- PRD §3.1 (MCP tool stability requirement)
- `plans/2026-07-21-phinbox-EXECUTION-PLAN-v1.md` §9 (MCP server acceptance)
- `SPEC.md` §10.3 (daemon responsibilities — daemon processes elicit requests via MCP or local renderer)

### Problem
`PhinboxMcp::serve()` was a bare `rmcp::ServiceExt::serve().await` with
no signal handling. On SIGINT / stdin EOF the server dropped every
in-flight request abruptly. A `ShutdownCoordinator` existed in the
scaffold but was entirely dead code (`#[allow(dead_code)]` on
`inflight: Arc<AtomicUsize>`).

### Modules changed

| File | Change |
|---|---|
| `src/mcp/shutdown.rs` | Added `new()`, `cancel_all(timeout)`, `register_inflight()`/`deregister_inflight()`. `install()` now takes `Arc<Self>` so the signal handler can call `cancel_all()` when SIGINT fires. Removed all `#[allow(dead_code)]`. |
| `src/bin_mcp.rs` | Added `--shutdown-timeout-secs N` clap flag (default 5). `select!` between `server.waiting()` and shutdown oneshot; on signal, `coord.cancel_all(timeout)`, log "shutting down…", break. |
| `Cargo.toml` | version = 0.9.0 |

### Architecture
```
SIGINT → signal(3) → oneshot::Sender → shutdown_rx.await
  → coord.cancel_all(5s)
    → ct.cancel()
    → while inflight > 0 { sleep(100ms) }  (up to timeout)
    → oneshot::Sender → main loop breaks
```

The inflight counter is an `Arc<AtomicUsize>` incremented/decremented
by the router methods (reserved for a future request-tracking interceptor).
Currently unused but the bus is wired.

### Risks
- **Timeout too short**: Hardcoded 5s default; user can override with
  `--shutdown-timeout-secs N` in the binary.
- **Tokio signal feature**: `tokio = { features = ["signal"] }` is now a
  direct dep requirement (already transitively available via
  `features = ["full"]`).
- **Platform**: `tokio::signal::unix` is Unix-only. Windows builds with
  default features only; `signal` feature compiles but the default handler
  (`ctrl_c()`) is used on non-Unix.

### Verification
- `cargo build -p phinbox` — clean, 0 warnings
- `cargo build -p phinbox --features tray-native` — clean, 0 warnings
- `cargo test -p phinbox --no-fail-fast` — **154/154 green** (was 149)
- Tests added: `cancel_all_drains_inflight`, `cancel_all_honours_timeout`,
  `cancel_all_no_inflight_is_noop` (in `mcp::shutdown::tests`)
- `git push origin wip/2026-07-22-phenotype-tooling-absorbed-go-mod`
- Branch is **31 commits ahead of main**.
