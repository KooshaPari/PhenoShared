use std::path::{Path, PathBuf};

use super::{answered_dir, inbox_pending_dir, PendingRequest};
use crate::error::ElicitError;

use super::change::InboxChangeBus;

/// Persist a pending request to disk. Creates parent dirs if missing.
///
/// After the atomic rename, pings the global `InboxChangeBus` so any TUI
/// or daemon subscriber re-renders promptly (no 1 s polling latency).
pub fn enqueue(root: &Path, req: &PendingRequest) -> Result<PathBuf, ElicitError> {
    let dir = inbox_pending_dir(root);
    std::fs::create_dir_all(&dir)?;
    let path = req.path_in(&dir);
    let json = serde_json::to_vec_pretty(req).map_err(ElicitError::Json)?;
    // Atomic write: stage in <id>.tmp, rename over final.
    let tmp = dir.join(format!("{}.tmp", req.request_id));
    std::fs::write(&tmp, &json)?;
    std::fs::rename(&tmp, &path)?;
    InboxChangeBus::global().notify(&format!("enqueue:{}", req.request_id));
    Ok(path)
}

/// Move a request from the pending directory to the answered directory
/// after the user has responded. Returns the new path.
///
/// The mutated `req` (with `state` / `response` populated by the caller) is
/// serialized to the new path *before* the original pending file is removed.
/// Renaming alone would carry the pre-answer state forward and the waiter
/// would never observe the response.
///
/// Pings the global `InboxChangeBus` after the final write so waiters
/// unblock immediately (no `poll_interval` latency).
pub fn finalize(root: &Path, req: &PendingRequest) -> Result<PathBuf, ElicitError> {
    let pending = inbox_pending_dir(root).join(format!("{}.json", req.request_id));
    let answered = answered_dir(root);
    std::fs::create_dir_all(&answered)?;
    let dst = answered.join(format!("{}.json", req.request_id));
    if let Some(parent) = dst.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    // 1. Write the *updated* req (new state/response) to the answered path.
    let json = serde_json::to_vec_pretty(req).map_err(ElicitError::Json)?;
    let tmp = answered.join(format!("{}.tmp", req.request_id));
    std::fs::write(&tmp, &json)?;
    std::fs::rename(&tmp, &dst)?;
    // 2. Best-effort remove the original pending file (no-op if it was
    //    already removed by another worker).
    std::fs::remove_file(&pending).ok();
    InboxChangeBus::global().notify(&format!("finalize:{}", req.request_id));
    Ok(dst)
}
