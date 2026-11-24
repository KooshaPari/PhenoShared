//! Crash detection and unfinished-work projection.
//!
//! The normalized session model does not yet carry a provider lifecycle field,
//! so detection is deliberately conservative: a session with operator work is
//! unfinished unless its final assistant turn contains an explicit completion
//! marker. The reason is serialized so consumers can distinguish strong signals
//! (for example, an unanswered user turn) from a missing marker.

use super::session::{Corpus, Role, Session};
use serde::{Deserialize, Serialize};

/// Why a session was projected as unfinished.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum UnfinishedReason {
    /// The final turn is from the operator and has no assistant response.
    AwaitingAssistantResponse,
    /// The transcript stops during tool or subagent activity.
    InterruptedExecution,
    /// The assistant responded, but no terminal completion marker was recorded.
    MissingCompletionMarker,
}

/// A viewer-ready reference to work that may need to be resumed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnfinishedWorkItem {
    pub session_id: String,
    pub corpus: Corpus,
    pub title: Option<String>,
    /// The latest operator request, whitespace-normalized and size-bounded.
    pub summary: String,
    pub reason: UnfinishedReason,
    pub message_count: usize,
    /// Timestamp of the latest timestamped message, when supplied by the corpus.
    pub last_activity_ms: Option<i64>,
}

/// The typed body stored in a continuation bundle's `Worklog` slice.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorklogProjection {
    pub message_count: usize,
    pub unfinished: Vec<UnfinishedWorkItem>,
}

impl WorklogProjection {
    /// Detect unfinished work for one normalized session.
    #[must_use]
    pub fn from_session(session: &Session) -> Self {
        Self {
            message_count: session.messages.len(),
            unfinished: detect_unfinished(session).into_iter().collect(),
        }
    }
}

/// Project all unfinished work across a collection of normalized sessions.
#[must_use]
pub fn project_unfinished_work(sessions: &[Session]) -> Vec<UnfinishedWorkItem> {
    sessions.iter().filter_map(detect_unfinished).collect()
}

/// Return an unfinished-work item when transcript signals indicate that a
/// session ended without an explicit completion.
#[must_use]
pub fn detect_unfinished(session: &Session) -> Option<UnfinishedWorkItem> {
    let latest_user = session.messages.iter().rev().find(|message| message.role == Role::User)?;
    let final_message = session.messages.last()?;

    if final_message.role == Role::Assistant && has_completion_marker(&final_message.content) {
        return None;
    }

    let reason = match final_message.role {
        Role::User => UnfinishedReason::AwaitingAssistantResponse,
        Role::Tool | Role::Subagent => UnfinishedReason::InterruptedExecution,
        Role::Assistant | Role::System => UnfinishedReason::MissingCompletionMarker,
    };

    Some(UnfinishedWorkItem {
        session_id: session.id.clone(),
        corpus: session.corpus,
        title: session.title.clone(),
        summary: summarize(&latest_user.content),
        reason,
        message_count: session.messages.len(),
        last_activity_ms: session.messages.iter().rev().find_map(|message| message.ts_ms),
    })
}

fn has_completion_marker(content: &str) -> bool {
    content.lines().map(str::trim).any(|line| {
        let line = line.to_ascii_lowercase();
        matches!(
            line.as_str(),
            "complete"
                | "completed"
                | "done"
                | "[completed]"
                | "<completed>"
                | "status: complete"
                | "status: completed"
                | "task complete"
                | "task completed"
        )
    })
}

fn summarize(content: &str) -> String {
    const MAX_CHARS: usize = 240;
    let normalized = content.split_whitespace().collect::<Vec<_>>().join(" ");
    let mut chars = normalized.chars();
    let summary: String = chars.by_ref().take(MAX_CHARS).collect();
    if chars.next().is_some() {
        format!("{summary}…")
    } else {
        summary
    }
}

#[cfg(test)]
mod tests {
    // Traceability: unfinished-work detector + WorklogProjection → FR-011 (T-024).
    use super::*;
    use crate::domain::session::Message;

    fn session_with(messages: &[(Role, &str)]) -> Session {
        let mut session = Session::new("session-1", Corpus::Cursor);
        session.title = Some("Crash recovery".into());
        session.messages =
            messages.iter().map(|(role, content)| Message::new(*role, *content)).collect();
        session
    }

    #[test]
    fn fr011_unanswered_user_turn_is_unfinished() {
        let session = session_with(&[(Role::User, "Implement crash recovery")]);
        let item = detect_unfinished(&session).expect("user work should be unfinished");

        assert_eq!(item.reason, UnfinishedReason::AwaitingAssistantResponse);
        assert_eq!(item.summary, "Implement crash recovery");
    }

    #[test]
    fn tool_tail_is_interrupted_execution() {
        let session = session_with(&[
            (Role::User, "Run the migration"),
            (Role::Assistant, "Starting it"),
            (Role::Tool, "process exited unexpectedly"),
        ]);

        assert_eq!(
            detect_unfinished(&session).map(|item| item.reason),
            Some(UnfinishedReason::InterruptedExecution)
        );
    }

    #[test]
    fn assistant_without_terminal_marker_is_conservatively_unfinished() {
        let session = session_with(&[
            (Role::User, "Implement crash recovery"),
            (Role::Assistant, "I updated the domain module."),
        ]);

        assert_eq!(
            detect_unfinished(&session).map(|item| item.reason),
            Some(UnfinishedReason::MissingCompletionMarker)
        );
    }

    #[test]
    fn explicit_completion_marker_finishes_session() {
        let session = session_with(&[
            (Role::User, "Implement crash recovery"),
            (Role::Assistant, "Implemented and tested.\n\nStatus: completed"),
        ]);

        assert_eq!(detect_unfinished(&session), None);
    }

    #[test]
    fn sessions_without_operator_work_are_not_projected() {
        let empty = Session::new("empty", Corpus::Forge);
        let system_only = session_with(&[(Role::System, "bootstrap")]);

        assert_eq!(detect_unfinished(&empty), None);
        assert_eq!(detect_unfinished(&system_only), None);
    }

    #[test]
    fn projection_collects_only_unfinished_sessions() {
        let unfinished = session_with(&[(Role::User, "Continue this")]);
        let completed = session_with(&[(Role::User, "Finish this"), (Role::Assistant, "Done")]);

        let projected = project_unfinished_work(&[unfinished, completed]);

        assert_eq!(projected.len(), 1);
        assert_eq!(projected[0].summary, "Continue this");
    }

    #[test]
    fn worklog_projection_serializes_and_round_trips() {
        let mut session = session_with(&[(Role::User, "Recover this session")]);
        session.messages[0].ts_ms = Some(42);
        let projection = WorklogProjection::from_session(&session);

        let json = serde_json::to_string(&projection).expect("projection should serialize");
        let decoded: WorklogProjection =
            serde_json::from_str(&json).expect("projection should deserialize");

        assert_eq!(decoded, projection);
        assert_eq!(decoded.unfinished[0].last_activity_ms, Some(42));
    }

    #[test]
    fn summary_is_whitespace_normalized_and_bounded() {
        let request = format!("  {}\n next  ", "x".repeat(250));
        let session = session_with(&[(Role::User, &request)]);
        let item = detect_unfinished(&session).expect("request should be unfinished");

        assert_eq!(item.summary.chars().count(), 241);
        assert!(item.summary.ends_with('…'));
        assert!(!item.summary.contains('\n'));
    }
}
