//! Typed errors for the phinbox crate.

/// All errors returned by the [`phinbox`](crate) library.
///
/// Note that **user cancellations** and **popups timing out** are **not**
/// errors — they're surfaced as [`ElicitResponse::Cancelled`](crate::ElicitResponse::Cancelled)
/// and [`ElicitResponse::TimedOut`](crate::ElicitResponse::TimedOut)
/// respectively. Only failures that prevent the popup from running or
/// returning a meaningful response are errors.
#[derive(Debug, thiserror::Error)]
pub enum ElicitError {
    /// The provided [`PromptSpec`](crate::PromptSpec) is structurally
    /// invalid (e.g., a choice with zero options, a regex that won't
    /// compile, a title that exceeds the 80-char limit).
    #[error("invalid prompt spec: {0}")]
    InvalidSpec(String),

    /// The OS-level renderer failed to launch or returned malformed output.
    /// Examples: `osascript` not on PATH, PowerShell execution policy
    /// blocked, `zenity` returned a non-zero exit with no stderr.
    #[error("renderer failed: {0}")]
    RendererFailed(String),

    /// Standard I/O error from spawning the renderer subprocess.
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    /// JSON serialization/deserialization error (e.g., parsing the
    /// `osascript` stdout payload).
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    /// The popup exceeded its configured timeout without a user response.
    /// Note: this is the **error** variant; the typed `TimedOut` response
    /// is separate and is returned by the renderer on graceful timeout.
    #[error("popup timed out after {0:?}")]
    Timeout(std::time::Duration),

    /// No renderer is available on this host (no GUI, no TTY).
    /// Caller should fall back to inline questions or set
    /// `--renderer=force-tty`.
    #[error("no renderer available (set --renderer=force-tty to force TUI)")]
    NoRenderer,

    /// The tokio task that was running the popup was cancelled
    /// (e.g., the MCP server got SIGTERM).
    #[error("popup task cancelled: {0}")]
    TaskCancelled(String),

    /// A regex supplied in [`FieldSpec::Text::pattern`](crate::FieldSpec::Text)
    /// failed to compile.
    #[error("invalid pattern regex: {0}")]
    InvalidRegex(#[from] regex::Error),

    /// JSON-RPC error returned by the phinbox daemon over its IPC
    /// socket. The `code` mirrors the JSON-RPC error code; the `message`
    /// is the daemon's error string. Used by the sync `ipc::Client` and
    /// by any external Swift/Go/whatever client speaking JSON-RPC 2.0.
    #[error("rpc error {code}: {message}")]
    Rpc { code: i32, message: String },
}