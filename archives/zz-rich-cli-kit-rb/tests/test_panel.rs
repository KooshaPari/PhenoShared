//! Integration tests for status panel rendering
//! Traces to: FR-004

use rck_core::{emit_panel, emit_panel_spans, BorderStyle, Capabilities, Span};

fn caps(unicode_width: u16, hyperlinks: bool) -> Capabilities {
    Capabilities {
        graphics: false,
        sixel: false,
        truecolor: false,
        unicode_width,
        terminal: "test".into(),
        is_tty: true,
        hyperlinks,
        clipboard: false,
        task_markers: false,
        kitty_keyboard: false,
        in_tmux: false,
    }
}

/// Test that all three border styles emit correct box-drawing characters
/// Traces to: FR-004 (AC-004.2, AC-004.3, AC-004.4)
#[test]
fn test_panel_border_styles() {
    let unicode_caps = caps(2, false);
    let ascii_caps = caps(1, false);

    // Rounded borders use ╭╮╰╯
    let mut buf = Vec::new();
    emit_panel(&mut buf, &unicode_caps, "status", &["ok"], BorderStyle::Rounded).unwrap();
    let s = String::from_utf8(buf).unwrap();
    assert!(s.contains("╭"), "rounded should have ╭ corner");
    assert!(s.contains("╮"), "rounded should have ╮ corner");
    assert!(s.contains("╯"), "rounded should have ╯ corner");
    assert!(s.contains("╰"), "rounded should have ╰ corner");

    // Square borders use ┌┐└┘
    let mut buf = Vec::new();
    emit_panel(&mut buf, &unicode_caps, "status", &["ok"], BorderStyle::Square).unwrap();
    let s = String::from_utf8(buf).unwrap();
    assert!(s.contains("┌"), "square should have ┌ corner");
    assert!(s.contains("┐"), "square should have ┐ corner");
    assert!(s.contains("└"), "square should have └ corner");
    assert!(s.contains("┘"), "square should have ┘ corner");

    // ASCII borders use + and -
    let mut buf = Vec::new();
    emit_panel(&mut buf, &ascii_caps, "status", &["ok"], BorderStyle::Ascii).unwrap();
    let s = String::from_utf8(buf).unwrap();
    assert!(s.contains("+"), "ascii should have + corners");
    assert!(s.contains("-"), "ascii should have - horizontals");
    assert!(!s.contains("╭"), "ascii should NOT have unicode corners");
}

/// Test that panel renders title and body content
/// Traces to: FR-004 (AC-004.1, AC-004.6, AC-004.7)
#[test]
fn test_panel_renders_title_and_body() {
    let c = caps(2, false);
    let mut buf = Vec::new();
    emit_panel(
        &mut buf,
        &c,
        "build status",
        &["tests: 42 passed", "lint: clean"],
        BorderStyle::Rounded,
    )
    .unwrap();
    let s = String::from_utf8(buf).unwrap();
    assert!(s.contains("build status"), "should contain title");
    assert!(s.contains("tests: 42 passed"), "should contain first body line");
    assert!(s.contains("lint: clean"), "should contain second body line");
}

/// Test that spans with hyperlinks render OSC 8 sequences when supported
/// Traces to: FR-004 (AC-004.1), FR-005 (AC-005.1)
#[test]
fn test_panel_spans_with_hyperlink() {
    let c = caps(2, true);
    let rows = vec![vec![Span::text("see "), Span::link("https://example.com", "docs")]];
    let mut buf = Vec::new();
    emit_panel_spans(&mut buf, &c, "links", &rows, BorderStyle::Square).unwrap();
    let s = String::from_utf8(buf).unwrap();
    assert!(s.contains("\x1b]8;;https://example.com"), "should emit OSC 8 hyperlink");
    assert!(s.contains("docs"), "should include link text");
}

/// Test that ASCII fallback is used when unicode width < 2
/// Traces to: FR-004 (AC-004.4)
#[test]
fn test_panel_ascii_fallback_on_low_unicode() {
    let c = caps(1, false);
    let mut buf = Vec::new();
    emit_panel(&mut buf, &c, "title", &["body"], BorderStyle::Rounded).unwrap();
    let s = String::from_utf8(buf).unwrap();
    // With unicode_width=1, Rounded is treated as ASCII
    assert!(s.contains("+"), "should fall back to + corners when unicode_width < 2");
    assert!(!s.contains("╭"), "should NOT use unicode rounded corners");
}
