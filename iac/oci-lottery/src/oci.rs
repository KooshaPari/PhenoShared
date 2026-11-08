//! Thin wrapper over the `oci` CLI. We deliberately shell out rather than
//! pull the OCI Rust SDK — keeps auth handling delegated to the user's
//! existing `~/.oci/config` and avoids surface area.

use anyhow::{Context, Result, anyhow};
use serde_json::Value;
use tokio::process::Command;

use crate::config::Config;

#[derive(Debug)]
pub struct LaunchOutcome {
    /// True when capacity was granted (instance OCID returned).
    pub success: bool,
    pub instance_ocid: Option<String>,
    pub raw_stdout: String,
    pub raw_stderr: String,
    /// Set when the CLI returned a structured error string we recognized as
    /// "out of capacity" — so the caller can keep looping silently.
    pub out_of_capacity: bool,
}

/// Discover the AD names for a given region by listing them via `oci`.
pub async fn list_availability_domains(cfg: &Config, region: &str) -> Result<Vec<String>> {
    let compartment = cfg
        .compartment_ocid
        .as_deref()
        .ok_or_else(|| anyhow!("compartment_ocid not set"))?;

    let out = Command::new("oci")
        .args([
            "iam",
            "availability-domain",
            "list",
            "--compartment-id",
            compartment,
            "--region",
            region,
            "--profile",
            &cfg.profile,
        ])
        .output()
        .await
        .context("invoking `oci iam availability-domain list`")?;

    if !out.status.success() {
        return Err(anyhow!(
            "oci availability-domain list failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    ad_names_from_list_stdout(&out.stdout)
}

/// Extract availability-domain names from `oci iam availability-domain list`
/// stdout. Entries without a string `name` are skipped; a payload without a
/// `data` array yields an empty list (the CLI can emit `{}` on odd tenancies).
fn ad_names_from_list_stdout(stdout: &[u8]) -> Result<Vec<String>> {
    let v: Value = serde_json::from_slice(stdout)?;
    let names = v
        .get("data")
        .and_then(|d| d.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|e| e.get("name").and_then(|n| n.as_str().map(String::from)))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    Ok(names)
}

/// Classify a failed `oci compute instance launch` as a retryable capacity or
/// throttling condition rather than a fatal configuration error.
fn classify_launch_failure(stderr: &str) -> bool {
    let lower = stderr.to_ascii_lowercase();
    lower.contains("out of host capacity")
        || lower.contains("outofhostcapacity")
        || lower.contains("internalerror")
        || lower.contains("toomanyrequests")
        || lower.contains("limitexceeded")
}

/// Extract the instance OCID from `oci compute instance launch` stdout.
fn ocid_from_launch_stdout(stdout: &str) -> Option<String> {
    let v: Value = serde_json::from_str(stdout).unwrap_or(Value::Null);
    v.pointer("/data/id")
        .and_then(|n| n.as_str())
        .map(String::from)
}

/// Extract the first public IP from `oci compute instance list-vnics` stdout.
fn public_ip_from_vnics_stdout(stdout: &[u8]) -> Result<Option<String>> {
    let v: Value = serde_json::from_slice(stdout)?;
    let ip = v
        .pointer("/data/0/public-ip")
        .and_then(|n| n.as_str())
        .map(String::from);
    Ok(ip)
}

/// Attempt to launch an A1.Flex instance in the given region/AD.
pub async fn try_launch(cfg: &Config, region: &str, ad_name: &str) -> Result<LaunchOutcome> {
    let compartment = cfg
        .compartment_ocid
        .as_deref()
        .ok_or_else(|| anyhow!("compartment_ocid not set"))?;
    let image = cfg
        .image_ocid
        .as_deref()
        .ok_or_else(|| anyhow!("image_ocid not set"))?;
    let subnet = cfg
        .subnet_ocid
        .as_deref()
        .ok_or_else(|| anyhow!("subnet_ocid not set"))?;

    let shape_config = serde_json::json!({
        "ocpus": cfg.ocpus,
        "memoryInGBs": cfg.memory_gb
    })
    .to_string();

    let ssh_key = tokio::fs::read_to_string(&cfg.ssh_authorized_keys_path)
        .await
        .with_context(|| {
            format!(
                "reading ssh public key {}",
                cfg.ssh_authorized_keys_path.display()
            )
        })?;
    let metadata = serde_json::json!({ "ssh_authorized_keys": ssh_key.trim() }).to_string();

    let out = Command::new("oci")
        .args([
            "compute",
            "instance",
            "launch",
            "--region",
            region,
            "--profile",
            &cfg.profile,
            "--availability-domain",
            ad_name,
            "--compartment-id",
            compartment,
            "--shape",
            &cfg.shape,
            "--shape-config",
            &shape_config,
            "--image-id",
            image,
            "--subnet-id",
            subnet,
            "--display-name",
            &cfg.display_name,
            "--metadata",
            &metadata,
            "--wait-for-state",
            "RUNNING",
            "--max-wait-seconds",
            "600",
        ])
        .output()
        .await
        .context("invoking `oci compute instance launch`")?;

    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let stderr = String::from_utf8_lossy(&out.stderr).to_string();

    if out.status.success() {
        let ocid = ocid_from_launch_stdout(&stdout);
        return Ok(LaunchOutcome {
            success: ocid.is_some(),
            instance_ocid: ocid,
            raw_stdout: stdout,
            raw_stderr: stderr,
            out_of_capacity: false,
        });
    }

    let out_of_capacity = classify_launch_failure(&stderr);

    Ok(LaunchOutcome {
        success: false,
        instance_ocid: None,
        raw_stdout: stdout,
        raw_stderr: stderr,
        out_of_capacity,
    })
}

/// Best-effort lookup of the public IP of a freshly-launched instance.
pub async fn instance_public_ip(
    cfg: &Config,
    region: &str,
    instance_ocid: &str,
) -> Result<Option<String>> {
    let compartment = cfg
        .compartment_ocid
        .as_deref()
        .ok_or_else(|| anyhow!("compartment_ocid not set"))?;

    let out = Command::new("oci")
        .args([
            "compute",
            "instance",
            "list-vnics",
            "--instance-id",
            instance_ocid,
            "--compartment-id",
            compartment,
            "--region",
            region,
            "--profile",
            &cfg.profile,
        ])
        .output()
        .await?;

    if !out.status.success() {
        return Ok(None);
    }
    public_ip_from_vnics_stdout(&out.stdout)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Config;

    #[test]
    fn test_ad_names_extracted_in_order() {
        let stdout = br#"{"data":[
            {"name":"Uocm:AP-TOKYO-1-AD-1"},
            {"name":"Uocm:AP-TOKYO-1-AD-2"},
            {"name":"Uocm:AP-TOKYO-1-AD-3"}
        ]}"#;
        let names = ad_names_from_list_stdout(stdout).unwrap();
        assert_eq!(
            names,
            vec![
                "Uocm:AP-TOKYO-1-AD-1",
                "Uocm:AP-TOKYO-1-AD-2",
                "Uocm:AP-TOKYO-1-AD-3",
            ]
        );
    }

    #[test]
    fn test_ad_names_skips_entries_without_a_string_name() {
        let stdout = br#"{"data":[{"name":"AD-1"},{"id":"no-name"},{"name":null}]}"#;
        let names = ad_names_from_list_stdout(stdout).unwrap();
        assert_eq!(names, vec!["AD-1".to_string()]);
    }

    #[test]
    fn test_ad_names_without_data_key_is_empty_not_an_error() {
        assert!(ad_names_from_list_stdout(b"{}").unwrap().is_empty());
        assert!(ad_names_from_list_stdout(br#"{"data":null}"#).unwrap().is_empty());
    }

    #[test]
    fn test_ad_names_rejects_non_json_output() {
        assert!(ad_names_from_list_stdout(b"ServiceError: not authorized").is_err());
    }

    #[test]
    fn test_classify_launch_failure_recognizes_capacity_errors() {
        for stderr in [
            "Out of host capacity.",
            "OUTOFHOSTCAPACITY",
            "InternalError: unexpected",
            "TooManyRequests",
            "LimitExceeded",
        ] {
            assert!(
                classify_launch_failure(stderr),
                "should be retryable: {stderr}"
            );
        }
    }

    #[test]
    fn test_classify_launch_failure_rejects_fatal_errors() {
        for stderr in [
            "",
            "NotAuthorizedOrNotFound",
            "InvalidParameter: subnet OCID not found",
            "ServiceError: 404",
        ] {
            assert!(
                !classify_launch_failure(stderr),
                "must not be retried: {stderr}"
            );
        }
    }

    #[test]
    fn test_ocid_extracted_from_launch_stdout() {
        let stdout = r#"{"data":{"id":"ocid1.instance.oc1..abc","lifecycle-state":"RUNNING"}}"#;
        assert_eq!(
            ocid_from_launch_stdout(stdout).as_deref(),
            Some("ocid1.instance.oc1..abc")
        );
    }

    #[test]
    fn test_ocid_missing_or_malformed_stdout_yields_none() {
        assert!(ocid_from_launch_stdout(r#"{"data":{}}"#).is_none());
        assert!(ocid_from_launch_stdout(r#"{"data":{"id":null}}"#).is_none());
        assert!(ocid_from_launch_stdout(r#"{"data":{"id":42}}"#).is_none());
        assert!(ocid_from_launch_stdout("not json at all").is_none());
    }

    #[test]
    fn test_public_ip_taken_from_first_vnic() {
        let stdout = br#"{"data":[{"public-ip":"203.0.113.9"},{"public-ip":"203.0.113.10"}]}"#;
        assert_eq!(
            public_ip_from_vnics_stdout(stdout).unwrap().as_deref(),
            Some("203.0.113.9")
        );
    }

    #[test]
    fn test_public_ip_absent_when_vnic_has_no_public_address() {
        assert!(
            public_ip_from_vnics_stdout(br#"{"data":[{"public-ip":null}]}"#)
                .unwrap()
                .is_none()
        );
        assert!(
            public_ip_from_vnics_stdout(br#"{"data":[]}"#)
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn test_public_ip_rejects_non_json_output() {
        assert!(public_ip_from_vnics_stdout(b"<html>502</html>").is_err());
    }

    #[tokio::test]
    async fn test_list_availability_domains_requires_a_compartment() {
        let cfg = Config::default();
        let err = list_availability_domains(&cfg, "ap-tokyo-1")
            .await
            .unwrap_err();
        assert_eq!(err.to_string(), "compartment_ocid not set");
    }

    #[tokio::test]
    async fn test_try_launch_requires_image_before_touching_the_cli() {
        let cfg = Config {
            compartment_ocid: Some("ocid1.compartment.test".into()),
            ..Config::default()
        };

        let err = try_launch(&cfg, "ap-tokyo-1", "AD-1").await.unwrap_err();
        assert_eq!(err.to_string(), "image_ocid not set");
    }

    #[tokio::test]
    async fn test_try_launch_requires_subnet_after_image() {
        let cfg = Config {
            compartment_ocid: Some("ocid1.compartment.test".into()),
            image_ocid: Some("ocid1.image.test".into()),
            ..Config::default()
        };

        let err = try_launch(&cfg, "ap-tokyo-1", "AD-1").await.unwrap_err();
        assert_eq!(err.to_string(), "subnet_ocid not set");
    }

    #[tokio::test]
    async fn test_try_launch_reports_a_missing_ssh_key_with_its_path() {
        let dir = crate::test_support::temp_dir("oci-missing-key");
        let key = dir.join("absent.pub");

        let cfg = Config {
            compartment_ocid: Some("ocid1.compartment.test".into()),
            image_ocid: Some("ocid1.image.test".into()),
            subnet_ocid: Some("ocid1.subnet.test".into()),
            ssh_authorized_keys_path: key.clone(),
            ..Config::default()
        };

        let err = try_launch(&cfg, "ap-tokyo-1", "AD-1").await.unwrap_err();
        let text = format!("{err:#}");
        assert!(
            text.contains("reading ssh public key"),
            "unexpected error: {text}"
        );
        assert!(text.contains("absent.pub"), "path missing from: {text}");

        crate::test_support::remove(&dir);
    }

    #[tokio::test]
    async fn test_instance_public_ip_requires_a_compartment() {
        let cfg = Config::default();
        let err = instance_public_ip(&cfg, "ap-tokyo-1", "ocid1.instance.test")
            .await
            .unwrap_err();
        assert_eq!(err.to_string(), "compartment_ocid not set");
    }
}
