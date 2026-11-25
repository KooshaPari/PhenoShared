//! Paste collapse — replace long pastes with a placeholder + summary.
//!
//! Why collapse?
//! * Terminal pastes can be 10s of MB (e.g. a minified JS file). Sending the raw bytes to
//!   the model blows the context window.
//! * Long stack traces / logs are usually the same content the user can scroll back to.
//! * The placeholder `@[collapsed:N chars kind=Code first=... last=...]` lets the agent
//!   `read` the file instead if it needs the content.
//!
//! This is the "I7" / "I4" gap from the audit.

use crate::classifier::{classify, ClassifierResult, PasteKind};
use crate::paste_event::PasteEvent;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CollapseConfig {
    /// Default threshold for collapsing (bytes). Pasters longer than this get collapsed.
    pub threshold_bytes: usize,
    /// When collapsing, how many leading bytes to keep verbatim.
    pub head_keep_bytes: usize,
    /// When collapsing, how many trailing bytes to keep verbatim.
    pub tail_keep_bytes: usize,
    /// Classifiers whose result short-circuits collapse (images are always kept).
    pub keep_kinds: Vec<PasteKind>,
}

impl Default for CollapseConfig {
    fn default() -> Self {
        Self {
            threshold_bytes: 4 * 1024, // 4 KiB
            head_keep_bytes: 256,
            tail_keep_bytes: 256,
            keep_kinds: vec![PasteKind::Image, PasteKind::EscapeSequence],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum CollapseOutcome {
    /// Below threshold OR in keep_kinds — paste forwarded unchanged.
    Passthrough { len: usize, paste_kind: PasteKind },
    /// Above threshold — collapsed to a placeholder.
    Collapsed {
        original_len: usize,
        kept_bytes: usize,
        paste_kind: PasteKind,
        /// The placeholder text that replaces the original paste in the prompt.
        placeholder: String,
    },
}

impl CollapseOutcome {
    pub fn is_collapsed(&self) -> bool {
        matches!(self, CollapseOutcome::Collapsed { .. })
    }

    pub fn rewritten(&self) -> String {
        match self {
            CollapseOutcome::Passthrough { .. } => String::new(), // no rewrite needed
            CollapseOutcome::Collapsed { placeholder, .. } => placeholder.clone(),
        }
    }
}

/// Apply collapse policy to a paste event.
///
/// Pure function — does not touch the filesystem. The placeholder is intended to be
/// injected into the prompt via `@[collapsed:N chars kind=Code first=... last=...]`.
pub fn collapse_paste(event: &PasteEvent, cfg: &CollapseConfig) -> CollapseOutcome {
    let cr: ClassifierResult = classify(&event.bytes, cfg.threshold_bytes);

    // Images/escapes always pass through.
    if cfg.keep_kinds.contains(&cr.kind) {
        return CollapseOutcome::Passthrough { len: event.bytes.len(), paste_kind: cr.kind };
    }
    // Below threshold — pass through.
    if event.bytes.len() < cfg.threshold_bytes {
        return CollapseOutcome::Passthrough { len: event.bytes.len(), paste_kind: cr.kind };
    }

    // Build placeholder
    let total = event.bytes.len();
    let head_end = cfg.head_keep_bytes.min(total);
    let tail_start = total.saturating_sub(cfg.tail_keep_bytes);
    let kept = head_end + (total - tail_start);

    let head = bstr::ByteSlice::to_str_lossy(&event.bytes[..head_end]);
    let tail = bstr::ByteSlice::to_str_lossy(&event.bytes[tail_start..]);
    let first_line = head.lines().next().unwrap_or("").trim();
    let last_line = tail.lines().last().unwrap_or("").trim();

    let placeholder = format!(
        "@[collapsed:{} bytes kind={} first=\"{}\" last=\"{}\"]",
        total,
        cr.kind.as_str(),
        truncate(first_line, 60),
        truncate(last_line, 60),
    );

    CollapseOutcome::Collapsed {
        original_len: total,
        kept_bytes: kept,
        paste_kind: cr.kind,
        placeholder,
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}…", &s[..max])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn paste(s: &str) -> PasteEvent {
        PasteEvent::new_programmatic(s.as_bytes().to_vec())
    }

    #[test]
    fn small_paste_passes_through() {
        let p = paste("hello world");
        let cfg = CollapseConfig::default();
        let r = collapse_paste(&p, &cfg);
        assert!(!r.is_collapsed());
        assert_eq!(r.rewritten(), "");
    }

    #[test]
    fn large_text_collapses() {
        let p = paste(&"x".repeat(8192));
        let cfg = CollapseConfig::default();
        let r = collapse_paste(&p, &cfg);
        assert!(r.is_collapsed());
        if let CollapseOutcome::Collapsed { placeholder, .. } = r {
            assert!(placeholder.contains("collapsed:8192 bytes"));
            assert!(placeholder.contains("kind=text"));
        }
    }

    #[test]
    fn large_code_collapses() {
        let p = paste(&format!(
            "fn main() {{\n    println!(\"hi\");\n}}\n{}",
            "x".repeat(8192)
        ));
        let cfg = CollapseConfig::default();
        let r = collapse_paste(&p, &cfg);
        assert!(r.is_collapsed());
        if let CollapseOutcome::Collapsed { placeholder, .. } = r {
            assert!(placeholder.contains("kind=code"));
            assert!(placeholder.contains("first=\"fn main()"));
        }
    }

    #[test]
    fn image_passes_through_even_if_large() {
        let bytes = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
        let mut bytes = bytes.repeat(2000);
        bytes.truncate(8000);
        let p = PasteEvent::new(crate::paste_event::PasteSource::ClipboardImage, bytes);
        let cfg = CollapseConfig::default();
        let r = collapse_paste(&p, &cfg);
        assert!(!r.is_collapsed());
    }

    #[test]
    fn placeholder_includes_first_last_line() {
        let mut p_text = String::from("first line here\n");
        p_text.push_str(&"filler line\n".repeat(1000));
        p_text.push_str("last line here\n");
        let p = paste(&p_text);
        let cfg = CollapseConfig::default();
        let r = collapse_paste(&p, &cfg);
        if let CollapseOutcome::Collapsed { placeholder, .. } = r {
            assert!(placeholder.contains("first=\"first line here"));
            assert!(placeholder.contains("last=\"last line here"));
        } else {
            panic!("expected collapsed");
        }
    }

    #[test]
    fn threshold_is_per_byte() {
        let cfg = CollapseConfig { threshold_bytes: 100, ..Default::default() };
        let p = paste(&"x".repeat(99));
        assert!(!collapse_paste(&p, &cfg).is_collapsed());
        let p = paste(&"x".repeat(100));
        assert!(collapse_paste(&p, &cfg).is_collapsed());
    }
}
