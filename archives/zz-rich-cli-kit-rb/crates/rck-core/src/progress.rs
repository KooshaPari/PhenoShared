//! One-shot progress-bar rendering.

use crate::spans::{render_spans, Span};
use crate::Capabilities;
use serde::{Deserialize, Serialize};
use std::io::Write;

#[derive(Debug, Default, Clone, Copy, Serialize, Deserialize)]
pub enum ProgressStyle {
    /// Unicode heavy-block + truecolor gradient when available; ASCII `#` otherwise.
    #[default]
    Blocks,
    /// Always ASCII `#` / `-`.
    Ascii,
}

/// Render a single progress bar line. `ratio` is clamped to `[0.0, 1.0]`.
///
/// Width is fixed at 40 cells. No trailing newline is omitted — always writes `\n`.
pub fn emit_progress<W: Write>(
    out: &mut W,
    caps: &Capabilities,
    ratio: f32,
    style: ProgressStyle,
    label: Option<&str>,
) -> anyhow::Result<()> {
    let ratio = ratio.clamp(0.0, 1.0);
    const WIDTH: usize = 40;
    let filled = (ratio * WIDTH as f32).round() as usize;
    let empty = WIDTH - filled;

    let unicode_ok = caps.unicode_width >= 2 && !matches!(style, ProgressStyle::Ascii);
    let color_ok = caps.truecolor && unicode_ok;

    if color_ok {
        // Gradient green→yellow→red inverted: green at high progress is friendly.
        let (r, g, b) = gradient(ratio);
        write!(out, "\x1b[38;2;{r};{g};{b}m")?;
        for _ in 0..filled {
            write!(out, "█")?;
        }
        write!(out, "\x1b[0m")?;
        write!(out, "\x1b[2m")?;
        for _ in 0..empty {
            write!(out, "░")?;
        }
        write!(out, "\x1b[0m")?;
    } else if unicode_ok {
        for _ in 0..filled {
            write!(out, "█")?;
        }
        for _ in 0..empty {
            write!(out, "░")?;
        }
    } else {
        write!(out, "[")?;
        for _ in 0..filled {
            write!(out, "#")?;
        }
        for _ in 0..empty {
            write!(out, "-")?;
        }
        write!(out, "]")?;
    }

    let pct = (ratio * 100.0).round() as u32;
    if let Some(l) = label {
        writeln!(out, " {pct:>3}%  {l}")?;
    } else {
        writeln!(out, " {pct:>3}%")?;
    }
    Ok(())
}

/// Same as [`emit_progress`] but accepts a span-based label (mix of plain
/// text + OSC 8 hyperlinks). Falls back to plain text on non-hyperlink
/// terminals.
pub fn emit_progress_spans<W: Write>(
    out: &mut W,
    caps: &Capabilities,
    ratio: f32,
    style: ProgressStyle,
    label: &[Span],
) -> anyhow::Result<()> {
    let rendered = render_spans(caps, label);
    let label_opt = if rendered.is_empty() {
        None
    } else {
        Some(rendered.as_str())
    };
    emit_progress(out, caps, ratio, style, label_opt)
}

fn gradient(t: f32) -> (u8, u8, u8) {
    // 0.0 → red (229, 62, 62), 0.5 → amber (246, 173, 85), 1.0 → green (72, 187, 120)
    let lerp = |a: f32, b: f32, t: f32| -> u8 { (a + (b - a) * t).round().clamp(0.0, 255.0) as u8 };
    if t < 0.5 {
        let u = t / 0.5;
        (
            lerp(229.0, 246.0, u),
            lerp(62.0, 173.0, u),
            lerp(62.0, 85.0, u),
        )
    } else {
        let u = (t - 0.5) / 0.5;
        (
            lerp(246.0, 72.0, u),
            lerp(173.0, 187.0, u),
            lerp(85.0, 120.0, u),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capabilities::Capabilities;

    fn caps(graphics: bool, truecolor: bool, unicode_width: u16) -> Capabilities {
        Capabilities {
            graphics,
            sixel: false,
            truecolor,
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
    fn ascii_fallback_has_brackets() {
        let c = caps(false, false, 1);
        let mut buf = Vec::new();
        emit_progress(&mut buf, &c, 0.5, ProgressStyle::Blocks, None).unwrap();
        let s = String::from_utf8(buf).unwrap();
        assert!(s.contains('['));
        assert!(s.contains(']'));
        assert!(s.contains("50%"));
    }

    #[test]
    fn truecolor_emits_sgr() {
        let c = caps(true, true, 2);
        let mut buf = Vec::new();
        emit_progress(&mut buf, &c, 1.0, ProgressStyle::Blocks, Some("done")).unwrap();
        let s = String::from_utf8(buf).unwrap();
        assert!(s.contains("\x1b[38;2;"));
        assert!(s.contains("100%"));
        assert!(s.contains("done"));
    }

    #[test]
    fn ratio_clamped() {
        let c = caps(false, false, 2);
        let mut buf = Vec::new();
        emit_progress(&mut buf, &c, 5.0, ProgressStyle::Blocks, None).unwrap();
        assert!(String::from_utf8(buf).unwrap().contains("100%"));
    }
}
