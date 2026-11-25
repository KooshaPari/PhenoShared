use dioxus::prelude::*;
use session_ledger::domain::session::Role;

use crate::app::SessionContext;

/// Render a session as a readable chat transcript shared by bundle and history views.
#[component]
pub fn SessionTranscript(session_id: String) -> Element {
    let context = use_context::<SessionContext>();
    let session = context.0.read().iter().find(|s| s.id == session_id).cloned();

    let Some(session) = session else {
        return rsx! {
            div { class: "transcript-empty", "No transcript is available for this session." }
        };
    };

    rsx! {
        div { class: "session-transcript", "aria-label": "Session transcript",
            div { class: "transcript-header",
                h3 { "Conversation" }
                span { class: "transcript-count", "{session.messages.len()} messages" }
            }
            for (index, message) in session.messages.iter().enumerate() {
                {
                    let (role, role_label) = match message.role {
                        Role::User => ("user", "You"),
                        Role::Assistant => ("assistant", "Assistant"),
                        Role::Subagent => ("subagent", "Subagent"),
                        Role::Tool => ("tool", "Tool"),
                        Role::System => ("system", "System"),
                    };
                    let test_id = format!("message-{role}");
                    rsx! {
                        article {
                            key: "{index}",
                            class: "transcript-message transcript-{role}",
                            "data-testid": "{test_id}",
                            div { class: "transcript-role", "{role_label}" }
                            p { "{message.content}" }
                        }
                    }
                }
            }
        }
    }
}
