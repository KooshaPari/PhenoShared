# Session: phinbox approval landing — feedback-loop closure

**Date:** 2026-09-18
**Scope:** `crates/phinbox`
**Trigger:** Prior validation accepted compile + `cargo test --lib` as sufficient. It was not.
Driving the real surface (popup renderer, MCP binary, IPC defer flow, agent
packaging) exposed five distinct product bugs that narrow checks could not see.

## Outcome

| Surface | Evidence | Result |
|---|---|---|
| macOS popup, Boolean field | live `phinbox smoke` → typed `Answered(Boolean(true))` | works |
| macOS popup, Text field | unit assertion: answer box present, `text returned` read | works |
| macOS popup timeout | `giving up` guard + Rust wall-clock kill, both exit-0 | works |
| IPC defer → re-answer | `deferred_flow.rs` 6 tests incl. real-UDS server | works |
| MCP elicit tool | `mcp_stdio.rs` e2e over JSON-RPC with Boolean field | works |
| MCP handshake | fresh signed binary, initialize + tools/list | works |
| Agent packaging | claude, codex, forgecode, cursor, droid, kilo all register | works |

Full matrix: **179 passed, 0 failed** (`cargo test -p phinbox`).
Commits: `c0350183`, `8652e0f7`, `a35c9eae` — all pushed to `origin/main`.

## Bugs found by closing the loop

1. **AppleScript `text returned` crash** (`script.rs`). `display dialog` only
   exposes `text returned` when invoked with `default answer`. Button-only
   dialogs (Boolean/Choice — the core approval case) read it unconditionally
   and raised *"Can't get text returned"*, failing every popup. Fixed by
   deriving `has_answer_box` from the field kind.

2. **No typed coercion** (`parse.rs`, `mod.rs`). Every answered popup returned
   `FieldValue::Text`, so `phinbox smoke` (Boolean) died with
   *"unexpected response variant"*. The `coerce_value` helper existed but was
   dead code. Now button-only dialogs fall back to the button label as the raw
   value and the render boundary coerces to the requested kind.

3. **Smoke violated its documented contract** (`cli/common.rs`). `agents_smoke`
   states *"smoke should exit 0 even if the popup times out"*; the impl returned
   `Err` on timeout. A rendered popup that times out still proves the whole
   render path.

4. **AppleScript gave-up race** (`script.rs`). On an AppleScript-side timeout
   the response record has `gave up:true` and no `button returned`; reading it
   throws. Rust's wall-clock loop usually wins, but that is a race, not a
   guarantee. Added an explicit `gave up` guard mapping to `timed_out`.

5. **Defer discarded the request** (`server.rs`, prior session). A `Deferred`
   response was passed to `finalize()`, moving the file to `answered/` and
   making it unanswerable — defeating the entire "defer to inbox" contract.

## Lessons

- `cargo test -p <crate> --lib` skips bins and integration targets. The real
  gate is `cargo test -p <crate>`. Two compile-level bugs (CLI bin, integration
  test literals) were invisible under `--lib`.
- A popup that "renders" is not a popup that "answers". Type coercion across
  the render boundary is part of the product contract.
- Test budgets that assert protocol correctness must not double as latency
  assertions; cold-start first-exec of a fresh signed binary can exceed 3s.
- Binaries copied out of `target/` on macOS need `codesign --force --sign -`
  or taskgated SIGKILLs them (provenance xattr breaks the adhoc signature).

## Machine-environment notes

- phinbox installed at `~/.local/bin` and `~/.cargo/bin` (both copies, both
  signed). Re-install pattern: `cp` then `codesign --force --sign -`.
- `phinbox` and `phinbox-mcp` binaries both verified to contain the fixes via
  `strings`.

---

# Phase 2 — renderer parity (linux / windows / tty)

The macOS closure above left three renderers that had never been driven.
Auditing them found six more defects of the same classes. Commit `ed295a3c`.

## Defects

1. **Coercion was macOS-only.** `render::dispatch` is the single choke point
   for every backend; coercion now lives there (`spec::coerce`, moved out of
   the macOS-gated module). `windows.rs` even carried the comment *"the
   dispatcher coerces using the original spec"* — it never did, so every
   Windows Boolean/Choice/Integer answer was mistyped. Same leak in linux/tty.
2. **linux.rs discarded the answer.** `run_with_timeout` piped stdout and
   never read it; `parse_zenity_status` returned a hardcoded `Text("yes")` and
   kdialog returned the literal `"(see kdialog stdout)"`. Every Text, Integer,
   Choice and Date answer was replaced by a placeholder. The outcome now
   carries stdout and the real value flows through.
3. **linux.rs reported timeouts as errors.** `Err(ElicitError::Timeout)` rather
   than `ElicitResponse::TimedOut`; dispatch now maps it.
4. **tty.rs panicked** on a fixed 10-byte slice when a DateTime `default` was
   shorter than 10 bytes. `default` is caller-supplied (MCP/CLI), so a client
   could crash the server. Verified with a standalone `rustc` reproduction.
5. **tty.rs leaked secrets.** `secret: true` Text fields were rendered in
   plaintext (`secret: _` was destructured away). Now a masked
   `inquire::Password`.
6. **tty.rs LongText lied.** Help text promised multi-line entry while
   collecting a single line.

## Windows had never compiled

`windows.rs` passed `default`, `placeholder` and an icon expression to
`format!` that the template never referenced — a hard *"unused formatting
arguments"* error. The crate cannot build for Windows (see the structural gap
below). The script now applies `default`/`placeholder`, renders urgency as a
label colour, and escapes button labels into the output line. The module is
compiled under `test` on every host so its pure script builder and parser stay
covered from a macOS checkout.

## Verification method

| Check | Evidence |
|---|---|
| macOS full matrix | 193 passed / 0 failed |
| Windows renderer logic | 10 tests run on macOS, incl. a real `pwsh` parse of the generated script |
| Linux full lib suite **executed** | 123 passed / 0 failed in `rust:1-bookworm`, incl. all 6 `platform::linux` tests (stdout capture, real-value flow, timeout mapping, cancel, fallbacks) and all 6 `spec::coerce` tests |
| Linux renderer compiles | `cargo check --target x86_64-unknown-linux-gnu` (lib + tests) clean |
| Windows renderer compiles | `cargo check --target x86_64-pc-windows-gnu`: `windows.rs` clean |

The real workspace root cannot resolve inside the container (an unrelated member
pulls a private git dependency), so the Linux run uses a generated mini
workspace containing only `phinbox` plus the workspace's inherited
`[workspace.package]` / `[workspace.dependencies]`. Same source, no other
members.

## Structural gap — closed in `d0144316`

`crates/phinbox/src/inbox/ipc/` is a Unix-domain-socket design and was **not**
`cfg`-gated, so `phinbox` could not compile for Windows at all
(`tokio::net::UnixListener`, `std::os::unix`). That made the Windows renderer
fix unreachable. Nothing in the crate references the module except its own
declaration and one integration test, so it is now `#[cfg(unix)]` and that
test is gated to match; the HTTP daemon, the inbox and every renderer are
unaffected on Unix. `installer/powershell.rs` also used `Command` inside its
Windows-only blocks without importing it.

Because the platform renderers are `cfg`-gated, a broken one is invisible to a
native `cargo test` — it is simply never compiled. That is how both failures
survived. `crates/phinbox/scripts/check-targets.sh` now checks Linux and
Windows for all targets (skipping uninstalled ones), with a negative control
confirmed: breaking `windows.rs` makes it exit 1, and 0 when clean.

| Check | Result |
|---|---|
| `--all-targets` for `x86_64-pc-windows-gnu` | 0 errors (was: could not compile) |
| `--all-targets` for `x86_64-unknown-linux-gnu` | 0 errors |
| macOS full matrix after the change | 193 passed / 0 failed |
| guard negative control | exit 1 broken, exit 0 clean |


---

# Phase 3 — audit of the untested surfaces, and real Windows runtime

A read-only audit of every surface never driven end-to-end, plus a native
Windows run, found eight more defects. Each was reproduced before being
fixed. Commits `e2ebd5e6`, `b215d543`, `0562f222`.

## Defects

1. **`--features tray-native` had never compiled.** `[lints.rust]` sets
   `unsafe_code = "deny"` while `src/tray/native.rs` and the `phinbox-app`
   bin contain five FFI `unsafe` blocks. The whole tray feature and the
   `phinbox-app` binary were unreachable, which also invalidated the SPEC
   acceptance criteria and README claims built on them. Fixed with the
   escape hatch already used in `cli/open.rs`.

2. **The TUI panicked on any non-ASCII title.** `tui/state.rs::truncate`
   sliced `&s[..n]` on a byte index, so a multi-byte character straddling
   the boundary aborted the viewer. `title`/`request_id` are agent-supplied
   and `validate()` allows 80 chars, so this was ordinary input.

3. **`timeout_secs: 0` fired instantly**, contradicting both
   `PromptSpec::timeout_secs` ("Set to 0 for no timeout") and
   `phinbox ask --help`. All three renderers did `start.elapsed() >=
   timeout`, true on the first poll. Now resolved via
   `platform::deadline_for`, where 0 means no deadline.

4. **Every inbox HTTP route returned 200.** The status was computed and
   discarded by the response helpers. Behind it sat a second bug: a
   successful answer emitted *two* status lines because the 500
   fall-through wrote a second full response after the redirect.

5. **An already-answered request could be re-answered and silently
   overwritten.** The CLI and the IPC server both already refused this;
   HTTP did not.

6. **An empty or partial POST body was recorded as a successful answer**,
   so `phinbox wait` returned a plausible value the human never chose.
   Now an absent key is a 400 while an explicit `value=` is a legitimate
   empty answer — conflating those two was the bug.

7. **The HTML form emitted its `<input>` and `<textarea>` outside
   `<form>`**, so a browser submit sent only `confirm=ok` and the typed
   value never arrived. Defect 6 is precisely what hid this: the daemon
   used to accept the result as an empty answer. Found by the audit, not
   by the tests, because the tests POSTed directly.

8. **`--tui` did not degrade as documented.** Non-TTY stdin produced
   `enable_raw_mode: Device not configured` and exit 1 rather than the
   documented plain-text fallback. `?` help was also documented but
   unimplemented, and `PHINBOX_TUI_KEYMAP_*` was documented in four places
   with no implementation at all — the docs were corrected rather than the
   feature invented.

## Windows: verified at runtime, not just compiled

A Tailscale Windows host was used. Two things had to be established first:

- **The Rust shims were fine; RedirectionGuard was the problem.** The
  earlier "0-byte cargo.exe" reading was wrong — PowerShell reports
  `Length 0` for symlinks, and `cargo.exe` is a symlink to `rustup.exe`.
  `sshd.exe` carries an IFEO `MitigationOptions` opt-in, so every
  sshd-descended process refuses symlinks created by a non-elevated token
  (`STATUS_UNTRUSTED_MOUNT_POINT`). Recreated from an elevated session;
  `.cargo\bin` was also missing from PATH. Verified with a real
  `cargo new` + `cargo run`.
- **Bare `link.exe` resolves to Git's, not MSVC's.** Entering `vcvars64.bat`
  is required or the link step picks the wrong tool.

Runtime result: native `cargo test -p phinbox --lib` → **127 passed, 0
failed** (including the 10 `platform::windows` tests). The popup itself
renders and round-trips:

```
window_station=WinSta0
visible-titled-window-count=28
  hwnd=0x110e7e title=phinbox · phinbox smoke test
smoke: passed        exit 0
```

An SSH login runs in **session 0** (`UserInteractive=False`, window station
`Service-0x6-…$`), so a popup launched over SSH has no real desktop and
cannot be verified there; the dialog was run in **session 1** via a
scheduled task and answered by a purpose-built Win32 injector (PowerShell
and cscript hang under the scheduler on that host). This is now documented
in `platform/windows.rs`. Negative controls confirmed a garbled script
yields a parser error and exit 1, so a broken script cannot report success.

## Verification

| Check | Result |
|---|---|
| macOS full matrix | 212 passed / 0 failed |
| Windows native lib suite | 127 passed / 0 failed (executed on the Windows host) |
| Windows runtime popup | dialog rendered, `smoke: passed`, exit 0 |
| Linux lib suite | 123 passed / 0 failed (executed in a container) |
| Cross-target guard | Linux + Windows, 0 errors |
| `--features tray-native --all-targets` | compiles (was: 5 hard errors) |

## Method note

Every defect here was invisible to the existing suite, for one of three
reasons: the code was `cfg`-gated so it was never compiled; the test POSTed
to the daemon directly and so never exercised the HTML form; or the
documented behaviour simply had no test because it had never been
implemented. Compile-and-unit-test gates do not reach any of those.
