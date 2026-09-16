//! TUI state types and inbox snapshot logic.

use crate::inbox::{list_pending as inbox_list_pending, PendingRequest, RequestState};
use std::path::Path;
use std::time::Duration;

/// Hard cap on entries rendered in the list pane — anything older scrolls
/// off the bottom but stays on disk.
pub(crate) const MAX_VISIBLE_REQUESTS: usize = 256;

/// How often to re-scan the inbox directory.
pub(crate) const POLL_INTERVAL: Duration = Duration::from_secs(1);

/// Outcome of running the TUI to completion.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TuiOutcome {
    /// User quit with `q` / `Esc` / `Ctrl+C`.
    Quit,
    /// User answered a request — the ID of the request that was answered.
    Answered(String),
    /// User dismissed a request — the ID of the request that was dismissed.
    Dismissed(String),
    /// TUI fell back to plain-text rendering because the terminal didn't
    /// support raw mode (e.g. CI without TTY, ssh with `TERM=dumb`).
    NoTty,
}

/// Lightweight description of a request as the list pane sees it.
///
/// We don't keep the full `PendingRequest` in the UI state because the list
/// pane is redrawn often and we don't want to keep parsing JSON twice.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ListEntry {
    pub request_id: String,
    pub title: String,
    pub urgency_label: String,
    pub state_badge: String,
    pub age_label: String,
    pub is_terminal: bool,
}

/// UI state for the inbox viewer — renderable without touching the terminal.
#[derive(Debug, Clone)]
pub struct ViewerState {
    pub entries: Vec<ListEntry>,
    pub selected: usize,
    pub focus_on_list: bool,
    pub status_message: String,
}

impl Default for ViewerState {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
            selected: 0,
            focus_on_list: true,
            status_message: String::from("press ? for keys · q to quit"),
        }
    }
}

impl ViewerState {
    /// Move selection down by `n`, clamped to the last entry.
    pub fn move_down(&mut self, n: usize) {
        if self.entries.is_empty() {
            return;
        }
        let max = self.entries.len() - 1;
        self.selected = (self.selected + n).min(max);
    }

    /// Move selection up by `n`, clamped to 0.
    pub fn move_up(&mut self, n: usize) {
        self.selected = self.selected.saturating_sub(n);
    }

    /// Jump to the first entry.
    pub fn jump_top(&mut self) {
        self.selected = 0;
    }

    /// Jump to the last entry.
    pub fn jump_bottom(&mut self) {
        if !self.entries.is_empty() {
            self.selected = self.entries.len() - 1;
        }
    }

    /// Toggle focus between list and detail pane.
    pub fn toggle_focus(&mut self) {
        self.focus_on_list = !self.focus_on_list;
    }

    /// The currently selected entry (if any).
    #[must_use]
    pub fn selected_entry(&self) -> Option<&ListEntry> {
        self.entries.get(self.selected)
    }
}

/// Build a `ListEntry` from a `PendingRequest` + the snapshot clock.
pub(crate) fn build_entry(req: &PendingRequest, now_ms: u64) -> ListEntry {
    let age_ms = now_ms.saturating_sub(req.queued_at_ms);
    let age_label = format_age(age_ms);
    let state_badge = match req.state {
        RequestState::Pending => "[P]",
        RequestState::Seen => "[S]",
        RequestState::Answered => "[A]",
        RequestState::Cancelled => "[X]",
        RequestState::Expired => "[E]",
    }
    .to_string();
    let urgency_label = format!("{:?}", req.spec.urgency);
    ListEntry {
        request_id: req.request_id.clone(),
        title: truncate(&req.spec.title, 40),
        urgency_label,
        state_badge,
        age_label,
        is_terminal: req.is_terminal(),
    }
}

/// Render a millisecond duration as a short human-readable string.
pub(crate) fn format_age(ms: u64) -> String {
    let s = ms / 1000;
    if s < 60 {
        format!("{s}s")
    } else if s < 3600 {
        format!("{}m", s / 60)
    } else if s < 86_400 {
        format!("{}h", s / 3600)
    } else {
        format!("{}d", s / 86_400)
    }
}

/// Truncate a string at `max` bytes, appending `…` if truncated.
pub(crate) fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}…", &s[..max.saturating_sub(1)])
    }
}

/// Sort entries: pending first (newest at top), then terminal (newest first
/// among themselves).
pub(crate) fn sort_entries(entries: &mut [ListEntry]) {
    entries.sort_by(|a, b| match (a.is_terminal, b.is_terminal) {
        (false, true) => std::cmp::Ordering::Less,
        (true, false) => std::cmp::Ordering::Greater,
        _ => a.age_label.cmp(&b.age_label),
    });
}

/// Public entry point — refresh the inbox from disk and return the snapshot.
pub fn snapshot_inbox(inbox_root: &Path) -> Result<Vec<ListEntry>, String> {
    let now_ms = crate::inbox::unix_now_ms();
    let pending = inbox_list_pending(inbox_root).map_err(|e| format!("list_pending: {e}"))?;
    let mut entries: Vec<ListEntry> = pending
        .iter()
        .take(MAX_VISIBLE_REQUESTS)
        .map(|r| build_entry(r, now_ms))
        .collect();
    sort_entries(&mut entries);
    Ok(entries)
}

/// Lookup helper used by the tests: find the request with the given ID in a
/// snapshot, returning its position if present.
#[must_use]
pub fn position_of(snapshot: &[ListEntry], id: &str) -> Option<usize> {
    snapshot.iter().position(|e| e.request_id == id)
}
