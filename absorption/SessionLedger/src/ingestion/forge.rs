//! Forge corpus adapter.
//!
//! Reads forgecode's `conversations` table (`~/forge/.forge.db`, ~12.9k rows)
//! via rusqlite. Handles zstd `context_zstd` decompression and user/subagent
//! message classification (the curation pipeline at
//! `phenotype-org-audits/curation/forge/curate.py` is the shared intent core).
//!
//! The rusqlite-backed reader is gated on the `sqlite` feature:
//! ```toml
//! session-ledger = { features = ["sqlite"] }
//! ```
//!
//! ## Forge DB schema (relevant columns)
//!
//! ```sql
//! CREATE TABLE conversations (
//!     id          TEXT    PRIMARY KEY,
//!     title       TEXT,
//!     cwd         TEXT,
//!     context_zstd BLOB,   -- zstd-compressed JSON array of messages
//!     context     TEXT     -- plaintext JSON fallback (may be NULL)
//! );
//! ```
//!
//! Each decompressed `context_zstd` value is a JSON array of message objects:
//! ```json
//! [{"role": "user"|"assistant"|"system"|"tool", "content": "..."},  ...]
//! ```
//! `ts` and `timestamp` fields (unix millis) are extracted if present.

use crate::domain::session::Corpus;

/// Marker for the forge ingestion adapter.
#[derive(Debug, Default, Clone, Copy)]
pub struct ForgeAdapter;

impl ForgeAdapter {
    /// Returns the corpus tag for this adapter.
    #[must_use]
    pub fn corpus(self) -> Corpus {
        Corpus::Forge
    }
}

// ─── sqlite feature: full rusqlite-backed implementation ───────────────────

#[cfg(feature = "sqlite")]
pub use sqlite_impl::{ForgeDb, ForgeIngestionReport};

#[cfg(feature = "sqlite")]
mod sqlite_impl {
    use std::path::Path;

    use rusqlite::{Connection, OpenFlags};
    use serde_json::Value;

    use crate::{
        domain::session::{Message, Session},
        ingestion::forge::map_role,
        ports::{CorpusSource, PortError},
    };

    /// A snapshot of skipped rows collected during an ingestion pass.
    ///
    /// All errors are surfaced here rather than silently dropped; callers
    /// decide how to handle partial failures.
    #[derive(Debug, Default)]
    pub struct ForgeIngestionReport {
        /// Number of rows successfully ingested.
        pub ingested: usize,
        /// Per-row failures: `(row_id, reason)`.
        pub skipped: Vec<(String, String)>,
    }

    impl ForgeIngestionReport {
        /// Returns `true` if every row was ingested without errors.
        #[must_use]
        pub fn is_clean(&self) -> bool {
            self.skipped.is_empty()
        }
    }

    /// A read-only handle to a Forge `SQLite` database.
    ///
    /// Opens with `SQLITE_OPEN_READ_ONLY` so it never modifies the live DB.
    /// Implements [`CorpusSource`] for per-ID access, and exposes
    /// [`ForgeDb::ingest_all`] for full-corpus batch ingestion with error
    /// accounting.
    pub struct ForgeDb {
        conn: Connection,
    }

    impl ForgeDb {
        /// Open the Forge `SQLite` database at `path` in read-only mode.
        ///
        /// # Errors
        ///
        /// Returns [`PortError::Backend`] if the file cannot be opened or is
        /// not a valid `SQLite` database.
        pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, PortError> {
            let conn = Connection::open_with_flags(
                path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
            )
            .map_err(|e| PortError::Backend(format!("open forge.db: {e}")))?;
            Ok(Self { conn })
        }

        /// Ingest every conversation row, returning all sessions and an error
        /// report for malformed or undecompressible rows.
        ///
        /// Malformed rows are **counted and described** — they are never
        /// silently dropped. The caller receives both the clean sessions and the
        /// full accounting of what was skipped and why.
        ///
        /// # Errors
        ///
        /// Returns [`PortError::Backend`] only if the database itself cannot be
        /// queried (e.g. missing `conversations` table). Per-row failures are
        /// accumulated into the returned [`ForgeIngestionReport`].
        pub fn ingest_all(&self) -> Result<(Vec<Session>, ForgeIngestionReport), PortError> {
            let mut stmt = self
                .conn
                .prepare(
                    "SELECT id, title, cwd, context_zstd, context \
                     FROM conversations",
                )
                .map_err(|e| PortError::Backend(format!("prepare conversations query: {e}")))?;

            let mut sessions: Vec<Session> = Vec::new();
            let mut report = ForgeIngestionReport::default();

            let rows = stmt
                .query_map([], |row| {
                    let id: String = row.get(0)?;
                    let title: Option<String> = row.get(1)?;
                    let cwd: Option<String> = row.get(2)?;
                    let context_zstd: Option<Vec<u8>> = row.get(3)?;
                    let context_plain: Option<String> = row.get(4)?;
                    Ok((id, title, cwd, context_zstd, context_plain))
                })
                .map_err(|e| PortError::Backend(format!("query conversations: {e}")))?;

            for row_result in rows {
                let (id, title, cwd, context_zstd, context_plain) = match row_result {
                    Ok(r) => r,
                    Err(e) => {
                        report.skipped.push(("<unknown>".into(), format!("row read error: {e}")));
                        continue;
                    }
                };

                // Resolve the context JSON: prefer zstd blob, fall back to
                // the plain text column (never silently skip if neither is
                // present — that is a schema error we surface).
                let context_json = match decode_context(context_zstd, context_plain) {
                    Ok(json) => json,
                    Err(reason) => {
                        report.skipped.push((id, reason));
                        continue;
                    }
                };

                let messages = match parse_messages(&context_json) {
                    Ok(msgs) => msgs,
                    Err(reason) => {
                        report.skipped.push((id, reason));
                        continue;
                    }
                };

                let mut session = Session::new(id, crate::domain::session::Corpus::Forge);
                session.title = title;
                session.cwd = cwd;
                session.messages = messages;

                sessions.push(session);
                report.ingested += 1;
            }

            Ok((sessions, report))
        }
    }

    // CorpusSource: per-id access (list + load).
    impl CorpusSource for ForgeDb {
        fn list(&self) -> Result<Vec<String>, PortError> {
            let mut stmt = self
                .conn
                .prepare("SELECT id FROM conversations")
                .map_err(|e| PortError::Backend(format!("prepare list: {e}")))?;

            let ids = stmt
                .query_map([], |row| row.get::<_, String>(0))
                .map_err(|e| PortError::Backend(format!("query ids: {e}")))?
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e| PortError::Backend(format!("collect ids: {e}")))?;

            Ok(ids)
        }

        fn load(&self, id: &str) -> Result<Session, PortError> {
            let mut stmt = self
                .conn
                .prepare(
                    "SELECT id, title, cwd, context_zstd, context \
                     FROM conversations WHERE id = ?1",
                )
                .map_err(|e| PortError::Backend(format!("prepare load: {e}")))?;

            let row = stmt
                .query_row([id], |row| {
                    let id: String = row.get(0)?;
                    let title: Option<String> = row.get(1)?;
                    let cwd: Option<String> = row.get(2)?;
                    let context_zstd: Option<Vec<u8>> = row.get(3)?;
                    let context_plain: Option<String> = row.get(4)?;
                    Ok((id, title, cwd, context_zstd, context_plain))
                })
                .map_err(|e| match e {
                    rusqlite::Error::QueryReturnedNoRows => PortError::NotFound(id.to_owned()),
                    other => PortError::Backend(format!("load row {id}: {other}")),
                })?;

            let (row_id, title, cwd, context_zstd, context_plain) = row;

            let context_json = decode_context(context_zstd, context_plain)
                .map_err(|reason| PortError::Backend(format!("decompress {row_id}: {reason}")))?;

            let messages = parse_messages(&context_json).map_err(|reason| {
                PortError::Backend(format!("parse messages {row_id}: {reason}"))
            })?;

            let mut session = Session::new(row_id, crate::domain::session::Corpus::Forge);
            session.title = title;
            session.cwd = cwd;
            session.messages = messages;

            Ok(session)
        }
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    /// Decompress `context_zstd` blob if present; fall back to the plain
    /// text column; return an explicit error if neither is available.
    fn decode_context(zstd_blob: Option<Vec<u8>>, plain: Option<String>) -> Result<String, String> {
        if let Some(blob) = zstd_blob {
            if !blob.is_empty() {
                return zstd::stream::decode_all(blob.as_slice())
                    .map_err(|e| format!("zstd decompress: {e}"))
                    .and_then(|bytes| {
                        String::from_utf8(bytes).map_err(|e| format!("zstd output not utf-8: {e}"))
                    });
            }
        }
        plain.ok_or_else(|| {
            "no context_zstd blob and no plain context column — schema mismatch".into()
        })
    }

    /// Parse the decompressed JSON into a `Vec<Message>`.
    ///
    /// The expected shape is a JSON array of objects with at minimum a `role`
    /// string field and a `content` string field.  A `ts` or `timestamp` unix-
    /// millis field is consumed when present.  Unknown fields are tolerated.
    ///
    /// Returns an error string (to be stored in the skip report) rather than
    /// propagating `serde_json::Error` so all failures share the same type.
    fn parse_messages(json: &str) -> Result<Vec<Message>, String> {
        let arr: Value = serde_json::from_str(json).map_err(|e| format!("JSON parse: {e}"))?;

        let items = arr.as_array().ok_or("context is not a JSON array")?;

        let mut messages = Vec::with_capacity(items.len());
        for (i, item) in items.iter().enumerate() {
            let role_str = item
                .get("role")
                .and_then(Value::as_str)
                .ok_or_else(|| format!("message[{i}] missing 'role' string"))?;

            let content = item.get("content").and_then(Value::as_str).unwrap_or("").to_owned();

            let ts_ms = item.get("ts").or_else(|| item.get("timestamp")).and_then(Value::as_i64);

            let role = map_role(role_str);
            messages.push(Message { role, content, ts_ms });
        }

        Ok(messages)
    }
}

// ── shared helper ────────────────────────────────────────────────────────────

/// Map a Forge message role string to the normalized [`Role`] enum.
///
/// - `"user"` → [`Role::User`]
/// - `"assistant"` → [`Role::Assistant`]
/// - `"system"` → [`Role::System`]
/// - `"tool"` → [`Role::Tool`]
/// - anything else (e.g. `"subagent"`, forge-specific roles) → [`Role::Subagent`]
///
/// Used by the `sqlite` feature's `sqlite_impl::parse_messages`.  The function
/// is unconditionally compiled so the role tests run regardless of feature flags.
#[cfg_attr(not(feature = "sqlite"), allow(dead_code))]
pub(crate) fn map_role(role: &str) -> crate::domain::session::Role {
    use crate::domain::session::Role;
    match role {
        "user" => Role::User,
        "assistant" => Role::Assistant,
        "system" => Role::System,
        "tool" => Role::Tool,
        _ => Role::Subagent,
    }
}

// Tests require rusqlite + zstd dev-dependencies AND the sqlite feature so that
// ForgeDb and ForgeIngestionReport are available.
#[cfg(all(test, feature = "sqlite"))]
mod tests {
    use rusqlite::Connection;

    use super::*;
    use crate::domain::session::Role;
    use crate::ports::{CorpusSource, PortError};

    /// Row fixture for `open_temp_db`: (id, title, cwd, `context_zstd`, context).
    type ForgeRow<'a> =
        (&'a str, Option<&'a str>, Option<&'a str>, Option<Vec<u8>>, Option<&'a str>);

    // ── fixture helpers ───────────────────────────────────────────────────────

    /// Compress a string with zstd at level 3 (same as forgecode).
    fn zstd_compress(s: &str) -> Vec<u8> {
        zstd::stream::encode_all(s.as_bytes(), 3).expect("compress fixture")
    }

    /// Build a minimal valid context JSON array with one user + one assistant turn.
    fn minimal_context_json() -> String {
        serde_json::json!([
            {"role": "user", "content": "fix the bug", "ts": 1_700_000_000_000_i64},
            {"role": "assistant", "content": "on it"}
        ])
        .to_string()
    }

    // Write a ForgeDb directly from an in-memory connection for testing.
    // We duplicate the `ingest_all` + `list`/`load` logic via the public API
    // by writing the DB to a temp file (in-memory DBs cannot be shared across
    // Connection handles in different structs).
    fn open_temp_db(rows: &[ForgeRow<'_>]) -> (ForgeDb, tempfile::TempPath) {
        let tmp = tempfile::NamedTempFile::new().expect("tempfile");
        let path = tmp.path().to_owned();

        {
            // Write through a regular Connection, then close it before ForgeDb opens.
            let conn = Connection::open(&path).expect("write conn");
            conn.execute_batch(
                "CREATE TABLE conversations (
                    id           TEXT PRIMARY KEY,
                    title        TEXT,
                    cwd          TEXT,
                    context_zstd BLOB,
                    context      TEXT
                 );",
            )
            .expect("create table");
            for (id, title, cwd, blob, plain) in rows {
                conn.execute(
                    "INSERT INTO conversations (id, title, cwd, context_zstd, context) \
                     VALUES (?1, ?2, ?3, ?4, ?5)",
                    rusqlite::params![id, title, cwd, blob, plain],
                )
                .expect("insert row");
            }
        }

        let db = ForgeDb::open(&path).expect("open ForgeDb");
        let tmp_path = tmp.into_temp_path();
        (db, tmp_path)
    }

    // ── happy-path tests ──────────────────────────────────────────────────────

    #[test]
    fn ingest_all_happy_path_zstd_compressed() {
        let ctx = minimal_context_json();
        let blob = zstd_compress(&ctx);

        let rows: &[ForgeRow<'_>] =
            &[("conv-001", Some("fix the bug"), Some("/home/user/proj"), Some(blob), None)];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all");
        assert!(report.is_clean(), "unexpected skips: {:?}", report.skipped);
        assert_eq!(sessions.len(), 1);

        let s = &sessions[0];
        assert_eq!(s.id, "conv-001");
        assert_eq!(s.corpus, Corpus::Forge);
        assert_eq!(s.title.as_deref(), Some("fix the bug"));
        assert_eq!(s.cwd.as_deref(), Some("/home/user/proj"));
        assert_eq!(s.messages.len(), 2);
        assert_eq!(s.messages[0].role, crate::domain::session::Role::User);
        assert_eq!(s.messages[0].content, "fix the bug");
        assert_eq!(s.messages[0].ts_ms, Some(1_700_000_000_000));
        assert_eq!(s.messages[1].role, crate::domain::session::Role::Assistant);
        assert_eq!(s.messages[1].content, "on it");
        assert_eq!(s.messages[1].ts_ms, None);
    }

    #[test]
    fn ingest_all_happy_path_plain_fallback() {
        let ctx = minimal_context_json();
        let rows: &[ForgeRow<'_>] = &[(
            "conv-002",
            Some("fallback test"),
            Some("/home/user/other"),
            None, // no zstd blob
            Some(ctx.as_str()),
        )];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all");
        assert!(report.is_clean(), "unexpected skips: {:?}", report.skipped);
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].messages.len(), 2);
    }

    #[test]
    fn ingest_all_multiple_rows() {
        let ctx = minimal_context_json();
        let blob = zstd_compress(&ctx);

        let rows: &[ForgeRow<'_>] = &[
            ("c-1", Some("first"), Some("/a"), Some(blob.clone()), None),
            ("c-2", Some("second"), Some("/b"), Some(blob.clone()), None),
            ("c-3", Some("third"), Some("/c"), None, Some(ctx.as_str())),
        ];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all");
        assert!(report.is_clean());
        assert_eq!(sessions.len(), 3);
    }

    // ── error / skip accounting tests ─────────────────────────────────────────

    #[test]
    fn ingest_all_decompress_error_is_skipped_and_counted() {
        // Not-valid zstd bytes: should fail decompression.
        let garbage = vec![0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01, 0x02];
        let ctx = minimal_context_json();
        let good_blob = zstd_compress(&ctx);

        let rows: &[ForgeRow<'_>] = &[
            ("bad-row", None, None, Some(garbage), None),
            ("good-row", None, Some("/ok"), Some(good_blob), None),
        ];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all query");

        // Exactly one row skipped (the corrupt blob).
        assert_eq!(report.skipped.len(), 1, "expected 1 skip, got {:?}", report.skipped);
        assert_eq!(report.skipped[0].0, "bad-row");
        assert!(
            report.skipped[0].1.contains("zstd"),
            "skip reason should mention zstd, got: {}",
            report.skipped[0].1
        );

        // Good row still ingested.
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, "good-row");
        assert_eq!(report.ingested, 1);
    }

    #[test]
    fn ingest_all_schema_mismatch_both_null_is_counted() {
        let rows: &[ForgeRow<'_>] = &[(
            "null-row", None, None, None, // no zstd
            None, // no plain
        )];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all query");
        assert_eq!(sessions.len(), 0);
        assert_eq!(report.skipped.len(), 1);
        assert_eq!(report.skipped[0].0, "null-row");
        assert!(
            report.skipped[0].1.contains("schema mismatch"),
            "expected schema-mismatch message, got: {}",
            report.skipped[0].1
        );
    }

    #[test]
    fn ingest_all_invalid_json_is_counted() {
        // Valid zstd but the payload is not JSON.
        let not_json = zstd_compress("this is not json at all");
        let rows: &[ForgeRow<'_>] = &[("bad-json", None, None, Some(not_json), None)];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all query");
        assert_eq!(sessions.len(), 0);
        assert_eq!(report.skipped.len(), 1);
        assert!(
            report.skipped[0].1.contains("JSON parse"),
            "expected JSON parse error, got: {}",
            report.skipped[0].1
        );
    }

    #[test]
    fn ingest_all_non_array_json_is_counted() {
        // Decompresses fine, valid JSON — but a map, not an array.
        let obj = zstd_compress(r#"{"role":"user","content":"oops"}"#);
        let rows: &[ForgeRow<'_>] = &[("non-array", None, None, Some(obj), None)];
        let (db, _tmp) = open_temp_db(rows);

        let (sessions, report) = db.ingest_all().expect("ingest_all query");
        assert_eq!(sessions.len(), 0);
        assert!(report.skipped[0].1.contains("not a JSON array"));
    }

    // ── CorpusSource trait: list + load ───────────────────────────────────────

    #[test]
    fn corpus_source_list_returns_all_ids() {
        let ctx = minimal_context_json();
        let blob = zstd_compress(&ctx);
        let rows: &[ForgeRow<'_>] = &[
            ("id-a", None, None, Some(blob.clone()), None),
            ("id-b", None, None, Some(blob), None),
        ];
        let (db, _tmp) = open_temp_db(rows);

        let ids = db.list().expect("list");
        assert_eq!(ids.len(), 2);
        assert!(ids.contains(&"id-a".to_owned()));
        assert!(ids.contains(&"id-b".to_owned()));
    }

    #[test]
    fn corpus_source_load_returns_session() {
        let ctx = minimal_context_json();
        let blob = zstd_compress(&ctx);
        let rows: &[ForgeRow<'_>] =
            &[("load-me", Some("Load Test"), Some("/cwd"), Some(blob), None)];
        let (db, _tmp) = open_temp_db(rows);

        let session = db.load("load-me").expect("load");
        assert_eq!(session.id, "load-me");
        assert_eq!(session.title.as_deref(), Some("Load Test"));
        assert_eq!(session.messages.len(), 2);
    }

    #[test]
    fn corpus_source_load_missing_id_returns_not_found() {
        let (db, _tmp) = open_temp_db(&[]);

        let err = db.load("no-such-id").expect_err("should be NotFound");
        assert!(matches!(err, PortError::NotFound(_)), "expected NotFound, got {err:?}");
    }

    // ── role classification tests ─────────────────────────────────────────────

    #[test]
    fn role_mapping_covers_all_known_variants() {
        assert_eq!(map_role("user"), Role::User);
        assert_eq!(map_role("assistant"), Role::Assistant);
        assert_eq!(map_role("system"), Role::System);
        assert_eq!(map_role("tool"), Role::Tool);
        // Unknown / forge-specific roles → Subagent
        assert_eq!(map_role("subagent"), Role::Subagent);
        assert_eq!(map_role("forge-internal"), Role::Subagent);
        assert_eq!(map_role(""), Role::Subagent);
    }

    // ── marker struct ─────────────────────────────────────────────────────────

    #[test]
    fn forge_adapter_corpus_tag() {
        assert_eq!(ForgeAdapter.corpus(), Corpus::Forge);
    }

    // ── timestamp field aliasing ──────────────────────────────────────────────

    #[test]
    fn ingest_timestamp_alias_is_parsed() {
        // Forge sometimes uses `timestamp` instead of `ts`.
        let ctx = serde_json::json!([
            {"role": "user", "content": "hello", "timestamp": 999_i64}
        ])
        .to_string();
        let blob = zstd_compress(&ctx);
        let rows: &[ForgeRow<'_>] = &[("ts-alias", None, None, Some(blob), None)];
        let (db, _tmp) = open_temp_db(rows);
        let (sessions, report) = db.ingest_all().expect("ingest_all");
        assert!(report.is_clean());
        assert_eq!(sessions[0].messages[0].ts_ms, Some(999));
    }

    #[test]
    fn ingest_empty_context_array_produces_empty_messages() {
        let ctx = "[]".to_owned();
        let blob = zstd_compress(&ctx);
        let rows: &[ForgeRow<'_>] = &[("empty-ctx", None, None, Some(blob), None)];
        let (db, _tmp) = open_temp_db(rows);
        let (sessions, report) = db.ingest_all().expect("ingest_all");
        assert!(report.is_clean());
        assert!(sessions[0].messages.is_empty());
    }
}
