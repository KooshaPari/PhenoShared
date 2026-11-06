//! In-memory image representation used by the encoder.

use anyhow::Context;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct ImageData {
    pub png_bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub alt_text: Option<String>,
}

impl ImageData {
    /// Load an image from a filesystem path. Anything supported by the `image` crate
    /// is re-encoded to PNG so kitty's `f=100` path always works.
    pub fn from_path(path: &Path) -> anyhow::Result<Self> {
        let img = image::open(path).with_context(|| format!("opening {}", path.display()))?;
        let width = img.width();
        let height = img.height();
        let mut png_bytes = Vec::new();
        img.write_to(
            &mut std::io::Cursor::new(&mut png_bytes),
            image::ImageFormat::Png,
        )
        .context("re-encoding image as PNG")?;
        Ok(ImageData {
            png_bytes,
            width,
            height,
            alt_text: path.file_name().map(|s| s.to_string_lossy().into_owned()),
        })
    }

    /// Construct from raw PNG bytes (no re-encoding; width/height must be provided).
    pub fn from_png(png_bytes: Vec<u8>, width: u32, height: u32, alt: Option<String>) -> Self {
        ImageData {
            png_bytes,
            width,
            height,
            alt_text: alt,
        }
    }
}
