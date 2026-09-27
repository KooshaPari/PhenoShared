//! Tailscale enroll — mints an ephemeral auth-key via the Tailscale API and
//! installs+brings up `tailscale` on the freshly-booted instance over SSH.

use crate::InstanceFile;
use anyhow::{Context, Result, anyhow};
use serde::{Deserialize, Serialize};
use tokio::process::Command;
use tracing::info;

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

    let body = CreateKeyReq {
        capabilities: Caps {
            devices: Devices {
                create: DeviceCreate {
                    reusable: false,
                    ephemeral: true,
                    preauthorized: true,
                    tags: &["tag:oci", "tag:phenotype-mesh"],
                },
            },
        },
        expiry_seconds: 600,
    };

    let url = format!("https://api.tailscale.com/api/v2/tailnet/{tailnet}/keys");
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
    let remote_cmd = format!(
        "set -e; curl -fsSL https://tailscale.com/install.sh | sudo sh; \
         sudo tailscale up --auth-key={} --ssh --hostname={}-oci --accept-routes",
        parsed.key,
        inst.region.replace('_', "-")
    );
    let status = Command::new("ssh")
        .arg("-o")
        .arg("StrictHostKeyChecking=accept-new")
        .arg("-o")
        .arg("ConnectTimeout=10")
        .arg(format!("ubuntu@{}", inst.public_ip))
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
