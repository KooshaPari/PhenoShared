//! ETL transform — the *consumer* half of the pipeline.
//!
//! For each `*.jsonl` path handed over by the watcher, run the full
//! session-ledger pipeline (ingest → compile → export) and write one
//! `<session-id>.okf.json` per session into the output directory.
//!
//! The heavy lifting lives in the root `session-ledger` crate; this module is a
//! thin, well-tested adapter that turns a file path into on-disk OKF documents.

use std::path::{Path, PathBuf};

use session_ledger::export::okf::export_to_okf;
use session_ledger::ports::CorpusSource;
use session_ledger::ports::MemoryStore;
use session_ledger::{compile_and_store, process_session, read_jsonl_sessions, CodexDir};

/// Default cap on a single transcript file the ETL pipeline will ingest.
///
/// Transcripts are buffered wholesale during ingestion (`parse_jsonl_sessions`
/// accumulates every session of a file, then each is compiled and exported),
/// so a multi-GB file used to grow the daemon's heap without bound. Files
/// larger than the cap are rejected with [`EtlError::TooLarge`] instead of
/// being loaded into RAM. Override with `SL_ETL_MAX_FILE_BYTES` (min 1 MiB).
const DEFAULT_ETL_MAX_FILE_BYTES: u64 = 512 * 1024 * 1024; // 512 MiB
const MIN_ETL_MAX_FILE_BYTES: u64 = 1024 * 1024; // 1 MiB

/// Resolve the per-file ingest cap from `SL_ETL_MAX_FILE_BYTES` (fallback:
/// [`DEFAULT_ETL_MAX_FILE_BYTES`]). Values below 1 MiB are treated as unset.
pub fn max_etl_file_bytes() -> u64 {
    std::env::var("SL_ETL_MAX_FILE_BYTES")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .filter(|value| *value >= MIN_ETL_MAX_FILE_BYTES)
        .unwrap_or(DEFAULT_ETL_MAX_FILE_BYTES)
}

/// Errors surfaced while transforming one JSONL file into OKF documents.
#[derive(Debug, thiserror::Error)]
pub enum EtlError {
    #[error("ingestion failed for {path}: {source}")]
    Ingest {
        path: PathBuf,
        #[source]
        source: session_ledger::IngestionError,
    },
    #[error("writing OKF for {path}: {source}")]
    Write {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("I/O error for {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("memory persistence failed for {path}: {source}")]
    Memory {
        path: PathBuf,
        #[source]
        source: session_ledger::ports::PortError,
    },
    #[error(
        "transcript exceeds ingest size cap ({size} bytes > {max} bytes); \
         raise SL_ETL_MAX_FILE_BYTES to ingest it: {path}"
    )]
    TooLarge { path: PathBuf, size: u64, max: u64 },
    #[error("serializing OKF: {0}")]
    Serialize(#[from] serde_json::Error),
}

/// Compile + export every session in `jsonl_path`, writing one
/// `<session-id>.okf.json` per session under `out_dir`.
///
/// When `memory_store` is set, distilled episodic facts are persisted through
/// the configured [`MemoryStore`] before OKF export.
///
/// Returns the paths written (stable order — same as the sessions in the file).
/// `out_dir` is created if missing.
pub fn transform_file(
    jsonl_path: &Path,
    out_dir: &Path,
    memory_store: Option<&dyn MemoryStore>,
) -> Result<Vec<PathBuf>, EtlError> {
    enforce_size_cap(jsonl_path)?;

    let sessions = read_sessions(jsonl_path)
        .map_err(|source| EtlError::Ingest { path: jsonl_path.to_path_buf(), source })?;

    let mut written = Vec::with_capacity(sessions.len());
    for session in &sessions {
        written.push(transform_session(session, out_dir, memory_store)?);
    }
    Ok(written)
}

/// Compile, optionally distill, and export one normalized session to its durable
/// OKF document. Both filesystem-watch and HTTP ingestion use this path so they
/// have identical persistence and SQLite-memory semantics.
pub fn transform_session(
    session: &session_ledger::Session,
    out_dir: &Path,
    memory_store: Option<&dyn MemoryStore>,
) -> Result<PathBuf, EtlError> {
    std::fs::create_dir_all(out_dir)
        .map_err(|source| EtlError::Write { path: out_dir.to_path_buf(), source })?;

    let doc = if let Some(store) = memory_store {
        let output = compile_and_store(session, store)
            .map_err(|source| EtlError::Memory { path: out_dir.to_path_buf(), source })?;
        export_to_okf(&output.bundle, session.corpus.as_str())
    } else {
        process_session(session)
    };
    let json = serde_json::to_string_pretty(&doc)?;
    let out_path = out_dir.join(format!("{}.okf.json", sanitize(&session.id)));
    std::fs::write(&out_path, json)
        .map_err(|source| EtlError::Write { path: out_path.clone(), source })?;
    Ok(out_path)
}

/// Reject transcripts larger than the configured ingest cap before any of the
/// file is buffered into RAM.
fn enforce_size_cap(path: &Path) -> Result<(), EtlError> {
    enforce_size_cap_with(path, max_etl_file_bytes())
}

/// Core cap check, parameterized for direct unit testing.
fn enforce_size_cap_with(path: &Path, max: u64) -> Result<(), EtlError> {
    let size = std::fs::metadata(path)
        .map_err(|source| EtlError::Io { path: path.to_path_buf(), source })?
        .len();
    if size > max {
        return Err(EtlError::TooLarge { path: path.to_path_buf(), size, max });
    }
    Ok(())
}

fn read_sessions(
    path: &Path,
) -> Result<Vec<session_ledger::Session>, session_ledger::IngestionError> {
    let name = path.file_name().and_then(|name| name.to_str()).unwrap_or_default();
    if !name.ends_with(".jsonl.zst") {
        return read_jsonl_sessions(path);
    }
    let source = CodexDir::new(path);
    let id = source
        .list()
        .map_err(|error| std::io::Error::other(error.to_string()))?
        .into_iter()
        .next()
        .ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::InvalidData, "compressed transcript is empty")
        })?;
    let session = source.load(&id).map_err(|error| std::io::Error::other(error.to_string()))?;
    Ok(vec![session])
}

/// Make a session id safe to use as a filename (path separators → `_`).
pub(crate) fn sanitize(id: &str) -> String {
    id.chars().map(|c| if matches!(c, '/' | '\\' | ':') { '_' } else { c }).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::session::Corpus;
    use session_ledger::{Message, Role, Session};

    /// Build a JSONL file of `n` forge sessions in `dir`, return its path.
    ///
    /// Mirrors the on-disk shape `read_jsonl_sessions` expects: one serialized
    /// `Session` per line (see the root crate's `tests/skeleton.rs`).
    fn write_fixture(dir: &Path, n: usize) -> PathBuf {
        let mut buf = String::new();
        for i in 0..n {
            let mut s = Session::new(format!("sess-{i}"), Corpus::Forge);
            s.title = Some(format!("task {i}"));
            s.messages.push(Message::new(Role::User, "add pagination to the users endpoint"));
            s.messages.push(Message::new(Role::Assistant, "on it — adding a cursor param"));
            s.messages.push(Message::new(Role::User, "lgtm, ship it"));
            buf.push_str(&serde_json::to_string(&s).expect("serialize session"));
            buf.push('\n');
        }
        let path = dir.join("sessions.jsonl");
        std::fs::write(&path, buf).expect("write fixture");
        path
    }

    #[test]
    fn transform_file_writes_one_okf_per_session() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = write_fixture(tmp.path(), 3);
        let out = tmp.path().join("out");

        let written = transform_file(&jsonl, &out, None).expect("transform");

        assert_eq!(written.len(), 3, "one OKF doc per session");
        for (i, path) in written.iter().enumerate() {
            assert!(path.exists(), "{path:?} should exist");
            let content = std::fs::read_to_string(path).expect("read okf");
            let doc: serde_json::Value = serde_json::from_str(&content).expect("okf is valid json");
            assert_eq!(doc["source_id"], format!("sess-{i}"));
            assert_eq!(doc["provenance"]["corpus"], "forge");
        }
    }

    #[test]
    fn transform_file_creates_missing_out_dir() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = write_fixture(tmp.path(), 1);
        let out = tmp.path().join("nested").join("deeper");
        assert!(!out.exists());

        let written = transform_file(&jsonl, &out, None).expect("transform");
        assert_eq!(written.len(), 1);
        assert!(out.is_dir(), "out dir auto-created");
    }

    #[test]
    fn transform_file_reads_compressed_codex_transcript() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = tmp.path().join("codex.jsonl.zst");
        let input = format!(
            "{}\n{}\n",
            serde_json::json!({"type":"session_meta","payload":{"id":"zst-session"}}),
            serde_json::json!({"type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"ship compressed"}]}})
        );
        let compressed = zstd::stream::encode_all(input.as_bytes(), 3).expect("compress");
        std::fs::write(&path, compressed).expect("write compressed transcript");
        let written = transform_file(&path, &tmp.path().join("out"), None).expect("transform");
        assert_eq!(written.len(), 1);
        let doc: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&written[0]).unwrap()).unwrap();
        assert_eq!(doc["source_id"], "zst-session");
    }

    #[test]
    fn sanitize_replaces_path_separators() {
        assert_eq!(sanitize("a/b:c\\d"), "a_b_c_d");
        assert_eq!(sanitize("plain-id"), "plain-id");
    }

    #[test]
    fn size_cap_rejects_oversized_transcript() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = tmp.path().join("giant.jsonl");
        std::fs::write(&jsonl, vec![b'x'; 2 * 1024 * 1024]).expect("write oversized transcript");

        let error = enforce_size_cap_with(&jsonl, 1024 * 1024)
            .expect_err("oversized file must be rejected");
        assert!(matches!(error, EtlError::TooLarge { .. }), "got {error}");
    }

    #[test]
    fn size_cap_accepts_transcript_at_the_limit() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = tmp.path().join("boundary.jsonl");
        std::fs::write(&jsonl, vec![b'y'; 1024 * 1024]).expect("write boundary transcript");

        enforce_size_cap_with(&jsonl, 1024 * 1024).expect("file at the cap must be accepted");
    }

    #[test]
    fn size_cap_surfaces_io_errors_for_missing_files() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let missing = tmp.path().join("missing.jsonl");

        let error = enforce_size_cap_with(&missing, 1024).expect_err("missing file must error");
        assert!(matches!(error, EtlError::Io { .. }), "got {error}");
    }

    #[test]
    fn size_cap_env_parsing_is_single_sequenced_check() {
        // One test, no parallel env races: valid override, garbage, and
        // sub-minimum values are handled deterministically.
        std::env::set_var("SL_ETL_MAX_FILE_BYTES", (2 * 1024 * 1024).to_string());
        assert_eq!(max_etl_file_bytes(), 2 * 1024 * 1024);
        std::env::set_var("SL_ETL_MAX_FILE_BYTES", "not-a-number");
        assert_eq!(max_etl_file_bytes(), DEFAULT_ETL_MAX_FILE_BYTES);
        std::env::set_var("SL_ETL_MAX_FILE_BYTES", "0");
        assert_eq!(max_etl_file_bytes(), DEFAULT_ETL_MAX_FILE_BYTES);
        std::env::remove_var("SL_ETL_MAX_FILE_BYTES");
    }

    #[cfg(feature = "sqlite")]
    #[test]
    fn transform_file_persists_distilled_facts_when_memory_store_configured() {
        use session_ledger::SqliteMemoryStore;

        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = write_fixture(tmp.path(), 1);
        let out = tmp.path().join("out");
        let memory_path = tmp.path().join("memory.db");
        let store = SqliteMemoryStore::open(&memory_path).expect("open memory db");

        let written =
            transform_file(&jsonl, &out, Some(&store)).expect("transform with memory store");
        assert_eq!(written.len(), 1);

        let recalled = store.recall("pagination", 5).expect("recall distilled facts");
        assert!(!recalled.is_empty(), "distilled episodic facts should persist");
    }

    #[cfg(feature = "sqlite")]
    #[test]
    fn transform_file_does_not_duplicate_durable_facts_for_repeated_input() {
        use session_ledger::SqliteMemoryStore;

        let tmp = tempfile::tempdir().expect("tempdir");
        let jsonl = write_fixture(tmp.path(), 1);
        let out = tmp.path().join("out");
        let store = SqliteMemoryStore::open(tmp.path().join("memory.db")).expect("open memory db");

        transform_file(&jsonl, &out, Some(&store)).expect("first transform");
        transform_file(&jsonl, &out, Some(&store)).expect("repeated transform");

        let facts = store.recall("session/sess-0", 10).expect("recall durable facts");
        assert_eq!(facts.len(), 3, "repeated watcher events must not duplicate durable facts");
    }
}
