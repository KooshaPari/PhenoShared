//! `substrate-browser-cdp` - a real Chrome DevTools provider.
//!
//! # Why
//!
//! The audit docket and the harness both describe a normalized browser contract,
//! but the only implemented provider drives a headed Firefox through a browser
//! extension. Nothing could run headless, nothing could be launched against a
//! caller-owned data directory, and nothing could be driven from a server.
//!
//! This crate supplies the missing provider: it launches Chrome itself, points it
//! at a caller-supplied user data directory, speaks the DevTools Protocol
//! directly, and exposes the normalized read/act/capture surface.
//!
//! Pairing it with a profile generation from `substrate-browser` is what makes
//! two agents get two genuinely separate browsers rather than two windows over
//! one cookie jar.
//!
//! # Whole-tree shutdown
//!
//! Chrome supervises renderer, GPU and utility children, so shutdown has to
//! reach the whole tree rather than only the parent. The mechanism is
//! platform-specific: a process group on Unix, a job object on Windows. Both
//! are scoped to this launch alone and both verify the tree is gone before
//! reporting success.
//!
//! Verification status, stated plainly:
//! - The Unix path is exercised by integration tests on macOS/Linux.
//! - The Windows path is **type-checked** for `x86_64-pc-windows-msvc` and has a
//!   `#[cfg(windows)]` runtime test in `tests/process_tree.rs`, which
//!   `.github/workflows/windows-browser-tree.yml` runs on `windows-latest`. No
//!   macOS or Linux host can execute it, so that CI job is its first real run.

#![deny(missing_docs)]

// Whole-tree termination is platform-specific. Unix uses a process group
// (`process_tree`); Windows uses a job object (`job_object`). Each module is
// compiled only on its own platform, and neither replaces the other.
#[cfg(windows)]
mod job_object;
mod launch;
#[cfg(unix)]
mod process_tree;
mod provider;
mod snapshot;
mod transport;

pub use transport::FenceCheck;

pub use launch::{chrome_binary, ChromeProcess, LaunchOptions};
#[cfg(unix)]
pub use process_tree::processes_using_user_data_dir;
pub use provider::CdpProvider;
pub use snapshot::{AxNode, Snapshot};

use thiserror::Error;

/// Errors produced by the CDP provider.
#[derive(Debug, Error)]
pub enum CdpError {
    /// No Chrome/Chromium binary could be found.
    #[error("no Chrome or Chromium binary found; set CHROME_BIN or install a browser")]
    NoBrowser,

    /// The browser process could not be started.
    #[error("failed to launch {binary}: {source}")]
    Launch {
        /// Binary that was attempted.
        binary: String,
        /// Underlying spawn error.
        #[source]
        source: std::io::Error,
    },

    /// The DevTools protocol was violated or the connection misbehaved.
    #[error("devtools protocol error: {0}")]
    Protocol(String),

    /// The browser answered a command with an error.
    #[error("devtools command {method} failed: {message}")]
    DevTools {
        /// Command that failed.
        method: String,
        /// Browser-provided message.
        message: String,
    },

    /// A bounded wait elapsed.
    #[error("timed out: {0}")]
    Timeout(String),

    /// Filesystem failure.
    #[error("browser filesystem error: {0}")]
    Io(#[from] std::io::Error),

    /// JSON encoding failure.
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Result alias for this crate.
pub type Result<T> = std::result::Result<T, CdpError>;
