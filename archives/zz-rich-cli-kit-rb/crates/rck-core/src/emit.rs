//! Low-level OSC/APC/DCS emit primitives with tmux passthrough wrapping.
//!
//! Every outbound OSC/APC sequence destined for a terminal running under tmux
//! must be DCS-wrapped so tmux forwards it to the outer terminal. This module
//! centralizes that policy so hyperlinks, clipboard, task markers, panels, and
//! progress labels all benefit automatically.
//!
//! Tmux passthrough (requires `tmux set -g allow-passthrough on`):
//!
//! ```text
//! ESC P tmux ; <inner with every ESC doubled> ESC \
//! ```
//!
//! Reference: <https://tmuxai.dev/tmux-allow-passthrough/>

use base64::Engine;

/// Return whether the current process is running inside tmux.
pub fn in_tmux() -> bool {
    std::env::var("TMUX").is_ok()
}

/// Wrap a raw escape sequence for tmux DCS passthrough if needed.
///
/// If `TMUX` is unset the input is returned unchanged. Otherwise every ESC
/// (`0x1b`) byte inside `inner` is doubled (`ESC ESC`) and the whole thing is
/// framed as `ESC P tmux ; <escaped> ESC \`.
///
/// Idempotency: calling this on an already-wrapped sequence will wrap it again
/// (nested). Callers should wrap exactly once at the `emit` boundary.
pub fn wrap_for_tmux(inner: &str) -> String {
    wrap_for_tmux_with(inner, in_tmux())
}

/// Like [`wrap_for_tmux`] but with explicit tmux detection, for testing.
pub fn wrap_for_tmux_with(inner: &str, in_tmux: bool) -> String {
    if !in_tmux {
        return inner.to_string();
    }
    let mut out = String::with_capacity(inner.len() + 8);
    out.push_str("\x1bPtmux;");
    for ch in inner.chars() {
        if ch == '\x1b' {
            out.push('\x1b');
            out.push('\x1b');
        } else {
            out.push(ch);
        }
    }
    out.push_str("\x1b\\");
    out
}

/// Emit an OSC 8 hyperlink: `ESC ] 8 ; ; URL ESC \ TEXT ESC ] 8 ; ; ESC \`.
///
/// If `hyperlinks` is false, returns `text` unchanged. When inside tmux the
/// *hyperlink escape sequences* (but not the surrounding text) are DCS-wrapped
/// so tmux forwards them to the outer terminal.
pub fn emit_hyperlink(hyperlinks: bool, in_tmux_val: bool, url: &str, text: &str) -> String {
    if !hyperlinks {
        return text.to_string();
    }
    let open = format!("\x1b]8;;{url}\x1b\\");
    let close = "\x1b]8;;\x1b\\".to_string();
    let open_w = wrap_for_tmux_with(&open, in_tmux_val);
    let close_w = wrap_for_tmux_with(&close, in_tmux_val);
    format!("{open_w}{text}{close_w}")
}

/// Emit an OSC 52 clipboard-write sequence. Base64-encodes `content`.
/// Returns empty string if the terminal does not support clipboard.
pub fn emit_clipboard(clipboard: bool, in_tmux_val: bool, content: &str) -> String {
    if !clipboard {
        return String::new();
    }
    let b64 = base64::engine::general_purpose::STANDARD.encode(content.as_bytes());
    let seq = format!("\x1b]52;c;{b64}\x1b\\");
    wrap_for_tmux_with(&seq, in_tmux_val)
}

/// OSC 133 semantic prompt phases.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskPhase {
    /// `OSC 133;A` — prompt start.
    PromptStart,
    /// `OSC 133;B` — prompt end / user command begins.
    PromptEnd,
    /// `OSC 133;C` — command start (output begins).
    CommandStart,
    /// `OSC 133;D;<exit>` — command end with exit code.
    CommandEnd(i32),
}

/// Emit an OSC 133 task marker. Returns empty string if not supported.
pub fn emit_task_markers(task_markers: bool, in_tmux_val: bool, phase: TaskPhase) -> String {
    if !task_markers {
        return String::new();
    }
    let seq = match phase {
        TaskPhase::PromptStart => "\x1b]133;A\x1b\\".to_string(),
        TaskPhase::PromptEnd => "\x1b]133;B\x1b\\".to_string(),
        TaskPhase::CommandStart => "\x1b]133;C\x1b\\".to_string(),
        TaskPhase::CommandEnd(code) => format!("\x1b]133;D;{code}\x1b\\"),
    };
    wrap_for_tmux_with(&seq, in_tmux_val)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wrap_is_noop_without_tmux() {
        let s = "\x1b]8;;https://x\x1b\\";
        assert_eq!(wrap_for_tmux_with(s, false), s);
    }

    #[test]
    fn wrap_doubles_escapes_in_tmux() {
        let s = "\x1b]8;;x\x1b\\";
        let w = wrap_for_tmux_with(s, true);
        assert!(w.starts_with("\x1bPtmux;"));
        assert!(w.ends_with("\x1b\\"));
        // Every inner ESC must be doubled.
        // Original has 2 ESCs; wrapped inner should have 4 ESCs between the
        // leading `\x1bPtmux;` and trailing `\x1b\\`.
        let inner = &w["\x1bPtmux;".len()..w.len() - 2];
        let esc_count = inner.chars().filter(|c| *c == '\x1b').count();
        assert_eq!(esc_count, 4);
    }

    #[test]
    fn wrap_nested_escapes_double_correctly() {
        // Simulate an APC sequence containing multiple ESCs.
        let s = "\x1b_Gf=100;AAAA\x1b\\";
        let w = wrap_for_tmux_with(s, true);
        let inner = &w["\x1bPtmux;".len()..w.len() - 2];
        // Original had 2 ESCs; doubled = 4.
        assert_eq!(inner.chars().filter(|c| *c == '\x1b').count(), 4);
    }

    #[test]
    fn hyperlink_plain_when_unsupported() {
        let s = emit_hyperlink(false, false, "https://x", "click");
        assert_eq!(s, "click");
    }

    #[test]
    fn hyperlink_emits_osc8() {
        let s = emit_hyperlink(true, false, "https://x", "click");
        assert!(s.contains("\x1b]8;;https://x\x1b\\"));
        assert!(s.contains("click"));
        assert!(s.ends_with("\x1b]8;;\x1b\\"));
    }

    #[test]
    fn hyperlink_wraps_in_tmux() {
        let s = emit_hyperlink(true, true, "https://x", "click");
        assert!(s.starts_with("\x1bPtmux;"));
        // Plain text still visible in the output.
        assert!(s.contains("click"));
    }

    #[test]
    fn hyperlink_empty_text() {
        let s = emit_hyperlink(true, false, "https://x", "");
        assert!(s.contains("https://x"));
    }

    #[test]
    fn clipboard_b64_encodes() {
        let s = emit_clipboard(true, false, "hello");
        // base64 of "hello" = "aGVsbG8="
        assert!(s.contains("aGVsbG8="));
        assert!(s.starts_with("\x1b]52;c;"));
    }

    #[test]
    fn clipboard_empty_when_unsupported() {
        assert_eq!(emit_clipboard(false, false, "x"), "");
    }

    #[test]
    fn clipboard_wraps_in_tmux() {
        let s = emit_clipboard(true, true, "hi");
        assert!(s.starts_with("\x1bPtmux;"));
        assert!(s.ends_with("\x1b\\"));
    }

    #[test]
    fn task_marker_prompt_start() {
        let s = emit_task_markers(true, false, TaskPhase::PromptStart);
        assert_eq!(s, "\x1b]133;A\x1b\\");
    }

    #[test]
    fn task_marker_command_end_carries_exit() {
        let s = emit_task_markers(true, false, TaskPhase::CommandEnd(2));
        assert_eq!(s, "\x1b]133;D;2\x1b\\");
    }

    #[test]
    fn task_marker_empty_when_unsupported() {
        assert_eq!(emit_task_markers(false, false, TaskPhase::PromptStart), "");
    }
}
