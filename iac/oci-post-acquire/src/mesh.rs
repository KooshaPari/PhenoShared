//! Mesh-state commit — flips OCI to ✅ in compute-mesh-state.md and commits.

use anyhow::{Context, Result, anyhow};
use chrono::Utc;
use oci_helpers::expand_home;
use tokio::process::Command;
use tracing::info;

use crate::InstanceFile;

pub async fn commit_state(repo: &str, inst: &InstanceFile) -> Result<()> {
    let repo_path = expand_home(repo);
    let doc = repo_path.join("docs/governance/compute-mesh-state.md");
    let original = tokio::fs::read_to_string(&doc)
        .await
        .with_context(|| format!("read {}", doc.display()))?;

    let timestamp = Utc::now().format("%Y-%m-%d %H:%M UTC").to_string();
    let marker = mesh_marker(inst, &timestamp);

    // Idempotent: replace any prior auto-insert block.
    let updated = merge_mesh_doc(&original, &marker);
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

/// Sentinel that marks the block this tool owns inside `compute-mesh-state.md`.
const AUTO_INSERT_SENTINEL: &str = "<!-- oci-post-acquire: AUTO-INSERTED";

/// The status block written for a freshly acquired instance.
fn mesh_marker(inst: &InstanceFile, timestamp: &str) -> String {
    format!(
        "\n\n<!-- oci-post-acquire: AUTO-INSERTED {timestamp} -->\n## OCI Status: ✅ \
         ACQUIRED\n\n- Region: `{}`\n- AD: `{}`\n- Public IP: `{}`\n- Instance OCID: `{}`\n- \
         Acquired: `{}`\n",
        inst.region, inst.ad, inst.public_ip, inst.instance_ocid, inst.acquired_at,
    )
}

/// Replace any previously auto-inserted block, or append one if absent.
///
/// Everything before the sentinel is operator-authored content and is kept
/// verbatim; everything from the sentinel onwards is owned by this tool.
fn merge_mesh_doc(original: &str, marker: &str) -> String {
    if let Some(idx) = original.find(AUTO_INSERT_SENTINEL) {
        let mut s = original[..idx].trim_end().to_string();
        s.push_str(marker);
        s
    } else {
        format!("{}{marker}", original.trim_end())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn instance() -> InstanceFile {
        InstanceFile {
            instance_ocid: "ocid1.instance.oc1..abc".into(),
            region: "us-ashburn-1".into(),
            ad: "AD-2".into(),
            public_ip: "203.0.113.20".into(),
            acquired_at: "2026-10-31T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_marker_carries_every_instance_field() {
        let marker = mesh_marker(&instance(), "2026-10-31 03:00 UTC");
        assert!(marker.contains("2026-10-31 03:00 UTC"), "{marker}");
        assert!(marker.contains("## OCI Status: ✅ ACQUIRED"), "{marker}");
        assert!(marker.contains("- Region: `us-ashburn-1`"), "{marker}");
        assert!(marker.contains("- AD: `AD-2`"), "{marker}");
        assert!(marker.contains("- Public IP: `203.0.113.20`"), "{marker}");
        assert!(
            marker.contains("- Instance OCID: `ocid1.instance.oc1..abc`"),
            "{marker}"
        );
        assert!(marker.contains("- Acquired: `2026-10-31T00:00:00Z`"), "{marker}");
    }

    #[test]
    fn test_marker_starts_with_a_sentinel_after_a_blank_line() {
        let marker = mesh_marker(&instance(), "t");
        assert!(marker.starts_with("\n\n"), "marker must separate blocks: {marker:?}");
        assert!(marker.contains(AUTO_INSERT_SENTINEL), "{marker}");
        assert!(marker.ends_with('\n'), "{marker:?}");
    }

    #[test]
    fn test_merge_appends_when_no_prior_block_exists() {
        let original = "# Compute Mesh State\n\nStatus: PENDING\n\n";
        let marker = mesh_marker(&instance(), "t1");

        let merged = merge_mesh_doc(original, &marker);
        assert_eq!(merged, format!("{}{marker}", original.trim_end()));
        assert_eq!(merged.matches("# Compute Mesh State").count(), 1);
        assert!(merged.contains(AUTO_INSERT_SENTINEL), "{merged}");
    }

    #[test]
    fn test_merge_replaces_a_prior_block_and_keeps_operator_content() {
        let original = "# Compute Mesh State\n\nHand-written note.\n\n\
                        <!-- oci-post-acquire: AUTO-INSERTED 2020-01-01 00:00 UTC -->\n\
                        ## OCI Status: ✅ ACQUIRED\n\n- Region: `old-region`\n";
        let marker = mesh_marker(&instance(), "2026-10-31 03:00 UTC");

        let merged = merge_mesh_doc(original, &marker);
        assert!(
            merged.contains("Hand-written note."),
            "operator content lost: {merged}"
        );
        assert!(!merged.contains("old-region"), "stale block survived: {merged}");
        assert!(
            merged.contains("2026-10-31 03:00 UTC"),
            "new block missing: {merged}"
        );
        assert_eq!(merged.matches(AUTO_INSERT_SENTINEL).count(), 1);
        assert!(merged.starts_with("# Compute Mesh State\n\nHand-written note."), "{merged}");
    }

    #[test]
    fn test_merge_is_idempotent_across_repeated_runs() {
        let original = "# Compute Mesh State\n";
        let marker = mesh_marker(&instance(), "t");

        let once = merge_mesh_doc(original, &marker);
        let twice = merge_mesh_doc(&once, &marker);
        assert_eq!(once, twice);
        assert_eq!(twice.matches(AUTO_INSERT_SENTINEL).count(), 1);
    }

    #[tokio::test]
    async fn test_commit_state_reports_a_missing_document() {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or_default();
        let dir = std::env::temp_dir().join(format!(
            "oci-post-acquire-mesh-{}-{nanos}",
            std::process::id()
        ));
        std::fs::create_dir_all(&dir).unwrap();

        let err = commit_state(&dir.to_string_lossy(), &instance())
            .await
            .unwrap_err();
        let text = format!("{err:#}");
        assert!(text.contains("compute-mesh-state.md"), "{text}");

        let _ = std::fs::remove_dir_all(&dir);
    }
}
