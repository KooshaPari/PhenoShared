use std::path::{Path, PathBuf};

use super::{inbox_pending_dir, PendingRequest};
use crate::error::ElicitError;

use super::change::InboxChangeBus;

/// Mark an expired request in-place inside the pending directory.
///
/// Unlike [`super::mark::finalize`], this does NOT move the file to
/// `answered/` — it rewrites the JSON in `inbox/` with the new terminal
/// state so the inbox UI can still render it (greyed-out / expired badge).
pub fn mark_expired_in_place(
    root: &Path,
    req: &PendingRequest,
) -> Result<PathBuf, ElicitError> {
    let dir = inbox_pending_dir(root);
    let path = dir.join(format!("{}.json", req.request_id));
    if !path.exists() {
        // Already removed (e.g. user answered between poll cycles).
        return Ok(path);
    }
    let json = serde_json::to_vec_pretty(req).map_err(ElicitError::Json)?;
    let tmp = dir.join(format!("{}.tmp", req.request_id));
    std::fs::write(&tmp, &json)?;
    std::fs::rename(&tmp, &path)?;
    InboxChangeBus::global().notify(&format!("expire:{}", req.request_id));
    Ok(path)
}
