use oci_helpers::home_or_fallback;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

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
