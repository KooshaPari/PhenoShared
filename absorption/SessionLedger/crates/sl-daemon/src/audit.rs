//! Durable local audit sink for structured actor/action events.
//!
//! Backends are append-only: JSONL (default) or SQLite (`SL_AUDIT_BACKEND=sqlite`).

use std::fs::OpenOptions;
use std::io::{self, Write as _};
use std::path::{Path, PathBuf};
use std::sync::Arc;
#[cfg(feature = "sqlite")]
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;

pub(crate) const AUDIT_JSONL_RELATIVE_PATH: &str = "audit/events.jsonl";
#[cfg(feature = "sqlite")]
pub(crate) const AUDIT_SQLITE_RELATIVE_PATH: &str = "audit/events.db";
pub(crate) const LOCAL_ACTOR: &str = "local";

const BACKEND_JSONL: &str = "jsonl";
const BACKEND_SQLITE: &str = "sqlite";

#[derive(Clone, Debug)]
pub(crate) struct AuditSink {
    backend: AuditBackend,
    location: Arc<PathBuf>,
}

#[derive(Clone, Debug)]
enum AuditBackend {
    Jsonl {
        path: Arc<PathBuf>,
    },
    #[cfg(feature = "sqlite")]
    Sqlite {
        conn: Arc<Mutex<rusqlite::Connection>>,
    },
}

#[derive(Debug, Serialize)]
pub(crate) struct AuditEvent<'a> {
    pub timestamp: u128,
    pub actor: &'a str,
    pub action: &'a str,
    pub outcome: &'a str,
    pub request_id: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource: Option<String>,
}

impl AuditSink {
    /// Open the configured append-only audit sink for `data_dir`.
    ///
    /// `SL_AUDIT_BACKEND` selects the backend (`jsonl` default, or `sqlite` when
    /// `sl-daemon` is built with `--features sqlite`).
    pub(crate) fn open(data_dir: impl AsRef<Path>) -> io::Result<Self> {
        Self::open_with_backend(data_dir, backend_from_env()?)
    }

    pub(crate) fn open_with_backend(
        data_dir: impl AsRef<Path>,
        backend: AuditBackendKind,
    ) -> io::Result<Self> {
        let data_dir = data_dir.as_ref();
        match backend {
            AuditBackendKind::Jsonl => Self::open_jsonl(data_dir),
            #[cfg(feature = "sqlite")]
            AuditBackendKind::Sqlite => Self::open_sqlite(data_dir),
            #[cfg(not(feature = "sqlite"))]
            AuditBackendKind::Sqlite => Err(io::Error::new(
                io::ErrorKind::Unsupported,
                "SL_AUDIT_BACKEND=sqlite requires sl-daemon built with --features sqlite",
            )),
        }
    }

    pub(crate) fn path(&self) -> &Path {
        &self.location
    }

    pub(crate) fn append(&self, event: &AuditEvent<'_>) -> io::Result<()> {
        match &self.backend {
            AuditBackend::Jsonl { path } => append_jsonl(path, event),
            #[cfg(feature = "sqlite")]
            AuditBackend::Sqlite { conn } => append_sqlite(conn, event),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum AuditBackendKind {
    Jsonl,
    Sqlite,
}

fn parse_audit_backend(raw: Option<&str>) -> io::Result<AuditBackendKind> {
    match raw.map(str::trim).unwrap_or("").to_ascii_lowercase().as_str() {
        "" | BACKEND_JSONL => Ok(AuditBackendKind::Jsonl),
        BACKEND_SQLITE => Ok(AuditBackendKind::Sqlite),
        other => Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!("unsupported SL_AUDIT_BACKEND value {other:?}; use jsonl or sqlite"),
        )),
    }
}

fn backend_from_env() -> io::Result<AuditBackendKind> {
    parse_audit_backend(std::env::var("SL_AUDIT_BACKEND").ok().as_deref())
}

impl AuditSink {
    fn open_jsonl(data_dir: &Path) -> io::Result<Self> {
        let path = Arc::new(data_dir.join(AUDIT_JSONL_RELATIVE_PATH));
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        Ok(Self { backend: AuditBackend::Jsonl { path: path.clone() }, location: path })
    }

    #[cfg(feature = "sqlite")]
    fn open_sqlite(data_dir: &Path) -> io::Result<Self> {
        let path = Arc::new(data_dir.join(AUDIT_SQLITE_RELATIVE_PATH));
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let conn = rusqlite::Connection::open(path.as_ref()).map_err(io::Error::other)?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             CREATE TABLE IF NOT EXISTS audit_events (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp INTEGER NOT NULL,
                 actor TEXT NOT NULL,
                 action TEXT NOT NULL,
                 outcome TEXT NOT NULL,
                 request_id TEXT NOT NULL,
                 reason TEXT,
                 resource TEXT
             );",
        )
        .map_err(io::Error::other)?;
        Ok(Self {
            backend: AuditBackend::Sqlite { conn: Arc::new(Mutex::new(conn)) },
            location: path,
        })
    }
}

fn append_jsonl(path: &Path, event: &AuditEvent<'_>) -> io::Result<()> {
    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    serde_json::to_writer(&mut file, event)?;
    file.write_all(b"\n")?;
    file.flush()?;
    file.sync_data()
}

#[cfg(feature = "sqlite")]
fn append_sqlite(
    conn: &Arc<Mutex<rusqlite::Connection>>,
    event: &AuditEvent<'_>,
) -> io::Result<()> {
    let conn = conn
        .lock()
        .map_err(|error| io::Error::other(format!("audit sqlite lock poisoned: {error}")))?;
    conn.execute(
        "INSERT INTO audit_events (timestamp, actor, action, outcome, request_id, reason, resource)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        rusqlite::params![
            i64::try_from(event.timestamp).unwrap_or(i64::MAX),
            event.actor,
            event.action,
            event.outcome,
            event.request_id,
            event.reason,
            event.resource,
        ],
    )
    .map_err(io::Error::other)?;
    Ok(())
}

pub(crate) fn data_dir_from_env_or(default_dir: &Path) -> PathBuf {
    std::env::var_os("SL_DATA_DIR")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| default_dir.to_owned())
}

pub(crate) fn timestamp_unix_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or_default()
}

pub(crate) fn local_request_id() -> String {
    format!("local-{}-{}", std::process::id(), timestamp_unix_ms())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_event<'a>(action: &'a str, request_id: &'a str) -> AuditEvent<'a> {
        AuditEvent {
            timestamp: 1,
            actor: LOCAL_ACTOR,
            action,
            outcome: "accepted",
            request_id,
            reason: Some("validation"),
            resource: None,
        }
    }

    #[test]
    fn audit_sink_appends_jsonl_without_rewriting_existing_records() {
        let dir = tempfile::TempDir::new().unwrap();
        let sink = AuditSink::open(dir.path()).unwrap();
        let first = sample_event("ingest", "req-1");
        let second = AuditEvent {
            timestamp: 2,
            actor: LOCAL_ACTOR,
            action: "export",
            outcome: "succeeded",
            request_id: "req-2",
            reason: None,
            resource: Some("bundle.okf.json".to_owned()),
        };

        sink.append(&first).unwrap();
        let first_len = std::fs::metadata(sink.path()).unwrap().len();
        sink.append(&second).unwrap();
        let second_len = std::fs::metadata(sink.path()).unwrap().len();

        assert!(second_len > first_len, "audit file should grow after each append");
        let contents = std::fs::read_to_string(sink.path()).unwrap();
        let lines: Vec<&str> = contents.lines().collect();
        assert_eq!(lines.len(), 2);

        let parsed: Vec<serde_json::Value> =
            lines.iter().map(|line| serde_json::from_str(line).unwrap()).collect();
        assert_eq!(parsed[0]["action"], "ingest");
        assert_eq!(parsed[0]["request_id"], "req-1");
        assert_eq!(parsed[1]["action"], "export");
        assert_eq!(parsed[1]["resource"], "bundle.okf.json");
    }

    #[test]
    fn data_dir_from_env_or_prefers_sl_data_dir() {
        let temp = tempfile::TempDir::new().unwrap();
        let custom = temp.path().join("custom-data");
        std::env::set_var("SL_DATA_DIR", &custom);
        let resolved = data_dir_from_env_or(Path::new("/fallback"));
        std::env::remove_var("SL_DATA_DIR");
        assert_eq!(resolved, custom);
    }

    #[test]
    fn open_defaults_to_jsonl_backend() {
        let dir = tempfile::TempDir::new().unwrap();
        let sink = AuditSink::open_with_backend(dir.path(), AuditBackendKind::Jsonl).unwrap();
        assert!(sink.path().ends_with(AUDIT_JSONL_RELATIVE_PATH));
    }

    #[test]
    fn parse_audit_backend_rejects_unknown_values() {
        let error = parse_audit_backend(Some("postgres")).unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::InvalidInput);
    }

    #[test]
    fn parse_audit_backend_accepts_jsonl_and_sqlite() {
        assert_eq!(parse_audit_backend(None).unwrap(), AuditBackendKind::Jsonl);
        assert_eq!(parse_audit_backend(Some("jsonl")).unwrap(), AuditBackendKind::Jsonl);
        assert_eq!(parse_audit_backend(Some("sqlite")).unwrap(), AuditBackendKind::Sqlite);
    }

    #[cfg(feature = "sqlite")]
    mod sqlite_backend {
        use super::*;

        #[test]
        fn sqlite_sink_appends_rows_without_rewriting_existing_records() {
            let dir = tempfile::TempDir::new().unwrap();
            let sink = AuditSink::open_with_backend(dir.path(), AuditBackendKind::Sqlite).unwrap();

            sink.append(&sample_event("ingest", "req-1")).unwrap();
            sink.append(&AuditEvent {
                timestamp: 2,
                actor: LOCAL_ACTOR,
                action: "export",
                outcome: "succeeded",
                request_id: "req-2",
                reason: None,
                resource: Some("bundle.okf.json".to_owned()),
            })
            .unwrap();

            let conn = rusqlite::Connection::open(sink.path()).unwrap();
            let count: i64 =
                conn.query_row("SELECT COUNT(*) FROM audit_events", [], |row| row.get(0)).unwrap();
            assert_eq!(count, 2);

            let (action, request_id): (String, String) = conn
                .query_row("SELECT action, request_id FROM audit_events WHERE id = 1", [], |row| {
                    Ok((row.get(0)?, row.get(1)?))
                })
                .unwrap();
            assert_eq!(action, "ingest");
            assert_eq!(request_id, "req-1");
        }
    }
}
