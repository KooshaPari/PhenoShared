//! Paste event — input boundary type that the editor produces and the pipeline consumes.
//!
//! Every paste arriving from the terminal/clipboard/drag-drop becomes a [`PasteEvent`]
//! before it enters mention parsing, collapse, or model submission. This is the seam where
//! `editor::ForgeEditor::normalize_result` (existing) hands off to the new pipeline.

use serde::{Deserialize, Serialize};

/// Source of the paste — drives UI affordance and mention-extraction policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PasteSource {
    /// User typed/pasted into the prompt (bracketed paste CSI ?2004h/l).
    TerminalBracketed,
    /// User pasted but terminal didn't negotiate bracketed mode (legacy fallback).
    TerminalRaw,
    /// Programmatic paste via `forge` subcommand (test fixture, automation).
    Programmatic,
    /// Drag-and-drop from file manager (Ghostty/iTerm2/WezTerm emit OSC52).
    DragDropFile,
    /// Image dropped from image viewer / screenshot tool (OSC52/clipboard).
    DragDropImage,
    /// Image pasted via Ctrl+V / Cmd+V (clipboard).
    ClipboardImage,
    /// Screenshot captured by the terminal (e.g. Kitty's `kitty +kitten icat`).
    TerminalScreenshot,
}

impl PasteSource {
    /// Sources where the content is safe to read into the conversation as-is (already
    /// typed/pasted by the user).
    pub const fn is_user_initiated(self) -> bool {
        matches!(
            self,
            Self::TerminalBracketed
                | Self::TerminalRaw
                | Self::DragDropFile
                | Self::DragDropImage
                | Self::ClipboardImage
                | Self::TerminalScreenshot
        )
    }

    /// Sources where the content should be treated as a side-channel (debug log,
    /// drag-drop, screenshot) and may want collapse/expand affordances.
    pub const fn is_side_channel(self) -> bool {
        matches!(
            self,
            Self::DragDropFile
                | Self::DragDropImage
                | Self::ClipboardImage
                | Self::TerminalScreenshot
                | Self::Programmatic
        )
    }
}

/// Raw paste arriving from one of the [`PasteSource`] channels.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PasteEvent {
    pub source: PasteSource,
    /// Raw bytes — UTF-8 lossy decode via `String::from_utf8_lossy` is the consumer's
    /// responsibility (some images are binary).
    pub bytes: Vec<u8>,
    /// Original terminal sequence the bytes came in (if any) — used for round-trip
    /// reconstruction during paste-out (e.g. for `paste-mode exit` cleanup).
    pub original_term: Option<String>,
    /// Timestamp (ms since epoch) when the paste was observed.
    pub received_at_ms: u64,
}

impl PasteEvent {
    pub fn new(source: PasteSource, bytes: Vec<u8>) -> Self {
        Self { source, bytes, original_term: None, received_at_ms: now_ms() }
    }

    pub fn new_programmatic(bytes: Vec<u8>) -> Self {
        Self::new(PasteSource::Programmatic, bytes)
    }

    pub fn with_original_term(mut self, term: impl Into<String>) -> Self {
        self.original_term = Some(term.into());
        self
    }

    /// Decode as UTF-8 lossy string (replacement char for invalid sequences).
    pub fn as_string(&self) -> String {
        bstr::ByteSlice::to_str_lossy(self.bytes.as_slice()).into_owned()
    }
    /// Total byte length.
    pub fn len(&self) -> usize {
        self.bytes.len()
    }

    /// True if empty paste.
    pub fn is_empty(&self) -> bool {
        self.bytes.is_empty()
    }
}

fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_classification() {
        assert!(PasteSource::TerminalBracketed.is_user_initiated());
        assert!(PasteSource::DragDropImage.is_user_initiated());
        assert!(!PasteSource::Programmatic.is_user_initiated());
        assert!(PasteSource::DragDropImage.is_side_channel());
        assert!(!PasteSource::TerminalBracketed.is_side_channel());
    }

    #[test]
    fn programmatic_construction() {
        let e = PasteEvent::new_programmatic(b"hello".to_vec());
        assert_eq!(e.source, PasteSource::Programmatic);
        assert_eq!(e.as_string(), "hello");
        assert_eq!(e.len(), 5);
        assert!(!e.is_empty());
    }

    #[test]
    fn empty_event() {
        let e = PasteEvent::new(PasteSource::TerminalRaw, vec![]);
        assert!(e.is_empty());
        assert_eq!(e.len(), 0);
    }

    #[test]
    fn with_term() {
        let e = PasteEvent::new(PasteSource::TerminalBracketed, b"x".to_vec())
            .with_original_term("xterm-256color");
        assert_eq!(e.original_term.as_deref(), Some("xterm-256color"));
    }

    #[test]
    fn lossy_decode_handles_binary() {
        let mut bytes = vec![0xFF, 0xFE, 0xFD];
        bytes.extend_from_slice(b"hello");
        let e = PasteEvent::new(PasteSource::ClipboardImage, bytes);
        // Should not panic; replacement chars are fine.
        let _s = e.as_string();
    }
}
