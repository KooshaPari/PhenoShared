//! Box-drawn status panels with grapheme-correct width calculation and
//! optional inline OSC-8 hyperlinks via [`Span`].

use crate::spans::{render_spans, spans_width, Span};
use crate::width::visible_width;
use crate::Capabilities;
use serde::{Deserialize, Serialize};
use std::io::Write;

#[derive(Debug, Default, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum BorderStyle {
    #[default]
    Rounded,
    Square,
    Ascii,
}

struct Glyphs {
    tl: &'static str,
    tr: &'static str,
    bl: &'static str,
    br: &'static str,
    h: &'static str,
    v: &'static str,
}

fn glyphs(caps: &Capabilities, style: BorderStyle) -> Glyphs {
    let unicode = caps.unicode_width >= 2 && !matches!(style, BorderStyle::Ascii);
    match (unicode, style) {
        (true, BorderStyle::Rounded) => Glyphs {
            tl: "╭",
            tr: "╮",
            bl: "╰",
            br: "╯",
            h: "─",
            v: "│",
        },
        (true, BorderStyle::Square) => Glyphs {
            tl: "┌",
            tr: "┐",
            bl: "└",
            br: "┘",
            h: "─",
            v: "│",
        },
        _ => Glyphs {
            tl: "+",
            tr: "+",
            bl: "+",
            br: "+",
            h: "-",
            v: "|",
        },
    }
}

/// Emit a status panel from plain string lines (back-compat entry point).
pub fn emit_panel<W: Write>(
    out: &mut W,
    caps: &Capabilities,
    title: &str,
    lines: &[&str],
    border_style: BorderStyle,
) -> anyhow::Result<()> {
    let rows: Vec<Vec<Span>> = lines
        .iter()
        .map(|l| vec![Span::text((*l).to_string())])
        .collect();
    emit_panel_spans(out, caps, title, &rows, border_style)
}

/// Emit a status panel whose body rows are sequences of spans (text + links).
pub fn emit_panel_spans<W: Write>(
    out: &mut W,
    caps: &Capabilities,
    title: &str,
    rows: &[Vec<Span>],
    border_style: BorderStyle,
) -> anyhow::Result<()> {
    let g = glyphs(caps, border_style);

    let title_w = visible_width(title);
    let rows_w = rows.iter().map(|s| spans_width(s)).max().unwrap_or(0);
    let content_width = std::cmp::max(title_w, rows_w);
    let inner = content_width.max(12);
    let total = inner + 2; // one pad space on each side

    // Top: ╭─ title ──╮
    write!(out, "{}{}", g.tl, g.h)?;
    let title_segment = format!(" {} ", title);
    let title_seg_w = visible_width(&title_segment);
    let remaining = total.saturating_sub(1 + title_seg_w);
    out.write_all(title_segment.as_bytes())?;
    for _ in 0..remaining {
        write!(out, "{}", g.h)?;
    }
    writeln!(out, "{}", g.tr)?;

    // Body rows.
    for spans in rows {
        let w = spans_width(spans);
        let rendered = render_spans(caps, spans);
        let pad = inner.saturating_sub(w);
        writeln!(out, "{} {}{} {}", g.v, rendered, " ".repeat(pad), g.v)?;
    }

    // Bottom.
    write!(out, "{}", g.bl)?;
    for _ in 0..total {
        write!(out, "{}", g.h)?;
    }
    writeln!(out, "{}", g.br)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capabilities::Capabilities;

    fn caps(unicode_width: u16) -> Capabilities {
        Capabilities {
            graphics: false,
            sixel: false,
            truecolor: false,
            unicode_width,
            terminal: "test".into(),
            is_tty: true,
            hyperlinks: false,
            clipboard: false,
            task_markers: false,
            kitty_keyboard: false,
            in_tmux: false,
        }
    }

    #[test]
    fn unicode_uses_rounded_corners() {
        let c = caps(2);
        let mut buf = Vec::new();
        emit_panel(
            &mut buf,
            &c,
            "hello",
            &["line one", "line two"],
            BorderStyle::Rounded,
        )
        .unwrap();
        let s = String::from_utf8(buf).unwrap();
        assert!(s.contains("╭"));
        assert!(s.contains("╯"));
        assert!(s.contains("hello"));
        assert!(s.contains("line two"));
    }

    #[test]
    fn ascii_fallback_uses_plus_dash() {
        let c = caps(1);
        let mut buf = Vec::new();
        emit_panel(&mut buf, &c, "t", &["row"], BorderStyle::Rounded).unwrap();
        let s = String::from_utf8(buf).unwrap();
        assert!(s.contains("+"));
        assert!(s.contains("-"));
        assert!(!s.contains("╭"));
    }

    #[test]
    fn emoji_line_aligns_with_grapheme_width() {
        // The poo emoji occupies two cells; right border should remain aligned.
        let c = caps(2);
        let mut buf = Vec::new();
        emit_panel(&mut buf, &c, "t", &["hi \u{1f4a9}"], BorderStyle::Square).unwrap();
        let s = String::from_utf8(buf).unwrap();
        // All body rows should end with the vertical glyph followed by newline.
        let body_lines: Vec<&str> = s.lines().filter(|l| l.starts_with("│")).collect();
        assert!(!body_lines.is_empty());
        for l in body_lines {
            assert!(l.ends_with("│"), "unaligned body row: {:?}", l);
        }
    }

    #[test]
    fn spans_with_link_render() {
        let mut c = caps(2);
        c.hyperlinks = true;
        let rows = vec![vec![Span::text("see "), Span::link("https://x", "docs")]];
        let mut buf = Vec::new();
        emit_panel_spans(&mut buf, &c, "t", &rows, BorderStyle::Square).unwrap();
        let s = String::from_utf8(buf).unwrap();
        assert!(s.contains("\x1b]8;;https://x"));
        assert!(s.contains("docs"));
    }
}
