//! Integration tests for terminal capability detection
//! Traces to: FR-001

use rck_core::{detect, Capabilities};
use std::env;

/// Test environment-based capability detection for known terminals
/// Traces to: FR-001 (AC-001.1)
#[test]
fn test_capability_detection_env_vars() {
    env::set_var("TERM_PROGRAM", "ghostty");
    let caps = detect();
    assert_eq!(caps.terminal, "ghostty");
    assert!(caps.graphics, "ghostty should support graphics");
    
    env::set_var("TERM_PROGRAM", "WezTerm");
    let caps = detect();
    assert_eq!(caps.terminal, "wezterm");
    assert!(caps.graphics, "wezterm should support graphics");
    
    env::set_var("TERM", "xterm-kitty");
    env::remove_var("TERM_PROGRAM");
    let caps = detect();
    assert_eq!(caps.terminal, "kitty");
    assert!(caps.graphics, "kitty should support graphics");
}

/// Test that graphics capability is disabled when stdout is not a TTY
/// Traces to: FR-001 (AC-001.3)
#[test]
fn test_capability_tty_check() {
    // This test runs in CI where stdout is typically redirected
    let caps = detect();
    
    // Capability struct should always be valid
    assert!(!caps.terminal.is_empty(), "terminal name should never be empty");
    
    // If not a TTY, graphics must be false even if env suggests support
    if !caps.is_tty {
        assert!(!caps.graphics, "graphics should be false when not a TTY");
    }
}

/// Test that plain capabilities have safe defaults
/// Traces to: FR-001 (AC-001.4)
#[test]
fn test_plain_capabilities() {
    let caps = Capabilities::plain();
    assert!(!caps.graphics);
    assert!(!caps.sixel);
    assert!(!caps.truecolor);
    assert!(!caps.hyperlinks);
    assert!(!caps.clipboard);
    assert!(!caps.task_markers);
    assert!(!caps.kitty_keyboard);
    assert!(!caps.in_tmux);
    assert_eq!(caps.unicode_width, 1);
    assert_eq!(caps.terminal, "unknown");
}

/// Test that detect always returns a valid result and never panics
/// Traces to: FR-001 (AC-001.5)
#[test]
fn test_detect_never_panics() {
    // Clear all env vars that might influence detection
    let vars_to_clear = [
        "TERM", "TERM_PROGRAM", "COLORTERM", "KITTY_WINDOW_ID",
        "WEZTERM_EXECUTABLE", "KONSOLE_VERSION", "TMUX"
    ];
    
    for var in vars_to_clear {
        env::remove_var(var);
    }
    
    let caps = detect();
    assert!(!caps.terminal.is_empty(), "terminal should have a value even with no env vars");
    
    // Restore a minimal TERM for subsequent tests
    env::set_var("TERM", "xterm");
}
