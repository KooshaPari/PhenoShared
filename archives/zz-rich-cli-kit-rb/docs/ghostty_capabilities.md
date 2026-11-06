# Ghostty Capabilities Audit for rich-cli-kit v0.2

Research-only design doc. No code changes. Target: rich-cli-kit v0.2 roadmap.
Sources cited inline; full list at bottom.

## 1. Executive Summary — Top 5 for v0.2

1. **OSC 8 hyperlinks** (`rck link`) — cheapest, biggest UX win. Agents cite docs, files, PRs as clickable text. One-shot emit, no state. P0.
2. **OSC 52 clipboard write** (`rck copy`) — agent pushes a result into the user's clipboard without asking. P0. Ghostty default is `clipboard-write=allow`.
3. **Kitty keyboard protocol + alt-screen mini-UI** (`rck ask`, `rck pick`) — unlock *interactive* primitives (confirm, multi-choice, single-line input) that degrade to stdin prompts. P0.
4. **OSC 133 semantic prompts emitted by long-running agent tasks** (`rck mark start|end`) — lets Ghostty/WezTerm jump-to-prompt, scroll-to-output, and report exit status visually. P0.
5. **Focus-aware notifications** (`rck notify`, `rck defer`) — CSI ?1004 tells us if the user is looking; if not, hold a summary panel until they return, else emit OSC 9 / BEL. P1 (but cheap).

Secondary but mentioned below: OSC 7 (CWD), OSC 1337 user-var + badge, shader-pack opt-in (focus/success/failure tints), tmux-passthrough wrapping, and width-safe grapheme measurement for the existing panel.

## 2. Features Audit (Track A)

Columns: Feature | Emit | Detect | Agent-UX unlock | Priority.

| Feature | Emit / API | Detect | Agent-UX unlock | Pri |
|---|---|---|---|---|
| **OSC 8 hyperlink** | `ESC ] 8 ; ; URL ESC \ text ESC ] 8 ; ; ESC \` | Env (`TERM_PROGRAM`), terminfo xterm-ghostty; Ghostty supports natively; `link-previews` config. `terminal-features` for tmux. | Clickable "see docs" / "open PR" / file-path links inside agent output, plus link previews in Ghostty. | P0 |
| **OSC 52 clipboard write** | `ESC ] 52 ; c ; <base64> ESC \` | Ghostty default `clipboard-write=allow`; probe not needed. Under tmux requires `allow-passthrough on` and DCS wrap. | Agent emits final result → user ⌘V it anywhere without re-selecting. | P0 |
| **OSC 52 clipboard read** | `ESC ] 52 ; c ; ? ESC \` | `clipboard-read=ask` by default — will prompt. | Low-value for agents; skip. | P3 |
| **OSC 133 A/B/C/D** | `ESC ] 133 ; A ST` (prompt start), `;B` (prompt end / cmd start), `;C` (output start), `;D;<exit>` (output end) | Ghostty ships shell integration for bash/zsh/fish/elvish/nu; supports OSC 133 + click-events + `cl=line` extension. | Agents wrapping long tasks mark boundaries so terminal offers jump-to-prompt, scroll-to-last-output, exit-status color. Complements progress bar. | P0 |
| **Kitty keyboard protocol** | Enable: `CSI > 1 u` (progressive flags). Disable/pop: `CSI < u`. Query: `CSI ? u` → response `CSI ? <flags> u`. | Query above; also `TERM=xterm-ghostty` + `TERM_PROGRAM=ghostty`. Known bug: modifiers+arrows still legacy. | Distinguishes Shift+Enter, Ctrl+Space, paste-vs-keystroke, release events. Enables reliable `rck ask` picker without ncurses. | P0 |
| **Kitty graphics** (current) | APC `G ... ESC \` | already implemented | existing inline image | — |
| **Sixel** | DCS `P q ...` | Ghostty: **will not support**, by design. WezTerm/Konsole/iTerm2 do. | Keep current fallback-to-text; do not invest. | P3 |
| **Focus reporting (CSI ?1004h)** | Enable: `CSI ? 1004 h`. Events: `ESC [ I` (focus in) / `ESC [ O` (focus out). | Enable + wait for any response on first agent-run; Ghostty supports. | Defer notifications while user focused on another window; flush summary OSC 9 bell when they return. | P1 |
| **Bracketed paste** | `CSI ? 2004 h` wraps pastes in `ESC [200~ ... ESC [201~`. | Default in Ghostty. | For `rck ask`: distinguish typed text from pasted multi-line input. | P1 |
| **OSC 7 CWD** | `ESC ] 7 ; file://HOST/PATH ESC \` | Ghostty shell integration emits on cd; config `window-inherit-working-directory`. | Agents can read this (if spawned as child with PTY) to coordinate "operate in the dir the user is in". Low agent-value for us (we're *in* the shell). | P2 |
| **OSC 1337 badge** | `ESC ] 1337 ; SetBadgeFormat = <base64> ESC \` | iTerm2 original; Ghostty implementing gradually (per discussion #11105). Probe by sending + reading device status. | Persistent "agent: running / done / failed" overlay in the window corner. Valuable on iTerm2, partial on Ghostty. | P2 |
| **OSC 1337 user var** | `ESC ] 1337 ; SetUserVar= key = <b64val> ESC \` | Same as badge. | Status machines for external dashboards; low direct user-UX gain. | P3 |
| **OSC 1337 `File=`** | iTerm2 inline image / download trigger. | Ghostty: under discussion (#11105), partial. | Prefer kitty graphics (already shipped). For file-download "save this artifact" UX, P2. | P2 |
| **OSC 9 bell / notify** | `ESC ] 9 ; <msg> ESC \` (ConEmu/Ghostty). Also `BEL` (0x07). Ghostty config `notify-on-command-finish`. | Ghostty supports OSC 9;N-family (see docs/vt/osc/conemu). | Emit push notification when long agent task completes while unfocused. | P1 |
| **Colored / styled underlines** | `CSI 4 : 3 m` (curly), `CSI 58 : 2 : r : g : b m` (underline color). In xterm-ghostty terminfo. | terminfo query `Smulx`, `Setulc`. | Lint-style inline annotation: red-wavy under problems, green-straight under success, inside a plain agent log. Pairs with OSC 8. | P1 |
| **Alternate screen (smcup/rmcup)** | `CSI ? 1049 h` / `l` | Universal. | Any interactive `rck` subcommand (`ask`, `pick`, `live`) enters alt-screen, restores on exit — doesn't scroll away user's log. | P0 (for interactive primitives only) |
| **Mouse reporting (SGR)** | `CSI ? 1006 h`, `CSI ? 1002 h` | Ghostty `mouse-reporting=true` default. | Click-to-select in `rck pick`, click-to-copy in panels. | P2 |
| **Grapheme-cluster width** | Measurement lib, not an escape. | Ghostty does grapheme clustering correctly. | Fix panel right-border misalignment when content has emoji / zwj / flags. Use `unicode-width` + `icu_segmenter`, or query with CPR (`CSI 6n`) to verify. | P1 (bug-fix) |
| **Title set / report** | `OSC 0 ; t ST`, `OSC 2 ; t ST`. Ghostty `title-report` opt-in. | Trivial emit. | Set window title to "agent: building …" during task; restore on exit. | P2 |
| **Cursor shape hint** | `CSI <n> SP q` (DECSCUSR). | Universal. | Switch to bar while in `rck ask`, back to block on exit. | P2 |
| **Shell integration click-events** | OSC 133 `cl=line` (Ghostty). | Ghostty only. | In `rck panel --interactive`, turn log lines into click targets that re-run. Bonus. | P3 |
| **CSI DA / XTVERSION** | `CSI >q` → `DCS>|GhosttyVERSION ST`. | **Best** single detect for Ghostty version. Use before emitting OSC 1337 that Ghostty may not yet implement. | — | Infra for detect. |
| **Tmux DCS passthrough** | Wrap as `ESC P tmux ; ESC <escaped-inner-seq> ESC \` when inside tmux. | `TMUX` env var. | Makes OSC 8, OSC 52, kitty-graphics, OSC 133 survive tmux. Required to not regress. | P0 |
| **Ghostty custom shaders** | User-config only; `custom-shader = path.glsl`. | `ghostty +show-config`. | Not agent-emittable. Ship opt-in pack. See §3. | P2 |

### Feature discovery beyond the prompt list
- **`notify-on-command-finish`** Ghostty native completion notification. Pairs with OSC 133;D. Cheapest way to notify without our own code if shell integration is on.
- **`clipboard-paste-protection`**: be aware — agents emitting multi-line shell commands will trigger the confirm dialog unless wrapped in bracketed paste markers.
- **`link-previews = osc8`**: Ghostty shows preview on hover for OSC 8 links — big UX multiplier for our P0.
- **`iFocus` / `iTimeFocus` shader uniforms**: enable shader-based focus ambient effect without agent involvement.

## 3. Shader Design Doc (Track B)

### Pipeline
- Ghostty accepts GLSL fragment shaders, ShaderToy-compatible.
- On macOS: glslang → SPIR-V → SPIRV-Cross → MSL, compiled at startup.
- Uniforms currently exposed: `iTime`, `iResolution` (vec2 in Ghostty, vec3 on Shadertoy), `iChannel0` (terminal framebuffer texture), `iFocus` (bool-like), `iTimeFocus`, `iMouse`, `iCurrentCursor`, `iCurrentCursorColor`.
- Pipeline is **post-process** on the rendered cell grid; runs every frame at display Hz.
- Multi-shader: list the key multiple times (`custom-shader = a.glsl` then `custom-shader = b.glsl`) and they stack in order. **Metal (macOS) works; OpenGL multi-shader is broken** (issue #4729).
- Performance on M-series: single mid-complexity shader (bloom or CRT) ~free; stacks of 3+ (tft + crt + bloom) visibly warm the GPU but 60 fps holds.

### Config surface
```
# ~/.config/ghostty/config
custom-shader = shaders/focus-vignette.glsl
custom-shader = shaders/agent-tint.glsl
custom-shader-animation = true    # keeps iTime advancing when idle
```

### Community examples
- `0xhckr/ghostty-shaders` — tft, bettercrt, bloom, glitchy, water, retro-terminal
- `thijskok/ghostty-shaders` — CRT variants (amber/green/blue)
- `luiscarlospando/crt-shader-...` — chromatic aberration + glow + scanlines + dot matrix
- `yuxiangcheng2002/ghostty-shader-lab` — starfield, better-crt, retro

### rich-cli-kit "rck-shaders" opt-in pack (proposal)

| Shader | Trigger | Mechanism |
|---|---|---|
| `focus-vignette.glsl` | `iFocus == 0` (user switched away) | Terminal-side, no agent emit. Uses `iTimeFocus` to fade vignette in over 400 ms. |
| `success-tint.glsl` | Transient green wash on OSC 133;D with exit=0 | **Not directly agent-triggerable.** Workaround: agent emits OSC 9 bell; shader reads `iTime` delta since bell? Not exposed. So this is *aspirational* — requires a new uniform. File as Ghostty feature request. |
| `failure-tint.glsl` | Same, red | Same limitation. |
| `progress-pulse.glsl` | Subtle bloom along bottom row | Pure time-based; user enables while they know an agent is working. |
| `agent-active.glsl` | Persistent dim outer ring | Pure config; user toggles via keybind bound to `ghostty +reload-config` equivalent. |

**Honest conclusion**: of our five proposed shaders, only `focus-vignette` and the two time-based ambients work *today*. Success/failure tints **require a new Ghostty uniform** (e.g. `iAgentStatus` OSC). We should (a) ship the three that work, (b) file one upstream RFC proposing a `CSI = <n> #p` "shader broadcast" channel or `OSC 133;D` payload readable from shaders. Until then: use shaders for ambient mood, use OSC 9 / OSC 133 for transient signals.

Shaders are not one-shot agent outputs. We ship them as `rck shader install` (copies files into `~/.config/ghostty/shaders/`) and print the config lines for the user to opt-in.

## 4. Compatibility Matrix

| Feature | Ghostty | kitty | WezTerm | Konsole | Apple Term | tmux (passthrough) |
|---|---|---|---|---|---|---|
| Kitty graphics | ✓ | ✓ | ✓ | — | — | with DCS wrap |
| Sixel | ✗ (by design) | partial | ✓ | ✓ | — | ✓ |
| OSC 8 hyperlink | ✓ (+ preview) | ✓ | ✓ | ✓ | — | ✓ w/ wrap |
| OSC 52 write | ✓ (allow) | ✓ | ✓ | ✓ | ✓ (tiny limit) | needs wrap |
| OSC 133 | ✓ (+ click) | ✓ | ✓ | partial | — | partial |
| Kitty keyboard | ✓ (bugs) | ✓ canonical | ✓ | — | — | passthru |
| Focus (1004) | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Alt screen | all | all | all | all | all | ✓ |
| Custom shaders | ✓ unique | ✗ | ✗ (different) | ✗ | ✗ | n/a |
| Styled underlines | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Grapheme cluster | ✓ | ✓ | ✓ | partial | partial | passthru |

Degradation path: if `TMUX` is set, every APC/OSC emit must DCS-wrap (`ESC P tmux ; …`). If `TERM_PROGRAM` is Apple_Terminal, disable kitty graphics, OSC 8, OSC 133, kitty-kbd; keep OSC 52 (capped) and styled colors.

## 5. Proposed v0.2 Roadmap (8–12 items)

| # | Item | Status | Deps | Rough LOC |
|---|---|---|---|---|
| 1 | `rck link <url> <text>` — OSC 8 emitter | ✅ v0.2 | none | 40 |
| 2 | `rck copy` (stdin → OSC 52) | ✅ v0.2 | none | 60 |
| 3 | `rck task-start / task-end [--exit N]` — OSC 133 A/B/C/D | ✅ v0.2 (renamed from `mark`) | shell detection | 80 |
| 4 | `rck ask`, `rck pick`, `rck input` — alt-screen + kitty-kbd | ✅ v0.2 | kbd probe, term state restore | 450 |
| 5 | Focus-aware `rck notify --defer` (CSI ?1004 + OSC 9) | ⏳ deferred to v0.3 | signal handler, async listener | 180 |
| 6 | Tmux DCS-passthrough wrapper in rck-core emit layer | ✅ v0.2 (gated at `emit`) | detect `TMUX` | 60 |
| 7 | Grapheme-correct width for panel rendering | ✅ v0.2 | `unicode-width` + `unicode-segmentation` | 120 |
| 8 | XTVERSION-based capability cache (TTL 60s) | ⏳ deferred to v0.3 | stdin poll infra already exists | 90 |
| 9 | `rck title set/restore` + cursor-shape hints | partial (title emitted on `task-start --id`) | none | 40 |
| 10 | `rck shader install <name>` — ship focus-vignette + two ambients | ✅ v0.2 (`focus-vignette`, `progress-pulse`, `agent-active`) | bundled assets | 120 |
| 11 | Styled-underline helpers (`rck annotate --curly --color red`) | ⏳ deferred to v0.3 | terminfo | 70 |
| 12 | MCP surface for all of the above (`rich.emit_hyperlink`, `rich.copy_to_clipboard`, `rich.task_marker`, `rich.ask`, `rich.pick`, `rich.input_line`) | ✅ v0.2 | FastMCP existing | 200 |

Total: ~1,500 LOC Rust + 200 LOC Python MCP wrappers. Dependencies add: `unicode-width`, `icu_segmenter` (or `unicode-segmentation`), maybe `crossterm` for kbd input decode (or hand-roll to stay minimal).

Sequencing: 1, 2, 6, 8 (infra) → 3, 9, 11 (one-shot emitters) → 7 (panel fix) → 4, 5 (interactive + async) → 10 (shader pack) → 12 (MCP).

## 6. Rejected / Out-of-Scope

- **Sixel encoder.** Ghostty will never support it; WezTerm/Konsole users are already covered by our "text summary" fallback. Not worth the encoder complexity.
- **OSC 52 clipboard read.** Ghostty prompts; noisy UX; agents rarely need to *read* user clipboard.
- **OSC 1337 File= upload.** Kitty graphics already covers inline images; file-download is niche for agent output.
- **AppleScript / Ghostty scripting API** (discussion #2353). Not standardized, not stable, macOS-only.
- **Full TUI widget library.** Out of scope — we stay "one-shot + minimal interactive". Users wanting tables/trees should use `ratatui`.
- **Agent-triggered transient shaders.** Impossible without a new Ghostty uniform; file RFC upstream, don't pretend we can do it now.
- **OSC 7 publishing from rck.** We're not a shell; Ghostty shell integration owns this.
- **Badge writer as P0.** Ghostty OSC 1337 support is partial; rework when status is clearer. Keep at P2.

---

## Sources

- https://ghostty.org/docs/features
- https://ghostty.org/docs/config/reference
- https://ghostty.org/docs/help/terminfo
- https://ghostty.org/docs/vt/concepts/sequences
- https://ghostty.org/docs/vt/osc/52
- https://ghostty.org/docs/vt/osc/conemu
- https://ghostty.org/docs/install/release-notes/1-3-0
- https://deepwiki.com/ghostty-org/ghostty/9.3-osc-133-prompt-marking
- https://deepwiki.com/ghostty-org/ghostty/9-shell-integration
- https://deepwiki.com/ghostty-org/ghostty/3.4-osc-commands-and-protocols
- https://github.com/ghostty-org/ghostty/discussions/9408 (shader uniforms)
- https://github.com/ghostty-org/ghostty/discussions/6901 (cursor uniforms)
- https://github.com/ghostty-org/ghostty/discussions/11105 (OSC 1337 File=)
- https://github.com/ghostty-org/ghostty/discussions/5886 (Sixel stance)
- https://github.com/ghostty-org/ghostty/issues/4729 (OpenGL multi-shader)
- https://github.com/ghostty-org/ghostty/discussions/9368 (kitty-kbd)
- https://sw.kovidgoyal.net/kitty/keyboard-protocol/
- https://sw.kovidgoyal.net/kitty/graphics-protocol/
- https://mitchellh.com/writing/ghostty-devlog-005
- https://github.com/0xhckr/ghostty-shaders
- https://github.com/thijskok/ghostty-shaders
- https://github.com/luiscarlospando/crt-shader-with-chromatic-aberration-glow-scanlines-dot-matrix
- https://github.com/yuxiangcheng2002/ghostty-shader-lab
- https://catskull.net/fun-with-ghostty-shaders.html
- https://martinemde.com/blog/ghostty-focus-shaders
- https://tmuxai.dev/tmux-allow-passthrough/
- https://github.com/tmux/tmux/issues/3064 (OSC 133 in tmux)
- https://iterm2.com/3.0/documentation-escape-codes.html
- https://blog.fsck.com/releases/2026/02/26/terminal-keyboard-protocol/
