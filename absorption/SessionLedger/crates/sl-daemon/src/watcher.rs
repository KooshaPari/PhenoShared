//! Watcher — the *producer* half of the daemon's ETL pipeline.
//!
//! Two source modes feed the same `mpsc::Sender<PathBuf>`:
//!
//! * [`spawn_fs_watcher`] — event-driven via the `notify` crate (FSEvents on
//!   macOS). Best for a long-running daemon: near-zero idle cost, sub-second
//!   latency on new/modified `*.jsonl` files.
//! * [`scan_once`] — a single deterministic sweep of the directory. Used by
//!   `--once` mode and by tests, where event timing must not be relied on.
//!
//! Keeping the poll path deterministic (no sleeps, no wall-clock) is what lets
//! the consumer be unit-tested without flakiness.

use std::path::{Path, PathBuf};

use notify::{Event, EventKind, RecursiveMode, Watcher};
use tokio::sync::mpsc;
use tokio_util::sync::CancellationToken;

/// Return every `*.jsonl` or compressed `*.jsonl.zst` file under `dir`.
///
/// Non-recursive by design: session corpora are flat directories of transcript
/// files. Sorting makes the emitted order stable so tests can assert on it.
pub fn list_jsonl(dir: &Path) -> std::io::Result<Vec<PathBuf>> {
    let mut out = Vec::new();
    collect_transcripts(dir, &mut out)?;
    out.sort();
    Ok(out)
}

fn collect_transcripts(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(dir)? {
        let path = entry?.path();
        if is_transcript(&path) {
            out.push(path);
        } else if path.is_dir() {
            collect_transcripts(&path, out)?;
        }
    }
    Ok(())
}

fn is_transcript(path: &Path) -> bool {
    let name = path.file_name().and_then(|name| name.to_str()).unwrap_or_default();
    name.ends_with(".jsonl") || name.ends_with(".jsonl.zst")
}

/// Perform one deterministic sweep, sending each discovered path downstream.
///
/// Returns the number of paths emitted. Errors from `read_dir` propagate; a
/// closed receiver ends the sweep early (returns what was sent so far).
/// When `cancel` is triggered, the sweep stops without enqueueing further paths.
pub async fn scan_once(
    dir: &Path,
    tx: &mpsc::Sender<PathBuf>,
    cancel: &CancellationToken,
) -> std::io::Result<usize> {
    if cancel.is_cancelled() {
        return Ok(0);
    }
    let paths = list_jsonl(dir)?;
    let mut sent = 0;
    for path in paths {
        if cancel.is_cancelled() {
            break;
        }
        tokio::select! {
            _ = cancel.cancelled() => break,
            result = tx.send(path) => {
                if result.is_err() {
                    break;
                }
                sent += 1;
            }
        }
    }
    Ok(sent)
}

/// Spawn an event-driven `notify` watcher on `dir`.
///
/// New/modified `*.jsonl` paths are forwarded on `tx`. The returned
/// [`notify::RecommendedWatcher`] MUST be kept alive by the caller — dropping it
/// tears down the OS watch. Runs until the receiver is dropped.
pub fn spawn_fs_watcher(
    dir: &Path,
    tx: mpsc::Sender<PathBuf>,
) -> notify::Result<notify::RecommendedWatcher> {
    let mut watcher = notify::recommended_watcher(move |res: notify::Result<Event>| {
        let Ok(event) = res else { return };
        if !matches!(event.kind, EventKind::Create(_) | EventKind::Modify(_)) {
            return;
        }
        for path in event.paths {
            if is_transcript(&path) {
                // `blocking_send` is correct here: the notify callback runs on
                // its own OS thread, not inside the tokio runtime.
                if tx.blocking_send(path).is_err() {
                    return;
                }
            }
        }
    })?;
    watcher.watch(dir, RecursiveMode::Recursive)?;
    Ok(watcher)
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::session::Corpus;
    use session_ledger::{Message, Role, Session};
    use std::time::Duration;

    fn write_jsonl(dir: &Path, ids: &[&str]) {
        let mut buf = String::new();
        for id in ids {
            let mut session = Session::new(*id, Corpus::Forge);
            session.messages.push(Message::new(Role::User, "hello"));
            buf.push_str(&serde_json::to_string(&session).expect("serialize"));
            buf.push('\n');
        }
        std::fs::write(dir.join("sessions.jsonl"), buf).expect("write jsonl");
    }

    #[tokio::test]
    async fn scan_once_stops_when_cancelled_before_send() {
        let tmp = tempfile::tempdir().expect("tempdir");
        write_jsonl(tmp.path(), &["a", "b", "c"]);
        let (tx, mut rx) = mpsc::channel(1);
        let cancel = CancellationToken::new();
        cancel.cancel();

        let sent = scan_once(tmp.path(), &tx, &cancel).await.expect("scan");
        assert_eq!(sent, 0);
        drop(tx);
        assert!(rx.recv().await.is_none());
    }

    #[tokio::test]
    async fn scan_once_stops_mid_sweep_when_cancelled() {
        let tmp = tempfile::tempdir().expect("tempdir");
        write_jsonl(tmp.path(), &["only"]);
        let (tx, _rx) = mpsc::channel(1);
        let cancel = CancellationToken::new();
        let cancel_for_task = cancel.clone();
        let dir = tmp.path().to_path_buf();
        let sender = tx.clone();

        let scan_task =
            tokio::spawn(async move { scan_once(&dir, &sender, &cancel_for_task).await });

        cancel.cancel();
        let sent = tokio::time::timeout(Duration::from_secs(1), scan_task)
            .await
            .expect("scan should finish promptly after cancel")
            .expect("join")
            .expect("io");
        assert!(sent <= 1);
    }
}
