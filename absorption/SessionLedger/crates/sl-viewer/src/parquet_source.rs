//! Parquet corpus source for Claude Code conversation exports.
//!
//! Claude Code drops conversation-history files under `~/.claude/projects` as
//! either JSONL or — on newer macOS builds — Parquet. The JSONL path is
//! handled by [`crate::corpus_loader`] via [`session_ledger::ClaudeDir`]; the
//! Parquet variant was previously silently skipped, which left a real data gap
//! for any user whose install writes `.parquet` rather than `.jsonl`.
//!
//! This module wires the row-based [`parquet`] reader into the
//! [`session_ledger::ports::CorpusSource`] trait used by the viewer. It is
//! compiled only when the `parquet` cargo feature is enabled; otherwise the
//! module compiles to a no-op `cfg`-stub so the rest of the crate stays
//! untouched.
//!
//! Expected per-row schema (one row per message; column order and repetition
//! are not enforced, but the names below are recognised case-insensitively):
//!
//! | column        | type     | notes                                |
//! |---------------|----------|--------------------------------------|
//! | `session_id`  | string   | REQUIRED; groups rows into sessions  |
//! | `role`        | string   | user / assistant / tool / system     |
//! | `content`     | string   | REQUIRED; the message body           |
//! | `ts_ms`       | int64    | Unix milliseconds; optional          |
//! | `cwd`         | string   | optional; first non-null wins        |
//! | `title`       | string   | optional; first non-null wins        |
//!
//! Each `.parquet` file may hold one or many sessions. A single file's rows are
//! grouped by `session_id`; the loader exposes one session per unique id.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    sync::OnceLock,
};

use parquet::{
    file::reader::{FileReader, SerializedFileReader},
    record::{Field, Row},
};
use session_ledger::{
    domain::session::{Corpus, Message, Role, Session},
    ports::{CorpusSource, PortError},
};

/// Parquet corpus source rooted at a `~/.claude/projects`-style directory.
///
/// One instance per directory. The session-id → file-path index is built
/// lazily on the first call to [`CorpusSource::list`] and then reused for any
/// subsequent [`CorpusSource::load`] calls so we re-read each parquet file at
/// most twice total (once for discovery, once for hydration).
pub struct ParquetCorpusSource {
    root: PathBuf,
    index: OnceLock<Result<BTreeMap<String, PathBuf>, String>>,
}

impl ParquetCorpusSource {
    /// Create a new source rooted at `root`.
    ///
    /// The directory does not have to exist; an empty `list()` is returned in
    /// that case so the loader can silently skip the root without surfacing a
    /// hard error for end users who do not have a Claude install.
    #[must_use]
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into(), index: OnceLock::new() }
    }

    /// Return the root directory backing this source.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Build (or return the cached) `session_id -> file_path` index.
    fn ensure_index(&self) -> Result<&BTreeMap<String, PathBuf>, PortError> {
        let result = self.index.get_or_init(|| build_index(&self.root).map_err(|e| e.to_string()));
        match result {
            Ok(index) => Ok(index),
            Err(message) => Err(PortError::Backend(message.clone())),
        }
    }
}

impl CorpusSource for ParquetCorpusSource {
    fn list(&self) -> Result<Vec<String>, PortError> {
        Ok(self.ensure_index()?.keys().cloned().collect())
    }

    fn load(&self, id: &str) -> Result<Session, PortError> {
        let index = self.ensure_index()?;
        let path = index.get(id).ok_or_else(|| PortError::NotFound(id.to_owned()))?.clone();
        load_session_from_file(&path, id)
    }
}

// ── index construction ───────────────────────────────────────────────────────

fn build_index(root: &Path) -> Result<BTreeMap<String, PathBuf>, ParquetSourceError> {
    let mut index: BTreeMap<String, PathBuf> = BTreeMap::new();
    let files = discover_parquet_files(root)?;
    for path in files {
        let ids = session_ids_in_file(&path)?;
        for id in ids {
            if let Some(prior) = index.insert(id.clone(), path.clone()) {
                // Two parquet files claim the same session id — keep the first
                // and surface a warning so duplicate-export noise is visible.
                eprintln!(
                    "[sl-viewer] parquet: duplicate session id {id} across {} and {}; keeping first",
                    prior.display(),
                    path.display()
                );
            }
        }
    }
    Ok(index)
}

fn discover_parquet_files(root: &Path) -> Result<Vec<PathBuf>, ParquetSourceError> {
    if !root.exists() {
        return Ok(Vec::new());
    }
    if !root.is_dir() {
        return Err(ParquetSourceError::Backend(format!(
            "parquet root is not a directory: {}",
            root.display()
        )));
    }
    let mut out = Vec::new();
    collect_parquet_files(root, &mut out)?;
    out.sort();
    Ok(out)
}

fn collect_parquet_files(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), ParquetSourceError> {
    let entries = fs::read_dir(dir)
        .map_err(|e| ParquetSourceError::Backend(format!("read_dir {}: {e}", dir.display())))?;
    for entry in entries {
        let entry = entry.map_err(|e| {
            ParquetSourceError::Backend(format!("read entry in {}: {e}", dir.display()))
        })?;
        let path = entry.path();
        if path.is_dir() {
            collect_parquet_files(&path, out)?;
        } else if path.extension().and_then(|s| s.to_str()) == Some("parquet") {
            out.push(path);
        }
    }
    Ok(())
}

/// Read every row in `path` and collect the distinct session ids it contains.
///
/// A missing or unreadable file is reported as a backend error so the caller
/// can decide whether to skip it (loader path) or fail (test path).
fn session_ids_in_file(path: &Path) -> Result<Vec<String>, ParquetSourceError> {
    let file = fs::File::open(path)
        .map_err(|e| ParquetSourceError::Backend(format!("open {}: {e}", path.display())))?;
    let reader = SerializedFileReader::new(file).map_err(|e| {
        ParquetSourceError::Backend(format!("parquet reader {}: {e}", path.display()))
    })?;
    let iter = reader.get_row_iter(None).map_err(|e| {
        ParquetSourceError::Backend(format!("parquet iter {}: {e}", path.display()))
    })?;
    let mut seen: Vec<String> = Vec::new();
    for row in iter {
        let row = row.map_err(|e| {
            ParquetSourceError::Backend(format!("parquet row in {}: {e}", path.display()))
        })?;
        if let Some(id) =
            field_string_by_name(&row, &["session_id", "sessionId", "conversation_id"])
        {
            if !seen.iter().any(|existing| existing == &id) {
                seen.push(id);
            }
        }
    }
    Ok(seen)
}

// ── per-file load ────────────────────────────────────────────────────────────

fn load_session_from_file(path: &Path, session_id: &str) -> Result<Session, PortError> {
    let file = fs::File::open(path)
        .map_err(|e| PortError::Backend(format!("open {}: {e}", path.display())))?;
    let reader = SerializedFileReader::new(file)
        .map_err(|e| PortError::Backend(format!("parquet reader {}: {e}", path.display())))?;
    let iter = reader
        .get_row_iter(None)
        .map_err(|e| PortError::Backend(format!("parquet iter {}: {e}", path.display())))?;

    let mut session = Session::new(session_id, Corpus::ClaudeCode);
    let mut cwd_seen = false;
    let mut title_seen = false;
    let mut messages: Vec<Message> = Vec::new();

    for row in iter {
        let row =
            row.map_err(|e| PortError::Backend(format!("parquet row in {}: {e}", path.display())))?;

        // Session scoping: a file may contain rows for many sessions. Only
        // rows whose session_id matches the requested id contribute messages
        // (and metadata).
        let row_session =
            field_string_by_name(&row, &["session_id", "sessionId", "conversation_id"]);
        if row_session.as_deref() != Some(session_id) {
            continue;
        }

        if !cwd_seen {
            if let Some(cwd) = field_string_by_name(&row, &["cwd", "workingDirectory", "workspace"])
            {
                session.cwd = Some(cwd);
                cwd_seen = true;
            }
        }
        if !title_seen {
            if let Some(title) = field_string_by_name(&row, &["title", "name"]) {
                session.title = Some(title);
                title_seen = true;
            }
        }

        let content = match field_string_by_name(&row, &["content", "text", "message"]) {
            Some(c) => c,
            None => continue,
        };
        let role = field_string_by_name(&row, &["role"])
            .as_deref()
            .and_then(map_role)
            .unwrap_or(Role::User);
        let ts_ms = field_int_by_name(&row, &["ts_ms", "timestamp_ms", "timestamp"]);
        messages.push(Message { role, content, ts_ms });
    }

    session.messages = messages;
    Ok(session)
}

// ── field extraction helpers ────────────────────────────────────────────────

fn field_string_by_name(row: &Row, candidates: &[&str]) -> Option<String> {
    for (name, field) in row.get_column_iter() {
        if !candidates.iter().any(|c| name.eq_ignore_ascii_case(c)) {
            continue;
        }
        if let Some(value) = field_to_string(field) {
            return Some(value);
        }
    }
    None
}

fn field_int_by_name(row: &Row, candidates: &[&str]) -> Option<i64> {
    for (name, field) in row.get_column_iter() {
        if !candidates.iter().any(|c| name.eq_ignore_ascii_case(c)) {
            continue;
        }
        if let Some(value) = field_to_i64(field) {
            return Some(value);
        }
    }
    None
}

fn field_to_string(field: &Field) -> Option<String> {
    match field {
        Field::Null => None,
        Field::Str(s) => Some(s.clone()),
        Field::Bytes(b) => Some(b.as_utf8().ok()?.to_owned()),
        Field::Bool(b) => Some(b.to_string()),
        Field::Int(i) => Some(i.to_string()),
        Field::Long(i) => Some(i.to_string()),
        Field::Float(f) => Some(f.to_string()),
        Field::Double(f) => Some(f.to_string()),
        Field::TimestampMillis(i) => Some(i.to_string()),
        Field::TimestampMicros(i) => Some(i.to_string()),
        _ => None,
    }
}

fn field_to_i64(field: &Field) -> Option<i64> {
    match field {
        Field::Long(i) => Some(*i),
        Field::Int(i) => Some(i64::from(*i)),
        Field::Short(i) => Some(i64::from(*i)),
        Field::Byte(i) => Some(i64::from(*i)),
        Field::UByte(i) => Some(i64::from(*i)),
        Field::UShort(i) => Some(i64::from(*i)),
        Field::UInt(i) => Some(i64::from(*i)),
        Field::ULong(i) => i64::try_from(*i).ok(),
        Field::Bool(b) => Some(i64::from(*b)),
        Field::TimestampMillis(i) => Some(*i),
        Field::TimestampMicros(i) => Some(*i / 1000),
        Field::Str(s) => s.trim().parse::<i64>().ok(),
        _ => None,
    }
}

fn map_role(value: &str) -> Option<Role> {
    match value.to_ascii_lowercase().as_str() {
        "user" | "human" => Some(Role::User),
        "assistant" | "agent" | "claude" => Some(Role::Assistant),
        "system" | "developer" => Some(Role::System),
        "tool" | "tool_result" | "tool-result" | "function" => Some(Role::Tool),
        "subagent" => Some(Role::Subagent),
        _ => None,
    }
}

/// Errors that arise while reading parquet files in this module.
#[derive(Debug)]
enum ParquetSourceError {
    /// A backend error wrapping a lower-level io / parse failure.
    Backend(String),
}

impl std::fmt::Display for ParquetSourceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Backend(message) => f.write_str(message),
        }
    }
}

impl std::error::Error for ParquetSourceError {}

// ── tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn list_returns_session_ids_for_every_unique_session() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("transcripts.parquet");
        test_fixture::write_fixture(
            &path,
            &[
                test_fixture::FixtureRow {
                    session_id: "sess-aaa".into(),
                    role: "user".into(),
                    content: "hello".into(),
                    ts_ms: Some(1_700_000_000_000),
                    cwd: Some("/repo/a".into()),
                    title: Some("alpha".into()),
                },
                test_fixture::FixtureRow {
                    session_id: "sess-aaa".into(),
                    role: "assistant".into(),
                    content: "hi".into(),
                    ts_ms: Some(1_700_000_001_000),
                    cwd: None,
                    title: None,
                },
                test_fixture::FixtureRow {
                    session_id: "sess-bbb".into(),
                    role: "user".into(),
                    content: "second session".into(),
                    ts_ms: Some(1_700_000_002_000),
                    cwd: Some("/repo/b".into()),
                    title: Some("beta".into()),
                },
            ],
        );

        let source = ParquetCorpusSource::new(dir.path());
        let ids = source.list().expect("list");
        assert_eq!(ids, vec!["sess-aaa".to_owned(), "sess-bbb".to_owned()]);
    }

    #[test]
    fn load_returns_messages_for_a_single_session() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("transcripts.parquet");
        test_fixture::write_fixture(
            &path,
            &[
                test_fixture::FixtureRow {
                    session_id: "sess-aaa".into(),
                    role: "user".into(),
                    content: "hello".into(),
                    ts_ms: Some(1_700_000_000_000),
                    cwd: Some("/repo/a".into()),
                    title: Some("alpha".into()),
                },
                test_fixture::FixtureRow {
                    session_id: "sess-aaa".into(),
                    role: "assistant".into(),
                    content: "hi there".into(),
                    ts_ms: Some(1_700_000_001_000),
                    cwd: None,
                    title: None,
                },
                test_fixture::FixtureRow {
                    session_id: "sess-bbb".into(),
                    role: "user".into(),
                    content: "unrelated session content".into(),
                    ts_ms: Some(1_700_000_002_000),
                    cwd: Some("/repo/b".into()),
                    title: Some("beta".into()),
                },
            ],
        );

        let source = ParquetCorpusSource::new(dir.path());
        let session = source.load("sess-aaa").expect("load session");
        assert_eq!(session.id, "sess-aaa");
        assert_eq!(session.corpus, Corpus::ClaudeCode);
        assert_eq!(session.cwd.as_deref(), Some("/repo/a"));
        assert_eq!(session.title.as_deref(), Some("alpha"));
        assert_eq!(session.messages.len(), 2);
        assert_eq!(session.messages[0].role, Role::User);
        assert_eq!(session.messages[0].content, "hello");
        assert_eq!(session.messages[0].ts_ms, Some(1_700_000_000_000));
        assert_eq!(session.messages[1].role, Role::Assistant);
        assert_eq!(session.messages[1].content, "hi there");
        assert_eq!(session.messages[1].ts_ms, Some(1_700_000_001_000));
    }

    #[test]
    fn list_returns_empty_for_missing_directory() {
        let dir = tempfile::tempdir().expect("tempdir");
        let source = ParquetCorpusSource::new(dir.path().join("does-not-exist"));
        assert!(source.list().expect("list missing dir").is_empty());
    }

    #[test]
    fn load_returns_not_found_for_unknown_id() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("transcripts.parquet");
        test_fixture::write_fixture(
            &path,
            &[test_fixture::FixtureRow {
                session_id: "sess-aaa".into(),
                role: "user".into(),
                content: "hello".into(),
                ts_ms: Some(1),
                cwd: None,
                title: None,
            }],
        );
        let source = ParquetCorpusSource::new(dir.path());
        let error = source.load("missing").expect_err("load should fail");
        assert!(matches!(error, PortError::NotFound(_)));
    }

    #[test]
    fn load_discovers_files_in_nested_project_directories() {
        // Mimic the `~/.claude/projects/-Users-foo-repo/transcript.parquet`
        // layout that the JSONL loader already supports.
        let root = tempfile::tempdir().expect("tempdir");
        let project = root.path().join("-Users-foo-repo");
        fs::create_dir_all(&project).expect("mkdir");
        let nested = project.join("transcripts.parquet");
        test_fixture::write_fixture(
            &nested,
            &[
                test_fixture::FixtureRow {
                    session_id: "deep-session".into(),
                    role: "user".into(),
                    content: "nested hello".into(),
                    ts_ms: Some(42),
                    cwd: Some("/repo/nested".into()),
                    title: None,
                },
                test_fixture::FixtureRow {
                    session_id: "deep-session".into(),
                    role: "assistant".into(),
                    content: "nested hi".into(),
                    ts_ms: Some(43),
                    cwd: None,
                    title: Some("nested-title".into()),
                },
            ],
        );

        let source = ParquetCorpusSource::new(root.path());
        let ids = source.list().expect("list nested");
        assert_eq!(ids, vec!["deep-session".to_owned()]);

        let session = source.load("deep-session").expect("load nested");
        assert_eq!(session.messages.len(), 2);
        assert_eq!(session.messages[0].content, "nested hello");
        assert_eq!(session.title.as_deref(), Some("nested-title"));
        assert_eq!(session.cwd.as_deref(), Some("/repo/nested"));
    }
}

/// Test fixture helpers — public so corpus-loader integration tests in
/// `corpus_loader::tests` can materialise small parquet files without
/// duplicating the writer plumbing. Compiled only under `cfg(test)`.
#[cfg(test)]
pub mod test_fixture {
    use std::{fs::File, path::Path, sync::Arc};

    use parquet::{
        data_type::ByteArrayType,
        file::{properties::WriterProperties, writer::SerializedFileWriter},
        schema::parser::parse_message_type,
    };

    /// Minimal Claude-conversation-shaped parquet schema used by the fixture
    /// writers below. Column order matches the convention used in production
    /// Claude exports but the reader is column-name based and does not depend
    /// on order.
    const CLAUDE_SCHEMA: &str = "
        message claude_session {
            REQUIRED BYTE_ARRAY session_id (UTF8);
            REQUIRED BYTE_ARRAY role (UTF8);
            REQUIRED BYTE_ARRAY content (UTF8);
            OPTIONAL INT64 ts_ms;
            OPTIONAL BYTE_ARRAY cwd (UTF8);
            OPTIONAL BYTE_ARRAY title (UTF8);
        }
    ";

    /// A single row of the test fixture. Mirrors the production Claude
    /// parquet row schema.
    #[derive(Clone)]
    pub struct FixtureRow {
        pub session_id: String,
        pub role: String,
        pub content: String,
        pub ts_ms: Option<i64>,
        pub cwd: Option<String>,
        pub title: Option<String>,
    }

    fn write_string_column<W: std::io::Write + Send>(
        row_group: &mut parquet::file::writer::SerializedRowGroupWriter<'_, W>,
        values: &[Option<&str>],
    ) {
        let mut writer = row_group.next_column().expect("column").expect("required column");
        // The parquet typed writer only writes `values_to_write` entries to
        // the values stream, where `values_to_write` equals the count of
        // `def_level == max_def_level` (i.e. non-null) entries. The values
        // buffer must therefore contain *only* the non-null entries in the
        // order they appear; the def-levels buffer continues to hold one
        // entry per logical row so the reader can recover nulls.
        let ba_values: Vec<parquet::data_type::ByteArray> =
            values.iter().filter_map(|v| v.map(parquet::data_type::ByteArray::from)).collect();
        let def_levels: Vec<i16> = values.iter().map(|v| i16::from(v.is_some())).collect();
        writer
            .typed::<ByteArrayType>()
            .write_batch(&ba_values, Some(&def_levels), None)
            .expect("write string batch");
        writer.close().expect("close string column");
    }

    fn write_int_column<W: std::io::Write + Send>(
        row_group: &mut parquet::file::writer::SerializedRowGroupWriter<'_, W>,
        values: &[Option<i64>],
    ) {
        let mut writer = row_group.next_column().expect("column").expect("required column");
        // See `write_string_column` — the values stream holds only non-null
        // entries in order; def-levels keep one entry per logical row.
        let int_values: Vec<i64> = values.iter().filter_map(|v| *v).collect();
        let def_levels: Vec<i16> = values.iter().map(|v| i16::from(v.is_some())).collect();
        writer
            .typed::<parquet::data_type::Int64Type>()
            .write_batch(&int_values, Some(&def_levels), None)
            .expect("write int batch");
        writer.close().expect("close int column");
    }

    /// Write a tiny parquet fixture containing the given rows. Used by the
    /// unit tests above and by the corpus-loader integration tests.
    pub fn write_fixture(path: &Path, rows: &[FixtureRow]) {
        let schema = Arc::new(parse_message_type(CLAUDE_SCHEMA).expect("parse schema"));
        let props = Arc::new(WriterProperties::builder().build());
        let file = File::create(path).expect("create fixture");
        let mut writer = SerializedFileWriter::new(file, schema, props).expect("create writer");

        // Column-aligned buffers. Each row contributes one entry per column.
        let mut session_ids: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut roles: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut contents: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut ts_values: Vec<Option<i64>> = Vec::with_capacity(rows.len());
        let mut cwds: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut titles: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        for row in rows {
            session_ids.push(Some(row.session_id.as_str()));
            roles.push(Some(row.role.as_str()));
            contents.push(Some(row.content.as_str()));
            ts_values.push(row.ts_ms);
            cwds.push(row.cwd.as_deref());
            titles.push(row.title.as_deref());
        }

        let mut row_group = writer.next_row_group().expect("row group");
        write_string_column(&mut row_group, &session_ids);
        write_string_column(&mut row_group, &roles);
        write_string_column(&mut row_group, &contents);
        write_int_column(&mut row_group, &ts_values);
        write_string_column(&mut row_group, &cwds);
        write_string_column(&mut row_group, &titles);
        row_group.close().expect("close row group");
        writer.close().expect("close writer");
    }
}
