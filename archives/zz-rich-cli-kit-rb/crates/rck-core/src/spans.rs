//! Mixed text spans — plain text + OSC-8 hyperlinks.
//!
//! Panel bodies and progress labels accept `Vec<Span>` so agents can weave
//! clickable links into otherwise-plain output. On terminals without
//! hyperlink support the link text is rendered plain.

use crate::emit::emit_hyperlink;
use crate::Capabilities;
use serde::{Deserialize, Serialize};

/// A single inline element of mixed panel/progress content.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Span {
    /// Plain text.
    Text { text: String },
    /// A hyperlink (OSC 8) with visible `text` pointing at `url`.
    Link { url: String, text: String },
}

impl Span {
    pub fn text<S: Into<String>>(s: S) -> Self {
        Span::Text { text: s.into() }
    }

    pub fn link<U: Into<String>, T: Into<String>>(url: U, text: T) -> Self {
        Span::Link {
            url: url.into(),
            text: text.into(),
        }
    }

    /// The visible text of this span (no escape sequences).
    pub fn visible(&self) -> &str {
        match self {
            Span::Text { text } | Span::Link { text, .. } => text,
        }
    }

    /// Render this span using the given capabilities. The returned string
    /// contains any OSC 8 + tmux DCS wrapping required.
    pub fn render(&self, caps: &Capabilities) -> String {
        match self {
            Span::Text { text } => text.clone(),
            Span::Link { url, text } => emit_hyperlink(caps.hyperlinks, caps.in_tmux, url, text),
        }
    }
}

/// Render a slice of spans into one string.
pub fn render_spans(caps: &Capabilities, spans: &[Span]) -> String {
    let mut s = String::new();
    for span in spans {
        s.push_str(&span.render(caps));
    }
    s
}

/// Visible width in terminal cells of a slice of spans, using unicode-width
/// across grapheme clusters. ANSI SGR sequences inside span text are ignored.
pub fn spans_width(spans: &[Span]) -> usize {
    let mut w = 0usize;
    for span in spans {
        w += crate::width::visible_width(span.visible());
    }
    w
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capabilities::Capabilities;

    fn caps(hyperlinks: bool) -> Capabilities {
        Capabilities {
            graphics: false,
            sixel: false,
            truecolor: false,
            unicode_width: 2,
            terminal: "test".into(),
            is_tty: true,
            hyperlinks,
            clipboard: false,
            task_markers: false,
            kitty_keyboard: false,
            in_tmux: false,
        }
    }

    #[test]
    fn plain_spans_roundtrip() {
        let spans = vec![Span::text("hello "), Span::text("world")];
        assert_eq!(render_spans(&caps(true), &spans), "hello world");
    }

    #[test]
    fn link_span_wraps_when_supported() {
        let spans = vec![Span::text("see "), Span::link("https://x", "docs")];
        let s = render_spans(&caps(true), &spans);
        assert!(s.contains("\x1b]8;;https://x\x1b\\"));
        assert!(s.contains("docs"));
    }

    #[test]
    fn link_span_falls_back_to_plain() {
        let spans = vec![Span::link("https://x", "docs")];
        let s = render_spans(&caps(false), &spans);
        assert_eq!(s, "docs");
    }
}
