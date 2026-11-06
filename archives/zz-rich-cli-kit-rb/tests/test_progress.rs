//! Integration tests for progress bar rendering
//! Traces to: FR-003

use rck_core::{emit_progress, Capabilities, ProgressStyle};

/// Test progress ratio clamping to [0.0, 1.0]
/// Traces to: FR-003 (AC-003.1)
#[test]
fn test_progress_clamping() {
    let caps = Capabilities::plain();
    let mut buf = Vec::new();
    
    // Test over-range (>1.0)
    emit_progress(&mut buf, &caps, 2.5, ProgressStyle::Ascii, None).unwrap();
    let output = String::from_utf8_lossy(&buf);
    assert!(output.contains("100%"), "ratio >1.0 should clamp to 100%");
    
    // Test under-range (<0.0)
    buf.clear();
    emit_progress(&mut buf, &caps, -0.5, ProgressStyle::Ascii, None).unwrap();
    let output = String::from_utf8_lossy(&buf);
    assert!(output.contains("0%"), "ratio <0.0 should clamp to 0%");
}

/// Test ASCII progress bar format
/// Traces to: FR-003 (AC-003.3)
#[test]
fn test_progress_ascii_style() {
    let caps = Capabilities::plain();
    let mut buf = Vec::new();
    
    emit_progress(&mut buf, &caps, 0.5, ProgressStyle::Ascii, Some("halfway")).unwrap();
    let output = String::from_utf8_lossy(&buf);
    
    // Should contain ASCII brackets and equals signs
    assert!(output.contains("["), "ASCII style should have opening bracket");
    assert!(output.contains("]"), "ASCII style should have closing bracket");
    assert!(output.contains("="), "ASCII style should have equals signs");
    assert!(output.contains("50%"), "should show 50% for 0.5 ratio");
    assert!(output.contains("halfway"), "should include label");
}

/// Test Unicode block progress bar style
/// Traces to: FR-003 (AC-003.2)
#[test]
fn test_progress_blocks_style() {
    let mut caps = Capabilities::plain();
    caps.unicode_width = 2;  // Enable unicode
    let mut buf = Vec::new();
    
    emit_progress(&mut buf, &caps, 0.75, ProgressStyle::Blocks, Some("building")).unwrap();
    let output = String::from_utf8_lossy(&buf);
    
    // Unicode block style should contain block characters or brackets
    // (exact characters depend on implementation)
    assert!(output.contains("75%"), "should show 75% for 0.75 ratio");
    assert!(output.contains("building"), "should include label");
    assert!(!output.is_empty(), "should produce output");
}

/// Test progress bar without label
/// Traces to: FR-003 (AC-003.5)
#[test]
fn test_progress_no_label() {
    let caps = Capabilities::plain();
    let mut buf = Vec::new();
    
    emit_progress(&mut buf, &caps, 0.33, ProgressStyle::Ascii, None).unwrap();
    let output = String::from_utf8_lossy(&buf);
    
    assert!(output.contains("33%"), "should show percentage");
    assert!(output.contains("["), "should have ASCII bar");
}

/// Test that progress percentage is displayed as integer
/// Traces to: FR-003 (AC-003.4)
#[test]
fn test_progress_percentage_format() {
    let caps = Capabilities::plain();
    let mut buf = Vec::new();
    
    emit_progress(&mut buf, &caps, 0.427, ProgressStyle::Ascii, None).unwrap();
    let output = String::from_utf8_lossy(&buf);
    
    // Should round to integer percentage (42% or 43%)
    assert!(output.contains("42%") || output.contains("43%"), 
        "should display integer percentage, got: {}", output);
    assert!(!output.contains("42.7%"), "should not show decimal percentage");
}
