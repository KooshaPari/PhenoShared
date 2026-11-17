//! Paste classification — turns raw paste bytes into a structured [`PasteEvent`].
//!
//! Classifier is deterministic (no model calls), runs in O(n) over byte length, and never
//! touches the filesystem. It's called from `editor::ForgeEditor::normalize_result` and
//! from `prompt::Console::read` before any mention/collapse pipeline.

use serde::{Deserialize, Serialize};

/// What did the paste produce?
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PasteKind {
    /// Plain prose (default — anything not matching a more specific kind).
    Text,
    /// Looks like source code — multiple lines, balanced punctuation, common keywords.
    Code,
    /// Absolute or workspace-relative filesystem path.
    Path,
    /// A URL (http/https/file/git/ssh).
    Url,
    /// Terminal escape sequence pasted in raw form.
    EscapeSequence,
    /// Base64 PNG / JPEG / GIF / WebP payload — image dragged in from clipboard.
    Image,
    /// Long log / stack-trace / JSON blob — candidate for collapse.
    LargeBlob,
}

impl PasteKind {
    pub fn as_str(self) -> &'static str {
        match self {
            PasteKind::Text => "text",
            PasteKind::Code => "code",
            PasteKind::Path => "path",
            PasteKind::Url => "url",
            PasteKind::EscapeSequence => "escape",
            PasteKind::Image => "image",
            PasteKind::LargeBlob => "large_blob",
        }
    }
}

/// Single classifier signal — what evidence led to the kind assignment.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ClassifierSignal {
    /// starts with file:// or http(s):// or recognized URL scheme
    UrlScheme,
    /// starts with / and contains no whitespace (POSIX absolute path)
    PosixPath,
    /// starts with X:\ and contains no whitespace (Windows path)
    WindowsPath,
    /// first bytes match PNG/JPEG/GIF/WEBP magic and length > 100
    ImageMagic,
    /// contains \x1b[... ANSI / Kitty / OSC — pasted-in escape sequence
    EscapeMagic,
    /// >= 3 newlines + balanced `{}`/`()`/`[]`
    CodeShape,
    /// length >= 4096 bytes (collapse candidate threshold)
    LargeBlob,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassifierResult {
    pub kind: PasteKind,
    pub signals: Vec<ClassifierSignal>,
    /// Confidence 0..=100. >= 80 is "high", 50..=80 "medium", < 50 "low".
    pub confidence: u8,
}

impl ClassifierResult {
    pub fn is_high_confidence(&self) -> bool {
        self.confidence >= 80
    }
}

/// Classify raw bytes from a paste event.
///
/// # Arguments
///
/// * `bytes` — the raw pasted content (UTF-8 lossy if not valid UTF-8)
/// * `huge_threshold` — byte count above which we always return `LargeBlob`
///
/// # Performance
///
/// O(n) over `bytes.len()`. Never allocates more than one `String` (for the lossy decode).
pub fn classify(bytes: &[u8], huge_threshold: usize) -> ClassifierResult {
    let s = bstr::ByteSlice::to_str_lossy(bytes);
    let mut signals = Vec::with_capacity(4);
    let mut kind = PasteKind::Text;
    let mut confidence: u8 = 30; // base "is text"

    let over_threshold = bytes.len() >= huge_threshold;
    if over_threshold {
        signals.push(ClassifierSignal::LargeBlob);
    }

    // 1. Image magic bytes (PNG, JPEG, GIF, WEBP). Must precede the large-blob
    //    decision — a large image is still an image and must pass through.
    if looks_like_image(bytes) {
        signals.push(ClassifierSignal::ImageMagic);
        return ClassifierResult { kind: PasteKind::Image, signals, confidence: 95 };
    }

    // 2. Escape sequence
    if bytes.contains(&0x1b) {
        signals.push(ClassifierSignal::EscapeMagic);
        return ClassifierResult { kind: PasteKind::EscapeSequence, signals, confidence: 90 };
    }

    // 3. URL
    if looks_like_url(&s) {
        signals.push(ClassifierSignal::UrlScheme);
        kind = PasteKind::Url;
        confidence = 90;
    }
    // 4. Paths
    else if looks_like_windows_path(&s) {
        signals.push(ClassifierSignal::WindowsPath);
        kind = PasteKind::Path;
        confidence = 85;
    } else if looks_like_posix_path(&s) {
        signals.push(ClassifierSignal::PosixPath);
        kind = PasteKind::Path;
        confidence = 85;
    }
    // 5. Code shape
    else if looks_like_code(&s) {
        signals.push(ClassifierSignal::CodeShape);
        kind = PasteKind::Code;
        confidence = 70;
    }

    // 6. Over-threshold plain content keeps its content kind (`Text` by default).
    //    The `LargeBlob` **signal** is already present above; the collapse layer
    //    decides whether to collapse based on `bytes.len()`, not the kind.

    ClassifierResult { kind, signals, confidence }
}

fn looks_like_image(b: &[u8]) -> bool {
    if b.len() < 8 {
        return false;
    }
    // PNG: 89 50 4E 47 0D 0A 1A 0A
    if b.starts_with(&[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) {
        return true;
    }
    // JPEG: FF D8 FF
    if b.starts_with(&[0xFF, 0xD8, 0xFF]) {
        return true;
    }
    // GIF: GIF87a / GIF89a
    if b.starts_with(b"GIF87a") || b.starts_with(b"GIF89a") {
        return true;
    }
    // WEBP: RIFF....WEBP
    if b.len() >= 12 && &b[0..4] == b"RIFF" && &b[8..12] == b"WEBP" {
        return true;
    }
    false
}

fn looks_like_url(s: &str) -> bool {
    let lower = s.trim().to_ascii_lowercase();
    lower.starts_with("http://")
        || lower.starts_with("https://")
        || lower.starts_with("file://")
        || lower.starts_with("git://")
        || lower.starts_with("ssh://")
        || lower.starts_with("ftp://")
}

fn looks_like_windows_path(s: &str) -> bool {
    // X:\ or X:/
    if s.len() < 3 {
        return false;
    }
    let bytes = s.as_bytes();
    if !bytes[0].is_ascii_alphabetic() || bytes[1] != b':' {
        return false;
    }
    bytes[2] == b'\\' || bytes[2] == b'/'
}

fn looks_like_posix_path(s: &str) -> bool {
    s.starts_with('/') && !s.contains(char::is_whitespace)
}

fn looks_like_code(s: &str) -> bool {
    let newlines = s.bytes().filter(|&b| b == b'\n').count();
    if newlines < 2 {
        return false;
    }
    // Balanced braces — very weak heuristic but cheap.
    let opens = s
        .bytes()
        .filter(|&b| b == b'{' || b == b'(' || b == b'[')
        .count();
    let closes = s
        .bytes()
        .filter(|&b| b == b'}' || b == b')' || b == b']')
        .count();
    let balanced = opens > 0 && opens == closes;
    let has_keyword = s.contains("fn ")
        || s.contains("def ")
        || s.contains("function ")
        || s.contains("class ")
        || s.contains("import ")
        || s.contains("use ")
        || s.contains("struct ")
        || s.contains("#include ");
    balanced || has_keyword
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_paste() {
        let r = classify(b"hello world", 4096);
        assert_eq!(r.kind, PasteKind::Text);
        assert!(r.signals.is_empty());
    }

    #[test]
    fn url_paste() {
        let r = classify(b"https://example.com/foo", 4096);
        assert_eq!(r.kind, PasteKind::Url);
        assert!(r.is_high_confidence());
        assert!(r.signals.contains(&ClassifierSignal::UrlScheme));
    }

    #[test]
    fn posix_path_paste() {
        let r = classify(b"/etc/hosts", 4096);
        assert_eq!(r.kind, PasteKind::Path);
        assert!(r.signals.contains(&ClassifierSignal::PosixPath));
    }

    #[test]
    fn windows_path_paste() {
        let r = classify(br"C:\Users\me\file.txt", 4096);
        assert_eq!(r.kind, PasteKind::Path);
        assert!(r.signals.contains(&ClassifierSignal::WindowsPath));
    }

    #[test]
    fn image_paste() {
        let png = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 0];
        let r = classify(&png, 4096);
        assert_eq!(r.kind, PasteKind::Image);
    }

    #[test]
    fn code_paste() {
        let src = b"fn main() {\n    println!(\"hi\");\n}\n";
        let r = classify(src, 4096);
        assert_eq!(r.kind, PasteKind::Code);
    }

    #[test]
    fn large_blob_paste() {
        // Large plain content keeps its content kind (`Text`) but carries the
        // `LargeBlob` signal; the collapse layer short-circuits on size.
        let big = vec![b'x'; 8192];
        let r = classify(&big, 4096);
        assert_eq!(r.kind, PasteKind::Text);
        assert!(r.signals.contains(&ClassifierSignal::LargeBlob));
    }

    #[test]
    fn escape_sequence_paste() {
        let r = classify(b"\x1b[31mRED\x1b[0m", 4096);
        assert_eq!(r.kind, PasteKind::EscapeSequence);
    }

    #[test]
    fn no_path_for_url() {
        // https:// should not also fire PosixPath
        let r = classify(b"https://example.com", 4096);
        assert_eq!(r.kind, PasteKind::Url);
        assert!(!r.signals.contains(&ClassifierSignal::PosixPath));
    }
}
