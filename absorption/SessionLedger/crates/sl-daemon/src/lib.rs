//! # `sl-daemon` — ETL producer-consumer pipeline for SessionLedger.
//!
//! A file-system watcher (producer) tails a sessions directory for new/changed
//! JSONL session files, feeds paths through a `tokio::mpsc` channel, and a
//! configurable consumer pool runs the existing session-ledger compile → OKF
//! export pipeline, writing `.okf.json` documents into an output directory.
//!
//! Worker tasks emit [`tracing`] spans (`worker` / `process_session`) so operators
//! can follow ETL progress via `RUST_LOG` (see the `sl` binary subscriber).
//! Optional W3C [`traceparent`](crate::traceparent) sidecars (`{path}.traceparent`)
//! continue distributed parentage across the file pipeline.
//!
//! # Architecture
//!
//! ```text
//! notify (file events)
//!   └─→ SessionWatcher (producer)
//!         └─→ tokio::mpsc (unbounded channel)
//!               └─→ Worker Pool (N consumers)
//!                     └─→ read_jsonl → compile → export_to_okf → write .okf.json
//! ```
//!
//! # Example
//!
//! ```no_run
//! use std::path::{Path, PathBuf};
//! use std::sync::Arc;
//! use tokio::sync::{mpsc, Mutex};
//! use sl_daemon::{spawn_fs_watcher, run_worker_pool, DaemonError};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), DaemonError> {
//!     // Event-driven watcher uses a bounded channel.
//!     let (tx, _rx) = mpsc::channel(64);
//!     let _handle = spawn_fs_watcher(Path::new("./sessions"), tx)?;
//!
//!     // Worker pool consumes an unbounded channel (wired separately in production).
//!     let (_wtx, wrx) = mpsc::unbounded_channel();
//!     let wrx = Arc::new(Mutex::new(wrx));
//!     run_worker_pool(wrx, PathBuf::from("./out"), 4).await;
//!     Ok(())
//! }
//! ```

pub mod event;
pub mod plugin;
pub mod resolver;
pub mod shutdown;
pub mod traceparent;
pub mod watcher;
pub mod worker;

pub use shutdown::ServeShutdown;
pub use traceparent::{TraceParent, HEADER as TRACEPARENT_HEADER};
pub use watcher::list_jsonl;
pub use watcher::scan_once;
pub use watcher::spawn_fs_watcher;
pub use worker::run_worker_pool;

use std::path::Path;

/// Errors that can occur during daemon operation.
#[derive(Debug, thiserror::Error)]
pub enum DaemonError {
    /// Underlying I/O error.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Notify (file-watcher) error.
    #[error("file watcher error: {0}")]
    Notify(#[from] notify::Error),

    /// SessionLedger ingestion error.
    #[error("ingestion error: {0}")]
    Ingestion(#[from] session_ledger::IngestionError),

    /// JSON serialization error.
    #[error("JSON serialization error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Determine whether a path has a `.jsonl` extension.
pub(crate) fn is_jsonl(path: &Path) -> bool {
    path.file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.ends_with(".jsonl") || name.ends_with(".jsonl.zst"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn is_jsonl_accepts_jsonl_extension() {
        assert!(is_jsonl(Path::new("session.jsonl")));
        assert!(is_jsonl(Path::new("session.jsonl.zst")));
    }

    #[test]
    fn is_jsonl_rejects_non_jsonl() {
        assert!(!is_jsonl(Path::new("session.txt")));
        assert!(!is_jsonl(Path::new("session.json")));
        assert!(!is_jsonl(Path::new("session")));
    }
}
