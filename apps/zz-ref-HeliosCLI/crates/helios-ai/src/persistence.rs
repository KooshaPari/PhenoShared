//! Session persistence — save/load chat sessions to disk.

use super::session::ChatSession;
use super::types::*;
use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tracing::{debug, info};
use uuid::Uuid;

/// Serialized representation of a chat session for persistence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionRecord {
    pub id: Uuid,
    pub created_at: DateTime<Utc>,
    pub saved_at: DateTime<Utc>,
    pub config: ProviderConfig,
    pub system_prompt: Option<String>,
    pub messages: Vec<Message>,
}

/// Get the helios sessions directory (`~/.helios/sessions/`).
pub fn sessions_dir() -> Result<PathBuf> {
    let home = dirs().context("Cannot determine home directory")?;
    let sessions = home.join(".helios").join("sessions");
    std::fs::create_dir_all(&sessions).context("Failed to create sessions directory")?;
    Ok(sessions)
}

/// Resolve the user's home directory.
fn dirs() -> Result<PathBuf> {
    if let Ok(home) = std::env::var("HOME") {
        return Ok(PathBuf::from(home));
    }
    if let Ok(profile) = std::env::var("USERPROFILE") {
        return Ok(PathBuf::from(profile));
    }
    anyhow::bail!("Cannot determine home directory (HOME/USERPROFILE not set)")
}

/// Get the file path for a session record.
pub fn session_path(id: &Uuid) -> Result<PathBuf> {
    Ok(sessions_dir()?.join(format!("{}.json", id)))
}

/// Save a chat session to disk.
pub fn save_session(record: &SessionRecord) -> Result<PathBuf> {
    let path = session_path(&record.id)?;
    let json = serde_json::to_string_pretty(record).context("Failed to serialize session")?;
    std::fs::write(&path, &json)
        .with_context(|| format!("Failed to write session to {}", path.display()))?;
    info!(id = %record.id, path = %path.display(), "Session saved");
    Ok(path)
}

/// Load a session from a specific file path.
pub fn load_session(path: &Path) -> Result<SessionRecord> {
    let json = std::fs::read_to_string(path)
        .with_context(|| format!("Failed to read session from {}", path.display()))?;
    let record: SessionRecord = serde_json::from_str(&json)
        .with_context(|| format!("Failed to parse session from {}", path.display()))?;
    debug!(id = %record.id, "Session loaded");
    Ok(record)
}

/// Load the most recently saved session.
pub fn load_last_session() -> Result<Option<SessionRecord>> {
    let dir = sessions_dir()?;
    let mut entries: Vec<PathBuf> = std::fs::read_dir(&dir)
        .with_context(|| format!("Failed to read sessions dir {}", dir.display()))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|ext| ext == "json"))
        .collect();

    if entries.is_empty() {
        return Ok(None);
    }

    entries.sort_by(|a, b| {
        let ta = std::fs::metadata(a).and_then(|m| m.modified()).ok();
        let tb = std::fs::metadata(b).and_then(|m| m.modified()).ok();
        tb.cmp(&ta)
    });

    let newest = &entries[0];
    debug!(path = %newest.display(), "Found most recent session");
    Ok(Some(load_session(newest)?))
}

/// Reconstruct a [`ChatSession`] from a loaded [`SessionRecord`].
pub fn session_from_record(record: &SessionRecord) -> Result<ChatSession> {
    let mut session = ChatSession::new(record.config.clone(), None)?;
    session.messages = record.messages.clone();
    Ok(session)
}
