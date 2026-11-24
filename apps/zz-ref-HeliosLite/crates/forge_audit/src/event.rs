//! Audit event types.

use serde::Serialize;

/// Phase of a tool-call lifecycle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolCallPhase {
    /// Tool about to be dispatched.
    Start,
    /// Tool call made a policy decision (allow/deny/confirm).
    Decision,
    /// Tool completed successfully.
    End,
    /// Tool failed.
    Error,
}

/// Decision result for policy evaluation of a tool call.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolCallDecision {
    Allowed,
    Denied,
    RequiresConfirm,
    Confirmed,
    Rejected,
}

/// A single tool-call audit record.
#[derive(Debug, Clone, Serialize)]
pub struct ToolCallEvent {
    /// Epoch millis timestamp.
    pub ts_ms: i64,
    /// Conversation identifier (if any).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub conversation_id: Option<String>,
    /// Agent / subagent identifier.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    /// Tool name (e.g. `write`, `patch`, `task`).
    pub tool: String,
    /// Lifecycle phase.
    pub phase: ToolCallPhase,
    /// Policy decision for this call.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub decision: Option<ToolCallDecision>,
    /// Cached risk score 0..1 (populated by the guardian layer).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub risk: Option<f64>,
    /// Duration of the call in millis.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration_ms: Option<i64>,
    /// Truncated output/error summary (kept small for NDJSON).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary: Option<String>,
}

/// Top-level audit event wrapper (enables a single NDJSON stream with
/// multiple event kinds).
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AuditEvent {
    ToolCall(ToolCallEvent),
    /// A sub-agent was spawned (fresh session / resumed / forked).
    SubagentSpawn {
        ts_ms: i64,
        #[serde(skip_serializing_if = "Option::is_none")]
        parent_id: Option<String>,
        #[serde(skip_serializing_if = "Option::is_none")]
        child_id: Option<String>,
        agent: String,
        mode: String,
    },
    /// A human granted or denied a permission.
    PermissionGrant {
        ts_ms: i64,
        tool: String,
        granted: bool,
    },
}
