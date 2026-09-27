//! Tool-approval helpers: turn a pending tool call into an `elicitate` prompt
//! with rich, legible details.
//!
//! This is the bridge the hook system and harnesses use. Given a tool call
//! (a command, the files it touches, why it is being asked), it builds a
//! [`PromptSpec`] whose `details` block renders the files, reason, effects and
//! warning in the popup, the TUI, the browser form, or the in-chat surface —
//! and whose `buttons.defer_label` lets the operator push the decision to the
//! durable inbox and answer it later.

use crate::spec::{
    ButtonSpec, DetailItem, DetailsSpec, FieldSpec, FileAction, PromptSpec, Urgency,
};

/// A single file the approved action will affect.
#[derive(Debug, Clone)]
pub struct AffectedFile {
    /// Path as the caller knows it (absolute or repo-relative).
    pub path: String,
    /// What the action does to the file.
    pub action: FileAction,
    /// Optional note, e.g. "92 MB".
    pub note: Option<String>,
}

/// A pending tool approval, rendered as a rich prompt.
#[derive(Debug, Clone)]
pub struct ToolApproval {
    /// Short tool/verb label, e.g. "gh repo delete".
    pub tool: String,
    /// One-line question. Defaults to a generated sentence if empty.
    pub question: String,
    /// The literal command or tool call.
    pub command: Option<String>,
    /// Why the agent is asking.
    pub reason: Option<String>,
    /// Consequences of approving.
    pub effects: Vec<String>,
    /// Files the action will touch.
    pub files: Vec<AffectedFile>,
    /// Extra key/values (repo, branch, remote, ...).
    pub facts: Vec<(String, String)>,
    /// Warnings the operator must read.
    pub warnings: Vec<String>,
    /// How alarming this is.
    pub urgency: Urgency,
    /// Timeout in seconds (0 = no timeout; the hook enforces its own bound).
    pub timeout_secs: u32,
}

impl Default for ToolApproval {
    fn default() -> Self {
        Self {
            tool: String::new(),
            question: String::new(),
            command: None,
            reason: None,
            effects: Vec::new(),
            files: Vec::new(),
            facts: Vec::new(),
            warnings: Vec::new(),
            urgency: Urgency::Warning,
            timeout_secs: 0,
        }
    }
}

impl ToolApproval {
    /// Start an approval for a tool/verb.
    #[must_use]
    pub fn new(tool: impl Into<String>) -> Self {
        Self {
            tool: tool.into(),
            ..Default::default()
        }
    }

    /// Set the one-line question.
    #[must_use]
    pub fn question(mut self, q: impl Into<String>) -> Self {
        self.question = q.into();
        self
    }

    /// Set the literal command being approved.
    #[must_use]
    pub fn command(mut self, c: impl Into<String>) -> Self {
        self.command = Some(c.into());
        self
    }

    /// Set why the agent is asking.
    #[must_use]
    pub fn reason(mut self, r: impl Into<String>) -> Self {
        self.reason = Some(r.into());
        self
    }

    /// Add a consequence of approving.
    #[must_use]
    pub fn effect(mut self, e: impl Into<String>) -> Self {
        self.effects.push(e.into());
        self
    }

    /// Add a file the action will touch.
    #[must_use]
    pub fn file(
        mut self,
        path: impl Into<String>,
        action: FileAction,
        note: Option<String>,
    ) -> Self {
        self.files.push(AffectedFile {
            path: path.into(),
            action,
            note,
        });
        self
    }

    /// Add a key/value fact.
    #[must_use]
    pub fn fact(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.facts.push((key.into(), value.into()));
        self
    }

    /// Add a warning.
    #[must_use]
    pub fn warn(mut self, w: impl Into<String>) -> Self {
        self.warnings.push(w.into());
        self
    }

    /// Set the urgency.
    #[must_use]
    pub fn urgency(mut self, u: Urgency) -> Self {
        self.urgency = u;
        self
    }

    /// Render into a [`PromptSpec`] ready for `elicitate`.
    ///
    /// The field is a boolean "Approve?" (default false). The buttons carry a
    /// `defer_label` so every capable renderer offers "defer to inbox".
    #[must_use]
    pub fn to_prompt_spec(&self) -> PromptSpec {
        let question = if self.question.is_empty() {
            format!("Approve `{}`?", self.tool)
        } else {
            self.question.clone()
        };

        let mut items: Vec<DetailItem> = Vec::new();
        if let Some(cmd) = &self.command {
            items.push(DetailItem::KeyValue {
                key: "command".to_string(),
                value: cmd.clone(),
            });
        }
        for (k, v) in &self.facts {
            items.push(DetailItem::KeyValue {
                key: k.clone(),
                value: v.clone(),
            });
        }
        for f in &self.files {
            items.push(DetailItem::File {
                path: f.path.clone(),
                action: f.action,
                note: f.note.clone(),
            });
        }
        for w in &self.warnings {
            items.push(DetailItem::Warning {
                message: w.clone(),
            });
        }
        if let Some(r) = &self.reason {
            items.push(DetailItem::Text {
                label: "Reason".to_string(),
                body: r.clone(),
            });
        }

        let details = DetailsSpec {
            reason: self.reason.clone(),
            items,
            effects: self.effects.clone(),
            command: self.command.clone(),
        };

        PromptSpec {
            title: format!("Approve: {}", self.tool),
            question,
            field: FieldSpec::Boolean {
                label: "Approve?".to_string(),
                default: Some(false),
            },
            notes: None,
            buttons: Some(ButtonSpec {
                cancel: "Deny".to_string(),
                confirm: "Approve".to_string(),
                default_is_cancel: false,
                defer_label: Some("Defer to inbox".to_string()),
            }),
            details: Some(details),
            urgency: self.urgency,
            timeout_secs: self.timeout_secs,
            request_id: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn delete_approval_renders_rich_items() {
        let spec = ToolApproval::new("delete files")
            .reason("Removing stale build artifacts.")
            .command("rm -rf target/")
            .file("target/debug", FileAction::Delete, Some("1.2 GB".into()))
            .file("target/release", FileAction::Delete, None)
            .effect("~1.2 GB reclaimed")
            .warn("Deletion is not recoverable")
            .fact("repo", "KooshaPari/PhenoShared")
            .to_prompt_spec();

        assert_eq!(spec.title, "Approve: delete files");
        assert!(matches!(
            spec.field,
            FieldSpec::Boolean {
                default: Some(false),
                ..
            }
        ));
        let buttons = spec.buttons.expect("buttons");
        assert_eq!(buttons.defer_label.as_deref(), Some("Defer to inbox"));
        let d = spec.details.expect("details");
        assert_eq!(d.reason.as_deref(), Some("Removing stale build artifacts."));
        assert_eq!(d.effects, vec!["~1.2 GB reclaimed"]);
        // command + repo + 2 files + 1 warning + 1 text
        assert_eq!(d.items.len(), 6);
        assert!(d
            .items
            .iter()
            .any(|i| matches!(i, DetailItem::Warning { .. })));
        assert!(d.items.iter().any(|i| matches!(
            i,
            DetailItem::File {
                action: FileAction::Delete,
                ..
            }
        )));
    }

    #[test]
    fn minimal_approval_has_default_question() {
        let spec = ToolApproval::new("gh repo create").to_prompt_spec();
        assert_eq!(spec.question, "Approve `gh repo create`?");
        assert_eq!(spec.urgency, Urgency::Warning);
        assert!(spec.details.is_some());
    }
}
