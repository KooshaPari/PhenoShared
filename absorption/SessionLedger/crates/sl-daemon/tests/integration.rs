//! Integration tests for `sl-daemon`.
//!
//! Tests the worker pool and pipeline end-to-end.

use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

/// A minimal JSONL session fixture for the "forge" corpus.
const FORGE_SESSION_JSONL: &str = r#"{"id":"test-forge","corpus":"forge","cwd":"/tmp","title":"fix pagination","messages":[{"role":"user","content":"fix the pagination bug","ts_ms":null},{"role":"assistant","content":"on it","ts_ms":null},{"role":"user","content":"looks good","ts_ms":null}]}"#;

/// An invalid JSONL line (not valid session JSON).
const INVALID_JSONL: &str = r#"{"id":"bad","corpus":"forge"}"#;

/// Wait up to `timeout` for a file to exist at `path`.
/// Uses `tokio::time::sleep` to yield back to the async executor.
async fn wait_for_file(path: &Path, timeout: Duration) -> bool {
    let start = std::time::Instant::now();
    while start.elapsed() < timeout {
        if path.exists() {
            return true;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    false
}

// ---------------------------------------------------------------------------
// Test 1: Worker pool processes a JSONL file via direct channel send
// ---------------------------------------------------------------------------
#[tokio::test]
async fn worker_processes_jsonl_directly() {
    let tmp = tempfile::tempdir().expect("create temp dir");
    let sessions_dir = tmp.path().join("sessions");
    let out_dir = tmp.path().join("out");

    std::fs::create_dir_all(&sessions_dir).unwrap();
    std::fs::create_dir_all(&out_dir).unwrap();

    // Create the fixture file before starting the pool.
    let fixture_path = sessions_dir.join("session1.jsonl");
    std::fs::write(&fixture_path, FORGE_SESSION_JSONL).unwrap();

    // Verify the file exists and is readable.
    assert!(fixture_path.exists(), "fixture must exist");
    let content = std::fs::read_to_string(&fixture_path).unwrap();
    assert!(!content.is_empty(), "fixture must not be empty");
    assert!(content.contains("test-forge"), "fixture must contain session id");

    // Start the worker pool and feed the path through the channel directly.
    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
    let rx = Arc::new(tokio::sync::Mutex::new(rx));

    let out = out_dir.clone();
    let pool_handle = tokio::spawn(async move {
        sl_daemon::run_worker_pool(rx, out, 2).await;
    });

    // Give pool time to start.
    tokio::time::sleep(Duration::from_millis(100)).await;

    // Send the path directly.
    tx.send(fixture_path).ok();

    let expected = out_dir.join("test-forge.okf.json");
    assert!(
        wait_for_file(&expected, Duration::from_secs(5)).await,
        "OKF file should appear: {}",
        expected.display()
    );

    let content = std::fs::read_to_string(&expected).unwrap();
    let doc: session_ledger::OkfDocument =
        serde_json::from_str(&content).expect("parse OKF document");
    assert_eq!(doc.source_id, "test-forge");
    assert!(doc.entities.iter().any(|e| e.r#type == "gate"));

    // Clean up
    drop(tx);
    pool_handle.await.unwrap();
}

// ---------------------------------------------------------------------------
// Test 2: Non-JSONL files are ignored (no OKF output)
// ---------------------------------------------------------------------------
#[tokio::test]
async fn non_jsonl_files_are_ignored() {
    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
    let rx = Arc::new(tokio::sync::Mutex::new(rx));
    let dir = tempfile::tempdir().unwrap();
    let out_dir = dir.path().join("out");
    std::fs::create_dir_all(&out_dir).unwrap();

    let out = out_dir.clone();
    let pool_handle = tokio::spawn(async move {
        sl_daemon::run_worker_pool(rx, out, 2).await;
    });

    let txt_path = dir.path().join("readme.txt");
    std::fs::write(&txt_path, b"hello").unwrap();
    tx.send(txt_path).ok();

    tokio::time::sleep(Duration::from_millis(500)).await;

    let count = std::fs::read_dir(&out_dir).unwrap().count();
    assert_eq!(count, 0, "output directory should be empty for non-JSONL input");

    drop(tx);
    pool_handle.await.unwrap();
}

// ---------------------------------------------------------------------------
// Test 3: Invalid JSONL does not crash the worker
// ---------------------------------------------------------------------------
#[tokio::test]
async fn invalid_jsonl_does_not_crash() {
    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
    let rx = Arc::new(tokio::sync::Mutex::new(rx));
    let dir = tempfile::tempdir().unwrap();
    let out_dir = dir.path().join("out");
    std::fs::create_dir_all(&out_dir).unwrap();

    let out = out_dir.clone();
    let pool_handle = tokio::spawn(async move {
        sl_daemon::run_worker_pool(rx, out, 2).await;
    });

    let bad_path = dir.path().join("bad.jsonl");
    std::fs::write(&bad_path, INVALID_JSONL).unwrap();
    tx.send(bad_path).ok();

    tokio::time::sleep(Duration::from_millis(500)).await;

    let count = std::fs::read_dir(&out_dir).unwrap().count();
    assert_eq!(count, 0, "output should be empty for invalid JSONL");

    drop(tx);
    pool_handle.await.unwrap();
}

// ---------------------------------------------------------------------------
// Test 4: Direct pipeline call (for debugging)
// ---------------------------------------------------------------------------
#[test]
fn direct_pipeline_call_works() {
    use session_ledger::*;

    let sessions = parse_jsonl_sessions(FORGE_SESSION_JSONL.as_bytes()).expect("parse JSONL");
    assert_eq!(sessions.len(), 1);
    let doc = process_session(&sessions[0]);
    assert_eq!(doc.source_id, "test-forge");

    // Write to temp dir
    let tmp = tempfile::tempdir().unwrap();
    let out_path = tmp.path().join("test-forge.okf.json");
    let file = std::fs::File::create(&out_path).unwrap();
    serde_json::to_writer_pretty(file, &doc).unwrap();
    assert!(out_path.exists());
}
