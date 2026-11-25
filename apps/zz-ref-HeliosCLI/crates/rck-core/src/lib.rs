//! Minimal terminal-UX toolkit stub.
//!
//! Replaces the deleted `rich-cli-kit` dependency with no-op implementations
//! so the workspace compiles. The original crate provided rich terminal panel
//! rendering; this stub degrades to plain text.

use std::io::{self, IsTerminal};

/// Terminal capabilities detected at runtime.
pub struct Caps {
    /// Whether stdout is a real TTY.
    pub is_tty: bool,
}

/// Border style for panel rendering.
pub enum BorderStyle {
    Rounded,
    Ascii,
}

/// Detect terminal capabilities.
pub fn detect() -> Caps {
    Caps { is_tty: io::stdout().is_terminal() }
}

/// Emit a bordered panel to the given writer.
pub fn emit_panel(
    writer: &mut dyn io::Write,
    _caps: &Caps,
    title: &str,
    lines: &[&str],
    border: BorderStyle,
) -> io::Result<()> {
    let (tl, tr, bl, br, hor, ver) = match border {
        BorderStyle::Rounded => {
            ("\u{256d}", "\u{256e}", "\u{2570}", "\u{256f}", "\u{2500}", "\u{2502}")
        }
        BorderStyle::Ascii => ("+", "+", "+", "+", "-", "|"),
    };

    let width = lines.iter().map(|l| l.len()).max().unwrap_or(0).max(title.len()) + 4;

    writeln!(writer, "{tl}{}{tr}", hor.repeat(width - 2))?;
    writeln!(writer, "{ver} {title:<width$} {ver}", width = width - 3)?;
    writeln!(writer, "{ver}{}{ver}", " ".repeat(width - 2))?;
    for line in lines {
        writeln!(writer, "{ver} {line:<width$} {ver}", width = width - 3)?;
    }
    writeln!(writer, "{bl}{}{br}", hor.repeat(width - 2))
}
