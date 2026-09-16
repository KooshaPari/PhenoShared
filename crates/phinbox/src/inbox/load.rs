use std::path::Path;

use super::{inbox_pending_dir, answered_dir, PendingRequest};
use crate::error::ElicitError;

/// Load a pending (non-terminal) request by id from `root`.
///
/// Returns `Ok(None)` when the entry is missing or already terminal.
pub fn load_pending(
    root: &Path,
    request_id: &str,
) -> Result<Option<PendingRequest>, ElicitError> {
    let pending = inbox_pending_dir(root).join(format!("{request_id}.json"));
    if !pending.exists() {
        return Ok(None);
    }
    let text = std::fs::read_to_string(&pending)?;
    let req: PendingRequest = serde_json::from_str(&text).map_err(ElicitError::Json)?;
    Ok(Some(req))
}

/// Load a request by id from `root` (pending OR answered).
///
/// Returns `Ok(None)` when the entry does not exist.
pub fn load_request(
    root: &Path,
    request_id: &str,
) -> Result<Option<PendingRequest>, ElicitError> {
    let candidates = [
        inbox_pending_dir(root).join(format!("{request_id}.json")),
        answered_dir(root).join(format!("{request_id}.json")),
    ];
    for path in candidates {
        if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            return serde_json::from_str(&text)
                .map(Some)
                .map_err(ElicitError::Json);
        }
    }
    Ok(None)
}

/// List all pending (non-terminal) requests, newest first.
pub fn list_pending(root: &Path) -> Result<Vec<PendingRequest>, ElicitError> {
    let dir = inbox_pending_dir(root);
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    for entry in std::fs::read_dir(&dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("json") {
            continue;
        }
        let text = std::fs::read_to_string(&path)?;
        let req: PendingRequest = match serde_json::from_str(&text) {
            Ok(r) => r,
            Err(_) => continue, // skip corrupt entries
        };
        out.push(req);
    }
    // Newest first
    out.sort_by(|a, b| b.queued_at_ms.cmp(&a.queued_at_ms));
    Ok(out)
}
