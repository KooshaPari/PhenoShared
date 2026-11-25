//! Mesh-state commit — flips OCI to ✅ in compute-mesh-state.md and commits.

use crate::InstanceFile;
use oci_helpers::expand_home;
use anyhow::{Context, Result, anyhow};
use chrono::Utc;
use tokio::process::Command;
use tracing::info;

pub async fn commit_state(repo: &str, inst: &InstanceFile) -> Result<()> {
    let repo_path = expand_home(repo);
    let doc = repo_path.join("docs/governance/compute-mesh-state.md");
    let original = tokio::fs::read_to_string(&doc)
        .await
        .with_context(|| format!("read {}", doc.display()))?;

    let timestamp = Utc::now().format("%Y-%m-%d %H:%M UTC");
    let marker = format!(
        "\n\n<!-- oci-post-acquire: AUTO-INSERTED {timestamp} -->\n\
         ## OCI Status: ✅ ACQUIRED\n\n\
         - Region: `{}`\n- AD: `{}`\n- Public IP: `{}`\n- Instance OCID: `{}`\n- Acquired: `{}`\n",
        inst.region, inst.ad, inst.public_ip, inst.instance_ocid, inst.acquired_at,
    );

    // Idempotent: replace any prior auto-insert block.
    let updated = if let Some(idx) = original.find("<!-- oci-post-acquire: AUTO-INSERTED") {
        let mut s = original[..idx].trim_end().to_string();
        s.push_str(&marker);
        s
    } else {
        format!("{}{marker}", original.trim_end())
    };
    tokio::fs::write(&doc, updated).await?;

    let run = |args: &[&str]| {
        let cwd = repo_path.clone();
        let owned: Vec<String> = args.iter().map(|s| s.to_string()).collect();
        async move {
            let status = Command::new("git")
                .args(&owned)
                .current_dir(&cwd)
                .status()
                .await?;
            if !status.success() {
                return Err(anyhow!("git {:?} exited {status}", owned));
            }
            anyhow::Ok(())
        }
    };
    run(&["add", "docs/governance/compute-mesh-state.md"]).await?;
    run(&[
        "commit",
        "-m",
        &format!("chore(mesh): OCI acquired {timestamp} ({})", inst.region),
    ])
    .await?;
    info!("mesh-state commit landed");
    Ok(())
}
