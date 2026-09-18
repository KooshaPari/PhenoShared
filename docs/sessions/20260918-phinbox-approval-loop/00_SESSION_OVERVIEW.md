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


