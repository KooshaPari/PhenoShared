//! Integration tests for OSC sequence emission and tmux passthrough
//! Traces to: FR-005

use rck_core::{emit_clipboard, emit_hyperlink, emit_task_markers, in_tmux, wrap_for_tmux_with, TaskPhase};

/// Test OSC 8 hyperlink sequence format
/// Traces to: FR-005 (AC-005.1)
#[test]
fn test_osc8_hyperlink_format() {
    let s = emit_hyperlink(true, false, "https://example.com", "click here");
    // Must open with ESC ]8;;<url>ESC \
    assert!(s.contains("\x1b]8;;https://example.com\x1b\\"), "should contain OSC 8 open sequence");
    // Must close with ESC ]8;;ESC \
    assert!(s.ends_with("\x1b]8;;\x1b\\"), "should end with OSC 8 close sequence");
    // Text must appear between the sequences
    assert!(s.contains("click here"), "should contain visible link text");
}

/// Test that hyperlink falls back to plain text when unsupported
/// Traces to: FR-005 (AC-005.5, AC-005.6)
#[test]
fn test_osc8_unsupported_returns_plain_text() {
    let s = emit_hyperlink(false, false, "https://example.com", "click here");
    assert_eq!(s, "click here", "should return plain text when hyperlinks unsupported");
    assert!(!s.contains("\x1b"), "should not contain any escape sequences");
}

/// Test OSC 52 clipboard write base64 encoding
/// Traces to: FR-005 (AC-005.2)
#[test]
fn test_osc52_clipboard_base64() {
    let s = emit_clipboard(true, false, "hello world");
    // Sequence must start with ESC ]52;c;
    assert!(s.starts_with("\x1b]52;c;"), "should start with OSC 52 sequence");
    // base64("hello world") = "aGVsbG8gd29ybGQ="
    assert!(s.contains("aGVsbG8gd29ybGQ="), "should contain base64-encoded content");
    assert!(s.ends_with("\x1b\\"), "should end with ST");
}

/// Test that clipboard returns empty string when unsupported
/// Traces to: FR-005 (AC-005.5, AC-005.6)
#[test]
fn test_osc52_empty_when_unsupported() {
    let s = emit_clipboard(false, false, "hello");
    assert_eq!(s, "", "should return empty string when clipboard unsupported");
}

/// Test OSC 133 task marker sequences
/// Traces to: FR-005 (AC-005.3)
#[test]
fn test_osc133_task_markers() {
    // Prompt start: A
    let s = emit_task_markers(true, false, TaskPhase::PromptStart);
    assert_eq!(s, "\x1b]133;A\x1b\\", "prompt start should emit OSC 133;A");

    // Prompt end: B
    let s = emit_task_markers(true, false, TaskPhase::PromptEnd);
    assert_eq!(s, "\x1b]133;B\x1b\\", "prompt end should emit OSC 133;B");

    // Command start: C
    let s = emit_task_markers(true, false, TaskPhase::CommandStart);
    assert_eq!(s, "\x1b]133;C\x1b\\", "command start should emit OSC 133;C");

    // Command end: D;<exit_code>
    let s = emit_task_markers(true, false, TaskPhase::CommandEnd(0));
    assert_eq!(s, "\x1b]133;D;0\x1b\\", "command end should emit OSC 133;D;0 for success");

    let s = emit_task_markers(true, false, TaskPhase::CommandEnd(1));
    assert_eq!(s, "\x1b]133;D;1\x1b\\", "command end should emit OSC 133;D;1 for failure");
}

/// Test that task markers return empty string when unsupported
/// Traces to: FR-005 (AC-005.5, AC-005.6)
#[test]
fn test_osc133_empty_when_unsupported() {
    let s = emit_task_markers(false, false, TaskPhase::PromptStart);
    assert_eq!(s, "", "should return empty string when task_markers unsupported");
}

/// Test tmux DCS passthrough wrapping doubles all inner ESC bytes
/// Traces to: FR-005 (AC-005.4)
#[test]
fn test_tmux_passthrough_wrapping() {
    let inner = "\x1b]8;;https://x\x1b\\";
    let wrapped = wrap_for_tmux_with(inner, true);

    // Must start with DCS passthrough prefix
    assert!(wrapped.starts_with("\x1bPtmux;"), "should start with tmux DCS prefix");
    // Must end with ST
    assert!(wrapped.ends_with("\x1b\\"), "should end with ST");

    // Inner ESCs must be doubled
    let inner_content = &wrapped["\x1bPtmux;".len()..wrapped.len() - 2];
    let esc_count = inner_content.chars().filter(|c| *c == '\x1b').count();
    // Original had 2 ESCs; after doubling = 4
    assert_eq!(esc_count, 4, "each inner ESC should be doubled in tmux passthrough");
}

/// Test that tmux wrapping is a no-op outside tmux
/// Traces to: FR-005 (AC-005.4)
#[test]
fn test_tmux_wrapping_noop_outside_tmux() {
    let inner = "\x1b]8;;https://x\x1b\\";
    let result = wrap_for_tmux_with(inner, false);
    assert_eq!(result, inner, "wrapping should be no-op when not in tmux");
}

/// Test that clipboard write in tmux is DCS-wrapped
/// Traces to: FR-005 (AC-005.2, AC-005.4)
#[test]
fn test_osc52_wraps_in_tmux() {
    let s = emit_clipboard(true, true, "data");
    assert!(s.starts_with("\x1bPtmux;"), "clipboard should be DCS-wrapped in tmux");
    assert!(s.ends_with("\x1b\\"), "wrapped clipboard should end with ST");
}
