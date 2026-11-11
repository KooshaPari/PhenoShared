//! Consumer pool — reads JSONL session paths off a shared channel, runs the
//! compile → OKF export pipeline, and writes results to an output directory.

use crate::traceparent::TraceParent;
use crate::{is_jsonl, DaemonError};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::{mpsc::UnboundedReceiver, Mutex};
use tracing::{error, info, info_span, Instrument};

/// Run a pool of `num_workers` consumers that receive session paths from `rx`,
/// compile each session into a [`ContinuationBundle`], export as OKF, and write
/// the resulting JSON document into `out_dir`.
///
/// Each worker runs in its own `tokio::spawn` task. File I/O and the
/// (CPU-bound) compile/export pipeline are executed on blocking threads via
/// `tokio::task::spawn_blocking`. The function returns when the channel closes
/// (all senders dropped) and all workers finish their current work.
///
/// When a sidecar `{path}.traceparent` is present, the worker attaches W3C
/// parentage fields to the `process_session` span and writes a child
/// `traceparent` sidecar next to each emitted `.okf.json`.
#[tracing::instrument(skip(rx), fields(out_dir = %out_dir.display(), num_workers))]
pub async fn run_worker_pool(
    rx: Arc<Mutex<UnboundedReceiver<PathBuf>>>,
    out_dir: PathBuf,
    num_workers: usize,
) {
    info!("starting worker pool");
    let mut handles = Vec::with_capacity(num_workers);
    for i in 0..num_workers {
        let rx = Arc::clone(&rx);
        let out = out_dir.clone();
        let worker_span = info_span!("worker", worker_id = i);
        handles.push(tokio::spawn(
            async move {
                loop {
                    let path = {
                        let mut guard = rx.lock().await;
                        guard.recv().await
                    };
                    let Some(path) = path else {
                        // Channel closed — shut down this worker.
                        info!(worker_id = i, "worker shutting down");
                        break;
                    };
                    if let Err(e) = process_session_file(&path, &out).await {
                        error!(worker_id = i, path = %path.display(), error = %e, "session processing failed");
                    }
                }
            }
            .instrument(worker_span),
        ));
    }

    for h in handles {
        let _ = h.await;
    }
    info!("worker pool drained");
}

/// Read a JSONL file, compile each session in it, export to OKF, and write
/// each export as `{session_id}.okf.json` into `out_dir`.
async fn process_session_file(path: &Path, out_dir: &Path) -> Result<(), DaemonError> {
    // Reject non-JSONL files early.
    if !is_jsonl(path) {
        return Ok(());
    }

    let parent = TraceParent::load_sidecar(path);
    let inbound = parent.as_ref().map(TraceParent::format).unwrap_or_default();
    let empty = String::new();
    let (trace_id, parent_span_id, trace_flags) = match parent.as_ref() {
        Some(parsed) => (&parsed.trace_id, &parsed.parent_id, &parsed.flags),
        None => (&empty, &empty, &empty),
    };

    let span = info_span!(
        "process_session",
        path = %path.display(),
        out_dir = %out_dir.display(),
        trace_id = %trace_id,
        parent_span_id = %parent_span_id,
        trace_flags = %trace_flags,
        traceparent = %inbound,
    );

    let path = path.to_path_buf();
    let out = out_dir.to_path_buf();

    async move {
        tokio::task::spawn_blocking(move || -> Result<(), DaemonError> {
            let sessions = session_ledger::read_jsonl_sessions(&path)?;
            info!(sessions = sessions.len(), "compiling sessions");

            let outbound = parent.as_ref().map(TraceParent::child);
            let outbound_header = outbound.as_ref().map(TraceParent::format).unwrap_or_default();

            for session in &sessions {
                let doc = session_ledger::process_session(session);
                let filename = format!("{}.okf.json", session.id);
                let out_path = out.join(&filename);
                let file = std::fs::File::create(&out_path)?;
                serde_json::to_writer_pretty(file, &doc)?;
                if let Some(ref child) = outbound {
                    child.write_sidecar(&out_path)?;
                }
                info!(
                    session_id = %session.id,
                    out = %out_path.display(),
                    traceparent = %outbound_header,
                    "wrote OKF"
                );
            }

            Ok(())
        })
        .await
        .map_err(std::io::Error::other)?
    }
    .instrument(span)
    .await
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::traceparent::TraceParent;

    #[tokio::test]
    async fn worker_propagates_traceparent_sidecar() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let sessions = tmp.path().join("sessions");
        let out = tmp.path().join("out");
        std::fs::create_dir_all(&sessions).unwrap();
        std::fs::create_dir_all(&out).unwrap();

        let fixture = sessions.join("session1.jsonl");
        std::fs::write(
            &fixture,
            r#"{"id":"tp-forge","corpus":"forge","cwd":"/tmp","title":"trace","messages":[{"role":"user","content":"hi","ts_ms":null},{"role":"assistant","content":"ok","ts_ms":null},{"role":"user","content":"done","ts_ms":null}]}"#,
        )
        .unwrap();
        let parent =
            TraceParent::parse("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01").unwrap();
        parent.write_sidecar(&fixture).unwrap();

        let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
        let rx = Arc::new(tokio::sync::Mutex::new(rx));
        let out_clone = out.clone();
        let handle = tokio::spawn(async move {
            run_worker_pool(rx, out_clone, 1).await;
        });
        tx.send(fixture).ok();
        drop(tx);

        let expected = out.join("tp-forge.okf.json");
        let start = std::time::Instant::now();
        while start.elapsed() < std::time::Duration::from_secs(5) {
            if expected.exists() {
                break;
            }
            tokio::time::sleep(std::time::Duration::from_millis(50)).await;
        }
        assert!(expected.exists(), "OKF should be written");
        handle.await.unwrap();

        let child = TraceParent::load_sidecar(&expected).expect("child sidecar");
        assert_eq!(child.trace_id, parent.trace_id);
        assert_eq!(child.flags, parent.flags);
        assert_ne!(child.parent_id, parent.parent_id);
    }
}
