use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use tempfile::tempdir;
use tokenledger::ingest::{load_ingest_checkpoint, source_mtime_unix, write_ingest_checkpoint};

#[test]
fn ingest_checkpoint_round_trips_nested_source_state() {
    let directory = tempdir().expect("temporary checkpoint directory should exist");
    let source = directory.path().join(".factory/sessions/session.jsonl");
    let checkpoint = directory.path().join("state/ingest/checkpoint.json");
    fs::create_dir_all(source.parent().expect("source parent should exist"))
        .expect("source directory should be created");
    fs::write(&source, "{\"session\":{\"id\":\"session-1\"}}\n")
        .expect("source fixture should be written");

    let mtime = source_mtime_unix(Path::new(&source)).expect("source mtime should be available");
    let source_key = source.to_string_lossy().into_owned();
    let expected = BTreeMap::from([(source_key, mtime)]);

    write_ingest_checkpoint(&checkpoint, &expected).expect("checkpoint should be written");
    let actual = load_ingest_checkpoint(&checkpoint).expect("checkpoint should be read");

    assert_eq!(actual, expected);
}
