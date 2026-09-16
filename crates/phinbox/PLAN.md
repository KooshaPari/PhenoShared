# phinbox — Implementation Plan

This is the working plan for bringing `phinbox` from scaffold to a tagged 0.1.0 release. It is
versioned; subsequent revisions bump `-v2.md`.

## Milestones

### M0 — Scaffold & contract (v0.1.0)

- [x] Crate skeleton under `crates/phinbox/`.
- [x] `PromptSpec` / `ElicitResponse` / `FieldSpec` / `FieldValue` types with serde + schemars.
- [x] Validation function (`spec::validate`) enforcing all bounds.
- [x] Renderer dispatcher (`render::dispatch`) with platform detection.
- [x] TTY renderer (`platform/tty.rs`) using `inquire`.
- [x] macOS / Windows / Linux GUI renderers as compile-guarded skeletons.
- [x] JSON renderer (`platform/detect` `Json` mode) for deterministic CI tests.
- [x] CLI binary `phinbox` with `ask`, `validate`, `schema`, `detect`, `version`, `smoke`.
- [x] MCP server binary `phinbox-mcp` with `tools/list` + `tools/call` (single tool
      `phinbox_mcp`).
- [x] Plugins: Forgecode, Codex, Cursor with install scripts and READMEs.
- [x] Skill manifest at `.phinbox/skills/phinbox/SKILL.md`.
- [x] RESEARCH.md, SPEC.md, PRD.md, README.md, CHANGELOG.md.
- [x] Integration tests under `tests/`.
- [x] Test fixtures under `tests/fixtures/`.

### M1 — Async inbox + install (v0.2.0)

- [x] `phinbox::inbox` subsystem: `PendingRequest`, `RequestState`, `RequestOrigin`,
      `wait_for_response`, `list_pending`, `load`.
- [x] `phinbox ask --async` enqueues to `<inbox-dir>/inbox/<id>.json` and prints
      `{status: "deferred", request_id, open_url}`.
- [x] `phinbox wait --request-id <id> [--timeout <sec>]` polls for `answered.json` and prints
      the response.
- [x] `phinbox answer --request-id <id> --file <spec.json>` writes the answer file directly
      (for testing or scripted reply).
- [x] `phinbox inbox {--list|--show <id>|--purge}` for inspecting the inbox directory.
- [x] `phinbox::views` module: HTML form renderer, full page with embedded CSS,
      plain-text summary, JSON envelope.
- [x] `phinbox::installer` module: platform-specific install paths, launch-agent / systemd /
      Run-key generation, PATH export, smoke verification, `--dry-run`.
- [x] `phinbox install [--prefix <dir>] [--no-launch-agent] [--skip-path] [--no-smoke]`.
- [x] `phinbox uninstall [--prefix <dir>] [--yes]`.
- [x] `phinbox daemon [--inbox-dir <dir>] [--bind <addr>] [--port <p>]` runs an HTTP
      server serving HTML forms; emits macOS tray / Windows tray notifications
      with click-to-open deep links.
- [x] `phinbox::inbox::notify` module: iMessage / SMS / email outbound channels
      (gated by environment variables, off by default).
- [x] Inbox deeplink helper: `phinbox::inbox::inbox_open_url(request_id, host)` returns
      `http://127.0.0.1:7117/?id=<id>` so a phone can open the form.
- [x] Test count grew from 68 → 108. 13 new CLI integration tests cover install /
      uninstall / async enqueue / inbox list / wait / answer.

### M1.5 — Non-blocking daemon + tray + iMessage (v0.3.0, addendum)

On 2026-07-22 we expanded the v0.2.0 inbox subsystem into a true non-blocking operator
inbox. Goal: agents that would otherwise be blocked waiting on a popup can now
`ask --async` and continue, while the operator gets a tray icon, a deep-link to the
form, and (optionally) iMessage / SMS / email notifications routed through existing
`agent-imessage` infrastructure.

- [x] Local HTTP inbox server (`127.0.0.1:7117` default, `--bind` configurable but
      loopback-only by default; non-loopback requires `--i-know-what-im-doing`).
- [x] `/healthz`, `/form/:id`, `/answer/:id`, `/list` routes; HTML form +
      plain-text fallback + JSON envelope for tooling.
- [x] macOS tray (`NSStatusItem`) + Windows tray (`Shell_NotifyIcon`) stubs gated on
      `cfg(target_os)`; click opens the form in the user's default browser.
- [x] iMessage / SMS / email notify fanout in `inbox::notify`, gated by env vars
      (`PHINBOX_NOTIFY_IMESSAGE`, `PHINBOX_NOTIFY_EMAIL`, …); off by default to
      prevent surprise outbound traffic.
- [x] CLI inheritance: `install [--yes]`, `uninstall [--yes]`, `daemon [--port N]`,
      `inbox {--list|--show ID|--purge}`, `wait --request-id ID [--timeout S]`,
      `answer --request-id ID [--values @file|--value k=v]`.
- [x] Smoke-after-install: `phinbox install` copies the binary, then runs
      `phinbox smoke` to verify PATH resolution and link sanity.

### M2 — Native tray icon (v0.4.0, addendum)

On 2026-07-22 we replaced the M2 placeholder (which originally scoped the native
popup renderers) with a narrower, higher-value deliverable: **a real persistent
tray icon for `phinbox daemon`**, behind a feature flag so the default build
stays portable.

Why swap scope: v0.3 already shipped native popups (Cocoa osascript / Win32
MessageBox via PowerShell) for blocking elicits. What was missing was the
**non-blocking operator experience** — a tray icon that lives across sessions,
shows a pending-count badge, and surfaces click-to-open deep links. That's what
agents actually need to keep the operator informed when an `ask --async` lands.

- [x] New `tray` module behind `--features tray-native`:
      `tray::Tray` trait + `tray::NoopTray` (always compiled) + `tray::NativeTray`
      (gated, cross-platform via `tray-icon 0.24`).
- [x] macOS tray (`NSStatusItem` via `objc2-app-kit`):
      menu-bar text = "phinbox · N pending"; tooltip = title + last question;
      click toggles a menu (Show inbox, Open latest, Toggle quiet, Quit).
- [x] Windows tray (`Shell_NotifyIconW` via `windows-sys` 0.61): same API surface
      as macOS; tray events pump on a dedicated OS thread because the Win32
      message loop is per-thread.
- [x] Linux tray (libappindicator via `tray-icon`'s `libappindicator` feature);
      falls back silently when no system tray is available (no panic in CI / SSH).
- [x] `tray::MenuAction` dispatch: `OpenInbox`, `OpenLatest(request_id)`,
      `ToggleQuiet`, `Quit`. `Quit` propagates to the daemon shutdown coordinator
      so the process exits cleanly.
- [x] `DaemonConfig.enable_tray: bool` (default `true`), wired to a new
      `--no-tray` CLI flag. When the feature isn't compiled in, `--no-tray` is
      silently no-op (the daemon still runs).
- [x] Badge count updates: `tray.update_pending_count(n)` called from the
      notifier loop whenever the inbox transitions (enqueue / answer / purge).
- [x] `Arc<dyn Tray>: Send` is achieved by owning-thread + channel architecture;
      the `TrayIcon` (which is `!Sync` on macOS) lives on a dedicated thread that
      owns it for its lifetime. Public API is `Send`-only, no `Sync`.
- [x] 7 new unit tests (`tray::tests`): noop default values, badge text
      formatting, MenuId parsing, Click event mapping, `build_tray` is `Send`,
      noop tray can be cloned through Arc, disable reason surfaces in errors.

### M2.5 — Terminal inbox viewer (v0.5.0, addendum)

On 2026-07-22 we shipped the **canonical local UX for the inbox**: a
`ratatui`-based TUI accessible via `phinbox inbox --tui` (or
`phinbox tui`). After v0.4 the daemon has a tray icon and the inbox
is durable on disk; v0.5 closes the gap for users who are already at a
terminal and want to see + answer pending requests without opening a
browser.

- [x] New `tui` module: `ViewerConfig`, `InboxEntry`, `Keymap`,
      `KeyAction`, `snapshot_inbox()`, `run_tui()`.
- [x] `ratatui` 0.30 + `crossterm` 0.29 as direct dependencies (always
      compiled; the TUI is the canonical local UX).
- [x] Split-pane layout: pending requests on the left, full `PromptSpec`
      on the right, status bar on the bottom. Live re-scan every 1 s
      (`--poll-ms` configurable).
- [x] Default keymap: `j/k` or `↓/↑` move; `Tab` switch focus; `Enter`/`o`
      open in browser; `r`/`F5` refresh; `d` dismiss; `?` help; `q`/`Esc`
      quit. Rebindable via `PHINBOX_TUI_KEYMAP_<KEY>=<action>` env vars.
- [x] Graceful fallback: `TERM=dumb`, no TTY, or `ratatui::init()` failure
      → plain-text output, exit 0. CI / `ssh` without TTY allocation
      works without extra flags.
- [x] `bin_phinbox.rs::InboxArgs` gained `--tui` and `--poll-ms`;
      `cmd_inbox` branches into TUI when set.
- [x] 14 new unit tests (`tui::tests`): `field_summary`, `format_age`,
      sort order, terminal-state marking, key handling, position lookup,
      detail-pane render, focus toggle, truncate, default state, empty
      dir, sorted snapshot.
- [x] Resolved the v0.4 "macOS `NSStatusItem` badge text is a placeholder"
      note: the owner-thread channel now accepts `SetTitle(String)` and
      `tray-icon::TrayIcon::set_title()` is called from the owning thread.
      Verified on macOS.

### M2.6 — Open-in-box discoverability fixes (v0.5.1, addendum)

On 2026-07-22 the user reported: "have yet to see open inbox app/tray".
After v0.4 the tray icon and the daemon's inbox URL both existed, but
no CLI surface made "open the inbox in my browser" discoverable. v0.5.1
closes that gap and patches the v0.4 regressions that prevented the
existing surfaces from actually working.

- [x] **`phinbox open`** — standalone subcommand with `--latest`,
      `--spawn-if-missing`, `--print-only`, `--inbox-dir`, `--port`.
      Resolves the live daemon URL via the new
      `inbox::daemon::live_url(root, bind_filter)` helper (no more
      hardcoded `:7117`).
- [x] **`phinbox daemon --auto-open-browser`** — opens the inbox index
      in the default browser as soon as the daemon finishes binding
      (also controllable via `PHINBOX_AUTO_OPEN_BROWSER=1`).
- [x] **Fix #1**: tray badge/tooltip now actually update — the v0.4
      owner-thread channel was dropping `SetBadge`/`SetTooltip`. Re-routed
      through `tray_icon::TrayIcon::set_title` + `set_tooltip` on the
      owning thread.
- [x] **Fix #2**: tray click URL is read from `TrayConfig::inbox_url`,
      not hardcoded `http://127.0.0.1:7117`.
- [x] **Fix #3**: `phinbox inbox --open` and `ask --async` now use
      `inbox::daemon::live_url()` so they correctly point at whatever
      port the daemon is bound to.
- [x] **New public API** for downstream crates:
      `phinbox::inbox_live_url`,
      `phinbox::inbox_read_lockfile`,
      `phinbox::open_in_default_browser`,
      `phinbox::LockfilePayload`.
- [x] **4 new regression tests** in `daemon::tests`:
      `live_url_returns_none_when_no_lockfile`,
      `live_url_rejects_stale_lockfile`,
      `live_url_accepts_running_daemon`,
      `live_url_respects_bind_filter`.
- [x] Test count grew from 129 → **133** (96 lib + 13 bin + 14 cli + 6
      lib intg + 4 mcp stdio).

### M3 — Native popup renderers (next, deferred from M2)

The M2 scope was originally "wire the macOS / Windows / Linux GUI renderers"
(already partially done via shell-out to `osascript` and PowerShell — see v0.3).
What remains is upgrading from shell-out to **in-process FFI**:

- [ ] Wire macOS renderer: `objc2` + `cocoa` build a real `NSPanel`, lay out a label + control +
      confirm/cancel, run a modal `NSApp::runModal` until the user clicks. Return the typed value
      via a captured `block` / closure stored in an `Id` trait object. (Tracked in
      `platform/macos.rs`.)
- [ ] Wire Windows renderer: `windows-sys` + `CreateWindowExW` create a top-level dialog, populate
      with `EDIT` / `COMBOBOX` / `BUTTON` controls, run `GetMessageW` in a loop, return on
      `WM_COMMAND` / `WM_CLOSE` / a `SetTimer`-driven timeout.
- [ ] Wire Linux renderer: `rfd::AsyncMessageDialog` for booleans; for richer fields, `rfd::FileDialog`
      + custom GTK4 builder; otherwise TUI.
- [ ] Add screenshot tests under `tests/render_screenshots/` (manual run only; CI skips with
      `PHINBOX_SCREENSHOTS=1`).

### M3 — Cross-client smoke

- [ ] Forgecode: register the tool, dispatch a sample prompt, screenshot the popup, and verify the
      agent loop resumes on confirm.
- [ ] Codex: write `~/.codex/mcp.toml`, run the Codex CLI with `--mcp phinbox`, and verify
      `phinbox_mcp` is callable.
- [ ] Cursor: merge `cursor-mcp.json`, restart Cursor, verify the tool list contains
      `phinbox_mcp`.

### M4 — Release

- [ ] Notarize the macOS `.app` bundle (separate `release-cut` plan).
- [ ] Sign the Windows binary with `signtool`.
- [ ] Bump version to `1.0.0`; tag the release; cut a `phenotype-tooling` release.

## PR sequencing

Each PR is small enough to review in ≤ 200 lines.

1. **PR-1:** Scaffold crate + library types + JSON schema export + unit tests. *(done in M0)*
2. **PR-2:** CLI binary + TTY renderer + integration tests. *(done in M0)*
3. **PR-3:** MCP server + JSON-RPC integration tests. *(done in M0)*
4. **PR-4:** Plugins + skill manifest. *(done in M0)*
5. **PR-5:** Async inbox subsystem + views + `ask --async` / `wait` / `answer` /
   `inbox` subcommands. *(done in M1)*
6. **PR-6:** Install / uninstall + daemon + iMessage/email notify channels. *(done in M1)*
7. **PR-7:** Tray icon (cross-platform via `tray-icon` + `objc2-app-kit` + `windows-sys`). *(done in M2 — v0.4.0)*
8. **PR-8:** macOS native renderer (in-process FFI). *(M3)*
9. **PR-9:** Windows + Linux native renderers (in-process FFI). *(M3)*
10. **PR-10:** Cross-client smoke tests + release. *(M3 / M4)*

## Review checklist (per PR)

- [ ] `cargo fmt --all -- --check`
- [ ] `cargo clippy -p phinbox --all-targets -- -D warnings`
- [ ] `cargo test -p phinbox`
- [ ] No new outbound network deps
- [ ] Secret fields never appear in tracing output
- [ ] Public types still `Serialize + Deserialize` roundtrip cleanly

## Open questions

- **Q1.** Should the macOS renderer pin itself as an LSUIElement (no Dock icon) or run as a regular
  foreground app? — *Lean toward LSUIElement (Info.plist on the bundled `.app`); for the dev binary
  it's a no-op.*
- **Q2.** Should `phinbox-mcp` support `notifications/cancelled` so a host can dismiss an open
  prompt? — *Yes for v0.2; tracked here so we don't forget.*
- **Q3.** Should the TUI fallback print on stdout or stderr? — *Stdout, because the JSON response
  is the primary artifact. Diagnostics go to stderr.*
