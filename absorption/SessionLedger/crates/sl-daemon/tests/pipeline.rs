//! Deterministic end-to-end test of the watcher→channel→ETL pipeline.
//!
//! Traceability: on-disk JSONL → compile → export is acceptance evidence for
//! FR-001 (corpus ingest into normalized Session).
//!
//! Uses [`scan_once`] rather than the event-driven `notify` watcher so the test
//! has NO dependency on OS event timing or sleeps — it is fully deterministic
//! and cannot flake. The bounded channel is drained to completion after the
//! sweep closes the sender.

use std::path::{Path, PathBuf};

use session_ledger::domain::session::Corpus;
use session_ledger::{Message, Role, Session};
use tokio::sync::mpsc;

// The daemon's modules are private to its binary crate, so the pipeline is
// re-exercised here through the same public session-ledger surface the daemon
// uses (read_jsonl_sessions + process_session), mirroring `etl::transform_file`.
// This proves the ingest→compile→export contract the daemon depends on holds
// end-to-end from a real on-disk JSONL file.

fn write_fixture(dir: &Path, ids: &[&str]) -> PathBuf {
    let mut buf = String::new();
    for id in ids {
        let mut s = Session::new(*id, Corpus::Forge);
        s.title = Some("add auth middleware".into());
        s.messages.push(Message::new(Role::User, "gate the api behind jwt"));
        s.messages.push(Message::new(Role::Assistant, "adding jsonwebtoken + middleware"));
        s.messages.push(Message::new(Role::User, "lgtm ship it"));
        buf.push_str(&serde_json::to_string(&s).expect("serialize"));
        buf.push('\n');
    }
    let path = dir.join("corpus.jsonl");
    std::fs::write(&path, buf).expect("write fixture");
    path
}

/// Mirror of the watcher's deterministic sweep for the integration boundary.
async fn scan_once(dir: &Path, tx: &mpsc::Sender<PathBuf>) -> std::io::Result<usize> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("jsonl"))
        .collect();
    paths.sort();
    let mut sent = 0;
    for p in paths {
        if tx.send(p).await.is_err() {
            break;
        }
        sent += 1;
    }
    Ok(sent)
}

#[tokio::test]
async fn fr001_watch_scan_channel_etl_produces_okf_files() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let jsonl = write_fixture(tmp.path(), &["alpha", "beta"]);
    assert!(jsonl.exists());
    let out = tmp.path().join("okf-out");

    // Producer: one deterministic sweep over a bounded channel.
    let (tx, mut rx) = mpsc::channel::<PathBuf>(16);
    let sent = scan_once(tmp.path(), &tx).await.expect("scan");
    assert_eq!(sent, 1, "one jsonl file discovered");
    drop(tx); // close so the consumer loop terminates

    // Consumer: drain + transform (same contract as etl::transform_file).
    std::fs::create_dir_all(&out).unwrap();
    let mut written = Vec::new();
    while let Some(path) = rx.recv().await {
        let sessions = session_ledger::read_jsonl_sessions(&path).expect("ingest");
        for session in &sessions {
            let doc = session_ledger::process_session(session);
            let json = serde_json::to_string_pretty(&doc).expect("serialize okf");
            let out_path = out.join(format!("{}.okf.json", session.id));
            std::fs::write(&out_path, json).expect("write okf");
            written.push((session.id.clone(), out_path));
        }
    }

    // Assert: two OKF documents, one per session, each valid + provenance-tagged.
    assert_eq!(written.len(), 2, "one OKF per session");
    for (id, path) in &written {
        assert!(path.exists(), "{path:?} exists");
        let doc: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(path).unwrap()).expect("valid json");
        assert_eq!(doc["source_id"], *id);
        assert_eq!(doc["provenance"]["corpus"], "forge");
        assert_eq!(doc["okf"], "1.0");
    }
}

#[tokio::test]
async fn empty_dir_yields_no_files() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let (tx, mut rx) = mpsc::channel::<PathBuf>(4);
    let sent = scan_once(tmp.path(), &tx).await.expect("scan");
    assert_eq!(sent, 0);
    drop(tx);
    assert!(rx.recv().await.is_none(), "no paths emitted");
}
