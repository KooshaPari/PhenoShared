//! Integration tests for the durable schema migration scaffold.

#[cfg(feature = "sqlite")]
#[test]
fn schema_migrate_apply_all_from_clean_db() {
    use rusqlite::Connection;
    use session_ledger::schema::{self, migrate};

    let conn = Connection::open_in_memory().expect("in-memory db");
    let version = migrate::apply_all(&conn).expect("apply migrations");
    assert_eq!(version, schema::CURRENT_VERSION);
    assert_eq!(migrate::applied_version(&conn).expect("read version"), schema::CURRENT_VERSION);
}
