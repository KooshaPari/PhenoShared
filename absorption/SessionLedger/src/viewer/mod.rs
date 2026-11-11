//! Read model for the wiki / docs / history viewer.
//!
//! Phase 1 ships the projection types; the HTTP/TUI surface and its FTS-backed
//! search (composed from context-mode `ctx_search`) land in Phase 4.

use crate::domain::intent::IntentState;
use serde::{Deserialize, Serialize};

/// A compact row for the session-history list view.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SessionSummary {
    pub id: String,
    pub title: Option<String>,
    pub intent_state: IntentState,
    pub message_count: usize,
    /// True when the session has outstanding work (lands in the "in-progress /
    /// unfinished" section — use case (b), lost-work localization).
    pub unfinished: bool,
}
