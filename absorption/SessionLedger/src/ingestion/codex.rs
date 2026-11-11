//! Codex native transcript adapter.
//!
//! Reads a transcript file or recursively scans a `~/.codex`-style directory.
//! Codex `session_meta`, `response_item`, and `event_msg` JSONL records are
//! normalized into [`Session`](crate::domain::session::Session) values.

use std::path::PathBuf;

use crate::{
    domain::session::{Corpus, Session},
    ingestion::json_source::{JsonCorpusSource, JsonIngestionReport},
    ports::{CorpusSource, PortError},
};

/// A Codex transcript file or directory corpus.
#[derive(Debug, Clone)]
pub struct CodexDir {
    source: JsonCorpusSource,
}

impl CodexDir {
    /// Create a source rooted at a transcript file or directory.
    #[must_use]
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self { source: JsonCorpusSource::new(path, Corpus::Codex) }
    }

    /// Load a transcript and return malformed-line accounting.
    ///
    /// # Errors
    /// Returns [`PortError`] if the transcript cannot be found or read.
    pub fn load_with_report(&self, id: &str) -> Result<(Session, JsonIngestionReport), PortError> {
        self.source.load_with_report(id)
    }
}

impl CorpusSource for CodexDir {
    fn list(&self) -> Result<Vec<String>, PortError> {
        self.source.list()
    }

    fn load(&self, id: &str) -> Result<Session, PortError> {
        self.source.load(id)
    }
}

#[cfg(test)]
mod tests {
    use std::io::Write;

    use super::*;
    use crate::domain::session::Role;

    #[test]
    fn parses_codex_rollout_jsonl_and_accounts_for_bad_lines() {
        let mut file = tempfile::NamedTempFile::new().expect("temp file");
        writeln!(
            file,
            "{}",
            serde_json::json!({
                "type": "session_meta",
                "payload": {"id": "codex-1", "cwd": "/repo"}
            })
        )
        .expect("metadata");
        writeln!(
            file,
            "{}",
            serde_json::json!({
                "timestamp": "2026-07-11T06:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "ship it"}]
                }
            })
        )
        .expect("message");
        writeln!(file, "{{not json").expect("bad line");

        let source = CodexDir::new(file.path());
        let id = source.list().expect("list").remove(0);
        let (session, report) = source.load_with_report(&id).expect("load");
        assert_eq!(session.id, "codex-1");
        assert_eq!(session.cwd.as_deref(), Some("/repo"));
        assert_eq!(session.messages[0].role, Role::User);
        assert_eq!(session.messages[0].content, "ship it");
        assert_eq!(session.messages[0].ts_ms, Some(1_783_749_600_000));
        assert_eq!(report.ingested, 1);
        assert_eq!(report.skipped.len(), 1);
    }
}
