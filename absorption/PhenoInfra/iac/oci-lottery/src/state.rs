use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LotteryState {
    pub attempts: u64,
    pub last_attempt: Option<DateTime<Utc>>,
    pub last_region: Option<String>,
    pub last_ad: Option<u8>,
    pub last_error: Option<String>,
    pub started_at: Option<DateTime<Utc>>,
    pub acquired: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcquiredInstance {
    pub instance_ocid: String,
    pub region: String,
    pub ad: u8,
    pub public_ip: Option<String>,
    pub acquired_at: DateTime<Utc>,
}

impl LotteryState {
    pub async fn load(path: &PathBuf) -> anyhow::Result<Self> {
        if tokio::fs::try_exists(path).await.unwrap_or(false) {
            let raw = tokio::fs::read_to_string(path).await?;
            Ok(serde_json::from_str(&raw).unwrap_or_default())
        } else {
            Ok(Self::default())
        }
    }

    pub async fn save(&self, path: &PathBuf) -> anyhow::Result<()> {
        if let Some(parent) = path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        let raw = serde_json::to_string_pretty(self)?;
        tokio::fs::write(path, raw).await?;
        Ok(())
    }
}

pub async fn write_acquired(path: &PathBuf, inst: &AcquiredInstance) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let raw = serde_json::to_string_pretty(inst)?;
    tokio::fs::write(path, raw).await?;
    Ok(())
}
