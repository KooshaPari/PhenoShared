//! Ingestion adapters — one per corpus. Each normalizes a raw transcript into a
//! [`crate::domain::session::Session`] and implements [`crate::ports::CorpusSource`].
//!
//! [`codex::CodexDir`], [`claude_code::ClaudeDir`], and [`cursor::CursorDir`]
//! accept either one transcript file or a directory to scan recursively. They
//! parse each tool's native JSONL/JSON records, including nested text content
//! blocks, while [`parse_jsonl_sessions`] remains the strict helper for already
//! normalized `Session` JSONL.

pub mod claude_code;
pub mod codex;
pub mod cursor;
pub mod forge;
mod json_source;
pub mod web;

pub use json_source::JsonIngestionReport;

use crate::domain::session::Session;
use std::io::BufRead;
use std::path::Path;

/// Errors that can occur during ingestion.
#[derive(Debug, thiserror::Error)]
pub enum IngestionError {
    /// Underlying I/O error.
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    /// JSON parse error on a line.
    #[error("JSON parse error at line {line}: {msg}")]
    Json { line: usize, msg: String },
}

/// Parse a JSONL reader into a [`Vec<Session>`].
///
/// Each non-empty line in the reader must be a JSON-serialized [`Session`].
/// Lines are numbered from 1 for error reporting.
///
/// # Errors
///
/// Returns [`IngestionError::Io`] on read failures or
/// [`IngestionError::Json`] if a line is not valid session JSON.
pub fn parse_jsonl_sessions<R: std::io::Read>(reader: R) -> Result<Vec<Session>, IngestionError> {
    let mut sessions: Vec<Session> = Vec::new();
    for (line_num, line) in std::io::BufReader::new(reader).lines().enumerate() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let session: Session = serde_json::from_str(trimmed)
            .map_err(|e| IngestionError::Json { line: line_num + 1, msg: e.to_string() })?;
        sessions.push(session);
    }
    Ok(sessions)
}

/// Read a JSONL file and parse each line as a [`Session`].
///
/// This is a convenience wrapper over [`parse_jsonl_sessions`] that opens the
/// file at `path` and delegates to the reader-based parser.
///
/// # Errors
///
/// Returns [`IngestionError::Io`] if the file cannot be opened or read, or
/// [`IngestionError::Json`] if a line is not valid session JSON.
pub fn read_jsonl_sessions<P: AsRef<Path>>(path: P) -> Result<Vec<Session>, IngestionError> {
    let file = std::fs::File::open(path)?;
    parse_jsonl_sessions(file)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};
    use std::io::Write as _;

    #[test]
    fn forge_adapter_marker_reports_corpus() {
        assert_eq!(forge::ForgeAdapter.corpus(), Corpus::Forge);
    }

    #[test]
    fn native_dir_adapters_construct_for_each_corpus() {
        let _ = claude_code::ClaudeDir::new(".");
        let _ = codex::CodexDir::new(".");
        let _ = cursor::CursorDir::new(".");
    }

    #[test]
    fn parser_ignores_blank_lines_and_preserves_session_order() {
        let mut first = Session::new("first", Corpus::Codex);
        first.messages.push(Message::new(Role::User, "one"));
        let second = Session::new("second", Corpus::Cursor);
        let input = format!(
            "\n{}\n \t\n{}\n",
            serde_json::to_string(&first).expect("serialize first session"),
            serde_json::to_string(&second).expect("serialize second session")
        );

        let sessions = parse_jsonl_sessions(input.as_bytes()).expect("parse valid JSONL");

        assert_eq!(sessions, vec![first, second]);
    }

    #[test]
    fn parser_reports_the_physical_line_for_malformed_json() {
        let valid = serde_json::to_string(&Session::new("valid", Corpus::Forge))
            .expect("serialize valid session");
        let input = format!("\n{valid}\n{{not-json}}\n");

        let error = parse_jsonl_sessions(input.as_bytes()).expect_err("line three is malformed");

        match error {
            IngestionError::Json { line, msg } => {
                assert_eq!(line, 3);
                assert!(!msg.is_empty());
            }
            IngestionError::Io(error) => panic!("expected JSON error, got {error}"),
        }
    }

    #[test]
    fn file_reader_parses_jsonl_from_disk() {
        let session = Session::new("from-file", Corpus::ClaudeCode);
        let mut file = tempfile::NamedTempFile::new().expect("create temporary JSONL");
        writeln!(file, "{}", serde_json::to_string(&session).expect("serialize session"))
            .expect("write JSONL fixture");

        let sessions = read_jsonl_sessions(file.path()).expect("read JSONL fixture");

        assert_eq!(sessions, vec![session]);
    }

    #[test]
    fn file_reader_surfaces_missing_file_as_io_error() {
        let directory = tempfile::tempdir().expect("create temporary directory");
        let missing = directory.path().join("missing.jsonl");

        assert!(matches!(read_jsonl_sessions(missing), Err(IngestionError::Io(_))));
    }
}
