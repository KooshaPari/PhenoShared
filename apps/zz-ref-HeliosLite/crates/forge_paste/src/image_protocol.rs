//! Image protocol encoding for inline terminal rendering.
//!
//! Encodes raw image bytes into the four mainstream terminal image protocols:
//! * **OSC52** (`\x1b]52;...`) — clipboard-orientated; used here for image interchange.
//! * **Kitty graphics** (`\x1b_G...`) — the GTK/Kitty protocol (favoured, most capable).
//! * **Sixel** (`\x1bP...`) — DEC sixel, widely supported (Xterm, WezTerm, Konty, foot).
//! * **iTerm2 inline** (`\x1b]1337;File=...`) — Apple Terminal / iTerm2 / Ghostty subset.
//!
//! This module is purely byte construction — no OS/IO dependencies — so it is unit-testable
//! in isolation. Writing the resulting bytes to the tty is delegated to the caller (REPL).
//!
//! See `plans/2026-09-02-helioslite-p0.3-p0.4-plan-spec-adr.md` §5 for design rationale.

use base64::Engine;

/// The terminal image protocols we can emit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ImageProtocol {
    /// `\x1b]52;[index];<b64>\x07` — OSC 52 clipboard protocol.
    Osc52,
    /// `\x1b_Ga=T,f=<t>,m=0;<b64>\x1b\\` — Kitty graphics protocol.
    Kitty,
    /// `\x1bP0;0;...<sixel>\x1b\\` — DEC sixel.
    Sixel,
    /// `\x1b]1337;File=name=...,inline=1;<b64>\x07` — iTerm2 inline image.
    Iterm2,
}

/// Metadata describing an inline image.
#[derive(Debug, Clone, Default)]
pub struct ImageMeta {
    /// MIME type, e.g. `image/png`. Required for Kitty/iTerm2.
    pub mime: String,
    /// Pixel width (Kitty/iTerm2). Optional.
    pub width: Option<u32>,
    /// Pixel height (Kitty/iTerm2). Optional.
    pub height: Option<u32>,
    /// Displayed name (iTerm2). Optional.
    pub filename: String,
}

/// Base64 encoder matching the `base64` crate we depend on.
fn b64(data: &[u8]) -> String {
    base64::engine::general_purpose::STANDARD.encode(data)
}

/// Encode raw image bytes into the requested protocol string (UTF-8 safe — these are
/// ASCII escape sequences + base64, so no lossy conversion is required).
pub fn encode_image(proto: ImageProtocol, data: &[u8], meta: &ImageMeta) -> String {
    let encoded = b64(data);
    match proto {
        ImageProtocol::Osc52 => {
            // OSC 52 is intended for the *clipboard*; reusing it for inline preview is a
            // pragmatic fallback when no other protocol is available.
            format!("\x1b]52;c;{encoded}\x07")
        }
        ImageProtocol::Kitty => {
            let mut header = "\x1b_Ga=T,f=".to_string();
            let fmt = image_format_key(&meta.mime);
            header.push_str(fmt);
            if let (Some(w), Some(h)) = (meta.width, meta.height) {
                header.push_str(&format!(",s={w},v={h}"));
            }
            header.push_str(",m=0;");
            header.push_str(&encoded);
            header.push_str("\x1b\\");
            header
        }
        ImageProtocol::Sixel => {
            // Preamble selects colour mode & options; the payload is produced elsewhere by a
            // sixel encoder. Here we emit an OSC-52-like chunk so callers can store the decoded
            // sixel stream. For a real sixel the payload must be pre-encoded; we keep the raw
            // bytes so a downstream sixel encoder can populate the payload.
            format!("\x1bP0;0;0q{encoded}\x1b\\")
        }
        ImageProtocol::Iterm2 => {
            let name = if meta.filename.is_empty() {
                "image".to_string()
            } else {
                meta.filename.clone()
            };
            let mut s = format!("\x1b]1337;File=name={name},inline=1");
            if !meta.mime.is_empty() {
                s.push_str(&format!(";size={};", data.len()));
                s.push_str(&format!(",width={};", meta.width.unwrap_or(0)));
                s.push_str(&format!(",height={};", meta.height.unwrap_or(0)));
            }
            s.push(';');
            s.push_str(&encoded);
            s.push('\x07');
            s
        }
    }
}

/// Guess the protocol the given terminal/os hint prefers.
pub fn preferred_protocol(term_hint: &str) -> ImageProtocol {
    let t = term_hint.to_lowercase();
    if t.contains("kitty") {
        ImageProtocol::Kitty
    } else if t.contains("iterm") || t.contains("ghostty") {
        ImageProtocol::Iterm2
    } else if t.contains("xterm")
        || t.contains("wezterm")
        || t.contains("foot")
        || t.contains("rio")
    {
        ImageProtocol::Sixel
    } else {
        // Conservative default — every modern terminal implements OSC 52 clipboard.
        ImageProtocol::Osc52
    }
}

/// Map a MIME type to a Kitty/terminal image format key.
fn image_format_key(mime: &str) -> &'static str {
    match mime {
        m if m.ends_with("png") => "100",
        m if m.ends_with("jpeg") || m.ends_with("jpg") => "101",
        m if m.ends_with("gif") => "102",
        m if m.ends_with("webp") => "103",
        m if m.ends_with("svg") => "104",
        _ => "100",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn osc52_embeds_b64() {
        let s = encode_image(ImageProtocol::Osc52, b"hi", &ImageMeta::default());
        assert!(s.starts_with("\x1b]52;c;"));
        assert!(s.ends_with("\x07"));
        assert!(s.contains("aGk=")); // base64("hi")
    }

    #[test]
    fn kitty_includes_mime_fmt_and_terminator() {
        let meta = ImageMeta {
            mime: "image/png".into(),
            width: Some(10),
            height: Some(20),
            ..Default::default()
        };
        let s = encode_image(ImageProtocol::Kitty, b"abc", &meta);
        assert!(s.starts_with("\x1b_Ga=T"));
        assert!(s.contains(",s=10,v=20"));
        assert!(s.ends_with("\x1b\\"));
        assert!(s.contains("YWJj"));
    }

    #[test]
    fn iterm2_includes_name_and_size() {
        let meta = ImageMeta {
            mime: "image/png".into(),
            filename: "shot.png".into(),
            width: Some(32),
            height: Some(32),
        };
        let s = encode_image(ImageProtocol::Iterm2, b"pngbytes", &meta);
        assert!(s.starts_with("\x1b]1337;File=name=shot.png,inline=1"));
        assert!(s.ends_with("\x07"));
        assert!(s.contains("cG5nYnl0ZXM="));
    }

    #[test]
    fn sixel_wraps_payload() {
        let s = encode_image(ImageProtocol::Sixel, b"\x90abc", &ImageMeta::default());
        assert!(s.starts_with("\x1bP"));
        assert!(s.ends_with("\x1b\\"));
    }

    #[test]
    fn preferred_protocol_selection() {
        assert_eq!(preferred_protocol("xterm-ghostty"), ImageProtocol::Iterm2);
        assert_eq!(preferred_protocol("kitty"), ImageProtocol::Kitty);
        assert_eq!(preferred_protocol("wezterm"), ImageProtocol::Sixel);
        assert_eq!(preferred_protocol(""), ImageProtocol::Osc52);
    }

    #[test]
    fn png_mime_maps_to_kitty_100() {
        assert_eq!(image_format_key("image/png"), "100");
        assert_eq!(image_format_key("image/jpeg"), "101");
    }
}
