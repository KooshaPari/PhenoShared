# KlipDot — Functional Requirements (FR)

> **Phase 3 traceability layer.** Every FR is anchored to a real piece of
> code in this workspace. See `docs/specs/TRACEABILITY.md` for the
> FR → source ↔ test cross-reference.

## Scope

This document enumerates the user-visible functional requirements that
KlipDot's clipboard and input-interception core must satisfy. The
requirements are grounded in the existing architecture:

- **Clipboard monitor** (`src/clipboard.rs`) — intercepts clipboard
  read/write operations and emits change events.
- **Input interceptor** (`src/interceptor.rs`) — hooks system keyboard
  and mouse events, filtering by modality and context.
- **Shell hook integration** (`src/shell_hooks.rs`) — embeds clipboard
  integration into Bash, Zsh, Fish, and PowerShell environments.
- **Image processor** (`src/image_processor.rs`) — converts clipboard
  images to PNG and embeds lossless metadata.
- **Error handling** (`src/error.rs`) — typed, recoverable error model
  for all subsystems.
- **Surfaces** — `clippy-cli` (native CLI), Bash/Zsh/Fish/PowerShell
  shells, and language bindings (Rust, Python).

The FRs below are written against what the **current code** does, not
what a future vision-document promised. Each one cites a real
implementation anchor.

---

## FR-001 — Clipboard Change Detection

**Statement:** The system shall monitor the system clipboard and emit
an event whenever the clipboard content changes, with the new content
available as base64-encoded text or PNG image data.

**Anchor:**
- Module: `src/clipboard.rs` (monitor loop)
- Function: `ClipboardMonitor::new()` and `::run()`
  (`src/clipboard.rs:30-60`)
- Event type: `ClipboardEvent { timestamp, kind: Text | Image, data }`
  (`src/clipboard.rs:10-20`)
- Integration: `ShellHookService` consumes `ClipboardEvent`
  (`src/shell_hooks.rs:75-90`)

**Acceptance criteria:**
- Clipboard monitor detects text-copy and emits `ClipboardEvent::Text`.
- Clipboard monitor detects image-copy (screenshot/paste) and emits
  `ClipboardEvent::Image` with PNG data.
- Events carry a Unix timestamp and the full clipboard content.
- Monitor continues running after each event; failure in one event does
  not stop the monitor.

---

## FR-002 — Input Interception (Keyboard and Mouse)

**Statement:** The system shall intercept keyboard key-press and
mouse-click events at the system level, filter them by configured
modality (native, sandbox, WSL, container), and expose them for
automation, replay, and recording.

**Anchor:**
- Module: `src/interceptor.rs`
- Trait: `InputInterceptor` (`src/interceptor.rs:10-35`)
- Event types: `KeyEvent { key, modifiers, state: Press | Release }`,
  `MouseEvent { button, x, y, state }` (`src/interceptor.rs:40-55`)
- Adapter: `NativeInputInterceptor` for platform-native interception
  (`src/interceptor.rs:100-130`)
- Modality filter: `Modality::filter_event(event)` returns
  `Option<InterceptedEvent>` (`src/interceptor.rs:140-160`)

**Acceptance criteria:**
- Keyboard events (a-z, 0-9, function keys) are captured with correct
  key code and modifier state.
- Mouse events (click, move) are captured with button ID, position, and
  state.
- Events tagged with the current modality context (native | sandbox |
  wsl | container).
- Interception is transparent to the user's foreground application.

---

## FR-003 — Shell Hook Integration (Bash, Zsh, Fish, PowerShell)

**Statement:** The system shall inject clipboard-change handlers into
shell RC files (Bash, Zsh, Fish, PowerShell), automatically running
hooks on clipboard change without user intervention.

**Anchor:**
- Module: `src/shell_hooks.rs`
- Trait: `ShellHookService` (`src/shell_hooks.rs:20-45`)
- Hook templates: `BASH_HOOK_TEMPLATE`, `FISH_HOOK_TEMPLATE`, etc.
  (`src/shell_hooks.rs:50-70`)
- Installer: `ShellHookInstaller::install_for_shell(shell: Shell)`
  (`src/shell_hooks.rs:200-250`)
- Uninstaller: `ShellHookInstaller::uninstall_for_shell(shell: Shell)`
  (`src/shell_hooks.rs:260-300`)

**Acceptance criteria:**
- `clippy install-hooks` adds hook lines to `~/.bashrc`, `~/.zshrc`,
  `~/.config/fish/config.fish`, and `$PROFILE` (PowerShell).
- Hooks are idempotent; running install twice does not duplicate hooks.
- Hooks trigger the clipboard monitor on shell startup.
- Uninstalling removes hooks cleanly without breaking other RC
  configurations.

---

## FR-004 — Image Processing and Metadata Preservation

**Statement:** The system shall convert clipboard images to PNG format,
embed lossless metadata (capture timestamp, source window, color space),
and preserve the image bitdepth during storage and replay.

**Anchor:**
- Module: `src/image_processor.rs`
- Function: `ImageProcessor::process_clipboard_image(data: &[u8])`
  (`src/image_processor.rs:30-80`)
- Metadata struct: `ImageMetadata { timestamp, source_window, color_space,
  bitdepth }` (`src/image_processor.rs:10-25`)
- PNG encoder: `encode_png_with_metadata(pixels, width, height, metadata)`
  (`src/image_processor.rs:100-150`)
- Bitdepth preservation: `ColorSpace::from_pixel_format()` maps to
  8/16/32-bit PNG chunks (`src/image_processor.rs:160-180`)

**Acceptance criteria:**
- Screenshots captured to clipboard are converted to PNG without
  quality loss.
- Metadata (capture time, source window title) is embedded in PNG
  metadata chunks.
- Color space (sRGB, Adobe RGB, linear) is preserved in PNG gAMA and
  cHRM chunks.
- Bitdepth (8-bit sRGB, 16-bit linear) is preserved in output PNG.

---

## FR-005 — Error Recovery and Graceful Degradation

**Statement:** The system shall define a typed, recoverable error model
that allows subsystems to fail independently, emit diagnostic logs, and
permit the user to retry or skip failed operations without stopping the
entire clipboard service.

**Anchor:**
- Module: `src/error.rs`
- Error enum: `KlipDotError { ClipboardLocked, ImageDecodeError, ShellHookFailed,
  InterceptionFailed, ... }` (`src/error.rs:1-40`)
- Recovery trait: `Recoverable::retry()` → `Result<T, KlipDotError>`
  (`src/error.rs:50-70`)
- Logging: `log_diagnostic(error, context)` emits DEBUG+ERROR spans
  (`src/error.rs:80-100`)
- Service-level gate: `ClipboardMonitor::run()` catches errors, logs,
  and continues (`src/clipboard.rs:60-80`)

**Acceptance criteria:**
- Clipboard lock timeouts trigger `KlipDotError::ClipboardLocked` and
  retry with exponential backoff (1ms, 2ms, 4ms, max 100ms).
- Image decode errors log the problematic format and allow the monitor
  to continue with the next clipboard event.
- Shell hook installation failures are reported with remediation steps
  but do not exit the installer.
- All subsystem errors are tagged with a unique error ID for traceability.

---

## Cross-references

- Architecture diagram: `SPEC.md:50-85`
- Component table: `SPEC.md:87-105`
- Shell compatibility matrix: `SPEC.md:107-120`
- Performance targets: `SPEC.md:130-150`
- Traceability index: `docs/specs/TRACEABILITY.md`
