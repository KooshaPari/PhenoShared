//! Apply forward-only schema migrations to a `SQLite` connection.

use rusqlite::{params, Connection};

use super::{migrations, Migration};

/// Error while reading or applying schema migrations.
#[derive(Debug, thiserror::Error)]
pub enum MigrateError {
    /// `SQLite` returned an error.
    #[error(transparent)]
    Sqlite(#[from] rusqlite::Error),
    /// A bundled migration failed to apply.
    #[error("migration v{version} ({name}) failed: {source}")]
    Apply {
        /// Target version.
        version: u32,
        /// Migration name.
        name: &'static str,
        /// Underlying `SQLite` error.
        source: rusqlite::Error,
    },
}

/// Returns the highest applied schema version, or `0` when none are recorded.
///
/// # Errors
///
/// Returns [`MigrateError::Sqlite`] when the metadata query fails.
pub fn applied_version(conn: &Connection) -> Result<u32, MigrateError> {
    let exists: i64 = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'",
        [],
        |row| row.get(0),
    )?;
    if exists == 0 {
        return Ok(0);
    }

    let version =
        conn.query_row("SELECT COALESCE(MAX(version), 0) FROM schema_migrations", [], |row| {
            row.get::<_, i64>(0)
        })?;
    Ok(u32::try_from(version).unwrap_or(0))
}

/// Apply every pending migration and return the new schema version.
///
/// # Errors
///
/// Returns [`MigrateError`] when `SQLite` fails or a migration cannot be applied.
pub fn apply_all(conn: &Connection) -> Result<u32, MigrateError> {
    let current = applied_version(conn)?;
    let mut version = current;

    for migration in migrations() {
        if migration.version <= current {
            continue;
        }
        apply_one(conn, migration)?;
        version = migration.version;
    }

    Ok(version)
}

fn apply_one(conn: &Connection, migration: &Migration) -> Result<(), MigrateError> {
    let tx = conn.unchecked_transaction()?;
    tx.execute_batch(migration.sql).map_err(|source| MigrateError::Apply {
        version: migration.version,
        name: migration.name,
        source,
    })?;
    tx.execute(
        "INSERT INTO schema_migrations (version, name) VALUES (?1, ?2)",
        params![migration.version, migration.name],
    )
    .map_err(|source| MigrateError::Apply {
        version: migration.version,
        name: migration.name,
        source,
    })?;
    tx.commit()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::schema::{migrations, CURRENT_VERSION};

    #[test]
    fn apply_all_is_idempotent() {
        let conn = Connection::open_in_memory().expect("in-memory db");
        assert_eq!(applied_version(&conn).expect("read version"), 0);

        let first = apply_all(&conn).expect("first apply");
        assert_eq!(first, CURRENT_VERSION);
        assert_eq!(applied_version(&conn).expect("read version"), CURRENT_VERSION);

        let second = apply_all(&conn).expect("second apply");
        assert_eq!(second, CURRENT_VERSION);

        let count: i64 = conn
            .query_row("SELECT COUNT(*) FROM schema_migrations", [], |row| row.get(0))
            .expect("count migrations");
        assert_eq!(usize::try_from(count).expect("count fits usize"), migrations().len());
    }

    #[test]
    fn initial_migration_creates_memory_facts() {
        let conn = Connection::open_in_memory().expect("in-memory db");
        apply_all(&conn).expect("apply");

        conn.execute(
            "INSERT INTO memory_facts (id, session_id, kind, payload_json, insertion_order)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params!["fact-1", "session-a", "EPISODIC", r#"{"summary":"ok"}"#, 1],
        )
        .expect("insert fact");

        let rows: i64 = conn
            .query_row("SELECT COUNT(*) FROM memory_facts", [], |row| row.get(0))
            .expect("count facts");
        assert_eq!(rows, 1);
    }

    #[test]
    fn upgrades_v1_memory_facts_with_stable_insertion_order() {
        let conn = Connection::open_in_memory().expect("in-memory db");
        conn.execute_batch(include_str!("migrations/001_initial.sql")).expect("create v1 schema");
        conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (1, 'initial_memory_facts')",
            [],
        )
        .expect("record v1 migration");
        conn.execute(
            "INSERT INTO memory_facts (id, session_id, kind, payload_json) VALUES (?1, ?2, ?3, ?4)",
            params!["legacy-first", "session-a", "EPISODIC", r#"{\"content\":\"first\"}"#],
        )
        .expect("insert first legacy fact");
        conn.execute(
            "INSERT INTO memory_facts (id, session_id, kind, payload_json) VALUES (?1, ?2, ?3, ?4)",
            params!["legacy-second", "session-a", "EPISODIC", r#"{\"content\":\"second\"}"#],
        )
        .expect("insert second legacy fact");

        assert_eq!(apply_all(&conn).expect("upgrade schema"), 2);

        let ids = conn
            .prepare("SELECT id FROM memory_facts ORDER BY insertion_order ASC")
            .expect("prepare insertion-order query")
            .query_map([], |row| row.get::<_, String>(0))
            .expect("query insertion order")
            .collect::<Result<Vec<_>, _>>()
            .expect("read insertion order");
        assert_eq!(ids, vec!["legacy-first", "legacy-second"]);
    }
}
