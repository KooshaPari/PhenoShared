//! Context bundle model — the working state a resumed session needs to know.
//!
//! Extracted from a session's message stream: what files were touched, what
//! decisions were reached, what symbols/types are load-bearing, and what
//! environment state was established.

use serde::{Deserialize, Serialize};

/// A single extracted decision with optional rationale.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Decision {
    /// Short summary (e.g. "use Axum over Actix").
    pub summary: String,
    /// Context that motivated the choice, when discernible.
    pub rationale: Option<String>,
}

/// Structured working-context extracted from a session's messages.
///
/// This is the output of the [`ContextExtractor`](crate::ports::ContextExtractor)
/// port: the distilled files, decisions, symbols, and environment that a
/// continuation needs to act without re-reading the entire transcript.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Context {
    /// Working directory / project root, when known.
    pub cwd: Option<String>,
    /// Session title or topic, when known.
    pub title: Option<String>,
    /// File paths explicitly mentioned in session messages.
    pub files_mentioned: Vec<String>,
    /// Key technical decisions reached during the session.
    pub key_decisions: Vec<Decision>,
    /// Important symbols / types / identifiers referenced.
    pub key_symbols: Vec<String>,
    /// Environment notes (dependencies installed, config changed, etc.).
    pub environment_notes: Vec<String>,
}

impl Context {
    /// Empty context — nothing extracted yet.
    #[must_use]
    pub fn empty() -> Self {
        Self {
            cwd: None,
            title: None,
            files_mentioned: Vec::new(),
            key_decisions: Vec::new(),
            key_symbols: Vec::new(),
            environment_notes: Vec::new(),
        }
    }

    /// Whether the extractor found any meaningful context data.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.cwd.is_none()
            && self.title.is_none()
            && self.files_mentioned.is_empty()
            && self.key_decisions.is_empty()
            && self.key_symbols.is_empty()
            && self.environment_notes.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_context_is_empty() {
        assert!(Context::empty().is_empty());
    }

    #[test]
    fn empty_context_all_fields_none_or_empty() {
        let ctx = Context::empty();
        assert!(ctx.cwd.is_none());
        assert!(ctx.title.is_none());
        assert!(ctx.files_mentioned.is_empty());
        assert!(ctx.key_decisions.is_empty());
        assert!(ctx.key_symbols.is_empty());
        assert!(ctx.environment_notes.is_empty());
    }

    #[test]
    fn cwd_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.cwd = Some("/home/user/project".into());
        assert!(!ctx.is_empty());
    }

    #[test]
    fn title_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.title = Some("fix auth bug".into());
        assert!(!ctx.is_empty());
    }

    #[test]
    fn files_mentioned_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.files_mentioned.push("src/main.rs".into());
        assert!(!ctx.is_empty());
    }

    #[test]
    fn key_decisions_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.key_decisions.push(Decision { summary: "use Axum".into(), rationale: None });
        assert!(!ctx.is_empty());
    }

    #[test]
    fn key_symbols_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.key_symbols.push("SessionLedger".into());
        assert!(!ctx.is_empty());
    }

    #[test]
    fn environment_notes_alone_makes_non_empty() {
        let mut ctx = Context::empty();
        ctx.environment_notes.push("cargo installed".into());
        assert!(!ctx.is_empty());
    }

    #[test]
    fn decision_rationale_can_be_none() {
        let d = Decision { summary: "s".into(), rationale: None };
        assert!(d.rationale.is_none());
    }

    #[test]
    fn decision_rationale_can_be_some() {
        let d = Decision { summary: "s".into(), rationale: Some("because".into()) };
        assert_eq!(d.rationale.as_deref(), Some("because"));
    }
}
