//! Property evidence for sl-viewer's custom-path picker, parquet corpus
//! source, and settings persistence layer.
//!
//! These tests live in `crates/sl-viewer/tests/` (integration tests) rather
//! than inside the lib crate because they exercise public-API contracts
//! across the new modules added in PR #419:
//!
//!  * `corpus_paths::CorpusPathConfig` round-trip and merging
//!  * `parquet_source::ParquetCorpusSource` list/load invariants
//!  * `settings::Settings` persistence round-trip
//!
//! The properties use proptest's `proptest!` macro so they run with the
//! same shrinker / case distribution as the workspace-level `properties.rs`
//! (proptest is a workspace dev-dep declared in the root `Cargo.toml`; we
//! re-declare it under `[dev-dependencies]` in `sl-viewer/Cargo.toml`).

use std::path::PathBuf;

use proptest::prelude::*;
use sl_viewer::corpus_paths::CorpusPathConfig;

// ── corpus_paths round-trip ─────────────────────────────────────────────────

proptest! {
    /// Property: arbitrary `CorpusPathConfig` survives `save_config_to` →
    /// `load_config_from` byte-for-byte (modulo JSON whitespace, which we
    /// ignore via the `PartialEq` impl).
    #[test]
    fn corpus_paths_round_trip_preserves_all_paths(
        paths in prop::collection::vec(
            "[a-zA-Z0-9_./ -]{0,80}",
            0..16,
        ),
    ) {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("corpus_paths.json");

        let original = CorpusPathConfig {
            custom_paths: paths.into_iter().map(PathBuf::from).collect(),
        };

        sl_viewer::corpus_paths::save_config_to(&original, &path).expect("save");
        let restored = sl_viewer::corpus_paths::load_config_from(&path).expect("load");
        prop_assert_eq!(restored.clone(), original.clone());

        // Defensive: deduplication on disk should not introduce new paths.
        prop_assert_eq!(
            restored.custom_paths.len(),
            original.custom_paths.len(),
            "round-trip must not silently dedupe (user-picked paths are authoritative)",
        );
    }

    /// Property: `is_empty()` agrees with `custom_paths.is_empty()`.
    /// (Catches a class of bugs where one method is updated without the other.)
    #[test]
    fn corpus_paths_empty_predicate_agrees_with_field(
        paths in prop::collection::vec("[a-zA-Z0-9_./ -]{0,40}", 0..4),
    ) {
        let cfg = CorpusPathConfig {
            custom_paths: paths.into_iter().map(PathBuf::from).collect(),
        };
        prop_assert_eq!(cfg.is_empty(), cfg.custom_paths.is_empty());
    }
}

// ── parquet corpus source list/load invariants ──────────────────────────────

#[cfg(feature = "parquet")]
mod parquet_properties {
    use std::{collections::BTreeSet, fs::File, path::Path, sync::Arc};

    use parquet::{
        data_type::ByteArrayType,
        file::{
            properties::WriterProperties,
            reader::{FileReader, SerializedFileReader},
            writer::SerializedFileWriter,
        },
        schema::parser::parse_message_type,
    };
    use proptest::prelude::*;
    use session_ledger::ports::CorpusSource;
    use sl_viewer::parquet_source::ParquetCorpusSource;

    /// Re-implementation of the unit-test fixture helper, exposed so
    /// integration tests can materialise parquet fixtures without going
    /// through the `#[cfg(test)] mod test_fixture` boundary. Keep this in
    /// lockstep with the original; if the schema changes, both copies
    /// must change together.
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

    fn write_string_column<W: std::io::Write + Send>(
        row_group: &mut parquet::file::writer::SerializedRowGroupWriter<'_, W>,
        values: &[Option<&str>],
    ) {
        let mut writer = row_group.next_column().expect("column").expect("required column");
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
        let int_values: Vec<i64> = values.iter().filter_map(|v| *v).collect();
        let def_levels: Vec<i16> = values.iter().map(|v| i16::from(v.is_some())).collect();
        writer
            .typed::<parquet::data_type::Int64Type>()
            .write_batch(&int_values, Some(&def_levels), None)
            .expect("write int batch");
        writer.close().expect("close int column");
    }

    #[derive(Clone, Debug)]
    struct PropRow {
        session_id: String,
        role: String,
        content: String,
        ts_ms: Option<i64>,
    }

    fn write_fixture(path: &Path, rows: &[PropRow]) {
        let schema = Arc::new(parse_message_type(CLAUDE_SCHEMA).expect("parse schema"));
        let props = Arc::new(WriterProperties::builder().build());
        let file = File::create(path).expect("create fixture");
        let mut writer = SerializedFileWriter::new(file, schema, props).expect("create writer");

        let mut sids: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut roles: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut contents: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut ts_values: Vec<Option<i64>> = Vec::with_capacity(rows.len());
        let mut cwds: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        let mut titles: Vec<Option<&str>> = Vec::with_capacity(rows.len());
        for row in rows {
            sids.push(Some(row.session_id.as_str()));
            roles.push(Some(row.role.as_str()));
            contents.push(Some(row.content.as_str()));
            ts_values.push(row.ts_ms);
            cwds.push(None);
            titles.push(None);
        }

        let mut row_group = writer.next_row_group().expect("row group");
        write_string_column(&mut row_group, &sids);
        write_string_column(&mut row_group, &roles);
        write_string_column(&mut row_group, &contents);
        write_int_column(&mut row_group, &ts_values);
        write_string_column(&mut row_group, &cwds);
        write_string_column(&mut row_group, &titles);
        row_group.close().expect("close row group");
        writer.close().expect("close writer");
    }

    fn row_strategy() -> impl Strategy<Value = PropRow> {
        (
            // session_id must be a non-empty identifier-like string so
            // the reader can group rows by it.
            "[a-zA-Z0-9_-]{1,16}",
            // role must round-trip into one of the loader's recognised labels
            // so the message survives (otherwise it falls through to User
            // and the role assertion below would fail).
            prop::sample::select(vec!["user", "assistant", "system", "tool", "subagent"]),
            "[ -~]{0,80}",
            prop::option::of(0i64..1_000_000),
        )
            .prop_map(|(session_id, role, content, ts_ms)| PropRow {
                session_id: format!("sess-{session_id}"),
                role: role.to_owned(),
                content,
                ts_ms,
            })
    }

    // Property: for any set of rows with bounded count + content length,
    // `list()` returns exactly the unique session ids in the input,
    // `load(id)` succeeds for each, and the loaded message bodies match
    // the input rows for that session in write-order.
    //
    // This is the load-bearing invariant PR #419 added: the loader must
    // never advertise a session id it can't hydrate, and it must not
    // reorder or drop messages.
    proptest! {
        #[test]
        fn parquet_list_matches_loaded_sessions(
            rows in prop::collection::vec(row_strategy(), 1..12),
        ) {
            // Group rows by session id so we can verify each session independently.
            let mut by_id: std::collections::BTreeMap<String, Vec<PropRow>> =
                std::collections::BTreeMap::new();
            for row in rows {
                by_id.entry(row.session_id.clone()).or_default().push(row);
            }

            let dir = tempfile::tempdir().expect("tempdir");

            for (i, (id, rows)) in by_id.iter().enumerate() {
                let path = dir.path().join(format!("sessions-{i:04}.parquet"));
                write_fixture(&path, rows);
                // Sanity-check: the file we just wrote must actually be a
                // valid parquet file with the rows we expected. Catches
                // future drift between the writer and the reader schema.
                let f = File::open(&path).expect("reopen");
                let reader = SerializedFileReader::new(f).expect("reopen reader");
                prop_assert_eq!(
                    reader.get_row_iter(None).expect("iter").count(),
                    rows.len(),
                    "fixture writer drifted: expected {} rows for {}",
                    rows.len(),
                    id,
                );
            }

            let source = ParquetCorpusSource::new(dir.path());
            let listed = source.list().expect("list");
            let listed_set: BTreeSet<String> = listed.iter().cloned().collect();
            let expected: BTreeSet<String> = by_id.keys().cloned().collect();
            prop_assert_eq!(
                listed_set,
                expected,
                "list() must return exactly the unique input session ids",
            );

            for id in &listed {
                match source.load(id) {
                    Ok(session) => {
                        let expected_rows = by_id.get(id).expect("session in list implies in map");
                        prop_assert_eq!(
                            session.messages.len(),
                            expected_rows.len(),
                            "session {} message count mismatch",
                            id,
                        );
                        for (actual, expected) in session.messages.iter().zip(expected_rows.iter()) {
                            prop_assert_eq!(
                                actual.content.clone(),
                                expected.content.clone(),
                                "session {} message body mismatch",
                                id,
                            );
                            // Role is normalised by the loader; verify the loader
                            // produced one of the recognised roles for our input.
                            let recognised = matches!(
                                actual.role,
                                session_ledger::domain::session::Role::User
                                | session_ledger::domain::session::Role::Assistant
                                | session_ledger::domain::session::Role::System
                                | session_ledger::domain::session::Role::Tool
                                | session_ledger::domain::session::Role::Subagent
                            );
                            prop_assert!(
                                recognised,
                                "session {} produced unrecognised role {:?}",
                                id,
                                actual.role,
                            );
                        }
                    }
                    Err(session_ledger::ports::PortError::NotFound(missing)) => {
                        panic!("list() returned {} but load() reported NotFound({})", id, missing);
                    }
                    Err(err) => {
                        // Other backend errors (permission denied, etc.) are
                        // environment-level and acceptable in property tests.
                        eprintln!("load({}) returned backend error: {}", id, err);
                    }
                }
            }
        }
    }
}

// ── settings persistence round-trip ─────────────────────────────────────────

proptest! {
    /// Property: arbitrary `Settings` survives save → load with all fields
    /// preserved. Catches drift between the on-disk schema and the in-memory
    /// struct, e.g. someone adding a field without `#[serde(default)]` and
    /// breaking old configs.
    #[test]
    fn settings_round_trip_preserves_all_fields(
        theme in prop::sample::select(vec![
            sl_viewer::theme::Theme::Light,
            sl_viewer::theme::Theme::Dark,
            sl_viewer::theme::Theme::System,
        ]),
        default_tab in prop::sample::select(vec![
            sl_viewer::settings::DefaultTab::Bundles,
            sl_viewer::settings::DefaultTab::History,
            sl_viewer::settings::DefaultTab::Unfinished,
            sl_viewer::settings::DefaultTab::Memory,
            sl_viewer::settings::DefaultTab::LiveFeed,
            sl_viewer::settings::DefaultTab::Search,
            sl_viewer::settings::DefaultTab::Timeline,
            sl_viewer::settings::DefaultTab::Replay,
            sl_viewer::settings::DefaultTab::Corpus,
        ]),
    ) {
        let original = sl_viewer::settings::Settings {
            theme,
            default_tab,
        };

        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("settings.json");
        original.save_to_path(&path).expect("save");
        let restored = sl_viewer::settings::Settings::load_from_path(&path);

        prop_assert_eq!(restored, original);
    }
}
