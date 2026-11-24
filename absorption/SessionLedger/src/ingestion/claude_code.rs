//! Claude Code native transcript adapter.
//!
//! Reads a transcript file or recursively scans a `~/.claude/projects`-style
//! directory. Outer event roles and nested Anthropic content blocks are
//! normalized into [`Session`](crate::domain::session::Session) values.

use std::path::PathBuf;

use crate::{
    domain::session::{Corpus, Session},
    ingestion::json_source::{JsonCorpusSource, JsonIngestionReport},
    ports::{CorpusSource, PortError},
};

/// A Claude Code transcript file or directory corpus.
#[derive(Debug, Clone)]
pub struct ClaudeDir {
    source: JsonCorpusSource,
}

impl ClaudeDir {
    /// Create a source rooted at a transcript file or directory.
    #[must_use]
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self { source: JsonCorpusSource::new(path, Corpus::ClaudeCode) }
    }

    /// Load a transcript and return malformed-line accounting.
    ///
    /// # Errors
    /// Returns [`PortError`] if the transcript cannot be found or read.
    pub fn load_with_report(&self, id: &str) -> Result<(Session, JsonIngestionReport), PortError> {
        self.source.load_with_report(id)
    }
}

impl CorpusSource for ClaudeDir {
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
    fn parses_claude_nested_messages() {
        let directory = tempfile::tempdir().expect("temp directory");
        let project = directory.path().join("project");
        std::fs::create_dir(&project).expect("project directory");
        let path = project.join("session.jsonl");
        let mut file = std::fs::File::create(&path).expect("fixture");
        writeln!(
            file,
            "{}",
            serde_json::json!({
                "type": "assistant",
                "sessionId": "claude-1",
                "cwd": "/repo",
                "timestamp": 456,
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "done"}]
                }
            })
        )
        .expect("message");

        let source = ClaudeDir::new(directory.path());
        assert_eq!(source.list().expect("list"), vec!["project/session.jsonl"]);
        let session = source.load("project/session.jsonl").expect("load");
        assert_eq!(session.id, "claude-1");
        assert_eq!(session.corpus, Corpus::ClaudeCode);
        assert_eq!(session.messages[0].role, Role::Assistant);
        assert_eq!(session.messages[0].content, "done");
        assert_eq!(session.messages[0].ts_ms, Some(456));
    }
}
