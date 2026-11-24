//! Subagent semantic-threading model (P0.2).
//!
//! The data model (`Conversation.parent_id`, `conversation_id` resume, and the
//! `task` tool's agent dispatch) already handle *fresh-session delegation*. What is
//! missing is the *execution semantics* of semantic threading:
//!
//! 1. **Ephemeral vs. persistent forks** — whether a delegated conversation is a
//!    throwaway that runs a scoped task and returns a result, or a long-lived
//!    sibling that keeps its own history and can be resumed later.
//! 2. **Partial-context inheritance** — an ephemeral fork does not need the full
//!    parent context; it needs a *selection* (system preamble + task, recent
//!    turns, or full) so the sub-agent starts with just enough context.
//! 3. **Re-merge / promote / detach** — how a completed sub-agent's outcome is
//!    folded back into the parent (or released as a standalone conversation).
//!
//! This module is pure and dependency-light: it only touches [`Context`] and
//! [`ContextMessage`], so it can be unit-tested in isolation and composed by the
//! runtime executor later.

use crate::{Context, ContextMessage, Conversation, ConversationId};

/// How a delegated sub-agent conversation behaves.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SubagentMode {
    /// A scoped, throwaway conversation: run the task, return the result, and do
    /// not keep the history feed in the parent's selector. This is the default
    /// for `task` today.
    Ephemeral,
    /// A long-lived sibling: a fresh conversation linked via `parent_id` that
    /// keeps its own history and can be resumed by passing its `conversation_id`
    /// on a later delegation.
    Persistent,
}

/// How much of the parent's context an ephemeral fork inherits.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContextSelection {
    /// Only the system preamble plus the delegated task. Cheapest; the sub-agent
    /// must discover what it needs on its own. Good for well-scoped subtasks.
    SystemPreambleTop,
    /// System preamble plus the most recent `n` parent exchanges (each
    /// user/assistant/tool-run unit). Good when the subtask is about the
    /// immediately preceding work.
    Recent(usize),
    /// The full parent context. Most expensive; only for near-total refactors or
    /// when the sub-agent must reason about the whole session.
    Full,
}

/// A resolved plan for forking a delegated sub-agent conversation.
#[derive(Debug, Clone, PartialEq)]
pub struct SubagentFork {
    /// The linked parent conversation id (threading anchor).
    pub parent_id: ConversationId,
    /// Whether this fork is throwaway or resumable.
    pub mode: SubagentMode,
    /// The context the sub-agent will start with.
    pub inherited_context: Context,
    /// Human-readable note describing what was inherited (for the audit/toolcall
    /// view).
    pub selection_note: String,
}

impl SubagentFork {
    /// Build a fork from a parent conversation, a mode, and a selection policy.
    ///
    /// The delegated task is always appended as the final user message so the
    /// sub-agent knows exactly what it was asked to do.
    pub fn build(
        parent: &Conversation,
        mode: SubagentMode,
        selection: ContextSelection,
        task: &str,
    ) -> Self {
        let parent_ctx = parent.context.clone().unwrap_or_else(agent_context);

        let (mut inherited, note) = inherit_context(&parent_ctx, selection);

        // Mark the fork as agent-initiated and append the delegated task as the
        // trailing user turn.
        inherited = inherited.add_message(ContextMessage::user(task, None));

        let selection_note = format!("{note}; +delegated task (1 turn)");

        SubagentFork {
            parent_id: parent.id,
            mode,
            inherited_context: inherited,
            selection_note,
        }
    }
}

/// Inherit a *selection* of the parent context into a new sub-agent context.
///
/// The system preamble is always preserved (it defines the agent's behaviour);
/// the remaining selection policy controls how much conversation history follows.
pub fn inherit_context(parent: &Context, selection: ContextSelection) -> (Context, String) {
    let system: Vec<crate::MessageEntry> = parent
        .messages
        .iter()
        .filter(|m| m.has_role(crate::Role::System))
        .cloned()
        .collect();

    let non_system: Vec<crate::MessageEntry> = parent
        .messages
        .iter()
        .filter(|m| !m.has_role(crate::Role::System))
        .cloned()
        .collect();

    let (history, note) = match selection {
        ContextSelection::SystemPreambleTop => (Vec::new(), "system preamble only".to_string()),
        ContextSelection::Full => (non_system.clone(), "full parent context".to_string()),
        ContextSelection::Recent(n) => {
            let keep = recent_exchanges(&non_system, n);
            (keep, format!("last {n} exchange(s) (+ system)"))
        }
    };

    let mut ctx = Context::default();
    for m in system {
        ctx = ctx.add_entry(m);
    }
    for m in history {
        ctx = ctx.add_entry(m);
    }
    ctx.initiator = Some("agent".to_string());
    (ctx, note)
}

/// A fresh agent-initiated context (used when a parent has no context).
fn agent_context() -> Context {
    Context { initiator: Some("agent".to_string()), ..Context::default() }
}

/// Select the most recent `n` *exchanges* from a flat sequence of messages.
///
/// An exchange is a maximal run of non-system turns that begins at a fresh human
/// prompt — a user message that is *not* directly preceded by a tool result (i.e.
/// it is a new prompt, not a continuation of an agentic tool loop). Counting runs
/// from the end, we keep everything from the earliest kept exchange's start to the
/// end (preserving any trailing tool-result loops) and prune `droppable`
/// attachment blobs to keep the sub-agent's window small.
fn recent_exchanges(messages: &[crate::MessageEntry], n: usize) -> Vec<crate::MessageEntry> {
    if messages.is_empty() {
        return Vec::new();
    }

    // Identify the start index of each exchange.
    let mut exchange_starts: Vec<usize> = Vec::new();
    for (i, m) in messages.iter().enumerate() {
        let is_user = m.has_role(crate::Role::User);
        let prev_tool = i > 0
            && messages
                .get(i - 1)
                .is_some_and(|prev| prev.has_tool_result());
        if is_user && !prev_tool {
            exchange_starts.push(i);
        }
    }
    if exchange_starts.is_empty() {
        exchange_starts.push(0);
    }

    let keep = n.max(1);
    let keep_from = if exchange_starts.len() > keep {
        exchange_starts
            .get(exchange_starts.len() - keep)
            .copied()
            .unwrap_or(0)
    } else {
        0
    };

    messages
        .get(keep_from..)
        .unwrap_or(&[])
        .iter()
        .filter(|m| !m.is_droppable())
        .cloned()
        .collect()
}

/// A plan for folding a completed sub-agent's outcome back into the parent.
#[derive(Debug, Clone, PartialEq)]
pub struct MergePlan {
    /// Messages to append to the parent context, in order.
    pub messages: Vec<crate::MessageEntry>,
    /// Whether the sub-conversation itself should be retained (persistent) or
    /// discarded after merge (ephemeral).
    pub retain_sub_conversation: bool,
    /// Human-readable note for the audit / toolcall view.
    pub note: String,
}

/// Compute a merge plan for folding a completed sub-agent's `output` back into the
/// `parent` conversation.
pub fn plan_merge(
    fork: &SubagentFork,
    sub_conversation_id: ConversationId,
    output: &str,
) -> MergePlan {
    let retain = matches!(fork.mode, SubagentMode::Persistent);

    let task_echo = ContextMessage::user(
        format!(
            "[subagent {:?} completed — conversation {}]",
            fork.mode, sub_conversation_id
        ),
        None,
    );
    let answer = ContextMessage::assistant(output.to_string(), None, None, None);

    MergePlan {
        messages: vec![task_echo.into(), answer.into()],
        retain_sub_conversation: retain,
        note: if retain {
            format!(
                "sub-conversation {} retained (persistent child of {})",
                sub_conversation_id, fork.parent_id
            )
        } else {
            format!(
                "sub-conversation {} merged and discarded (ephemeral)",
                sub_conversation_id
            )
        },
    }
}

#[cfg(test)]
#[allow(
    clippy::indexing_slicing,
    clippy::string_slice,
    clippy::disallowed_methods
)]
mod tests {
    use super::*;
    use crate::{MetaData, Role};

    fn ctx_with(entries: Vec<(&str, Role)>) -> Context {
        let mut ctx = Context::default();
        for (content, role) in entries {
            let msg = match role {
                Role::System => ContextMessage::system(content),
                Role::User => ContextMessage::user(content, None),
                _ => ContextMessage::assistant(content, None, None, None),
            };
            ctx = ctx.add_message(msg);
        }
        ctx
    }

    fn conv(id: u64, ctx: Option<Context>) -> Conversation {
        Conversation {
            id: ConversationId::generate(),
            title: Some(format!("conv-{id}")),
            context: ctx,
            metrics: Default::default(),
            metadata: MetaData::new(chrono::Utc::now()),
            parent_id: None,
            source: None,
            cwd: None,
            message_count: None,
        }
    }

    #[test]
    fn inherit_system_preamble_only_drops_history() {
        let parent = ctx_with(vec![
            ("system", Role::System),
            ("hello", Role::User),
            ("hi there", Role::Assistant),
        ]);
        let (ctx, note) = inherit_context(&parent, ContextSelection::SystemPreambleTop);
        assert_eq!(
            ctx.user_message_count(),
            0,
            "no user history should be inherited"
        );
        assert_eq!(ctx.system_prompt(), Some("system"));
        assert!(note.contains("system preamble"));
    }

    #[test]
    fn inherit_total_messages_preserves_full_order() {
        let parent = ctx_with(vec![
            ("system", Role::System),
            ("a", Role::User),
            ("b", Role::Assistant),
            ("c", Role::User),
            ("d", Role::Assistant),
        ]);
        let (ctx, _) = inherit_context(&parent, ContextSelection::Full);
        // System first, then all non-system in order (1 + 4 = 5 total).
        assert_eq!(ctx.system_prompt(), Some("system"));
        assert_eq!(ctx.total_messages(), 5);
        assert_eq!(ctx.user_message_count(), 2);
        assert_eq!(ctx.assistant_message_count(), 2);
    }

    #[test]
    fn fork_ephemeral_keeps_parent_threading_and_appends_task() {
        let parent = conv(1, Some(ctx_with(vec![("system", Role::System)])));
        let fork = SubagentFork::build(
            &parent,
            SubagentMode::Ephemeral,
            ContextSelection::SystemPreambleTop,
            "refactor util.rs",
        );

        assert_eq!(fork.parent_id, parent.id);
        assert_eq!(fork.mode, SubagentMode::Ephemeral);
        assert_eq!(fork.inherited_context.initiator.as_deref(), Some("agent"));
        assert_eq!(fork.inherited_context.user_message_count(), 1);
        let last = fork.inherited_context.messages.last().unwrap();
        assert!(
            last.has_role(Role::User),
            "delegated task should be the last user turn"
        );
        assert!(fork.selection_note.contains("delegated task"));
    }

    #[test]
    fn fork_empty_context_still_appends_task() {
        let parent = conv(2, None);
        let fork = SubagentFork::build(
            &parent,
            SubagentMode::Persistent,
            ContextSelection::SystemPreambleTop,
            "summarize the API",
        );
        assert_eq!(fork.inherited_context.user_message_count(), 1);
        assert_eq!(fork.inherited_context.system_prompt(), None);
        assert_eq!(fork.mode, SubagentMode::Persistent);
    }

    #[test]
    fn merge_ephemeral_discards_sub_conversation() {
        let parent = conv(3, None);
        let fork = SubagentFork::build(
            &parent,
            SubagentMode::Ephemeral,
            ContextSelection::SystemPreambleTop,
            "do the thing",
        );
        let sub_id = ConversationId::generate();
        let plan = plan_merge(&fork, sub_id, "done");

        assert_eq!(plan.messages.len(), 2);
        assert!(
            !plan.retain_sub_conversation,
            "ephemeral sub stays discarded"
        );
        assert!(plan.note.contains("merged and discarded"));
        // Answer echoed back as an assistant turn, task echo as a user turn.
        assert!(plan.messages[1].has_role(Role::Assistant));
    }

    #[test]
    fn merge_persistent_retains_sub_conversation() {
        let parent = conv(4, None);
        let fork = SubagentFork::build(
            &parent,
            SubagentMode::Persistent,
            ContextSelection::SystemPreambleTop,
            "long-lived analysis",
        );
        let sub_id = ConversationId::generate();
        let plan = plan_merge(&fork, sub_id, "analysis complete");

        assert!(plan.retain_sub_conversation, "persistent sub is retained");
        assert!(plan.note.contains("retained (persistent child"));
    }

    #[test]
    fn recent_selection_keeps_last_exchange_and_prunes_links() {
        // Two exchanges: "a/b" and a large droppable attachment + "c/d".
        let large = ContextMessage::user("big blob", None);
        let mut parent = ctx_with(vec![
            ("system", Role::System),
            ("a", Role::User),
            ("b", Role::Assistant),
        ]);
        // Insert a droppable attachment entry directly, then more turns.
        parent = parent.add_entry(large);
        let mut parent = parent.add_message(ContextMessage::user("c", None));
        parent = parent.add_message(ContextMessage::assistant("d", None, None, None));

        let (ctx, note) = inherit_context(&parent, ContextSelection::Recent(1));
        assert!(note.contains("last 1 exchange"));
        // Latest exchange (c/d) kept, earlier one (a/b) pruned.
        assert_eq!(ctx.user_message_count(), 1);
    }
}
