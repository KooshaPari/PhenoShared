use std::path::PathBuf;

use oci_helpers::home_or_fallback;
use serde::{Deserialize, Serialize};

/// Runtime configuration for the OCI lottery daemon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Regions to attempt, in priority order.
    pub regions: Vec<String>,
    /// Availability domain index to try (1-based, OCI-style "AD-1"). Optional;
    /// if `None`, daemon will iterate ADs 1..=3 per region.
    pub availability_domains: Option<Vec<u8>>,
    /// Compatibility shape — defaults to VM.Standard.A1.Flex (Always-Free Ampere).
    pub shape: String,
    /// OCPUs to request (Always-Free max = 4 across all A1 instances).
    pub ocpus: u8,
    /// Memory GB (Always-Free max = 24 across all A1 instances).
    pub memory_gb: u8,
    /// Image OCID (Ubuntu 22.04 ARM by default in your tenancy — must be set).
    pub image_ocid: Option<String>,
    /// Subnet OCID for the new instance.
    pub subnet_ocid: Option<String>,
    /// Display name for the instance.
    pub display_name: String,
    /// SSH public key path.
    pub ssh_authorized_keys_path: PathBuf,
    /// OCI CLI profile name in `~/.oci/config`.
    pub profile: String,
    /// Compartment OCID.
    pub compartment_ocid: Option<String>,
    /// Min/max backoff seconds between attempts.
    pub backoff_min_secs: u64,
    pub backoff_max_secs: u64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            regions: vec![
                "ap-tokyo-1".into(),
                "ap-osaka-1".into(),
                "eu-frankfurt-1".into(),
                "us-ashburn-1".into(),
                "sa-saopaulo-1".into(),
            ],
            availability_domains: None,
            shape: "VM.Standard.A1.Flex".into(),
            ocpus: 4,
            memory_gb: 24,
            image_ocid: None,
            subnet_ocid: None,
            display_name: "phenotype-arm-mesh-node".into(),
            ssh_authorized_keys_path: home_or_fallback().join(".ssh").join("id_ed25519.pub"),
            profile: "DEFAULT".into(),
            compartment_ocid: None,
            backoff_min_secs: 60,
            backoff_max_secs: 180,
        }
    }
}

impl Config {
    pub async fn load_or_default(path: &PathBuf) -> anyhow::Result<Self> {
        if tokio::fs::try_exists(path).await.unwrap_or(false) {
            let raw = tokio::fs::read_to_string(path).await?;
            let cfg: Config = serde_json::from_str(&raw)?;
            Ok(cfg)
        } else {
            Ok(Self::default())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support;

    #[test]
    fn test_default_stays_within_always_free_limits() {
        let cfg = Config::default();
        // Always-Free A1.Flex ceiling is 4 OCPU / 24 GB across all instances.
        assert!(cfg.ocpus <= 4, "default ocpus {} exceeds free tier", cfg.ocpus);
        assert!(
            cfg.memory_gb <= 24,
            "default memory {} exceeds free tier",
            cfg.memory_gb
        );
        assert_eq!(cfg.availability_domains, None);
        assert_eq!(cfg.image_ocid, None);
        assert_eq!(cfg.subnet_ocid, None);
        assert_eq!(cfg.profile, "DEFAULT");
    }

    #[test]
    fn test_default_region_order_is_deterministic() {
        let cfg = Config::default();
        assert_eq!(cfg.regions.first().map(String::as_str), Some("ap-tokyo-1"));
        assert_eq!(
            cfg.regions.last().map(String::as_str),
            Some("sa-saopaulo-1")
        );
        assert_eq!(cfg.regions.len(), 5);
    }

    #[test]
    fn test_default_backoff_is_ordered_and_sane() {
        let cfg = Config::default();
        assert!(cfg.backoff_min_secs > 0);
        assert!(cfg.backoff_min_secs < cfg.backoff_max_secs);
    }

    #[test]
    fn test_default_ssh_key_path_points_at_a_public_key() {
        let cfg = Config::default();
        assert!(
            cfg.ssh_authorized_keys_path.ends_with(".ssh/id_ed25519.pub"),
            "unexpected default key path: {}",
            cfg.ssh_authorized_keys_path.display()
        );
    }

    #[tokio::test]
    async fn test_load_or_default_missing_file_yields_default() {
        let dir = test_support::temp_dir("cfg-missing");
        let path = dir.join("does-not-exist.json");

        let cfg = Config::load_or_default(&path).await.unwrap();
        assert_eq!(cfg.shape, Config::default().shape);
        assert_eq!(cfg.regions, Config::default().regions);

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_load_or_default_reads_overrides_from_disk() {
        let dir = test_support::temp_dir("cfg-present");
        let path = dir.join("config.json");
        let raw = serde_json::json!({
            "regions": ["eu-amsterdam-1"],
            "availability_domains": [2],
            "shape": "VM.Standard.A1.Flex",
            "ocpus": 2,
            "memory_gb": 12,
            "image_ocid": "ocid1.image.test",
            "subnet_ocid": "ocid1.subnet.test",
            "display_name": "custom-node",
            "ssh_authorized_keys_path": "/tmp/custom.pub",
            "profile": "TESTPROFILE",
            "compartment_ocid": "ocid1.compartment.test",
            "backoff_min_secs": 5,
            "backoff_max_secs": 9
        });
        std::fs::write(&path, raw.to_string()).unwrap();

        let cfg = Config::load_or_default(&path).await.unwrap();
        assert_eq!(cfg.regions, vec!["eu-amsterdam-1".to_string()]);
        assert_eq!(cfg.availability_domains, Some(vec![2]));
        assert_eq!(cfg.ocpus, 2);
        assert_eq!(cfg.memory_gb, 12);
        assert_eq!(cfg.display_name, "custom-node");
        assert_eq!(cfg.profile, "TESTPROFILE");
        assert_eq!(cfg.compartment_ocid.as_deref(), Some("ocid1.compartment.test"));
        assert_eq!(cfg.backoff_min_secs, 5);
        assert_eq!(cfg.backoff_max_secs, 9);

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_load_or_default_rejects_malformed_json() {
        let dir = test_support::temp_dir("cfg-malformed");
        let path = dir.join("config.json");
        std::fs::write(&path, "{ this is not json").unwrap();

        let err = Config::load_or_default(&path).await.unwrap_err();
        assert!(
            err.to_string().contains("line 1"),
            "expected a serde position error, got: {err}"
        );

        test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_load_or_default_rejects_partial_config() {
        // `regions` is required, so a config that omits it must fail loudly
        // rather than silently falling back to defaults.
        let dir = test_support::temp_dir("cfg-partial");
        let path = dir.join("config.json");
        std::fs::write(&path, r#"{"ocpus": 4}"#).unwrap();

        assert!(Config::load_or_default(&path).await.is_err());

        test_support::remove(&dir);
    }

    #[test]
    fn test_config_serde_roundtrip_preserves_fields() {
        let cfg = Config::default();
        let json = serde_json::to_string(&cfg).unwrap();
        let back: Config = serde_json::from_str(&json).unwrap();
        assert_eq!(back.regions, cfg.regions);
        assert_eq!(back.ocpus, cfg.ocpus);
        assert_eq!(back.backoff_max_secs, cfg.backoff_max_secs);
        assert_eq!(back.ssh_authorized_keys_path, cfg.ssh_authorized_keys_path);
    }
}
