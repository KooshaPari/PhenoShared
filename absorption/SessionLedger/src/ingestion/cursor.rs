//! Cursor native transcript adapter.
//!
//! Reads JSONL event streams and JSON session objects from a file or recursively
//! from a Cursor session directory. Direct role/content messages and nested
//! `messages` or `conversation` arrays are supported.

use std::path::PathBuf;

use crate::{
    domain::session::{Corpus, Session},
    ingestion::json_source::{JsonCorpusSource, JsonIngestionReport},
    ports::{CorpusSource, PortError},
};

/// A Cursor transcript file or directory corpus.
#[derive(Debug, Clone)]
pub struct CursorDir {
    source: JsonCorpusSource,
}

impl CursorDir {
    /// Create a source rooted at a transcript file or directory.
    #[must_use]
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self { source: JsonCorpusSource::new(path, Corpus::Cursor) }
    }

    /// Load a transcript and return malformed-line accounting.
    ///
    /// # Errors
    /// Returns [`PortError`] if the transcript cannot be found or read.
    pub fn load_with_report(&self, id: &str) -> Result<(Session, JsonIngestionReport), PortError> {
        self.source.load_with_report(id)
    }
}

impl CorpusSource for CursorDir {
    fn list(&self) -> Result<Vec<String>, PortError> {
        self.source.list()
    }

    fn load(&self, id: &str) -> Result<Session, PortError> {
        self.source.load(id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::Role;

    #[test]
    fn parses_cursor_json_session_object() {
        let file = tempfile::Builder::new().suffix(".json").tempfile().expect("temp file");
        std::fs::write(
            file.path(),
            serde_json::json!({
                "conversationId": "cursor-1",
                "title": "JSON fixture",
                "messages": [
                    {"role": "user", "content": "hello"},
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "hi"}]
                    }
                ]
            })
            .to_string(),
        )
        .expect("fixture");

        let source = CursorDir::new(file.path());
        let id = source.list().expect("list").remove(0);
        let session = source.load(&id).expect("load");
        assert_eq!(session.id, "cursor-1");
        assert_eq!(session.title.as_deref(), Some("JSON fixture"));
        assert_eq!(session.messages.len(), 2);
        assert_eq!(session.messages[0].role, Role::User);
        assert_eq!(session.messages[1].content, "hi");
    }
}
