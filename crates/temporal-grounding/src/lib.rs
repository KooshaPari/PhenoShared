use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AgentEntry {
    pub id: String,
    pub started_at: String,
    pub label: Option<String>,
}

#[must_use]
pub fn claude_dir() -> PathBuf {
    std::env::var("HOME")
        .map_or_else(|_| PathBuf::from("."), PathBuf::from)
        .join(".claude")
}

#[must_use]
pub fn active_agents_path() -> PathBuf {
    claude_dir().join("active-agents.json")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn claude_dir_ends_with_dot_claude() {
        let p = claude_dir();
        assert_eq!(p.file_name().unwrap().to_str().unwrap(), ".claude");
    }

    #[test]
    fn active_agents_path_filename() {
        let p = active_agents_path();
        assert_eq!(
            p.file_name().unwrap().to_str().unwrap(),
            "active-agents.json"
        );
    }

    #[test]
    fn agent_entry_roundtrip() {
        let e = AgentEntry {
            id: "test-42".to_string(),
            started_at: "2024-01-01T00:00:00Z".to_string(),
            label: Some("sweep".to_string()),
        };
        let json = serde_json::to_string(&e).unwrap();
        let back: AgentEntry = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, e.id);
        assert_eq!(back.label, e.label);
    }
}
