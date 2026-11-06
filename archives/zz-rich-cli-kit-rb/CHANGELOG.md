# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## 📚 Documentation
- Docs(rich-cli-kit): Ghostty features + shaders research for v0.2

Standalone research doc enumerating every Ghostty capability that could
sharpen agent-emitted terminal output, plus a shader-pipeline deep dive.
Organized as exec summary + features audit + shader design + compatibility
matrix + v0.2 roadmap + rejected-ideas.

Key findings:

- Shader track is less agent-actionable than it first seemed — the three
  ambient shaders (focus-vignette, progress-pulse, agent-active) work on
  Ghostty's current time+iFocus uniforms; transient success/failure tints
  require a new agent-status uniform that doesn't exist upstream yet.
  Ship the three that work as opt-in `rck shader install`; file upstream
  RFC for agent-status; don't overpromise.
- OpenGL multi-shader is broken (ghostty#4729); shader pack must be Metal
  only (macOS) or single-stack elsewhere.
- Tmux DCS passthrough wrapping is P0 — without it, OSC 8 / 52 / 133 all
  silently fail in tmux. Blocks the rest of v0.2.
- Ghostty has explicit wontfix on Sixel (ghostty#5886). Demote "Sixel
  stretch goal" in README.
- Panel width likely buggy on emoji/ZWJ content; needs grapheme-cluster
  segmentation (~120 LOC fix budget).

Top-5 for v0.2 (full 12-item roadmap with LOC estimates in §5 of doc):
  1. OSC 8 hyperlinks in panels + progress labels
  2. OSC 52 copy-to-clipboard (agent → user ⌘V)
  3. Kitty keyboard protocol + alt-screen for interactive primitives
     (`rck ask`, `rck pick`, `rck input`)
  4. OSC 133 semantic prompt + task markers (jump-to-agent-output)
  5. Focus reporting (CSI ?1004) for deferred notifications

Sources cited inline.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`daaf53a`)
## ✨ Features
- Feat(rich-cli-kit): v0.2 — tmux passthrough, OSC 8/52/133, interactive primitives, shader pack

Top-5 additions from docs/ghostty_capabilities.md v0.2 roadmap. 44 tests
pass / 0 fail.

Core additions (rck-core):
- emit.rs — central sink that wraps every outbound sequence with the tmux
  DCS passthrough (\ePtmux;...\e\\) when TMUX env is set. Unblocks all
  downstream OSC features for the tmux cohort.
- spans.rs — Vec<Span> primitive where Span::Link(url, text) | Span::Text(s)
  lets labels mix clickable + plain segments in panels, progress, lists.
- width.rs — grapheme-cluster correct width via unicode-segmentation +
  unicode-width. Fixes emoji/ZWJ panel misalignment (~120 LOC).
- interactive.rs — alt-screen + kitty-keyboard-protocol primitives:
  rck ask (yes/no + arrows + enter), rck pick (list picker), rck input
  (readline). Trap SIGINT/SIGTERM to restore terminal state. Degrade on
  non-graphics terminals to plain stdin read.
- shader.rs — opt-in Metal-only user-shader installer: rck shader install
  {focus-vignette,progress-pulse,agent-active} copies into Ghostty's
  config-dir + prints opt-in snippet for the user's config.toml.

New CLI commands: rck link, rck copy, rck task-start, rck task-end,
rck ask, rck pick, rck input, rck shader list|install|uninstall.

New MCP tools exposed: rich.emit_hyperlink, rich.copy_to_clipboard,
rich.task_marker, rich.ask, rich.pick, rich.input.

shaders/ pack:
- focus-vignette.glsl — subtle vignette when terminal is focused
- progress-pulse.glsl — soft bloom synced to iTime during long ops
- agent-active.glsl — persistent ambient gradient while agent holds
  the terminal

README updated with tmux.conf note (set -g allow-passthrough on).
docs/ghostty_capabilities.md roadmap items 1-5 checked off; remaining
items 6-12 deferred per doc.

Skill ~/.claude/skills/rich-cli/SKILL.md updated with the new tool names
so agents discover them.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`78fda86`)
- Feat(rich-cli-kit): kitty-graphics adapter — images, progress, panels inline

Standalone Rust workspace + Python FastMCP server for emitting inline images,
progress bars, and status panels via the kitty-graphics protocol. Supports
Ghostty, kitty, WezTerm; degrades to ASCII/plain-text elsewhere.

Detection (rck-core::capabilities):
- Env-first: TERM_PROGRAM=Ghostty, TERM=xterm-ghostty, KITTY_WINDOW_ID,
  WEZTERM_EXECUTABLE, KONSOLE_VERSION, COLORTERM=truecolor
- TTY query fallback: sends _Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA + \x1b[c,
  polls stdin 150ms via poll(2), matches _Gi=31;OK response
- Never emits APC when stdout isn't a TTY

Encoder quirks worth remembering:
- q=2 essential in one-shot CLI mode (else response lands on next prompt)
- First APC frame carries format keys (a=T,f=100,q=2) AND m=1; middle frames
  only m=1; last frame m=0 — spec reads ambiguous but it's "both keys on
  frame one"
- Chunks split at 4096 base64 bytes (already multiple of 4)
- JPEG→PNG re-encode via image crate avoids f=24/f=32 pixel-stride complexity

Surfaces:
- rck CLI (clap): detect | image | progress | panel | demo
- MCP server (FastMCP): rich.emit_image, rich.emit_progress, rich.emit_panel
  — each returns {rendered: bool, fallback_text} so callers can switch
  output path per capability
- ~/.claude/skills/rich-cli/SKILL.md globally registered

Tests: 10 Rust (encoder byte-equal to spec, progress clamp, panel styles,
detect smoke) + 5 Python (MCP subprocess integration).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`f8df183`)
## 🔨 Other
- Chore(deps): align tokio + serde to org baseline (phenotype-versions.toml)

- tokio: unified to 1.39
- serde: unified to 1.0
- Verified: cargo check passed

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com> (`353b4aa`)
- Test(smoke): seed minimal smoke test — proves harness works (`432f36a`)
- Chore(ci): adopt phenotype-tooling quality-gate + fr-coverage (`2675c85`)
