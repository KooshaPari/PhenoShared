//! Success-hook chain. Fires sequentially after capacity is acquired.
//! Every hook is "failsoft" — a failure in one stage MUST NOT stop the
//! remaining hooks from running. We log + continue.

use std::path::PathBuf;

use anyhow::Result;
use oci_helpers::which_on_path;
use serde_json::json;
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
            "no post-acquire hook present (tried oci-post-acquire binary and .sh wrapper), \
             skipping"
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
        },
    };
    let body = webhook_body(inst);
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
    let line = mesh_state_line(inst);

    if let Some(parent) = doc.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let prior = tokio::fs::read_to_string(&doc).await.unwrap_or_default();
    let merged = merge_mesh_state(&prior, &line);
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
    let body = imessage_body(inst);
    let _ = Command::new(&bin)
        .args(["notify", "--message", &body])
        .status()
        .await;
    Ok(())
}

/// JSON body POSTed to `OCI_LOTTERY_WEBHOOK_URL` on success.
fn webhook_body(inst: &AcquiredInstance) -> String {
    json!({
        "text": format!(
            "OCI A1.Flex acquired in {} (AD-{}) — instance {} ip={}",
            inst.region,
            inst.ad,
            inst.instance_ocid,
            inst.public_ip.as_deref().unwrap_or("?")
        ),
        "instance": inst,
    })
    .to_string()
}

/// Single markdown bullet appended to `compute-mesh-state.md`.
fn mesh_state_line(inst: &AcquiredInstance) -> String {
    let stamp = inst.acquired_at.to_rfc3339();
    format!(
        "\n- [{}] OCI Always-Free A1.Flex acquired: region={} ad={} ocid={} ip={}\n",
        stamp,
        inst.region,
        inst.ad,
        inst.instance_ocid,
        inst.public_ip.as_deref().unwrap_or("pending")
    )
}

/// Merge a new status bullet into the existing mesh-state document. A missing
/// (empty) document gets a fresh header; an existing one keeps its history and
/// has the bullet appended after its trailing whitespace is trimmed.
fn merge_mesh_state(prior: &str, line: &str) -> String {
    if prior.is_empty() {
        format!("# Compute Mesh State\n\n## OCI (Always-Free A1.Flex)\n\nStatus: ACQUIRED\n{line}")
    } else {
        format!("{}{}", prior.trim_end(), line)
    }
}

/// Notification text for the optional iMessage relay.
fn imessage_body(inst: &AcquiredInstance) -> String {
    format!(
        "OCI A1.Flex acquired: {} (AD-{}) ip={}",
        inst.region,
        inst.ad,
        inst.public_ip.as_deref().unwrap_or("?")
    )
}

// Tiny embedded `which` to avoid an extra crate dep at compile time.
mod which {
    use std::ffi::OsStr;
    use std::path::PathBuf;

    pub fn which(name: &str) -> Result<PathBuf, ()> {
        let path = std::env::var_os("PATH").ok_or(())?;
        which_in(name, &path)
    }

    /// PATH lookup against an explicit search path, so the resolution rule can
    /// be exercised without mutating the process environment.
    pub fn which_in(name: &str, path: &OsStr) -> Result<PathBuf, ()> {
        for dir in std::env::split_paths(path) {
            let candidate = dir.join(name);
            if candidate.is_file() {
                return Ok(candidate);
            }
        }
        Err(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support;
    use chrono::Utc;
    use serde_json::Value;

    fn instance_with_ip(ip: Option<&str>) -> AcquiredInstance {
        AcquiredInstance {
            instance_ocid: "ocid1.instance.oc1..test".into(),
            region: "us-ashburn-1".into(),
            ad: 3,
            public_ip: ip.map(String::from),
            acquired_at: Utc::now(),
        }
    }

    #[test]
    fn test_webhook_body_is_json_with_text_and_instance() {
        let inst = instance_with_ip(Some("203.0.113.5"));
        let body = webhook_body(&inst);
        let v: Value = serde_json::from_str(&body).expect("webhook body must be JSON");

        let text = v["text"].as_str().expect("text field");
        assert!(text.contains("us-ashburn-1"), "region missing: {text}");
        assert!(text.contains("AD-3"), "AD missing: {text}");
        assert!(
            text.contains("ocid1.instance.oc1..test"),
            "ocid missing: {text}"
        );
        assert!(text.contains("ip=203.0.113.5"), "ip missing: {text}");
        assert_eq!(v["instance"]["region"], "us-ashburn-1");
        assert_eq!(v["instance"]["ad"], 3);
    }

    #[test]
    fn test_webhook_body_marks_unknown_ip_with_a_placeholder() {
        let body = webhook_body(&instance_with_ip(None));
        let v: Value = serde_json::from_str(&body).unwrap();
        let text = v["text"].as_str().unwrap();
        assert!(text.contains("ip=?"), "placeholder missing: {text}");
        assert!(v["instance"]["public_ip"].is_null());
    }

    #[test]
    fn test_mesh_state_line_carries_every_field() {
        let inst = instance_with_ip(Some("203.0.113.6"));
        let line = mesh_state_line(&inst);
        let stamp = inst.acquired_at.to_rfc3339();

        assert!(line.starts_with("\n- ["), "unexpected shape: {line:?}");
        assert!(line.ends_with('\n'), "line must end with a newline: {line:?}");
        assert!(line.contains(&stamp), "timestamp missing: {line}");
        assert!(line.contains("region=us-ashburn-1"), "{line}");
        assert!(line.contains("ad=3"), "{line}");
        assert!(line.contains("ocid=ocid1.instance.oc1..test"), "{line}");
        assert!(line.contains("ip=203.0.113.6"), "{line}");
    }

    #[test]
    fn test_mesh_state_line_says_pending_without_an_ip() {
        let line = mesh_state_line(&instance_with_ip(None));
        assert!(line.contains("ip=pending"), "{line}");
    }

    #[test]
    fn test_merge_mesh_state_bootstraps_an_empty_document() {
        let merged = merge_mesh_state("", "\n- [now] bullet\n");
        assert!(merged.starts_with("# Compute Mesh State\n"));
        assert!(merged.contains("## OCI (Always-Free A1.Flex)"));
        assert!(merged.contains("Status: ACQUIRED"));
        assert!(merged.ends_with("\n- [now] bullet\n"));
    }

    #[test]
    fn test_merge_mesh_state_collapses_trailing_blank_lines() {
        // The bullet already carries its own leading newline, so trailing
        // whitespace on the prior document must be trimmed to avoid a gap.
        let prior = "# Compute Mesh State\n\nStatus: PENDING\n\n\n";
        let merged = merge_mesh_state(prior, "\n- [t1] first\n");
        assert_eq!(merged, "# Compute Mesh State\n\nStatus: PENDING\n- [t1] first\n");
        assert!(!merged.contains("\n\n\n"), "blank-line run left behind: {merged:?}");
    }

    #[test]
    fn test_merge_mesh_state_preserves_prior_history() {
        let prior = "# Compute Mesh State\n\n- [t0] earlier acquisition\n";
        let merged = merge_mesh_state(prior, "\n- [t1] later acquisition\n");
        let earlier = merged.find("earlier acquisition").expect("history kept");
        let later = merged.find("later acquisition").expect("new bullet added");
        assert!(earlier < later, "history must precede the new bullet");
        assert_eq!(merged.matches("# Compute Mesh State").count(), 1);
    }

    #[test]
    fn test_imessage_body_includes_region_ad_and_ip() {
        let body = imessage_body(&instance_with_ip(Some("203.0.113.8")));
        assert_eq!(
            body,
            "OCI A1.Flex acquired: us-ashburn-1 (AD-3) ip=203.0.113.8"
        );
    }

    #[test]
    fn test_imessage_body_marks_unknown_ip_with_a_placeholder() {
        let body = imessage_body(&instance_with_ip(None));
        assert!(body.ends_with("ip=?"), "unexpected body: {body}");
    }

    #[test]
    fn test_which_in_finds_an_executable_in_the_search_path() {
        let dir = test_support::temp_dir("which-found");
        let tool = dir.join("tool-x");
        std::fs::write(&tool, "#!/bin/sh\nexit 0\n").unwrap();

        let found = which::which_in("tool-x", dir.as_os_str()).unwrap();
        assert_eq!(found, tool);

        test_support::remove(&dir);
    }

    #[test]
    fn test_which_in_searches_every_path_entry_in_order() {
        let first = test_support::temp_dir("which-first");
        let second = test_support::temp_dir("which-second");
        let tool = second.join("only-here");
        std::fs::write(&tool, "#!/bin/sh\nexit 0\n").unwrap();

        let joined =
            std::env::join_paths([first.as_os_str(), second.as_os_str()]).unwrap();

        let found = which::which_in("only-here", &joined).unwrap();
        assert_eq!(found, tool);

        test_support::remove(&first);
        test_support::remove(&second);
    }

    #[test]
    fn test_which_in_errors_for_a_missing_binary() {
        let dir = test_support::temp_dir("which-missing");
        assert!(which::which_in("definitely-not-installed-xyz", dir.as_os_str()).is_err());
        test_support::remove(&dir);
    }

    #[test]
    fn test_which_in_ignores_directories_with_the_binary_name() {
        let dir = test_support::temp_dir("which-dir");
        std::fs::create_dir_all(dir.join("not-a-binary")).unwrap();
        assert!(which::which_in("not-a-binary", dir.as_os_str()).is_err());
        test_support::remove(&dir);
    }
}
