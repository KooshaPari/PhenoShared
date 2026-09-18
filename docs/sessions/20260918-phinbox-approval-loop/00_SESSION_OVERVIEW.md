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
