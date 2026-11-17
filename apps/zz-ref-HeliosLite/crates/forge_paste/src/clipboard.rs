//! Clipboard read/write integration via [`arboard`].
//!
//! Wraps the platform clipboard behind three small, guarded functions. The `clipboard`
//! Cargo feature gates this module; it is off by default so the crate does not require the
//! system clipboard library on every platform at build time.

use crate::paste_event::{PasteEvent, PasteSource};

/// Represents a clipboard read result, normalising the empty case.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ClipboardResult {
    /// No clipboard contents.
    Empty,
    /// Text contents.
    Text(String),
    /// Binary contents (e.g. an image).
    Bytes(Vec<u8>),
}

/// Read current clipboard contents as text, if any.
pub fn read_text() -> ClipboardResult {
    let mut cb = match arboard::Clipboard::new() {
        Ok(c) => c,
        Err(_) => return ClipboardResult::Empty,
    };
    match cb.get_text() {
        Ok(t) if !t.trim().is_empty() => ClipboardResult::Text(t),
        _ => ClipboardResult::Empty,
    }
}

/// Read current clipboard contents as raw bytes (image or other binary), if any.
///
/// arboard 3.x exposes images through the `Get` builder's `image()` method
/// (returning `ImageData`), not a generic byte sink. We encode the image to
/// PNG bytes so the caller gets a single self-describing buffer.
pub fn read_bytes() -> ClipboardResult {
    let mut cb = match arboard::Clipboard::new() {
        Ok(c) => c,
        Err(_) => return ClipboardResult::Empty,
    };
    match cb.get().image() {
        Ok(img) => match encode_png(&img) {
            Some(png) => ClipboardResult::Bytes(png),
            None => ClipboardResult::Empty,
        },
        Err(_) => ClipboardResult::Empty,
    }
}

/// Encode an `ImageData` to PNG bytes using the `image` crate.
fn encode_png(img: &arboard::ImageData) -> Option<Vec<u8>> {
    let (w, h) = (img.width, img.height);
    // arboard gives RGBA pixels.
    let buf = image::RgbaImage::from_raw(w as u32, h as u32, img.bytes.to_vec())?;
    let mut out = Vec::new();
    image::DynamicImage::ImageRgba8(buf)
        .write_to(&mut std::io::Cursor::new(&mut out), image::ImageFormat::Png)
        .ok()?;
    Some(out)
}

/// Write text to the clipboard. Returns true on success.
pub fn write_text(text: &str) -> bool {
    let mut cb = match arboard::Clipboard::new() {
        Ok(c) => c,
        Err(_) => return false,
    };
    cb.set_text(text.to_owned()).is_ok()
}

/// Write a PNG-encoded image to the clipboard. Returns true on success.
///
/// Accepts already-encoded PNG bytes (as produced by [`read_bytes`]) and
/// decodes them to RGBA for arboard 3.x's `Set::image`.
pub fn write_bytes(data: &[u8]) -> bool {
    let Ok(img) = image::load_from_memory_with_format(data, image::ImageFormat::Png) else {
        return false;
    };
    let rgba = img.to_rgba8();
    let (w, h) = rgba.dimensions();
    let mut cb = match arboard::Clipboard::new() {
        Ok(c) => c,
        Err(_) => return false,
    };
    cb.set()
        .image(arboard::ImageData {
            width: w as usize,
            height: h as usize,
            bytes: std::borrow::Cow::Owned(rgba.into_raw()),
        })
        .is_ok()
}

/// Convert a clipboard read result into a paste event.
pub fn clipboard_to_paste(result: ClipboardResult) -> PasteEvent {
    match result {
        // `ClipboardImage` is the closest source discriminator (the OS clipboard image).
        ClipboardResult::Text(t) => PasteEvent::new(PasteSource::ClipboardImage, t.into_bytes()),
        ClipboardResult::Bytes(b) => PasteEvent::new(PasteSource::ClipboardImage, b),
        ClipboardResult::Empty => PasteEvent::new(PasteSource::ClipboardImage, Vec::new()),
    }
}

/// Minimal MIME sniff — extensible.
pub fn guess_mime(data: &[u8]) -> &'static str {
    if data.len() >= 8 && &data[0..8] == b"\x89PNG\r\n\x1a\n" {
        "image/png"
    } else if data.len() >= 3 && &data[0..3] == b"\xff\xd8\xff" {
        "image/jpeg"
    } else {
        "application/octet-stream"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mime_sniffs_png_and_jpeg() {
        assert_eq!(guess_mime(b"\x89PNG\r\n\x1a\n...."), "image/png");
        assert_eq!(guess_mime(b"\xff\xd8\xff..."), "image/jpeg");
        assert_eq!(guess_mime(b"plain text"), "application/octet-stream");
    }

    #[test]
    fn empty_text_is_empty_event() {
        let ev = clipboard_to_paste(ClipboardResult::Empty);
        assert_eq!(ev.as_string(), "");
        assert_eq!(ev.source, PasteSource::ClipboardImage);
        assert!(ev.is_empty());
    }

    #[test]
    fn bytes_become_image_event() {
        // 8-byte PNG magic (full signature required by guess_mime).
        let png = vec![0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
        let ev = clipboard_to_paste(ClipboardResult::Bytes(png));
        assert_eq!(ev.source, PasteSource::ClipboardImage);
        assert_eq!(guess_mime(&ev.bytes), "image/png");
    }
}
