//! SQLite plugin error types.

use thiserror::Error;

/// SQLite-specific error type.
#[derive(Debug, Error)]
pub enum SqliteError {
    #[error("SQLite error: {0}")]
    Sqlite(#[from] rusqlite::Error),

    #[error("JSON serialization error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Migration error: {0}")]
    Migration(String),

    #[error("Connection error: {0}")]
    Connection(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sqlite_error_display() {
        // Migration variant
        let migration = SqliteError::Migration("schema_v2".to_string());
        let s = migration.to_string();
        assert!(
            s.contains("Migration"),
            "Migration display should contain 'Migration': {s}"
        );
        assert!(
            s.contains("schema_v2"),
            "Migration display should contain 'schema_v2': {s}"
        );

        // Connection variant
        let connection = SqliteError::Connection("db locked".to_string());
        let s = connection.to_string();
        assert!(
            s.contains("Connection"),
            "Connection display should contain 'Connection': {s}"
        );
        assert!(
            s.contains("db locked"),
            "Connection display should contain 'db locked': {s}"
        );

        // Sqlite variant (converted from rusqlite::Error)
        let sqlite_err: SqliteError = rusqlite::Error::InvalidQuery.into();
        let s = sqlite_err.to_string();
        assert!(!s.is_empty(), "Sqlite display should be non-empty");
        assert!(
            s.contains("SQLite"),
            "Sqlite display should contain 'SQLite': {s}"
        );

        // Json variant (converted from serde_json::Error)
        let json_err: SqliteError = serde_json::from_str::<i32>("bad").unwrap_err().into();
        let s = json_err.to_string();
        assert!(!s.is_empty(), "Json display should be non-empty");
        assert!(
            s.contains("JSON"),
            "Json display should contain 'JSON': {s}"
        );
    }

    #[test]
    fn test_sqlite_error_from_sqlite() {
        let rusqlite_err = rusqlite::Error::InvalidQuery;
        let err: SqliteError = rusqlite_err.into();
        assert!(matches!(err, SqliteError::Sqlite(_)));
    }

    #[test]
    fn test_sqlite_error_from_json() {
        let serde_err = serde_json::from_str::<i32>("bad").unwrap_err();
        let err: SqliteError = serde_err.into();
        assert!(matches!(err, SqliteError::Json(_)));
    }

    #[test]
    fn test_sqlite_error_from_real_rusqlite_errors() {
        // NoRows variant
        let err: SqliteError = rusqlite::Error::QueryReturnedNoRows.into();
        assert!(matches!(err, SqliteError::Sqlite(_)));

        // InvalidQuery variant
        let err: SqliteError = rusqlite::Error::InvalidQuery.into();
        assert!(matches!(err, SqliteError::Sqlite(_)));

        // InvalidColumnIndex variant (rusqlite 0.40: InvalidParameterName has a
        // different signature than in older versions, so we use a stable variant
        // with a clear single-arg constructor).
        let err: SqliteError = rusqlite::Error::InvalidColumnIndex(0).into();
        assert!(matches!(err, SqliteError::Sqlite(_)));
    }

    #[test]
    fn test_sqlite_error_from_real_serde_errors() {
        // Parse error
        let parse_err = serde_json::from_str::<i32>("not a number").unwrap_err();
        let err: SqliteError = parse_err.into();
        assert!(matches!(err, SqliteError::Json(_)));

        // Type error
        let type_err = serde_json::from_str::<Vec<i64>>("\"string not array\"").unwrap_err();
        let err: SqliteError = type_err.into();
        assert!(matches!(err, SqliteError::Json(_)));
    }

    #[test]
    fn test_sqlite_error_source_chain() {
        use std::error::Error;

        // Sqlite variant: source() should be reachable and downcast to rusqlite::Error.
        let rusqlite_err = rusqlite::Error::InvalidQuery;
        let err = SqliteError::Sqlite(rusqlite_err);
        let source = err
            .source()
            .expect("SqliteError::Sqlite should expose an inner source");
        assert!(
            source.downcast_ref::<rusqlite::Error>().is_some(),
            "source() of SqliteError::Sqlite should downcast to rusqlite::Error"
        );

        // Json variant: source() should be reachable and downcast to serde_json::Error.
        let serde_err = serde_json::from_str::<i32>("bad").unwrap_err();
        let err = SqliteError::Json(serde_err);
        let source = err
            .source()
            .expect("SqliteError::Json should expose an inner source");
        assert!(
            source.downcast_ref::<serde_json::Error>().is_some(),
            "source() of SqliteError::Json should downcast to serde_json::Error"
        );

        // Migration and Connection have no #[from], so they have no source.
        assert!(SqliteError::Migration("x".to_string()).source().is_none());
        assert!(SqliteError::Connection("y".to_string()).source().is_none());
    }

    #[test]
    fn test_sqlite_error_migration_empty_string() {
        let err = SqliteError::Migration("".to_string());
        let s = err.to_string();
        assert!(
            !s.is_empty(),
            "Migration display with empty message should still be non-empty"
        );
        assert!(
            s.contains("Migration"),
            "Migration display should contain 'Migration': {s}"
        );
    }

    #[test]
    fn test_sqlite_error_debug_includes_variant_name() {
        let sqlite = SqliteError::Sqlite(rusqlite::Error::InvalidQuery);
        assert!(
            format!("{sqlite:?}").contains("Sqlite"),
            "Debug of Sqlite variant should contain 'Sqlite': {sqlite:?}"
        );

        let json = SqliteError::Json(serde_json::from_str::<i32>("bad").unwrap_err());
        assert!(
            format!("{json:?}").contains("Json"),
            "Debug of Json variant should contain 'Json': {json:?}"
        );

        let migration = SqliteError::Migration("x".to_string());
        assert!(
            format!("{migration:?}").contains("Migration"),
            "Debug of Migration variant should contain 'Migration': {migration:?}"
        );

        let connection = SqliteError::Connection("y".to_string());
        assert!(
            format!("{connection:?}").contains("Connection"),
            "Debug of Connection variant should contain 'Connection': {connection:?}"
        );
    }

    #[test]
    fn test_sqlite_error_debug_for_all_variants() {
        // For each of the 4 variants, format with Debug, assert it contains
        // the variant name AND the inner value. The inner value assertion
        // guards against Debug being suppressed in a way that loses payload.
        let json_err = serde_json::from_str::<i32>("not a number").unwrap_err();

        let cases: Vec<(SqliteError, &str, &str)> = vec![
            (
                SqliteError::Sqlite(rusqlite::Error::InvalidQuery),
                "Sqlite",
                "InvalidQuery",
            ),
            (
                SqliteError::Json(json_err),
                "Json",
                "expected",
            ),
            (
                SqliteError::Migration("migration_debug_payload".to_string()),
                "Migration",
                "migration_debug_payload",
            ),
            (
                SqliteError::Connection("connection_debug_payload".to_string()),
                "Connection",
                "connection_debug_payload",
            ),
        ];

        for (err, variant_tag, inner_substr) in cases {
            let dbg = format!("{err:?}");
            assert!(
                dbg.contains(variant_tag),
                "Debug of `{}` variant should contain variant name `{}`: `{}`",
                variant_tag,
                variant_tag,
                dbg
            );
            assert!(
                dbg.contains(inner_substr),
                "Debug of `{}` variant should contain inner value `{}`: `{}`",
                variant_tag,
                inner_substr,
                dbg
            );
        }
    }

    #[test]
    fn test_sqlite_error_source_chain_for_sqlite_variant() {
        use std::error::Error;

        // Build via the `#[from] rusqlite::Error` arm: `Into<SqliteError>`.
        let e: SqliteError = rusqlite::Error::InvalidQuery.into();
        let source = e
            .source()
            .expect("SqliteError::Sqlite built via `#[from]` should expose a source");
        assert!(
            source.downcast_ref::<rusqlite::Error>().is_some(),
            "source() of `#[from] rusqlite::Error` SqliteError should downcast to rusqlite::Error"
        );
    }

    #[test]
    fn test_sqlite_error_source_chain_for_json_variant() {
        use std::error::Error;

        // Build via the `#[from] serde_json::Error` arm: `Into<SqliteError>`.
        let s = serde_json::from_str::<i32>("x").unwrap_err();
        let e: SqliteError = s.into();
        let source = e
            .source()
            .expect("SqliteError::Json built via `#[from]` should expose a source");
        assert!(
            source.downcast_ref::<serde_json::Error>().is_some(),
            "source() of `#[from] serde_json::Error` SqliteError should downcast to serde_json::Error"
        );
    }

    #[test]
    fn test_sqlite_error_source_for_migration_variant() {
        use std::error::Error;

        // `Migration(String)` does not have an underlying source: the inner
        // payload is a plain `String`, not a `dyn Error`. `source()` must
        // return `None`.
        let e = SqliteError::Migration("m1 failed".into());
        assert!(
            e.source().is_none(),
            "SqliteError::Migration should have no underlying source"
        );
    }

    #[test]
    fn test_sqlite_error_send_sync() {
        // Compile-time assertion: `SqliteError` must be `Send + Sync` so it
        // can move across async task boundaries and be shared across threads.
        // The function body is empty; the bound check is what matters.
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<SqliteError>();
    }

    #[test]
    fn test_sqlite_error_from_io_error() {
        // Document: `SqliteError` does NOT currently implement
        // `From<std::io::Error>`. The only `#[from]` arms on the enum are
        // for `rusqlite::Error` and `serde_json::Error`. This test pins the
        // current surface so that adding or removing a `From<io::Error>`
        // arm is a deliberate, code-reviewed change.
        //
        // We cannot write `let e: SqliteError = io_err.into();` because that
        // conversion does not exist. The compile-time check is the assertion.
        let io_err = std::io::Error::new(std::io::ErrorKind::Other, "x");
        let _ = io_err; // Acknowledge that the value is constructible.

        // Exhaustively match every variant: there is no `Io` variant, so
        // a `std::io::Error` cannot be `?`-propagated into a `SqliteError`
        // directly. The match must be exhaustive on the four known variants.
        let sample = SqliteError::Connection("placeholder".into());
        match &sample {
            SqliteError::Sqlite(_)
            | SqliteError::Json(_)
            | SqliteError::Migration(_)
            | SqliteError::Connection(_) => {}
        }
    }

    #[test]
    fn test_sqlite_error_display_all_variants_unique() {
        // For each of the 4 variants, give it a payload that, when rendered
        // via `Display`, must be distinct from every other variant. The four
        // `#[error(...)]` templates start with different prefixes, so
        // uniqueness is a property of the `Display` impl itself.
        let json_err = serde_json::from_str::<i32>("x").unwrap_err();

        let variants: Vec<SqliteError> = vec![
            SqliteError::Sqlite(rusqlite::Error::InvalidQuery),
            SqliteError::Json(json_err),
            SqliteError::Migration("unique_migration_payload".into()),
            SqliteError::Connection("unique_connection_payload".into()),
        ];

        let original: Vec<String> = variants.iter().map(|e| format!("{e}")).collect();
        let mut sorted = original.clone();
        sorted.sort();
        sorted.dedup();
        assert_eq!(
            sorted.len(),
            original.len(),
            "Expected all {} variants to have distinct Display output, but found duplicates among: {:?}",
            original.len(),
            original
        );
    }

    #[test]
    fn test_sqlite_error_in_vessel_error_chain() {
        // Document: there is no `From<SqliteError> for pheno_plugin_core::PluginError`
        // defined in `pheno-plugin-core::error`. To embed a `SqliteError` inside
        // a `PluginError`, callers must wrap it manually (e.g. via
        // `PluginError::Execution(format!("{e}"))` or by adding a
        // `From<SqliteError>` arm upstream).
        //
        // This test pins the current behavior: a `SqliteError` cannot be
        // `.into()`-converted into a `PluginError`, but a manual wrap
        // preserves the inner Display text.
        use pheno_plugin_core::PluginError;

        // The line below MUST NOT compile, because `From<SqliteError> for
        // PluginError` does not exist. The test does not attempt it.
        // Instead, we verify the manual-wrapping path:
        let sqlite_err = SqliteError::Connection("x".into());
        let wrapped: PluginError = PluginError::Execution(format!("{sqlite_err}"));

        // The wrapped Display must contain both the inner "x" and the
        // SqliteError's prefix "Connection" (because `format!("{sqlite_err}")`
        // delegates to the inner `Display` impl).
        let wrapped_display = format!("{wrapped}");
        assert!(
            wrapped_display.contains("x"),
            "Wrapped PluginError Display should contain inner SqliteError text `x`: `{wrapped_display}`"
        );
        assert!(
            wrapped_display.contains("Connection"),
            "Wrapped PluginError Display should contain SqliteError prefix `Connection`: `{wrapped_display}`"
        );
    }

    #[test]
    fn test_sqlite_error_with_empty_string_message() {
        // `SqliteError::Migration` and `SqliteError::Connection` wrap a
        // `String`. Their `Display` impls are `"{prefix}: {inner}"`, so an
        // empty inner still produces a non-empty output (the prefix survives).
        let migration = SqliteError::Migration(String::new());
        let migration_display = format!("{migration}");
        assert!(
            migration_display.contains("Migration"),
            "Migration Display with empty inner should still contain 'Migration': `{migration_display}`"
        );
        assert!(
            migration_display.ends_with(": "),
            "Migration Display with empty inner should end with `: `: `{migration_display}`"
        );

        let connection = SqliteError::Connection(String::new());
        let connection_display = format!("{connection}");
        assert!(
            connection_display.contains("Connection"),
            "Connection Display with empty inner should still contain 'Connection': `{connection_display}`"
        );
        assert!(
            connection_display.ends_with(": "),
            "Connection Display with empty inner should end with `: `: `{connection_display}`"
        );
    }

    #[test]
    fn test_sqlite_error_via_map_err() {
        // `Result::map_err` should cleanly convert any `rusqlite::Error`
        // source into a `SqliteError` via the `#[from]` arm.
        let r: Result<(), rusqlite::Error> = Err(rusqlite::Error::InvalidQuery);
        let mapped: Result<(), SqliteError> = r.map_err(|e| e.into());
        assert!(mapped.is_err());
        let mapped_err = mapped.unwrap_err();
        assert!(
            matches!(mapped_err, SqliteError::Sqlite(_)),
            "map_err should produce SqliteError::Sqlite variant, got: {mapped_err:?}"
        );
    }
}
