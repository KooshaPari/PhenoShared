//! Downstream hook drop-ins — runs every executable in `oci-acquire-hooks.d/`
//! lexicographically, passing the instance file path as $1 and exporting key
//! fields as env vars. A failing hook does not abort the chain; we collect
//! errors and warn at the end.

use anyhow::{Result, anyhow};
use oci_helpers::expand_home;
use tokio::process::Command;
use tracing::{info, warn};

use crate::InstanceFile;

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
            },
            Err(e) => {
                warn!(hook = %name, error = ?e, "spawn failed");
                errors.push(format!("{name}: {e}"));
            },
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(anyhow!("{} hook(s) failed: {:?}", errors.len(), errors))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn instance() -> InstanceFile {
        InstanceFile {
            instance_ocid: "ocid1.instance.oc1..hooks".into(),
            region: "eu-frankfurt-1".into(),
            ad: "AD-1".into(),
            public_ip: "203.0.113.40".into(),
            acquired_at: "2026-10-31T00:00:00Z".into(),
        }
    }

    fn unique_dir(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or_default();
        let dir = std::env::temp_dir().join(format!(
            "oci-post-acquire-hooks-{tag}-{}-{nanos}",
            std::process::id()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[cfg(unix)]
    fn write_script(path: &std::path::Path, body: &str) {
        use std::os::unix::fs::PermissionsExt;
        std::fs::write(path, format!("#!/bin/sh\n{body}\n")).unwrap();
        let mut perms = std::fs::metadata(path).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(path, perms).unwrap();
    }

    #[tokio::test]
    async fn test_missing_hooks_dir_is_a_noop() {
        let dir = unique_dir("missing");
        let absent = dir.join("no-such-dir");

        run_dropins(&absent.to_string_lossy(), &instance())
            .await
            .expect("a missing hooks dir must not fail the chain");

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn test_hooks_run_in_lexicographic_order_with_env_exported() {
        let dir = unique_dir("order");
        let out = unique_dir("order-out");
        let log = out.join("order.log");

        write_script(
            &dir.join("10-first"),
            &format!("echo \"10 $OCI_REGION $OCI_AD $OCI_PUBLIC_IP\" >> '{}'", log.display()),
        );
        write_script(
            &dir.join("20-second"),
            &format!("echo \"20 $OCI_INSTANCE_OCID\" >> '{}'", log.display()),
        );

        run_dropins(&dir.to_string_lossy(), &instance())
            .await
            .expect("both hooks exit 0");

        let lines: Vec<String> = std::fs::read_to_string(&log)
            .unwrap()
            .lines()
            .map(str::to_string)
            .collect();
        assert_eq!(lines.len(), 2, "expected two hook runs: {lines:?}");
        assert_eq!(lines[0], "10 eu-frankfurt-1 AD-1 203.0.113.40");
        assert_eq!(lines[1], "20 ocid1.instance.oc1..hooks");

        let _ = std::fs::remove_dir_all(&dir);
        let _ = std::fs::remove_dir_all(&out);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn test_failing_hook_is_reported_but_does_not_stop_the_chain() {
        let dir = unique_dir("failsoft");
        let out = unique_dir("failsoft-out");
        let ran = out.join("last-ran");

        write_script(&dir.join("10-bad"), "exit 3");
        write_script(
            &dir.join("20-good"),
            &format!("echo ran > '{}'", ran.display()),
        );

        let err = run_dropins(&dir.to_string_lossy(), &instance())
            .await
            .expect_err("a non-zero hook must surface as an error");
        let text = err.to_string();
        assert!(text.contains("1 hook(s) failed"), "{text}");
        assert!(text.contains("10-bad"), "failing hook not named: {text}");
        assert!(
            ran.is_file(),
            "later hook must still run after an earlier failure"
        );

        let _ = std::fs::remove_dir_all(&dir);
        let _ = std::fs::remove_dir_all(&out);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn test_subdirectories_are_not_executed() {
        let dir = unique_dir("subdir");
        let out = unique_dir("subdir-out");
        let ran = out.join("subdir-ran");
        std::fs::create_dir_all(dir.join("30-a-directory")).unwrap();
        write_script(
            &dir.join("10-real"),
            &format!("echo ran > '{}'", ran.display()),
        );

        run_dropins(&dir.to_string_lossy(), &instance())
            .await
            .expect("only the regular file runs, and it exits 0");
        assert!(ran.is_file());

        let _ = std::fs::remove_dir_all(&dir);
        let _ = std::fs::remove_dir_all(&out);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn test_empty_hooks_dir_succeeds() {
        let dir = unique_dir("empty");
        run_dropins(&dir.to_string_lossy(), &instance())
            .await
            .expect("no hooks is not an error");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
