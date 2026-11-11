//! `SessionLedger` — compile, distill, and resume agent sessions.
//!
//! Hexagonal architecture:
//! - [`domain`]: the bundle model (Acceptance / Contract / Context / Intent /
//!   Provenance / Worklog), session entities, dedup keys, and the continuation
//!   bundle. Pure logic, no I/O.
//! - [`ports`]: trait boundaries the domain depends on (memory store, trace sink,
//!   compression, corpus source). Implemented by adapters; composed from existing
//!   Phenotype systems (see `docs/DESIGN.md`).
//! - [`ingestion`]: per-corpus adapters (forge, codex, claude-code, cursor) that
//!   normalize raw transcripts into [`domain::session::Session`].
//! - [`distill`]: the "dream" pass — distills a session into memory stores and
//!   produces the [`domain::bundle::ContinuationBundle`].
//! - [`viewer`]: read model for the wiki / docs / history surface.
//! - [`export`]: export adapters (OKF, YAML, etc.) for compiled bundles.
//!
//! Nothing here duplicates forgecode (lifecycle FSM + zstd + ADR-103 pruning),
//! `OmniRoute` memory (FTS5 + Qdrant), or pheno-tracing — those are composed via
//! [`ports`]. See `docs/DESIGN.md` for the composition map.

pub mod distill;
pub mod domain;
pub mod envelope;
pub mod export;
pub mod i18n;
pub mod i18n_fluent;
pub mod ingestion;
pub mod inject;
pub mod pii_redact;
pub mod ports;
pub mod schema;
pub mod viewer;

pub use distill::contract_compiler::ContractCompiler;
pub use distill::dedup_compiler::{DedupCompileError, DedupCompiler};
pub use distill::memory_writer::{DistillMemoryWriter, DistilledMemory};
pub use distill::token_estimator::{CharCountTokenEstimator, TokenEstimator};
pub use distill::{compile_and_store, DistillOutput};
pub use domain::acceptance::Acceptance;
pub use domain::bundle::{Bundle, BundleKind, ContinuationBundle};
pub use domain::context::{Context, Decision};
pub use domain::contract::Contract;
pub use domain::dedup::{DedupKey, DedupManifest, DedupMember};
pub use domain::intent::{Intent, IntentState};
pub use domain::merge::{
    LostWorkError, LostWorkLocalizer, MergeError, MergeExecutor, MergeMessageOrder, MergeResult,
};
pub use domain::session::{Corpus, Message, Role, Session};
pub use domain::worklog::{
    detect_unfinished, project_unfinished_work, UnfinishedReason, UnfinishedWorkItem,
    WorklogProjection,
};
pub use export::okf::export_to_okf;
pub use ingestion::{
    claude_code::ClaudeDir, codex::CodexDir, cursor::CursorDir, parse_jsonl_sessions,
    read_jsonl_sessions, web::ChatGptExport, web::ClaudeExport, web::GeminiExport, IngestionError,
    JsonIngestionReport,
};
pub use inject::{render_prompt, render_slice_prompt, InjectRenderError, PromptRenderer};
#[cfg(feature = "compress")]
pub use ports::adapters::ZstdCompressor;
pub use ports::adapters::{
    InMemoryMemoryStore, NoopTraceSink, PassthroughCompressor, TracingTraceSink,
};
pub use ports::okf::{
    validate_okf_document, OkfDocument, OkfEntity, OkfExporter, OkfProvenance, OkfRelation,
    OkfValidationError,
};
#[cfg(feature = "sqlite")]
pub use ports::sqlite_memory::SqliteMemoryStore;

/// Process a single session through the entire ingest→distill→export pipeline.
///
/// Compiles the session into a [`ContinuationBundle`] via
/// [`distill::compile`], then exports the result as an [`OkfDocument`].
#[must_use]
pub fn process_session(session: &Session) -> OkfDocument {
    let bundle = distill::compile(session);
    export_to_okf(&bundle, session.corpus.as_str())
}

/// Read a JSONL file, compile every session, and return the exported documents.
///
/// This is the top-level pipeline entry point for batch processing: reads
/// [`Session`]s from a JSONL file, distills each into a
/// [`ContinuationBundle`], and exports the results as [`OkfDocument`]s.
///
/// # Errors
///
/// Returns [`IngestionError::Io`] if the file cannot be opened or read, or
/// [`IngestionError::Json`] if a line contains invalid session JSON.
pub fn process_jsonl_file<P: AsRef<std::path::Path>>(
    path: P,
) -> Result<Vec<OkfDocument>, IngestionError> {
    let sessions = read_jsonl_sessions(path)?;
    Ok(sessions.iter().map(process_session).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    fn fixture_session() -> Session {
        let mut session = Session::new("lib-test-session", Corpus::Codex);
        session.messages = vec![
            Message::new(Role::User, "Please compile this session."),
            Message::new(Role::Assistant, "Compiled."),
        ];
        session
    }

    #[test]
    fn process_session_exports_compiled_document() {
        let document = process_session(&fixture_session());
        assert!(!document.entities.is_empty());
    }

    #[test]
    fn process_jsonl_file_reads_and_processes_sessions() {
        let session = fixture_session();
        let mut file = tempfile::NamedTempFile::new().expect("temp file");
        writeln!(file, "{}", serde_json::to_string(&session).expect("serialize"))
            .expect("write session");
        let documents = process_jsonl_file(file.path()).expect("process jsonl");
        assert_eq!(documents.len(), 1);
    }

    #[test]
    fn process_jsonl_file_reports_missing_path() {
        let result = process_jsonl_file("/tmp/session-ledger-missing-input.jsonl");
        assert!(matches!(result, Err(IngestionError::Io(_))));
    }
}
