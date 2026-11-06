//! rck-core — terminal capability detection + rich rendering primitives.
//!
//! Emits kitty-graphics-protocol sequences on capable terminals (Ghostty, kitty,
//! WezTerm), and falls back to plain ASCII otherwise. Also emits OSC 8
//! (hyperlinks), OSC 52 (clipboard), OSC 133 (task markers), and provides
//! alt-screen interactive primitives (`ask`, `pick`, `input`).
//!
//! Reference:
//! - <https://sw.kovidgoyal.net/kitty/graphics-protocol/>
//! - <https://ghostty.org/docs/features>

pub mod capabilities;
pub mod emit;
pub mod encoder;
pub mod image_data;
pub mod interactive;
pub mod panel;
pub mod progress;
pub mod shader;
pub mod spans;
pub mod width;

pub use capabilities::{detect, Capabilities};
pub use emit::{
    emit_clipboard, emit_hyperlink, emit_task_markers, in_tmux, wrap_for_tmux, wrap_for_tmux_with,
    TaskPhase,
};
pub use image_data::ImageData;
pub use interactive::{ask, input, pick, Outcome};
pub use panel::{emit_panel, emit_panel_spans, BorderStyle};
pub use progress::{emit_progress, emit_progress_spans, ProgressStyle};
pub use spans::{render_spans, Span};

use std::io::Write;

/// High-level convenience: write an image to `out` using the best mode for `caps`.
pub fn emit_image<W: Write>(
    out: &mut W,
    caps: &Capabilities,
    img: &ImageData,
) -> anyhow::Result<()> {
    if caps.graphics {
        encoder::write_kitty_png(out, &img.png_bytes)
    } else {
        // Fallback: short textual summary
        writeln!(
            out,
            "[image: {}x{} {} (graphics protocol unavailable)]",
            img.width,
            img.height,
            img.alt_text.as_deref().unwrap_or("untitled")
        )?;
        Ok(())
    }
}
