//! Async inbox subsystem for non-blocking elicitation.
//!
//! When an agent runs in a context where blocking the user's terminal on a
//! modal popup is unacceptable (background workers, CI, SSH without X
//! forwarding, long-running services), [`crate::elicit`] would either hang
//! or fail silently. The **inbox** turns that into an async workflow:
//!
//! 1. The agent calls `phinbox ask --async --json <spec>`. Instead of
//!    blocking on a popup, the spec is persisted to an on-disk queue,
//!    surfaced via tray notification / iMessage / email, and the CLI
//!    returns immediately with the new `request_id`.
//! 2. The user opens the inbox (`phinbox inbox` or `phinbox inbox
//!    --web`) at their leisure, reads the queued prompt, and submits
//!    an answer through the inbox UI.
//! 3. The agent's next call to `phinbox wait --request-id <id>`
//!    (or `--block-on <id>`) returns the now-answered response.
//!
//! ## File layout
//!
//! ```text
//! ~/.local/share/phinbox/
//! ├── inbox/<request_id>.json     # pending spec + state
//! ├── answered/<request_id>.json  # answered response (kept for audit)
//! └── daemon.lock                 # pidfile of running inbox daemon
//! ```
//!
//! The inbox is platform-independent — every backend just JSON-encodes a
//! [`PendingRequest`] to disk. The native popup path is only used when the
//! agent explicitly opts in.

use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

use crate::error::ElicitError;
use crate::spec::{ElicitResponse, PromptSpec};

pub mod change;
pub mod daemon;
pub mod ipc;
pub mod notify;
#[cfg(test)] mod tests;

pub mod expire;
pub mod load;
pub mod mark;

pub use change::{InboxChangeBus, InboxWatcher};
pub use expire::mark_expired_in_place;
pub use load::{load_pending, load_request, list_pending};
pub use mark::{enqueue, finalize};

/// Crate version, exposed so the IPC ping can report it.
pub const PHINBOX_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Lightweight status for IPC change-event notifications.  Mirrors
/// [`RequestState`] but is a separate type so the IPC layer doesn't
/// serialize without exposing the full response payload.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ResponseStatus {
    Pending,
    Answered,
    Cancelled,
    TimedOut,
}

/// State of a request in the inbox.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RequestState {
    /// Spec is queued and waiting for the user.
    #[default]
    Pending,
    /// User has viewed the spec (e.g. via iMessage deep link) but not yet
    /// answered.
    Seen,
    /// User submitted an answer; the response is in [`PendingRequest::response`].
    Answered,
    /// User dismissed / declined.
    Cancelled,
    /// Request exceeded its TTL without a response.
    Expired,
}

/// Surface that surfaced this request to the user.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NotificationKind {
    /// No external notification — the user will see it in the inbox UI.
    None,
    /// macOS `NSUserNotification` / `osascript display notification`.
    NativeNotification,
    /// Sent via iMessage.
    #[serde(rename = "imessage")]
    IMessage,
    /// Sent via email (mailto: deep link with rendered form in the body).
    Email,
    /// Pushed via NTFY / Pushover / generic webhook.
    Webhook,
}

/// One queued request — the on-disk artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PendingRequest {
    /// Stable identifier; mirrors [`PromptSpec::request_id`].
    pub request_id: String,

    /// Originating agent (hostname + process name + arbitrary tag).
    pub origin: RequestOrigin,

    /// The prompt payload.
    pub spec: PromptSpec,

    /// When the spec was queued (ms since epoch).
    pub queued_at_ms: u64,

    /// When the queue entry will expire if unanswered.
    pub expires_at_ms: u64,

    /// Current state.
    #[serde(default)]
    pub state: RequestState,

    /// The user's response, if [`RequestState::Answered`].
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub response: Option<ElicitResponse>,

    /// Where (if anywhere) the request was surfaced.
    #[serde(default)]
    pub notified_via: Vec<NotificationKind>,

    /// Free-form metadata for the agent's bookkeeping.
    #[serde(default)]
    pub metadata: serde_json::Map<String, serde_json::Value>,
}

/// Information about the agent that enqueued the request.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequestOrigin {
    pub hostname: String,
    pub process: String,
    pub pid: u32,
    /// Optional deep link (e.g. `imessage://…` or `mailto:…`) the inbox
    /// can use to reply from the same channel.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub callback: Option<String>,
}

/// Default per-request TTL when the prompt didn't set one.
const DEFAULT_TTL_MS: u64 = 24 * 60 * 60 * 1000;

impl PendingRequest {
    /// Construct a new pending request from a spec, populating `queued_at_ms`
    /// and `expires_at_ms` from the current clock + spec TTL.
    #[must_use]
    pub fn new(spec: PromptSpec, origin: RequestOrigin) -> Self {
        let now_ms = unix_now_ms();
        let ttl_ms = if spec.timeout_secs == 0 {
            DEFAULT_TTL_MS
        } else {
            u64::from(spec.timeout_secs).saturating_mul(1000)
        };
        Self {
            request_id: spec
                .request_id
                .clone()
                .unwrap_or_else(|| uuid::Uuid::new_v4().to_string()),
            origin,
            spec,
            queued_at_ms: now_ms,
            expires_at_ms: now_ms.saturating_add(ttl_ms),
            state: RequestState::Pending,
            response: None,
            notified_via: Vec::new(),
            metadata: serde_json::Map::new(),
        }
    }

    /// Whether the request has expired against the current wall clock.
    #[must_use]
    pub fn is_expired_now(&self) -> bool {
        unix_now_ms() >= self.expires_at_ms
    }

    /// Whether the state is terminal (Answered / Cancelled / Expired).
    #[must_use]
    pub fn is_terminal(&self) -> bool {
        matches!(
            self.state,
            RequestState::Answered | RequestState::Cancelled | RequestState::Expired
        )
    }

    /// Path on disk for this request inside `inbox_dir`.
    #[must_use]
    pub fn path_in(&self, inbox_dir: &Path) -> PathBuf {
        inbox_dir.join(format!("{}.json", self.request_id))
    }
}

/// Compute the current wall-clock millisecond timestamp.
#[must_use]
pub fn unix_now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_millis() as u64)
}

/// Where the inbox data lives on disk.
///
/// Honours `PHINBOX_INBOX_DIR` (overrides everything), falls back to
/// `$XDG_DATA_HOME/phinbox` / `~/Library/Application Support/phinbox` /
/// `%LOCALAPPDATA%\phinbox` depending on platform.
#[must_use]
pub fn default_inbox_root() -> PathBuf {
    if let Ok(p) = std::env::var("PHINBOX_INBOX_DIR") {
        return PathBuf::from(p);
    }
    if let Some(home) = std::env::var_os("XDG_DATA_HOME") {
        return PathBuf::from(home).join("phinbox");
    }
    if cfg!(target_os = "macos") {
        if let Some(home) = std::env::var_os("HOME") {
            return PathBuf::from(home).join("Library/Application Support/phinbox");
        }
    }
    if cfg!(target_os = "windows") {
        if let Ok(p) = std::env::var("LOCALAPPDATA") {
            return PathBuf::from(p).join("phinbox");
        }
    }
    if let Some(home) = std::env::var_os("HOME") {
        return PathBuf::from(home).join(".local/share/phinbox");
    }
    // last-resort fallback (CI without $HOME): a per-process temp dir.
    std::env::temp_dir().join("phinbox-inbox")
}

/// Subdirectory for pending entries.
#[must_use]
pub fn inbox_pending_dir(root: &Path) -> PathBuf {
    root.join("inbox")
}

/// Subdirectory for answered/terminal entries (audit trail).
#[must_use]
pub fn answered_dir(root: &Path) -> PathBuf {
    root.join("answered")
}

/// Load a single request by id from `root` (pending OR answered).
pub fn load(root: &Path, request_id: &str) -> Result<PendingRequest, ElicitError> {
    let candidates = [
        inbox_pending_dir(root).join(format!("{request_id}.json")),
        answered_dir(root).join(format!("{request_id}.json")),
    ];
    for path in candidates {
        if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            return serde_json::from_str(&text).map_err(ElicitError::Json);
        }
    }
    Err(ElicitError::InvalidSpec(format!(
        "no inbox entry for request_id '{request_id}'"
    )))
}

/// Wait until `req.request_id` reaches a terminal state or the wait times out.
///
/// Subscribes to the global `InboxChangeBus` and wakes immediately when
/// `enqueue` or `finalize` for *any* request pings it (crossbeam broadcast).
/// `poll_interval` is now only the floor; the wake path is event-driven.
pub fn wait_for_response(
    root: &Path,
    request_id: &str,
    poll_interval: Duration,
    overall_timeout: Duration,
) -> Result<PendingRequest, ElicitError> {
    let start = std::time::Instant::now();
    let deadline = start.checked_add(overall_timeout).unwrap_or(start);
    let mut watcher = InboxChangeBus::global().subscribe();
    loop {
        // Re-check the file on every wake (handles the case where the
        // notify raced the rename — the rename is in `enqueue`/`finalize`
        // *before* the bus ping, so this is theoretically unreachable,
        // but a defensive load() costs nothing).
        match load(root, request_id) {
            Ok(req) if req.is_terminal() => return Ok(req),
            Ok(_req) => {}
            Err(e) => return Err(e),
        }
        if std::time::Instant::now() >= deadline {
            return Err(ElicitError::Timeout(
                std::time::Instant::now()
                    .saturating_duration_since(start),
            ));
        }
        // Sleep at most `poll_interval` or until the next bus wake, whichever
        // comes first.
        let now = std::time::Instant::now();
        let remaining = deadline.saturating_duration_since(now);
        let cap = poll_interval.min(remaining.max(Duration::from_millis(1)));
        let _ = watcher.wait_changed(cap);
    }
}
