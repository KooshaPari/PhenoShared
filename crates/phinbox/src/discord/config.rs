use crate::management::{Status, ThreadMap};
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::{Path, PathBuf},
};

/// Concrete binding to the existing application, never a new persona account.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Binding {
    pub persona_reference: String,
    pub application_id: String,
    pub guild_id: String,
    pub forum_id: String,
    pub allowed_users: BTreeSet<String>,
    pub allowed_roles: BTreeSet<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub binding: Binding,
    pub credential_file: PathBuf,
    /// Existing /root/discord-wake/asks-board-map.json; metadata only.
    pub board_map_file: PathBuf,
    /// Required explicit election before subscribing to the existing bot Gateway.
    pub receiver_owner: String,
    pub tags: BTreeMap<String, String>,
}
#[derive(Deserialize)]
struct Board {
    forum_id: String,
    tag_ids: BTreeMap<String, String>,
}
impl Config {
    pub fn load(path: &Path) -> Result<Self> {
        let config: Self =
            serde_json::from_slice(&std::fs::read(path).context("read Discord configuration")?)
                .context("parse Discord configuration")?;
        config.validate()?;
        Ok(config)
    }
    pub fn validate(&self) -> Result<()> {
        let b = &self.binding;
        if b.application_id != "1558640911297028147"
            || b.guild_id != "1558641659778961432"
            || b.forum_id != "1560878303286534164"
        {
            bail!("Discord binding differs from authorized Instinct destination");
        }
        if b.persona_reference.trim().is_empty() {
            bail!("existing persona provenance reference required");
        }
        if b.allowed_users.is_empty() && b.allowed_roles.is_empty() {
            bail!("Discord actor allowlist is empty");
        }
        for id in b.allowed_users.iter().chain(&b.allowed_roles) {
            validate_id(id)?;
        }
        for status in [
            "open", "running", "waiting", "deferred", "partial", "blocked",
        ] {
            validate_id(
                self.tags
                    .get(status)
                    .context("required Discord status tag missing")?,
            )?;
        }
        Ok(())
    }
    pub fn validate_board(&self) -> Result<()> {
        let board: Board = serde_json::from_slice(
            &std::fs::read(&self.board_map_file)
                .context("existing asks-board bindings unavailable")?,
        )
        .context("invalid asks-board bindings")?;
        if board.forum_id != self.binding.forum_id {
            bail!("existing forum binding mismatch");
        }
        for (status, id) in &self.tags {
            if board.tag_ids.get(status) != Some(id) {
                bail!("existing status binding mismatch");
            }
        }
        Ok(())
    }
    pub fn tag(&self, status: Status) -> Result<&str> {
        let name = match status {
            Status::Open => "open",
            Status::Running => "running",
            Status::Waiting => "waiting",
            Status::Deferred => "deferred",
            Status::Partial => "partial",
            Status::Blocked => "blocked",
            Status::Closed => {
                bail!("closed workflow has no status tag; archive existing owned thread")
            },
        };
        self.tags
            .get(name)
            .map(String::as_str)
            .context("status tag missing")
    }
    pub fn check_map(&self, map: &ThreadMap) -> Result<()> {
        if map.guild_id != self.binding.guild_id || map.forum_id != self.binding.forum_id {
            bail!("remote thread mapping outside binding");
        }
        validate_id(&map.thread_id)?;
        validate_id(&map.message_id)
    }
}
pub(super) fn validate_id(id: &str) -> Result<()> {
    if id.is_empty() || id.len() > 20 || !id.bytes().all(|c| c.is_ascii_digit()) {
        bail!("invalid Discord snowflake");
    }
    Ok(())
}
