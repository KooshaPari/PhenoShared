use std::path::PathBuf;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support;

    fn sample_instance() -> AcquiredInstance {
        AcquiredInstance {
            instance_ocid: "ocid1.instance.test".into(),
            region: "eu-frankfurt-1".into(),
            ad: 2,
            public_ip: Some("203.0.113.7".into()),
            acquired_at: Utc::now(),
        }
    }

    #[tokio::test]
    async fn test_load_missing_file_yields_default_state() {
        let dir = test_support::temp_dir("state-missing");
        let path = dir.join("state.json");

        let state = LotteryState::load(&path).await.unwrap();
        assert_eq!(state.attempts, 0);
        assert!(!state.acquired);
        assert!(state.started_at.is_none());
        assert!(state.last_attempt.is_none());

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_save_then_load_roundtrips_all_fields() {
        let dir = test_support::temp_dir("state-roundtrip");
        let path = dir.join("state.json");

        let state = LotteryState {
            attempts: 42,
            last_attempt: Some(Utc::now()),
            last_region: Some("ap-tokyo-1".into()),
            last_ad: Some(1),
            last_error: Some("Out of host capacity".into()),
            started_at: Some(Utc::now()),
            acquired: true,
        };
        state.save(&path).await.unwrap();

        let back = LotteryState::load(&path).await.unwrap();
        assert_eq!(back.attempts, 42);
        assert_eq!(back.last_region.as_deref(), Some("ap-tokyo-1"));
        assert_eq!(back.last_ad, Some(1));
        assert_eq!(back.last_error.as_deref(), Some("Out of host capacity"));
        assert!(back.acquired);

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_save_creates_missing_parent_directories() {
        let dir = test_support::temp_dir("state-nested");
        let path = dir.join("nested").join("deeper").join("state.json");

        LotteryState::default().save(&path).await.unwrap();
        assert!(path.is_file());

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_save_writes_pretty_json() {
        let dir = test_support::temp_dir("state-pretty");
        let path = dir.join("state.json");

        LotteryState {
            attempts: 3,
            ..LotteryState::default()
        }
        .save(&path)
        .await
        .unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        assert!(raw.contains('\n'), "expected pretty-printed JSON: {raw}");
        assert!(raw.contains("\"attempts\": 3"), "unexpected JSON: {raw}");

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_load_corrupt_state_falls_back_to_default() {
        // A half-written state file must never wedge the daemon: it resumes
        // from zero rather than refusing to start.
        let dir = test_support::temp_dir("state-corrupt");
        let path = dir.join("state.json");
        std::fs::write(&path, "{\"attempts\": ").unwrap();

        let state = LotteryState::load(&path).await.unwrap();
        assert_eq!(state.attempts, 0);

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_write_acquired_persists_instance_json() {
        let dir = test_support::temp_dir("state-acquired");
        let path = dir.join("cloudprovider").join("oci-instance.json");
        let inst = sample_instance();

        write_acquired(&path, &inst).await.unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        let back: AcquiredInstance = serde_json::from_str(&raw).unwrap();
        assert_eq!(back.instance_ocid, inst.instance_ocid);
        assert_eq!(back.region, inst.region);
        assert_eq!(back.ad, 2);
        assert_eq!(back.public_ip.as_deref(), Some("203.0.113.7"));

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_write_acquired_overwrites_previous_result() {
        let dir = test_support::temp_dir("state-overwrite");
        let path = dir.join("oci-instance.json");

        write_acquired(&path, &sample_instance()).await.unwrap();
        let mut second = sample_instance();
        second.instance_ocid = "ocid1.instance.second".into();
        second.public_ip = None;
        write_acquired(&path, &second).await.unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        let back: AcquiredInstance = serde_json::from_str(&raw).unwrap();
        assert_eq!(back.instance_ocid, "ocid1.instance.second");
        assert!(back.public_ip.is_none());
        assert!(!raw.contains("ocid1.instance.test"));

        test_support::remove(&dir);
    }
}
