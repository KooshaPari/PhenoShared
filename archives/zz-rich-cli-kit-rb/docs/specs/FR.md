# Functional Requirements — rich-cli-kit

This document captures the functional requirements (FRs) for the rich-cli-kit project, which provides inline rich terminal output capabilities via the kitty graphics protocol with graceful ASCII fallback.

## FR-001: Terminal Capability Detection

**ID:** FR-001  
**Component:** rck-core/capabilities  
**Priority:** P0 (Critical)

### Description
The system shall detect terminal capabilities through environment variable inspection and optional TTY query, determining support for:
- Kitty graphics protocol
- Sixel graphics
- Truecolor (24-bit color)
- Unicode width support
- OSC 8 hyperlinks
- OSC 52 clipboard write
- OSC 133 task markers
- Kitty keyboard protocol
- tmux passthrough requirements

### Acceptance Criteria
- AC-001.1: System correctly identifies Ghostty, kitty, WezTerm, iTerm2, Konsole, and generic terminals via `TERM_PROGRAM`, `TERM`, and related environment variables
- AC-001.2: When stdout is a TTY and environment signals are inconclusive, system performs kitty-graphics query with 150ms timeout
- AC-001.3: When stdout is not a TTY (pipe/redirect), graphics capability is forced to false
- AC-001.4: Detection returns a `Capabilities` struct with all fields populated
- AC-001.5: Detection never panics and always returns a valid result

### Rationale
Accurate capability detection is the foundation of graceful degradation. Without it, the system would emit graphics sequences to incompatible terminals or fail to use advanced features when available.

---

## FR-002: Kitty Graphics Protocol Encoding

**ID:** FR-002  
**Component:** rck-core/encoder  
**Priority:** P0 (Critical)

### Description
The system shall encode PNG images into kitty graphics protocol APC sequences following the specification at <https://sw.kovidgoyal.net/kitty/graphics-protocol/>, supporting both single-frame and multi-chunk transmission.

### Acceptance Criteria
- AC-002.1: PNG bytes are base64-encoded and transmitted with control keys `a=T,f=100,q=2`
- AC-002.2: Single images under 4096 base64 bytes are transmitted in one APC frame
- AC-002.3: Larger images are split into multiple chunks, each ≤4096 bytes
- AC-002.4: Multi-chunk transmission uses `m=1` on non-final frames and `m=0` on the last frame
- AC-002.5: First frame carries all format keys (`a=T,f=100,q=2`), subsequent frames carry only `m` key
- AC-002.6: Each chunk length is a multiple of 4 to preserve base64 alignment
- AC-002.7: Output ends with APC terminator `ESC \` and a trailing newline

### Rationale
The kitty graphics protocol is the primary mechanism for inline image rendering. Correct encoding ensures compatibility with Ghostty, kitty, and WezTerm terminals.

---

## FR-003: Progress Bar Rendering

**ID:** FR-003  
**Component:** rck-core/progress  
**Priority:** P1 (High)

### Description
The system shall render one-shot progress bars with configurable style (Unicode blocks or ASCII), clamped ratio (0.0-1.0), and optional label text.

### Acceptance Criteria
- AC-003.1: Progress bars accept a ratio (f32) and clamp it to [0.0, 1.0]
- AC-003.2: Unicode block style (`ProgressStyle::Blocks`) renders using characters █, ▏-▊
- AC-003.3: ASCII style (`ProgressStyle::Ascii`) renders using `[=====>    ]` format
- AC-003.4: Percentage is displayed as integer (e.g., "42%")
- AC-003.5: Optional label is rendered to the right of the progress bar
- AC-003.6: Progress bar width adapts to terminal width when available
- AC-003.7: tmux passthrough wrapping is applied when `TMUX` environment variable is set

### Rationale
Progress bars provide visual feedback for long-running operations. Supporting both Unicode and ASCII ensures compatibility across terminal capabilities.

---

## FR-004: Status Panel Rendering

**ID:** FR-004  
**Component:** rck-core/panel  
**Priority:** P1 (High)

### Description
The system shall render titled status panels with configurable border styles (rounded, square, ASCII) and multi-line body content.

### Acceptance Criteria
- AC-004.1: Panels accept a title, array of body lines, and border style
- AC-004.2: Rounded border style uses Unicode box-drawing characters (╭─╮│╰─╯)
- AC-004.3: Square border style uses Unicode box-drawing characters (┌─┐│└─┘)
- AC-004.4: ASCII border style uses ASCII characters (+-+||+-+)
- AC-004.5: Panel width adapts to the longest line or terminal width
- AC-004.6: Title is centered in the top border with padding
- AC-004.7: Body lines are left-aligned with padding
- AC-004.8: tmux passthrough wrapping is applied when `TMUX` environment variable is set

### Rationale
Status panels provide structured output for build status, test results, and system information. Multiple border styles ensure compatibility with terminals lacking Unicode support.

---

## FR-005: OSC Sequence Emission

**ID:** FR-005  
**Component:** rck-core/emit  
**Priority:** P1 (High)

### Description
The system shall emit OSC (Operating System Command) sequences for hyperlinks (OSC 8), clipboard write (OSC 52), and task markers (OSC 133), with automatic tmux DCS passthrough wrapping when running inside tmux.

### Acceptance Criteria
- AC-005.1: OSC 8 hyperlinks follow format `ESC ]8;;<url>ESC \<text>ESC ]8;;ESC \`
- AC-005.2: OSC 52 clipboard write encodes content as base64 and emits `ESC ]52;c;<base64>ESC \`
- AC-005.3: OSC 133 task markers emit sequences for prompt start (A), command start (C), and command end (D with exit code)
- AC-005.4: When `TMUX` environment variable is set, all OSC sequences are wrapped in DCS passthrough: `ESC Ptmux;ESC<seq>ESC \`
- AC-005.5: Capability flags control whether sequences are emitted (no-op if unsupported)
- AC-005.6: Empty strings are returned for unsupported capabilities rather than failing

### Rationale
OSC sequences enable modern terminal features like clickable links, cross-platform clipboard integration, and semantic prompt markers. tmux passthrough ensures these sequences reach the outer terminal.

---

## FR-006: Interactive Input Primitives

**ID:** FR-006  
**Component:** rck-core/interactive  
**Priority:** P2 (Medium)

### Description
The system shall provide alt-screen interactive primitives for yes/no confirmation (`ask`), single-choice selection (`pick`), and single-line text input (`input`), with graceful fallback to plain stdin when TTY is unavailable.

### Acceptance Criteria
- AC-006.1: `ask` function displays a yes/no prompt and returns `Outcome::Selected(bool)` or `Outcome::Cancelled`
- AC-006.2: `pick` function displays a list of choices with arrow-key navigation and returns `Outcome::Selected(String)` or `Outcome::Cancelled`
- AC-006.3: `input` function displays a single-line input prompt and returns `Outcome::Selected(String)` or `Outcome::Cancelled`
- AC-006.4: When stdout is not a TTY, functions fall back to plain stdin reading
- AC-006.5: Interactive mode uses alt-screen buffer and restores original screen on exit
- AC-006.6: Kitty keyboard protocol is enabled for enhanced key handling when supported
- AC-006.7: ESC key triggers cancellation in all interactive modes

### Rationale
Interactive primitives enable agent-driven workflows requiring user confirmation or input. Alt-screen prevents pollution of terminal history, while stdin fallback ensures functionality in non-interactive contexts.

---

## FR-007: Image Data Handling

**ID:** FR-007  
**Component:** rck-core/image_data  
**Priority:** P1 (High)

### Description
The system shall load images from PNG and JPEG files, re-encode to PNG format for protocol transmission, and provide alt-text metadata support.

### Acceptance Criteria
- AC-007.1: System loads PNG and JPEG files via the `image` crate
- AC-007.2: JPEG inputs are re-encoded to PNG before transmission
- AC-007.3: Loaded images provide width, height, PNG bytes, and optional alt-text
- AC-007.4: Loading errors (file not found, invalid format) return `anyhow::Error` with context
- AC-007.5: Alt-text is used in fallback text summary when graphics are unavailable

### Rationale
PNG-only transmission simplifies the encoder (avoiding per-format quirks of f=24/f=32). Re-encoding JPEG to PNG is acceptable for CLI use cases where latency is not critical.

---

## FR-008: Shader Management

**ID:** FR-008  
**Component:** rck-core/shader  
**Priority:** P3 (Low)

### Description
The system shall bundle GLSL shader files and provide commands to list and install them into Ghostty's shader directory.

### Acceptance Criteria
- AC-008.1: Bundled shaders are embedded at compile time
- AC-008.2: `rck shader list` command prints all bundled shader names
- AC-008.3: `rck shader install <name>` copies the shader to `~/.config/ghostty/shaders/` (or user-specified directory)
- AC-008.4: Install command prints usage instructions for `~/.config/ghostty/config`
- AC-008.5: Install fails gracefully if the shader name is not found

### Rationale
Bundled shaders provide a convenience feature for Ghostty users. This is a low-priority enhancement that improves user experience without being critical to core functionality.

---

## Traceability

See `docs/specs/TRACEABILITY.md` for test-to-FR mappings.

---

**Document Status:** Active  
**Last Updated:** 2026-06-15  
**Version:** 1.0
