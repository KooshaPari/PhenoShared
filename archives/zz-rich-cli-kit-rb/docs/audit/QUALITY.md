# Quality Audit — rich-cli-kit

**Date:** 2026-06-14
**Scope:** All source under `crates/`, `tests/`, `mcp/` (`.rs` + `.py`).
**Method:** Read-only; `fs_search` / `read` / `shell` for line counts. No builds, no `cargo`/`go`/`npm` invocations, no git mutations.

---

## 0. Inventory

| Crate / Package | Lang | Files | LOC | Test fns | Test fns / 100 LOC |
|---|---:|---:|---:|---:|---:|
| `rck-core` (lib) | Rust | 11 | 1,635 | 44 | 2.69 |
| `rck-cli` (bin) | Rust | 1 | 273 | 0 | 0.00 |
| `tests/` (smoke) | Rust | 1 | 6 | 1 | 16.67 |
| `mcp/rich_cli_mcp/` | Python | 3 | 331 | 0 | 0.00 |
| `mcp/tests/` | Python | 1 | 67 | 11 | 16.42 |
| **Total** | | **17** | **2,310** | **56** | **2.42** |

Test-function count breakdown:
- Rust `#[test]` attributes: **44** (all inside inline `#[cfg(test)] mod tests` blocks).
- Python `def test_…` functions: **11**.
- Integration test files: **2** (`tests/smoke_test.rs`, `mcp/tests/test_rck_wrapper.py`).

---

## 1. TEST GAPS

### 1.1 Per-module test counts (Rust)

| Module | `#[test]` count | Notes |
|---|---:|---|
| `crates/rck-core/src/emit.rs:108-205` | 13 | best-covered |
| `crates/rck-core/src/interactive.rs:280-375` | 7 | tests largely stub stdio; see §1.3 |
| `crates/rck-core/src/width.rs:74-112` | 6 | grapheme/ANSI strip — solid |
| `crates/rck-core/src/panel.rs:116-192` | 4 | rounded/ascii/emoji/links |
| `crates/rck-core/src/encoder.rs:69-128` | 3 | single-frame, multi-frame, chunk cap |
| `crates/rck-core/src/progress.rs:114-163` | 3 | ascii, truecolor, clamp |
| `crates/rck-core/src/shader.rs:54-78` | 3 | bundled lookup, install round-trip, unknown |
| `crates/rck-core/src/spans.rs:69-109` | 3 | text, link-on, link-off |
| `crates/rck-core/src/capabilities.rs:299-322` | 2 | `plain()` + `detect()` smoke |
| `crates/rck-core/src/image_data.rs` | **0** | see §1.2 |
| `crates/rck-core/src/lib.rs` | **0** | re-exports + one `emit_image` wrapper, not exercised |
| `crates/rck-cli/src/main.rs` | **0** | entire binary un-tested; see §1.3 |

### 1.2 Modules with ZERO tests

| File | Public surface untested | Why it matters |
|---|---|---|
| `crates/rck-core/src/image_data.rs:6-43` | `ImageData::from_path` (PNG/JPG decode + re-encode, `image` crate integration) at `image_data.rs:17-33`; `ImageData::from_png` constructor at `image_data.rs:36-43` | The only path that feeds the encoder; a regression in width/height or PNG bytes silently breaks all kitty output |
| `crates/rck-core/src/lib.rs:37-55` | `emit_image` (the public high-level entry point) at `lib.rs:37-55` | Every CLI `rck image` and MCP `rich.emit_image` flows through this branch |
| `crates/rck-cli/src/main.rs:109-285` | All 12 subcommands, `read_body` helper at `main.rs:238-248`, `demo` renderer at `main.rs:250-285` | The whole CLI is exercised only indirectly by the Python wrapper at `mcp/tests/test_rck_wrapper.py:33-86` (which is a `pytest.skip` if `rck` isn't built) |

### 1.3 Coverage quality issues (where tests exist)

- **`interactive.rs` tests can't reach stdin** — `interactive.rs:316-355` admits in comments it cannot feed stdin; the fallback paths (`ask_fallback`, `pick_fallback`, `input_fallback`) are tested by re-implementing their classify logic in-test (`interactive.rs:357-375`) rather than exercising the real code, so the fallback functions themselves at `interactive.rs:147-161`, `interactive.rs:203-227`, `interactive.rs:266-278` are un-covered.
- **Capability tests are smoke-only** — `capabilities.rs:316-322` only asserts `terminal.is_empty()`; none of the per-terminal branch logic at `capabilities.rs:64-80`, the env-flag inference at `capabilities.rs:82-118`, or `query_kitty_graphics` (the unsafe path at `capabilities.rs:142-292`) is tested. The whole `#[cfg(unix)]` termios / libc shim block (`capabilities.rs:196-287`) is completely untested.
- **`rck-cli` subcommands have no unit tests** — the Python integration tests at `mcp/tests/test_rck_wrapper.py:33-86` are the only coverage, and they all `pytest.skip` if the debug binary is missing (see `mcp/tests/test_rck_wrapper.py:18-23`).

### 1.4 Test infrastructure observations

- `tests/smoke_test.rs:4-6` is a single `assert_eq!(2 + 2, 4)` — its only purpose is to verify the harness works (`smoke_test.rs:1-2`), not the library.
- `mcp/tests/` is missing `__init__.py` and a `conftest.py`; discovery depends on `sys.path.insert(0, …)` at `mcp/tests/test_rck_wrapper.py:13` — fragile.

---

## 2. DEBT

### 2.1 TODO / FIXME / unimplemented! scan

| Token | Count | Location |
|---|---:|---|
| `TODO` | 0 | — |
| `FIXME` | 0 | — |
| `todo!()` | 0 | — |
| `unimplemented!()` | 0 | — |
| `panic!(…)` | 0 | — |
| `expect(…)` | 0 | — |
| `XXX` | 0 | — |
| `HACK` | 0 | — |

Result: **zero debt markers** of the conventional kind. The codebase does not advertise unfinished work in comments.

### 2.2 `unwrap()` — full count

Total `\.unwrap\(\)` matches in `crates/`: **20**, all inside `#[cfg(test)] mod tests` blocks (verified by line context — test-module openers live at `width.rs:74`, `interactive.rs:280`, `spans.rs:69`, `shader.rs:54`, `panel.rs:116`, `progress.rs:114`, `emit.rs:108`, `capabilities.rs:299`, `encoder.rs:69`).

Per-file `unwrap()` ranking (tests only — see §2.3 for the production check):

| File | `.unwrap()` | File:line refs |
|---|---:|---|
| `crates/rck-core/src/panel.rs` | 8 | `panel.rs:148`, `panel.rs:149`, `panel.rs:160`, `panel.rs:161`, `panel.rs:172`, `panel.rs:173`, `panel.rs:188`, `panel.rs:189` |
| `crates/rck-core/src/progress.rs` | 6 | `progress.rs:139`, `progress.rs:140`, `progress.rs:150`, `progress.rs:151`, `progress.rs:161`, `progress.rs:162` |
| `crates/rck-core/src/encoder.rs` | 3 | `encoder.rs:79`, `encoder.rs:95`, `encoder.rs:113` |
| `crates/rck-core/src/shader.rs` | 2 | `shader.rs:68`, `shader.rs:70` |
| `crates/rck-core/src/interactive.rs` | 1 | `interactive.rs:334` |
| **Total** | **20** | |

### 2.3 `unwrap()` / `panic!` / `expect(` in **non-test lib / bin** code

**Production lib (`rck-core`): 0 `.unwrap()` / 0 `.expect(` / 0 `panic!`.** ✅

The only `.unwrap_or_default()` / `.unwrap_or(...)` calls in production code are safe fallbacks:
- `crates/rck-core/src/lib.rs:51` — `img.alt_text.as_deref().unwrap_or("untitled")` (rendering fallback).
- `crates/rck-core/src/panel.rs:83` — `rows.iter().map(...).max().unwrap_or(0)` (empty-rows fallback).
- `crates/rck-core/src/encoder.rs:121` — `.unwrap_or(frame.len())` (slice bound fallback inside test helper).
- `crates/rck-core/src/capabilities.rs:57-59` — three `env::var(...).unwrap_or_default()` for optional terminal hints.
- `crates/rck-core/src/capabilities.rs:178` — `libc_read(...).unwrap_or(0)` on raw syscall inside the query path; loss of a single byte is acceptable.

**Production bin (`rck-cli/src/main.rs`): 0 `.unwrap()` / 0 `.expect(` / 0 `panic!`.** ✅ All fallible work is `Result`-propagated via `?` and `anyhow::Context` (e.g. `main.rs:120-121`, `main.rs:163`, `main.rs:225-226`).

**Python server (`mcp/rich_cli_mcp/server.py`):** broad `except Exception as e` is used at `server.py:44`, `server.py:58`, `server.py:73`, `server.py:94`, `server.py:115`, `server.py:131`, `server.py:144`, `server.py:155`, `server.py:173` (9 sites) to convert subprocess failures into structured tool responses. This is **deliberate** (the MCP contract promises a dict, never a raise) and is the right pattern, but it does swallow the underlying traceback — flag as soft debt, not a defect.

### 2.4 Unsafe code

- 7 `unsafe` sites, all confined to `crates/rck-core/src/capabilities.rs:164, 178, 199, 212, 235, 248, 285` — a self-contained `libc` shim for the `query_kitty_graphics` TTY probe. None of it has a `// SAFETY:` comment justifying each block — **`clippy::missing_safety_doc` would fire** if a `#[deny(unsafe_op_in_unsafe_fn)]` lint were enabled.

---

## 3. ARCHITECTURE

### 3.1 Intended layering (from `Cargo.toml:3` and `CLAUDE.md:36-37`)

```
rck-cli (bin)  ──▶  rck-core (lib)
mcp/rich_cli_mcp (Py)  ──▶  rck binary (subprocess)
```

The workspace is split as documented; the public API surface (`lib.rs:23-32`) re-exports everything neatly.

### 3.2 Layering / SOLID violations found

| # | Severity | Module | Symptom | Reference |
|---|---|---|---|---|
| A | **High** | `crates/rck-core/src/capabilities.rs` (core lib) | `capabilities::detect()` is impure: it calls `io::stdout().is_tty()` (`capabilities.rs:56`) and reads 7+ env vars (`capabilities.rs:57-62`, `capabilities.rs:118`). Domain layer should be a pure function of `(&Env, IsStdoutTty)`; the function is not unit-testable without env mutation. | DIP violation; SRP violation (detect + env-IO + TTY-probe in one fn). |
| B | **High** | `crates/rck-core/src/capabilities.rs:142-292` (core lib) | The "domain" detect function reaches past lib boundaries into raw `libc::write`/`read`/`tcgetattr`/`poll` via inline `extern "C"` (`capabilities.rs:199-222`, `capabilities.rs:230-256`, `capabilities.rs:269-287`) and toggles global raw mode through `crossterm::terminal::enable_raw_mode()` (`capabilities.rs:262`). Mixing a stateless capability probe with side-effectful global termios toggling makes the function unsafe to call from tests. | Architectural smell — should be split into `detect_from_env` (pure) + `probe_tty` (side-effecting, behind a feature/cfg). |
| C | **High** | `crates/rck-core/src/interactive.rs` (core lib) | The `ask` / `pick` / `input` primitives hard-code `io::stdout()` (`interactive.rs:46`, `interactive.rs:67`, `interactive.rs:82`, `interactive.rs:148`, `interactive.rs:204`, `interactive.rs:267`) and `io::stdin()` (`interactive.rs:152`, `interactive.rs:212`, `interactive.rs:271`). Every other emitter in the crate takes `&mut impl Write`; interactive is the odd one out and cannot be driven from a test or a custom UI. | SRP / DIP — the signature should be `ask<W: Write, R: Read>(out, in, caps, …)`. |
| D | **Medium** | `crates/rck-core/src/emit.rs:19-21` | `in_tmux()` reads `TMUX` env on every call (callers do `emit.rs:32`, `emit.rs:59`, `emit.rs:72`, `emit.rs:95` etc. and the value is plumbed via `in_tmux_val: bool` already, so the function is dead in the lib's hot paths but exported). | Minor: API surface redundancy. |
| E | **Medium** | `crates/rck-core/src/shader.rs:28-37`, `shader.rs:41-52` (core lib) | The lib reads `XDG_CONFIG_HOME` / `HOME` and writes to `~/.config/ghostty/...` directly (`shader.rs:48`, `shader.rs:50`). A "rendering primitives" library should not perform filesystem IO. | SRP — install should live in the CLI (or a `rck-shader` binary), not the lib. |
| F | **Low** | `crates/rck-cli/src/main.rs:109-236` | `main.rs` is one 273-line `fn main` containing clap parsing, capability detection, subcommand dispatch, AND a `demo()` function (`main.rs:250-285`). Classic god-function. | Extract `dispatch(cmd, caps) -> Result<()>` and a per-subcommand helper module. |
| G | **Low** | `mcp/rich_cli_mcp/server.py:26-185` | `build_server` declares 9 inline `@mcp.tool` functions; each repeats the `try/except Exception` envelope. A `_run_tool(name, fn)` decorator would DRY this. | DRY violation, not blocking. |
| H | **Low** | `crates/rck-core/src/interactive.rs:33-35` | `can_interact(caps)` requires `caps.is_tty && caps.kitty_keyboard`, but `ask`/`pick`/`input` also fall through to `_fallback` which uses raw stdin — works only when `is_tty` is true; on `is_tty=false` the fallbacks hang. Not a layering bug, but the gating predicate under-models the actual contract. | Domain rule leak. |

### 3.3 God-modules / oversized files

Largest files (lines of source, including `#[cfg(test)]`):

| File | LOC | Concern |
|---|---:|---|
| `crates/rck-core/src/interactive.rs` | 353 | Three primitives + RAII guard + fallback paths; consider splitting into `ask.rs` / `pick.rs` / `input.rs` / `term_guard.rs` (or one module of small private fns). |
| `crates/rck-core/src/capabilities.rs` | 291 | Detection + TTY probe + libc shim all in one file. |
| `crates/rck-cli/src/main.rs` | 273 | CLI entrypoint with embedded `demo`. |
| `mcp/rich_cli_mcp/server.py` | 176 | Server definition, fine; would benefit from the decorator in §3.2-G. |

No file crosses the 600-line "blob" threshold.

### 3.4 Dependency direction

- `rck-cli` depends on `rck-core` only (one-way). ✅
- `mcp/rich_cli_mcp` is a Python sibling with **no in-tree binding** to `rck-core`; it shells out to the `rck` binary. This is the right call for an MCP server in a different runtime, but it does mean the MCP server's "tests" require a built `rck` binary (see `mcp/tests/test_rck_wrapper.py:18-23`).

---

## 4. LINES OF CODE

Total Rust + Python source under `crates/`, `tests/`, `mcp/`: **2,310 lines** across **17 files**.

Per-file (authoritative, from `Measure-Object -Line`):

```
crates/rck-core/src/lib.rs                       51
crates/rck-core/src/capabilities.rs             291
crates/rck-core/src/emit.rs                     184
crates/rck-core/src/encoder.rs                  116
crates/rck-core/src/image_data.rs                40
crates/rck-core/src/interactive.rs              353
crates/rck-core/src/panel.rs                    177
crates/rck-core/src/progress.rs                 151
crates/rck-core/src/shader.rs                    70
crates/rck-core/src/spans.rs                     97
crates/rck-core/src/width.rs                    103
crates/rck-cli/src/main.rs                      273
tests/smoke_test.rs                               6
mcp/rich_cli_mcp/__init__.py                      3
mcp/rich_cli_mcp/rck.py                         152
mcp/rich_cli_mcp/server.py                      176
mcp/tests/test_rck_wrapper.py                    67
```

**Files over 600 lines: 0.** (Threshold of 600 chosen as "needs-splitting"; largest is `interactive.rs` at 353.)

**Files over 200 lines (soft attention):** `interactive.rs` (353), `capabilities.rs` (291), `main.rs` (273), `emit.rs` (184), `panel.rs` (177), `server.py` (176).

**Sub-100-line files (mostly fine, but `image_data.rs` at 40 lines is the public loader and untested — see §1.2):** `lib.rs` (51), `image_data.rs` (40), `shader.rs` (70), `spans.rs` (97), `width.rs` (103), `smoke_test.rs` (6), `__init__.py` (3), `test_rck_wrapper.py` (67), `rck.py` (152).

---

## 5. 5-LINE SUMMARY

1. **Test coverage is thin at the seams:** 56 test functions total, but `image_data.rs` (the public image loader) and the entire `rck-cli` binary (273 LOC, 12 subcommands) have **zero** tests; `interactive.rs` fallback paths are un-exercised (its 7 tests re-implement logic to avoid stdin).
2. **No TODO/FIXME/panic/expect anywhere;** all 20 `\.unwrap\(\)` calls are inside `#[cfg(test)]` blocks — the lib and bin are panic-free in production code.
3. **Layering breaks in three places:** `capabilities::detect` mixes pure logic with env reads + raw `libc` termios toggling (`capabilities.rs:142-292`), `interactive::*` hard-codes `io::stdout/stdin` instead of taking `impl Write/Read` (`interactive.rs:46,67,82,152,212,271`), and `shader::install` does filesystem IO in a "rendering primitives" lib (`shader.rs:41-52`).
4. **LOC is healthy:** 2,310 total across 17 files; no file over 600 lines; largest is `interactive.rs` at 353; the only structural smells are god-function `main.rs:109-285` and the `interactive.rs` triple-primitive file.
5. **The 7 `unsafe` sites in `capabilities.rs` (libc shim) lack `// SAFETY:` comments** — would be the highest-signal, lowest-cost fix (one PR, ~7 lines added).
