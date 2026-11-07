use serde::{Deserialize, Serialize};

/// Workflow state only. None of these values grants a harness permission.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Open,
    Running,
    Waiting,
    Deferred,
    Partial,
    Blocked,
    Closed,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Item {
    pub id: String,
    pub source_request_id: Option<String>,
    /// Complete original item, immutable after creation.
    pub original: String,
    pub title: String,
    pub status: Status,
    pub lane: Option<String>,
    pub eta: Option<String>,
    pub assignee: Option<String>,
    pub acknowledged: bool,
    pub revision: u64,
}
impl Item {
    pub fn new(id: impl Into<String>, original: impl Into<String>) -> Self {
        let original = original.into();
        let title = original.lines().next().unwrap_or("Item").to_string();
        Self {
            id: id.into(),
            source_request_id: None,
            original,
            title,
            status: Status::Open,
            lane: None,
            eta: None,
            assignee: None,
            acknowledged: false,
            revision: 0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum Action {
    Ack,
    Assign(String),
    Defer,
    Close,
    SetStatus(Status),
    SetLane(Option<String>),
    SetEta(Option<String>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Command {
    /// Stable interaction/event identifier; duplicates return the original result.
    pub event_id: String,
    pub item_id: String,
    pub expected_revision: u64,
    /// Authenticated principal supplied by the trusted ingress, never a display name.
    pub actor: String,
    pub action: Action,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ThreadMap {
    pub guild_id: String,
    pub forum_id: String,
    pub thread_id: String,
    pub message_id: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EffectKind {
    Upsert,
    Close,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Effect {
    pub id: String,
    pub item_id: String,
    pub revision: u64,
    pub kind: EffectKind,
    pub item: Item,
    pub thread: Option<ThreadMap>,
    pub attempts: u32,
    pub last_error: Option<String>,
}
