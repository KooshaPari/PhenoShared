//! Success-hook chain. Fires sequentially after capacity is acquired.
//! Every hook is "failsoft" — a failure in one stage MUST NOT stop the
//! remaining hooks from running. We log + continue.

use anyhow::Result;
use oci_helpers::which_on_path;
use serde_json::json;
use std::path::PathBuf;
use tokio::process::Command;
use tracing::{error, info, warn};

use crate::state::AcquiredInstance;

pub async fn fire_all(inst: &AcquiredInstance, infra_repo: Option<&PathBuf>) {
    if let Err(e) = run_post_acquire_hook(inst).await {
        warn!(error = %e, "post-acquire shell hook failed");
    }
    if let Err(e) = post_webhook(inst).await {
        warn!(error = %e, "webhook delivery failed");
    }
    if let Some(repo) = infra_repo
        && let Err(e) = update_compute_mesh_state(repo, inst).await
    {
        warn!(error = %e, "compute-mesh-state.md update failed");
    }
    if let Err(e) = imessage_relay(inst).await {
        warn!(error = %e, "imessage relay failed (non-fatal)");
    }
}

async fn run_post_acquire_hook(inst: &AcquiredInstance) -> Result<()> {
    // Resolution order (sibling crate `oci-post-acquire` is now the
    // first-class integration; the `.sh` wrapper is kept as a legacy
    // fallback for hosts that haven't installed the Rust binary yet):
    //   1. `oci-post-acquire` binary on PATH
    //   2. `~/.local/bin/oci-post-acquire`  (cargo install --root ~/.local)
    //   3. `~/.local/bin/oci-post-acquire.sh` (legacy minimal wrapper)
    //
    // The Rust binary reads `~/.cloudprovider/oci-instance.json` (which
    // `oci-lottery` writes immediately before firing hooks), so it needs
    // no extra args. We still pass the env vars for the legacy wrapper.
    let home = std::env::var("HOME").unwrap_or_default();
    let payload = serde_json::to_string(inst)?;
    let envs: Vec<(&str, String)> = vec![
        ("OCI_LOTTERY_RESULT_JSON", payload),
        ("OCI_INSTANCE_OCID", inst.instance_ocid.clone()),
        ("OCI_REGION", inst.region.clone()),
        ("OCI_PUBLIC_IP", inst.public_ip.clone().unwrap_or_default()),
    ];

    let path_bin = PathBuf::from(&home).join(".local/bin/oci-post-acquire");
    let path_sh = PathBuf::from(&home).join(".local/bin/oci-post-acquire.sh");

    let (program, args): (String, Vec<String>) = if which_on_path("oci-post-acquire").await {
        ("oci-post-acquire".to_string(), vec![])
    } else if tokio::fs::try_exists(&path_bin).await.unwrap_or(false) {
        (path_bin.to_string_lossy().into_owned(), vec![])
    } else if tokio::fs::try_exists(&path_sh).await.unwrap_or(false) {
        (
            "bash".to_string(),
            vec![path_sh.to_string_lossy().into_owned()],
        )
    } else {
        info!(
            ?path_bin,
            ?path_sh,
            "no post-acquire hook present (tried oci-post-acquire binary and .sh wrapper), skipping"
        );
        return Ok(());
    };

    info!(%program, ?args, "invoking post-acquire hook");
    let mut cmd = Command::new(&program);
    cmd.args(&args);
    for (k, v) in &envs {
        cmd.env(k, v);
    }
    let status = cmd.status().await?;
    if !status.success() {
        error!(?status, %program, "post-acquire hook exited non-zero");
    }
    Ok(())
}

async fn post_webhook(inst: &AcquiredInstance) -> Result<()> {
    let url = match std::env::var("OCI_LOTTERY_WEBHOOK_URL") {
        Ok(u) if !u.is_empty() => u,
        _ => {
            info!("OCI_LOTTERY_WEBHOOK_URL not set, skipping webhook");
            return Ok(());
        }
    };
    let body = json!({
        "text": format!(
            "OCI A1.Flex acquired in {} (AD-{}) — instance {} ip={}",
            inst.region,
            inst.ad,
            inst.instance_ocid,
            inst.public_ip.as_deref().unwrap_or("?")
        ),
        "instance": inst,
    })
    .to_string();
    // Shell out to curl to avoid pulling reqwest+TLS into a tiny daemon.
    let status = Command::new("curl")
        .args([
            "-fsS",
            "-X",
            "POST",
            "-H",
            "content-type: application/json",
            "-d",
            &body,
            &url,
        ])
        .status()
        .await?;
    if !status.success() {
        error!(?status, "webhook POST failed");
    }
    Ok(())
}

async fn update_compute_mesh_state(repo: &PathBuf, inst: &AcquiredInstance) -> Result<()> {
    let doc = repo.join("docs/governance/compute-mesh-state.md");
    let stamp = inst.acquired_at.to_rfc3339();
    let line = format!(
        "\n- [{}] OCI Always-Free A1.Flex acquired: region={} ad={} ocid={} ip={}\n",
        stamp,
        inst.region,
        inst.ad,
        inst.instance_ocid,
        inst.public_ip.as_deref().unwrap_or("pending")
    );

    if let Some(parent) = doc.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let prior = tokio::fs::read_to_string(&doc).await.unwrap_or_default();
    let merged = if prior.is_empty() {
        format!(
            "# Compute Mesh State\n\n## OCI (Always-Free A1.Flex)\n\nStatus: ACQUIRED\n{}",
            line
        )
    } else {
        format!("{}{}", prior.trim_end(), line)
    };
    tokio::fs::write(&doc, merged).await?;

    let _ = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(["add", "docs/governance/compute-mesh-state.md"])
        .status()
        .await?;
    let msg = format!(
        "chore(compute-mesh): mark OCI A1.Flex acquired ({})",
        inst.region
    );
    let _ = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(["commit", "-m", &msg])
        .status()
        .await?;
    Ok(())
}

async fn imessage_relay(inst: &AcquiredInstance) -> Result<()> {
    // Optional: only fires if agent-imessage MCP socket is reachable.
    // We do a "best effort" CLI invocation; absence is not an error.
    let bin = std::env::var("AGENT_IMESSAGE_CLI").unwrap_or_else(|_| "agent-imessage".to_string());
    if which::which(&bin).is_err() {
        info!(bin = %bin, "imessage CLI not on PATH, skipping");
        return Ok(());
    }
    let body = format!(
        "OCI A1.Flex acquired: {} (AD-{}) ip={}",
        inst.region,
        inst.ad,
        inst.public_ip.as_deref().unwrap_or("?")
    );
    let _ = Command::new(&bin)
        .args(["notify", "--message", &body])
        .status()
        .await;
    Ok(())
}

// Tiny embedded `which` to avoid an extra crate dep at compile time.
mod which {
    use std::path::PathBuf;
    pub fn which(name: &str) -> Result<PathBuf, ()> {
        let path = std::env::var_os("PATH").ok_or(())?;
        for dir in std::env::split_paths(&path) {
            let candidate = dir.join(name);
            if candidate.is_file() {
                return Ok(candidate);
            }
        }
        Err(())
    }
}
