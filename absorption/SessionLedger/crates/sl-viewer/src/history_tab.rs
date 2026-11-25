//! Session history timeline tab.
//!
//! Shows a reverse-chronological timeline of sessions with message excerpts,
//! corpus badges, and completion status.

use dioxus::prelude::*;

use session_ledger::domain::session::{Corpus, Session};
use session_ledger::viewer::SessionSummary;

use crate::app::SessionContext;

/// A single entry in the history timeline.
#[derive(Debug, Clone, PartialEq)]
pub struct TimelineEntry {
    /// Position of this session in the source corpus. Unlike a session ID, it
    /// remains unique when external sources contain colliding IDs.
    pub source_index: usize,
    pub summary: SessionSummary,
    pub corpus: Corpus,
    pub cwd: Option<String>,
    /// First few message snippets for preview.
    pub message_previews: Vec<String>,
    pub total_messages: usize,
}

/// Derive a timeline entry from a [`Session`].
#[must_use]
pub fn to_timeline_entry(session: &Session) -> TimelineEntry {
    let unfinished = !session.messages.is_empty()
        && !session
            .messages
            .last()
            .map(|m| {
                let lower = m.content.to_lowercase();
                lower.contains("looks good")
                    || lower.contains("approved")
                    || lower.contains("ship it")
                    || lower.contains("all good")
                    || lower.contains("thanks")
                    || lower.contains("done")
            })
            .unwrap_or(true);

    let summary = SessionSummary {
        id: session.id.clone(),
        title: session.title.clone(),
        intent_state: session_ledger::domain::intent::IntentState::Extracted,
        message_count: session.messages.len(),
        unfinished,
    };

    // First 3 messages as previews (truncated).
    let message_previews: Vec<String> = session
        .messages
        .iter()
        .take(3)
        .map(|m| {
            let label = match m.role {
                session_ledger::domain::session::Role::User => "🧑",
                session_ledger::domain::session::Role::Assistant => "🤖",
                session_ledger::domain::session::Role::Subagent => "⚙️",
                session_ledger::domain::session::Role::Tool => "🔧",
                session_ledger::domain::session::Role::System => "💻",
            };
            let truncated = if m.content.len() > 100 {
                format!("{}...", &m.content[..97])
            } else {
                m.content.clone()
            };
            format!("{label} {truncated}")
        })
        .collect();

    TimelineEntry {
        source_index: 0,
        summary,
        corpus: session.corpus,
        cwd: session.cwd.clone(),
        message_previews,
        total_messages: session.messages.len(),
    }
}

/// Build all timeline entries from a slice of sessions.
#[must_use]
pub fn all_timeline_entries(sessions: &[Session]) -> Vec<TimelineEntry> {
    let mut entries: Vec<TimelineEntry> = sessions
        .iter()
        .enumerate()
        .map(|(source_index, session)| {
            let mut entry = to_timeline_entry(session);
            entry.source_index = source_index;
            entry
        })
        .collect();
    // Sort newest-first by message count as a proxy for chronological order.
    entries.sort_by_key(|e| std::cmp::Reverse(e.total_messages));
    entries
}

/// Resolve an entry to the exact source session that produced it.
///
/// IDs are supplied by external corpus providers and can collide, so timeline
/// detail selection must use the stable source position rather than `id`.
#[must_use]
pub fn session_for_timeline_entry<'a>(
    sessions: &'a [Session],
    entry: &TimelineEntry,
) -> Option<&'a Session> {
    sessions.get(entry.source_index)
}

/// Corpus badge colour.
fn corpus_label(corpus: Corpus) -> &'static str {
    match corpus {
        Corpus::Forge => "forge",
        Corpus::Codex => "codex",
        Corpus::ClaudeCode => "claude",
        Corpus::Cursor => "cursor",
        Corpus::FactoryDroid => "droid",
        Corpus::ChatGptWeb => "chatgpt",
        Corpus::ClaudeWeb => "claude web",
        Corpus::GeminiWeb => "gemini",
    }
}

/// The full history timeline component.
///
/// Reads sessions from the [`SessionContext`] injected by the root [`App`]
/// component.  When `FORGE_DB` is set, those are real ingested sessions.
#[component]
pub fn HistoryTimeline() -> Element {
    let ctx = use_context::<SessionContext>();
    // Reactive read: this body re-runs whenever the async corpus loader
    // updates the session signal. The earlier `use_signal(move || ...)`
    // wrapper only ran the closure once at mount, so the timeline stayed
    // frozen on the (then-empty) initial value forever.
    let entries = all_timeline_entries(&ctx.0.read());
    let mut selected_source_index: Signal<Option<usize>> = use_signal(|| None);

    let selected = selected_source_index()
        .and_then(|source_index| entries.iter().find(|entry| entry.source_index == source_index))
        .cloned();
    let timeline_rows: Vec<_> =
        entries.iter().cloned().map(|entry| (entry.source_index, entry)).collect();

    rsx! {
        style { r#"
            .history-entry {{
                padding: 14px 20px;
                cursor: pointer;
                border-bottom: 1px solid #1e2029;
                transition: background 0.15s;
            }}
            .history-entry:hover {{ background: #1c1f2b; }}
            .history-entry.selected {{ background: #252836; border-left: 3px solid #f59e0b; }}
            .history-entry .session-id {{
                font-size: 12px; color: #8b8fa3; margin-bottom: 4px;
                font-family: monospace;
            }}
            .history-entry .session-title {{
                font-size: 14px; font-weight: 600; color: #e1e4ea;
            }}
            .history-entry .meta-row {{
                font-size: 11px; color: #8b8fa3; margin-top: 6px;
                display: flex; gap: 8px; align-items: center;
            }}
            .history-entry .preview {{
                font-size: 12px; color: #8b8fa3; margin-top: 8px;
                line-height: 1.5;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
            }}
            .corpus-badge {{
                display: inline-block; padding: 1px 8px; border-radius: 4px;
                font-size: 10px; font-weight: 600; text-transform: uppercase;
            }}
            .corpus-forge {{ background: #1a3a2a; color: #4ade80; }}
            .corpus-codex {{ background: #1a2a3a; color: #60a5fa; }}
            .corpus-claude {{ background: #2a1a3a; color: #c084fc; }}
            .corpus-cursor {{ background: #2a2a1a; color: #facc15; }}
            .corpus-droid {{ background: #1a2a2a; color: #2dd4bf; }}
            .status-unfinished {{ color: #fb923c; }}
            .timeline-detail {{
                flex: 1; overflow-y: auto; padding: 32px 40px;
            }}
            .timeline-detail h1 {{
                font-size: 18px; font-weight: 600; margin: 0 0 24px 0; color: #e1e4ea;
            }}
            .timeline-detail .message {{
                padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;
                font-size: 13px; line-height: 1.6;
            }}
            .timeline-detail .message-user {{
                background: #1a1d2e; border-left: 3px solid #6c8cff;
            }}
            .timeline-detail .message-assistant {{
                background: #1e1a2e; border-left: 3px solid #c084fc;
            }}
            .timeline-detail .message-subagent {{
                background: #1e2a1e; border-left: 3px solid #4ade80;
            }}
            .timeline-detail .message-tool {{
                background: #2a1e1e; border-left: 3px solid #fb923c;
            }}
            .timeline-detail .message-system {{
                background: #1e1e2a; border-left: 3px solid #8b8fa3;
            }}
            .timeline-detail .message-role {{
                font-size: 10px; font-weight: 600; text-transform: uppercase;
                letter-spacing: 0.5px; margin-bottom: 4px;
            }}
            .role-user {{ color: #6c8cff; }}
            .role-assistant {{ color: #c084fc; }}
            .role-subagent {{ color: #4ade80; }}
            .role-tool {{ color: #fb923c; }}
            .role-system {{ color: #8b8fa3; }}
        "# }
        div { class: "sidebar",
            h2 { "Session History" }
            for (source_index, entry) in timeline_rows {
                TimelineRow {
                    key: "history-{source_index}",
                    entry,
                    is_selected: selected_source_index() == Some(source_index),
                    on_click: move |_| { selected_source_index.set(Some(source_index)); },
                }
            }
        }
        match selected {
            Some(ref entry) => rsx! { TimelineDetail { entry: entry.clone() } },
            None => rsx! {
                div { class: "empty-state", "Select a session from the timeline to inspect" }
            },
        }
    }
}

/// A single row in the history timeline.
#[component]
fn TimelineRow(entry: TimelineEntry, is_selected: bool, on_click: EventHandler<()>) -> Element {
    let sel_class = if is_selected { " selected" } else { "" };
    let corpus_class = format!("corpus-badge corpus-{}", corpus_label(entry.corpus));
    let status_text = if entry.summary.unfinished { "in progress" } else { "completed" };

    rsx! {
        div {
            class: "history-entry{sel_class}",
            onclick: move |_| on_click.call(()),
            div { class: "session-id", "{entry.summary.id}" }
            div { class: "session-title",
                if let Some(ref title) = entry.summary.title {
                    "{title}"
                } else {
                    "(untitled)"
                }
            }
            div { class: "meta-row",
                span { class: "{corpus_class}", "{corpus_label(entry.corpus)}" }
                span { "{entry.total_messages} messages" }
                span { "·" }
                if entry.summary.unfinished {
                    span { class: "status-unfinished", "{status_text}" }
                } else {
                    span { "{status_text}" }
                }
            }
            if !entry.message_previews.is_empty() {
                div { class: "preview",
                    for preview in &entry.message_previews {
                        "{preview}"
                        br {}
                    }
                }
            }
        }
    }
}

/// Detail view showing all messages in a session.
#[component]
fn TimelineDetail(entry: TimelineEntry) -> Element {
    // Look up the full session from the injected context (real or mock data).
    let ctx = use_context::<SessionContext>();
    let session = session_for_timeline_entry(&ctx.0.read(), &entry).cloned();
    let title_text = entry.summary.title.clone().unwrap_or_else(|| "Session Details".into());
    let status_text = if entry.summary.unfinished { "In Progress" } else { "Completed" };

    // Build message elements outside of rsx! so we can use match/format freely.
    let msg_header;
    let message_nodes;
    if let Some(sess) = session {
        let count = sess.messages.len();
        msg_header = format!("Message Log ({count})");
        message_nodes = sess
            .messages
            .iter()
            .map(|msg| {
                let role_str = match msg.role {
                    session_ledger::domain::session::Role::User => "user",
                    session_ledger::domain::session::Role::Assistant => "assistant",
                    session_ledger::domain::session::Role::Subagent => "subagent",
                    session_ledger::domain::session::Role::Tool => "tool",
                    session_ledger::domain::session::Role::System => "system",
                };
                let msg_class = format!("message message-{role_str}");
                let role_class = format!("message-role role-{role_str}");
                let content = msg.content.clone();
                rsx! {
                    div { class: "{msg_class}",
                        div { class: "{role_class}", "{role_str}" }
                        p { "{content}" }
                    }
                }
            })
            .collect::<Vec<_>>();
    } else {
        msg_header = String::new();
        message_nodes = Vec::new();
    }

    rsx! {
        div { class: "timeline-detail",
            h1 { "{title_text}" }
            div { class: "detail-section",
                h3 { "Session Info" }
                p { "ID: {entry.summary.id}" }
                if let Some(ref cwd) = entry.cwd {
                    p { "Directory: {cwd}" }
                }
                p { "Messages: {entry.total_messages}" }
                p { "Status: {status_text}" }
            }
            if !message_nodes.is_empty() {
                div { class: "detail-section",
                    h3 { "{msg_header}" }
                    {message_nodes.into_iter()}
                }
            }
        }
    }
}
