//! Tailscale enroll — mints an ephemeral auth-key via the Tailscale API and
//! installs+brings up `tailscale` on the freshly-booted instance over SSH.

use anyhow::{Context, Result, anyhow};
use serde::{Deserialize, Serialize};
use tokio::process::Command;
use tracing::info;

use crate::InstanceFile;

#[derive(Debug, Serialize)]
struct CreateKeyReq<'a> {
    capabilities: Caps<'a>,
    #[serde(rename = "expirySeconds")]
    expiry_seconds: u64,
}

#[derive(Debug, Serialize)]
struct Caps<'a> {
    devices: Devices<'a>,
}

#[derive(Debug, Serialize)]
struct Devices<'a> {
    create: DeviceCreate<'a>,
}

#[derive(Debug, Serialize)]
struct DeviceCreate<'a> {
    reusable: bool,
    ephemeral: bool,
    preauthorized: bool,
    tags: &'a [&'a str],
}

#[derive(Debug, Deserialize)]
struct CreateKeyResp {
    key: String,
}

pub async fn enroll(inst: &InstanceFile) -> Result<()> {
    let api_key = std::env::var("TS_API_KEY").context("TS_API_KEY env missing")?;
    let tailnet = std::env::var("TS_TAILNET").context("TS_TAILNET env missing")?;

    let tags: &[&str] = &["tag:oci", "tag:phenotype-mesh"];
    let body = create_key_body(tags, 600);

    let url = create_key_url(&tailnet);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .basic_auth(&api_key, Some(""))
        .json(&body)
        .send()
        .await?;
    if !resp.status().is_success() {
        let s = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(anyhow!("tailscale create-key {s}: {text}"));
    }
    let parsed: CreateKeyResp = resp.json().await?;
    info!("tailscale ephemeral auth-key minted");

    // SSH in, install + up.
    let remote_cmd = remote_install_cmd(&parsed.key, &inst.region);
    let status = Command::new("ssh")
        .arg("-o")
        .arg("StrictHostKeyChecking=accept-new")
        .arg("-o")
        .arg("ConnectTimeout=10")
        .arg(ssh_target(&inst.public_ip))
        .arg(&remote_cmd)
        .status()
        .await
        .context("spawn ssh for tailscale install")?;
    if !status.success() {
        return Err(anyhow!("ssh tailscale install exited {status}"));
    }
    info!(host = %inst.public_ip, "tailscale up complete");
    Ok(())
}

/// Endpoint that mints a new auth-key for `tailnet`.
fn create_key_url(tailnet: &str) -> String {
    format!("https://api.tailscale.com/api/v2/tailnet/{tailnet}/keys")
}

/// Request body for an ephemeral, single-use, preauthorized key.
fn create_key_body<'a>(tags: &'a [&'a str], ttl_secs: u64) -> CreateKeyReq<'a> {
    CreateKeyReq {
        capabilities: Caps {
            devices: Devices {
                create: DeviceCreate {
                    reusable: false,
                    ephemeral: true,
                    preauthorized: true,
                    tags,
                },
            },
        },
        expiry_seconds: ttl_secs,
    }
}

/// Remote shell command that installs and enrolls Tailscale on the new node.
///
/// OCI region names use `-` while hostnames prefer `-` too, so any `_` is
/// normalised away before it becomes part of the Tailscale hostname.
fn remote_install_cmd(auth_key: &str, region: &str) -> String {
    format!(
        "set -e; curl -fsSL https://tailscale.com/install.sh | sudo sh; sudo tailscale up \
         --auth-key={auth_key} --ssh --hostname={}-oci --accept-routes",
        region.replace('_', "-")
    )
}

/// SSH login target for a freshly launched OCI Ubuntu image.
fn ssh_target(public_ip: &str) -> String {
    format!("ubuntu@{public_ip}")
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn test_create_key_url_includes_the_tailnet() {
        assert_eq!(
            create_key_url("koosha.github"),
            "https://api.tailscale.com/api/v2/tailnet/koosha.github/keys"
        );
    }

    #[test]
    fn test_create_key_body_is_ephemeral_single_use_and_preauthorized() {
        let body = create_key_body(&["tag:oci"], 600);
        let v: Value = serde_json::to_value(&body).unwrap();
        let create = &v["capabilities"]["devices"]["create"];
        assert_eq!(create["reusable"], false);
        assert_eq!(create["ephemeral"], true);
        assert_eq!(create["preauthorized"], true);
        assert_eq!(create["tags"][0], "tag:oci");
        assert_eq!(v["expirySeconds"], 600);
    }

    #[test]
    fn test_create_key_body_preserves_the_tag_list() {
        let body = create_key_body(&["tag:oci", "tag:phenotype-mesh"], 60);
        let v: Value = serde_json::to_value(&body).unwrap();
        assert_eq!(v["capabilities"]["devices"]["create"]["tags"][1], "tag:phenotype-mesh");
        assert_eq!(v["expirySeconds"], 60);
    }

    #[test]
    fn test_remote_command_embeds_key_hostname_and_flags() {
        let cmd = remote_install_cmd("tskey-auth-abc", "us-ashburn-1");
        assert!(cmd.starts_with("set -e;"), "must fail fast: {cmd}");
        assert!(cmd.contains("--auth-key=tskey-auth-abc"), "{cmd}");
        assert!(cmd.contains("--hostname=us-ashburn-1-oci"), "{cmd}");
        assert!(cmd.contains("--ssh"), "{cmd}");
        assert!(cmd.contains("--accept-routes"), "{cmd}");
    }

    #[test]
    fn test_remote_command_normalises_underscores_in_region() {
        let cmd = remote_install_cmd("k", "us_ashburn_1");
        assert!(cmd.contains("--hostname=us-ashburn-1-oci"), "{cmd}");
        assert!(!cmd.contains("us_ashburn_1"), "underscores leaked: {cmd}");
    }

    #[test]
    fn test_ssh_target_uses_the_ubuntu_user() {
        assert_eq!(ssh_target("203.0.113.30"), "ubuntu@203.0.113.30");
    }
}
