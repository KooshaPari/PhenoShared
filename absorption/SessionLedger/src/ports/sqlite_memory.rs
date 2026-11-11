//! SQLite-backed [`MemoryStore`] adapter for durable episodic facts.
//!
//! Opens a database file, applies [`crate::schema::migrate::apply_all`], and
//! persists distilled facts in the versioned `memory_facts` table.

use std::path::Path;
use std::sync::Mutex;

use rusqlite::{params, Connection};
use sha2::{Digest, Sha256};

use super::{MemoryStore, PortError};
use crate::schema::migrate::{self, MigrateError};

/// Durable [`MemoryStore`] backed by `SQLite` with forward-only migrations.
pub struct SqliteMemoryStore {
    conn: Mutex<Connection>,
}

impl SqliteMemoryStore {
    /// Open (or create) a database at `path` and apply pending migrations.
    ///
    /// # Errors
    ///
    /// Returns [`PortError::Backend`] when the database cannot be opened or
    /// migrations fail to apply.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, PortError> {
        let conn = Connection::open(path).map_err(|error| map_sqlite(&error))?;
        conn.execute_batch("PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;")
            .map_err(|error| map_sqlite(&error))?;
        migrate::apply_all(&conn).map_err(|error| map_migrate(&error))?;

        Ok(Self { conn: Mutex::new(conn) })
    }

    /// Open an in-memory database for tests.
    ///
    /// # Errors
    ///
    /// Returns [`PortError::Backend`] when migrations fail to apply.
    pub fn open_in_memory() -> Result<Self, PortError> {
        let conn = Connection::open_in_memory().map_err(|error| map_sqlite(&error))?;
        migrate::apply_all(&conn).map_err(|error| map_migrate(&error))?;
        Ok(Self { conn: Mutex::new(conn) })
    }

    /// Lightweight readiness probe for `/readyz` dependency checks.
    ///
    /// # Errors
    ///
    /// Returns [`PortError::Backend`] when the database connection is unusable.
    pub fn ping(&self) -> Result<(), PortError> {
        let conn = self.conn.lock().map_err(|error| {
            PortError::Backend(format!("sqlite memory store lock poisoned: {error}"))
        })?;
        conn.query_row("SELECT 1", [], |_| Ok(())).map_err(|error| map_sqlite(&error))
    }
}

impl MemoryStore for SqliteMemoryStore {
    fn store(&self, session_id: &str, key: &str, content: &str) -> Result<String, PortError> {
        let id = fact_id(session_id, key, content);
        let payload = serde_json::json!({
            "key": key,
            "content": content,
        });
        let payload_json = serde_json::to_string(&payload)
            .map_err(|error| PortError::Backend(format!("serialize memory payload: {error}")))?;

        let conn = self.conn.lock().map_err(|error| {
            PortError::Backend(format!("sqlite memory store lock poisoned: {error}"))
        })?;
        conn.execute(
            "INSERT INTO memory_facts (id, session_id, kind, payload_json, insertion_order)
             SELECT ?1, ?2, 'EPISODIC', ?3, COALESCE(MAX(insertion_order), 0) + 1
             FROM memory_facts
             WHERE TRUE
             ON CONFLICT(id) DO NOTHING",
            params![id, session_id, payload_json],
        )
        .map_err(|error| map_sqlite(&error))?;

        Ok(id)
    }

    fn recall(&self, query: &str, top_k: usize) -> Result<Vec<String>, PortError> {
        if top_k == 0 {
            return Ok(Vec::new());
        }

        let query = query.to_lowercase();
        let pattern = format!("%{query}%");
        let conn = self.conn.lock().map_err(|error| {
            PortError::Backend(format!("sqlite memory store lock poisoned: {error}"))
        })?;

        let mut stmt = conn
            .prepare(
                "SELECT payload_json FROM memory_facts
                 WHERE lower(session_id) LIKE ?1
                    OR lower(payload_json) LIKE ?1
                 ORDER BY insertion_order ASC
                 LIMIT ?2",
            )
            .map_err(|error| map_sqlite(&error))?;

        let rows = stmt
            .query_map(params![pattern, i64::try_from(top_k).unwrap_or(i64::MAX)], |row| {
                row.get::<_, String>(0)
            })
            .map_err(|error| map_sqlite(&error))?;

        let mut matches = Vec::new();
        for row in rows {
            let payload_json = row.map_err(|error| map_sqlite(&error))?;
            let content = serde_json::from_str::<serde_json::Value>(&payload_json)
                .ok()
                .and_then(|value| {
                    value.get("content").and_then(|content| content.as_str()).map(str::to_owned)
                })
                .unwrap_or(payload_json);
            matches.push(content);
        }

        Ok(matches)
    }
}

fn fact_id(session_id: &str, key: &str, content: &str) -> String {
    let mut hasher = Sha256::new();
    for value in [session_id, key, content] {
        hasher.update(u64::try_from(value.len()).unwrap_or(u64::MAX).to_be_bytes());
        hasher.update(value.as_bytes());
    }
    let digest = hasher.finalize();
    let mut id = String::from("memory-");
    for byte in digest {
        use std::fmt::Write;
        let _ = write!(id, "{byte:02x}");
    }
    id
}

fn map_sqlite(error: &rusqlite::Error) -> PortError {
    PortError::Backend(format!("sqlite memory store: {error}"))
}

fn map_migrate(error: &MigrateError) -> PortError {
    PortError::Backend(format!("sqlite memory store migration: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill::memory_writer::DistillMemoryWriter;
    use crate::domain::bundle::{Bundle, BundleKind, ContinuationBundle};

    #[test]
    fn sqlite_memory_store_recalls_substrings_in_insertion_order() {
        let store = SqliteMemoryStore::open_in_memory().expect("open memory db");
        store
            .store("session-a", "database", "Use SQLite for persistence")
            .expect("store first memory");
        store
            .store("session-b", "api", "Expose a database health endpoint")
            .expect("store second memory");
        store.store("session-c", "ui", "Render the timeline").expect("store unrelated memory");

        assert_eq!(
            store.recall("DATABASE", 10).expect("recall memories"),
            vec![
                "Use SQLite for persistence".to_owned(),
                "Expose a database health endpoint".to_owned()
            ]
        );
    }

    #[test]
    fn sqlite_memory_store_recall_uses_insertion_order_for_top_k() {
        let store = SqliteMemoryStore::open_in_memory().expect("open memory db");
        store.store("alpha", "one", "first").expect("store first memory");
        store.store("alpha", "two", "second").expect("store second memory");

        // These two deterministic SHA-256 ids sort in the reverse of their
        // insertion order. `top_k` must remain chronological, not hash-ordered.
        assert_eq!(store.recall("alpha", 1).expect("recall first memory"), vec!["first"]);
    }

    #[test]
    fn sqlite_memory_store_duplicate_keeps_original_insertion_order() {
        let store = SqliteMemoryStore::open_in_memory().expect("open memory db");
        let first_id = store.store("alpha", "one", "first").expect("store first memory");
        let second_id = store.store("alpha", "two", "second").expect("store second memory");
        assert_eq!(store.store("alpha", "one", "first").expect("store duplicate memory"), first_id);

        let conn = store.conn.lock().expect("lock memory db");
        let mut stmt = conn
            .prepare("SELECT id FROM memory_facts ORDER BY insertion_order ASC")
            .expect("prepare insertion-order query");
        let ids = stmt
            .query_map([], |row| row.get::<_, String>(0))
            .expect("query insertion order")
            .collect::<Result<Vec<_>, _>>()
            .expect("read insertion order");

        assert_eq!(ids, vec![first_id, second_id]);
    }

    #[test]
    fn sqlite_memory_store_ping_reports_ready() {
        let store = SqliteMemoryStore::open_in_memory().expect("open memory db");
        store.ping().expect("ping");
    }

    #[test]
    fn sqlite_memory_store_applies_migrations_on_open() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = dir.path().join("memory.db");
        let store = SqliteMemoryStore::open(&path).expect("open file db");
        store.store("alpha", "one", "first").expect("store");
        drop(store);

        let reopened = SqliteMemoryStore::open(&path).expect("reopen file db");
        assert_eq!(reopened.recall("first", 1).expect("recall"), vec!["first".to_owned()]);
    }

    #[test]
    fn distill_memory_writer_persists_through_sqlite_store() {
        let store = SqliteMemoryStore::open_in_memory().expect("open memory db");
        let mut bundle = ContinuationBundle::new("session-42");
        bundle.push(Bundle::new(
            BundleKind::Intent,
            serde_json::json!({"goal": "ship durable memory"}),
        ));

        let writes = DistillMemoryWriter::new(&store).write(&bundle).expect("write memories");
        assert_eq!(writes.len(), 1);

        let recalled = store.recall("ship durable memory", 1).expect("recall");
        assert_eq!(recalled.len(), 1);
        assert!(recalled[0].contains("ship durable memory"));
    }
}
