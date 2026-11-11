//! Normalized session model — the common shape every ingestion adapter targets.

use serde::{Deserialize, Serialize};

/// Origin corpus a session was ingested from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Corpus {
    Forge,
    Codex,
    ClaudeCode,
    Cursor,
    FactoryDroid,
    ChatGptWeb,
    ClaudeWeb,
    GeminiWeb,
}

/// Who authored a message. Distinguishing user vs subagent is load-bearing for
/// intent extraction (the curation pipeline classifies these explicitly).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Role {
    User,
    Assistant,
    Subagent,
    Tool,
    System,
}

/// A single turn in a session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: String,
    /// Unix millis; `None` when the source omits a timestamp.
    pub ts_ms: Option<i64>,
}

impl Message {
    #[must_use]
    pub fn new(role: Role, content: impl Into<String>) -> Self {
        Self { role, content: content.into(), ts_ms: None }
    }
}

/// A normalized session: the unit `SessionLedger` compiles, distills, and resumes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    pub corpus: Corpus,
    /// Working directory / project scope, when known. Drives the dedup key.
    pub cwd: Option<String>,
    pub title: Option<String>,
    pub messages: Vec<Message>,
}

impl Corpus {
    /// Return the kebab-case corpus name as a string slice.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Forge => "forge",
            Self::Codex => "codex",
            Self::ClaudeCode => "claude-code",
            Self::Cursor => "cursor",
            Self::FactoryDroid => "factory-droid",
            Self::ChatGptWeb => "chatgpt-web",
            Self::ClaudeWeb => "claude-web",
            Self::GeminiWeb => "gemini-web",
        }
    }
}

impl Session {
    #[must_use]
    pub fn new(id: impl Into<String>, corpus: Corpus) -> Self {
        Self { id: id.into(), corpus, cwd: None, title: None, messages: Vec::new() }
    }

    /// Count of turns authored by a human operator (not agent/subagent/tool).
    #[must_use]
    pub fn user_turns(&self) -> usize {
        self.messages.iter().filter(|m| m.role == Role::User).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Corpus::as_str ───────────────────────────────────────────────────────

    #[test]
    fn corpus_as_str_forge() {
        assert_eq!(Corpus::Forge.as_str(), "forge");
    }

    #[test]
    fn corpus_as_str_codex() {
        assert_eq!(Corpus::Codex.as_str(), "codex");
    }

    #[test]
    fn corpus_as_str_claude_code() {
        assert_eq!(Corpus::ClaudeCode.as_str(), "claude-code");
    }

    #[test]
    fn corpus_as_str_cursor() {
        assert_eq!(Corpus::Cursor.as_str(), "cursor");
    }

    #[test]
    fn corpus_as_str_factory_droid() {
        assert_eq!(Corpus::FactoryDroid.as_str(), "factory-droid");
    }

    // ── Session::user_turns ──────────────────────────────────────────────────

    #[test]
    fn user_turns_empty_session_is_zero() {
        let s = Session::new("id1", Corpus::Forge);
        assert_eq!(s.user_turns(), 0);
    }

    #[test]
    fn user_turns_counts_only_user_role() {
        let mut s = Session::new("id1", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "hello"));
        s.messages.push(Message::new(Role::Assistant, "reply"));
        s.messages.push(Message::new(Role::User, "follow up"));
        s.messages.push(Message::new(Role::Tool, "tool result"));
        s.messages.push(Message::new(Role::Subagent, "sub"));
        s.messages.push(Message::new(Role::System, "sys"));
        assert_eq!(s.user_turns(), 2);
    }

    #[test]
    fn user_turns_all_non_user_is_zero() {
        let mut s = Session::new("id1", Corpus::Codex);
        s.messages.push(Message::new(Role::Assistant, "a"));
        s.messages.push(Message::new(Role::Tool, "t"));
        s.messages.push(Message::new(Role::System, "s"));
        assert_eq!(s.user_turns(), 0);
    }

    #[test]
    fn user_turns_single_user_message() {
        let mut s = Session::new("id1", Corpus::Cursor);
        s.messages.push(Message::new(Role::User, "only one"));
        assert_eq!(s.user_turns(), 1);
    }

    #[test]
    fn user_turns_only_user_messages() {
        let mut s = Session::new("id1", Corpus::ClaudeCode);
        for i in 0..5 {
            s.messages.push(Message::new(Role::User, format!("msg {i}")));
        }
        assert_eq!(s.user_turns(), 5);
    }

    // ── Session::new defaults ────────────────────────────────────────────────

    #[test]
    fn session_new_has_empty_messages() {
        let s = Session::new("abc", Corpus::Forge);
        assert!(s.messages.is_empty());
    }

    #[test]
    fn session_new_cwd_and_title_are_none() {
        let s = Session::new("abc", Corpus::Codex);
        assert!(s.cwd.is_none());
        assert!(s.title.is_none());
    }

    // ── Message::new ─────────────────────────────────────────────────────────

    #[test]
    fn message_new_ts_ms_is_none() {
        let m = Message::new(Role::User, "content");
        assert!(m.ts_ms.is_none());
    }

    #[test]
    fn message_new_captures_content() {
        let m = Message::new(Role::Assistant, "hello world");
        assert_eq!(m.content, "hello world");
        assert_eq!(m.role, Role::Assistant);
    }

    // ── Role equality ─────────────────────────────────────────────────────────

    #[test]
    fn role_variants_are_distinct() {
        let roles = [Role::User, Role::Assistant, Role::Subagent, Role::Tool, Role::System];
        for (i, a) in roles.iter().enumerate() {
            for (j, b) in roles.iter().enumerate() {
                if i == j {
                    assert_eq!(a, b);
                } else {
                    assert_ne!(a, b);
                }
            }
        }
    }
}
