//! Kitty graphics protocol encoder.
//!
//! Format (per <https://sw.kovidgoyal.net/kitty/graphics-protocol/>):
//!
//! ```text
//! ESC _ G <control>; <payload> ESC \
//! ```
//!
//! For PNG transmit-and-display we use `a=T,f=100`. When the base64 payload
//! exceeds 4096 bytes it is split across multiple APC frames with `m=1` on
//! every frame except the last which carries `m=0`. Every chunk length must be
//! a multiple of 4 base64 chars (so raw-byte slicing at multiples of 3 works).
//!
//! We set `q=2` to silence the terminal's OK/error responses — we do not want
//! them polluting stdout in one-shot CLI mode.

use anyhow::Result;
use base64::Engine;
use std::io::Write;

/// Maximum base64 payload bytes per APC frame. Kitty mandates a hard 4096-byte cap.
pub const MAX_CHUNK: usize = 4096;

/// Emit a PNG image using the kitty graphics protocol.
pub fn write_kitty_png<W: Write>(out: &mut W, png: &[u8]) -> Result<()> {
    let b64 = base64::engine::general_purpose::STANDARD.encode(png);
    let bytes = b64.as_bytes();

    if bytes.len() <= MAX_CHUNK {
        // Single-frame fast path.
        out.write_all(b"\x1b_Ga=T,f=100,q=2;")?;
        out.write_all(bytes)?;
        out.write_all(b"\x1b\\")?;
        // Trailing newline so following shell prompts land below the image.
        out.write_all(b"\n")?;
        return Ok(());
    }

    // Multi-chunk: first frame carries format keys, intermediate frames carry
    // only `m=1`, final frame carries `m=0`.
    let mut offset = 0usize;
    let mut first = true;
    while offset < bytes.len() {
        let end = (offset + MAX_CHUNK).min(bytes.len());
        let is_last = end == bytes.len();
        let chunk = &bytes[offset..end];

        if first {
            if is_last {
                // Edge-case: exactly one chunk needed.
                out.write_all(b"\x1b_Ga=T,f=100,q=2,m=0;")?;
            } else {
                out.write_all(b"\x1b_Ga=T,f=100,q=2,m=1;")?;
            }
            first = false;
        } else if is_last {
            out.write_all(b"\x1b_Gm=0;")?;
        } else {
            out.write_all(b"\x1b_Gm=1;")?;
        }
        out.write_all(chunk)?;
        out.write_all(b"\x1b\\")?;
        offset = end;
    }
    out.write_all(b"\n")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use base64::Engine;

    #[test]
    fn single_chunk_envelope_matches_spec() {
        // Short payload (well under 4096 base64 bytes).
        let png = b"\x89PNG\r\n\x1a\nhello";
        let mut buf = Vec::new();
        write_kitty_png(&mut buf, png).unwrap();

        let expected_b64 = base64::engine::general_purpose::STANDARD.encode(png);
        let mut expected = Vec::new();
        expected.extend_from_slice(b"\x1b_Ga=T,f=100,q=2;");
        expected.extend_from_slice(expected_b64.as_bytes());
        expected.extend_from_slice(b"\x1b\\");
        expected.extend_from_slice(b"\n");
        assert_eq!(buf, expected);
    }

    #[test]
    fn multi_chunk_has_correct_m_keys() {
        // Force two chunks: 5000 bytes of raw data → ~6668 base64 chars.
        let png: Vec<u8> = (0..5000u32).map(|i| (i & 0xff) as u8).collect();
        let mut buf = Vec::new();
        write_kitty_png(&mut buf, &png).unwrap();
        let s = String::from_utf8_lossy(&buf);

        // First frame must carry a=T,f=100 AND m=1 (not m=0).
        assert!(
            s.contains("\x1b_Ga=T,f=100,q=2,m=1;"),
            "missing first-chunk header"
        );
        // Last frame must be m=0.
        assert!(s.contains("\x1b_Gm=0;"), "missing final-chunk header");
        // Must end with APC terminator + newline.
        assert!(buf.ends_with(b"\x1b\\\n"));
    }

    #[test]
    fn chunks_respect_max_size() {
        let png: Vec<u8> = (0..20_000u32).map(|i| (i & 0xff) as u8).collect();
        let mut buf = Vec::new();
        write_kitty_png(&mut buf, &png).unwrap();

        // Split by APC terminator; each frame's payload (after the `;`) must be ≤ MAX_CHUNK.
        for frame in buf.split(|&b| b == 0x1b).filter(|f| !f.is_empty()) {
            if let Some(pos) = frame.iter().position(|&b| b == b';') {
                let payload_end = frame
                    .iter()
                    .rposition(|&b| b == b'\\')
                    .unwrap_or(frame.len());
                if payload_end > pos {
                    let payload_len = payload_end - pos - 1;
                    assert!(payload_len <= MAX_CHUNK, "chunk too big: {payload_len}");
                }
            }
        }
    }
}
