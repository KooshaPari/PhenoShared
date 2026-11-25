//! Downstream hook drop-ins — runs every executable in `oci-acquire-hooks.d/`
//! lexicographically, passing the instance file path as $1 and exporting key
//! fields as env vars. A failing hook does not abort the chain; we collect
//! errors and warn at the end.

use crate::InstanceFile;
use oci_helpers::expand_home;
use anyhow::{Result, anyhow};
use tokio::process::Command;
use tracing::{info, warn};

pub async fn run_dropins(dir: &str, inst: &InstanceFile) -> Result<()> {
    let p = expand_home(dir);
    if !p.exists() {
        info!(dir = %p.display(), "no hooks.d dir; skipping");
        return Ok(());
    }
    let mut entries: Vec<_> = std::fs::read_dir(&p)?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_file())
        .collect();
    entries.sort();

    let mut errors = Vec::new();
    for hook in entries {
        let name = hook
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("?")
            .to_string();
        info!(hook = %name, "running drop-in hook");
        let status = Command::new(&hook)
            .env("OCI_INSTANCE_OCID", &inst.instance_ocid)
            .env("OCI_REGION", &inst.region)
            .env("OCI_AD", &inst.ad)
            .env("OCI_PUBLIC_IP", &inst.public_ip)
            .env("OCI_ACQUIRED_AT", &inst.acquired_at)
            .status()
            .await;
        match status {
            Ok(s) if s.success() => info!(hook = %name, "ok"),
            Ok(s) => {
                warn!(hook = %name, ?s, "hook failed");
                errors.push(format!("{name}: {s}"));
            }
            Err(e) => {
                warn!(hook = %name, error = ?e, "spawn failed");
                errors.push(format!("{name}: {e}"));
            }
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(anyhow!("{} hook(s) failed: {:?}", errors.len(), errors))
    }
}
