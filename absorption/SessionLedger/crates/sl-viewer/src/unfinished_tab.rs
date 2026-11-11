//! Viewer tab for unfinished and in-progress work.

use dioxus::prelude::*;
use session_ledger::domain::session::Corpus;
use session_ledger::domain::worklog::{
    project_unfinished_work, UnfinishedReason, UnfinishedWorkItem,
};

use crate::app::SessionContext;

/// Project unfinished work and order the most recently active items first.
#[must_use]
pub fn unfinished_items(
    sessions: &[session_ledger::domain::session::Session],
) -> Vec<UnfinishedWorkItem> {
    let mut items = project_unfinished_work(sessions);
    items.sort_by(|left, right| {
        right
            .last_activity_ms
            .cmp(&left.last_activity_ms)
            .then_with(|| left.session_id.cmp(&right.session_id))
    });
    items
}

/// Human-readable label for an unfinished-work reason.
#[must_use]
pub const fn reason_label(reason: UnfinishedReason) -> &'static str {
    match reason {
        UnfinishedReason::AwaitingAssistantResponse => "Awaiting assistant response",
        UnfinishedReason::InterruptedExecution => "Interrupted execution",
        UnfinishedReason::MissingCompletionMarker => "Completion not recorded",
    }
}

const fn corpus_label(corpus: Corpus) -> &'static str {
    match corpus {
        Corpus::Forge => "Forge",
        Corpus::Codex => "Codex",
        Corpus::ClaudeCode => "Claude Code",
        Corpus::Cursor => "Cursor",
        Corpus::FactoryDroid => "Factory Droid",
        Corpus::ChatGptWeb => "ChatGPT",
        Corpus::ClaudeWeb => "Claude web",
        Corpus::GeminiWeb => "Gemini",
    }
}

/// A list of sessions that the domain worklog projection marks as unfinished.
#[component]
pub fn UnfinishedWork() -> Element {
    let sessions = use_context::<SessionContext>();
    let items = unfinished_items(&sessions.0.read());
    let count = items.len();
    let noun = if count == 1 { "item" } else { "items" };

    rsx! {
        style { r#"
            .unfinished-view {{
                height: 100%;
                overflow-y: auto;
                padding: 20px;
                box-sizing: border-box;
            }}
            .unfinished-heading {{
                margin: 0;
                font-size: 16px;
                color: #e2e8f0;
            }}
            .unfinished-count {{
                margin: 5px 0 16px;
                color: #94a3b8;
                font-size: 12px;
            }}
            .unfinished-list {{
                list-style: none;
                margin: 0;
                padding: 0;
                display: grid;
                gap: 10px;
            }}
            .unfinished-card {{
                padding: 14px;
                border: 1px solid #334155;
                border-left: 3px solid #f97316;
                border-radius: 8px;
                background: #1f2937;
            }}
            .unfinished-title {{
                margin: 0 0 7px;
                color: #e2e8f0;
                font-size: 14px;
                line-height: 1.3;
            }}
            .unfinished-summary {{
                margin: 0 0 10px;
                color: #cbd5e1;
                font-size: 13px;
                line-height: 1.5;
                overflow-wrap: anywhere;
            }}
            .unfinished-meta {{
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                color: #94a3b8;
                font-size: 11px;
            }}
            .unfinished-badge {{
                padding: 2px 7px;
                border-radius: 999px;
                background: #422006;
                color: #f97316;
                font-weight: 600;
            }}
            .unfinished-corpus {{
                padding: 2px 7px;
                border-radius: 999px;
                background: #172554;
                color: #93c5fd;
                font-weight: 600;
            }}
            .unfinished-empty {{
                padding: 32px 16px;
                border: 1px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                text-align: center;
                font-size: 13px;
            }}
        "# }
        section {
            class: "unfinished-view",
            "aria-labelledby": "unfinished-heading",
            h2 { id: "unfinished-heading", class: "unfinished-heading", "Unfinished work" }
            p {
                class: "unfinished-count",
                "aria-live": "polite",
                "{count} in-progress {noun}"
            }
            if items.is_empty() {
                div {
                    class: "unfinished-empty",
                    role: "status",
                    "No unfinished work was detected."
                }
            } else {
                ul {
                    class: "unfinished-list",
                    "aria-label": "Unfinished work items",
                    for item in items {
                        li {
                            key: "{item.session_id}",
                            article {
                                class: "unfinished-card",
                                h3 {
                                    class: "unfinished-title",
                                    {item.title.as_deref().unwrap_or("Untitled session")}
                                }
                                p { class: "unfinished-summary", "{item.summary}" }
                                div { class: "unfinished-meta",
                                    span { class: "unfinished-badge", "{reason_label(item.reason)}" }
                                    span { class: "unfinished-corpus", "{corpus_label(item.corpus)}" }
                                    span { "{item.message_count} messages" }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::session::{Message, Role, Session};

    fn unfinished_session(id: &str, timestamp: Option<i64>) -> Session {
        let mut session = Session::new(id, Corpus::Cursor);
        let mut message = Message::new(Role::User, format!("Continue {id}"));
        message.ts_ms = timestamp;
        session.messages.push(message);
        session
    }

    #[test]
    fn projection_orders_recent_activity_first_and_unknown_last() {
        let sessions = vec![
            unfinished_session("unknown", None),
            unfinished_session("older", Some(10)),
            unfinished_session("newer", Some(20)),
        ];

        let ids: Vec<_> =
            unfinished_items(&sessions).into_iter().map(|item| item.session_id).collect();

        assert_eq!(ids, ["newer", "older", "unknown"]);
    }

    #[test]
    fn reason_labels_explain_each_projection_signal() {
        assert_eq!(
            reason_label(UnfinishedReason::AwaitingAssistantResponse),
            "Awaiting assistant response"
        );
        assert_eq!(reason_label(UnfinishedReason::InterruptedExecution), "Interrupted execution");
        assert_eq!(
            reason_label(UnfinishedReason::MissingCompletionMarker),
            "Completion not recorded"
        );
    }
}
