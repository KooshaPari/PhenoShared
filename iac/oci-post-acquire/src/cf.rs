//! Cloudflare DNS upsert — creates or updates an A record.

use anyhow::{Context, Result, anyhow};
use serde::{Deserialize, Serialize};
use tracing::info;

use oci_helpers::expand_home;

#[derive(Debug, Serialize)]
struct ARecord<'a> {
    #[serde(rename = "type")]
    kind: &'a str,
    name: &'a str,
    content: &'a str,
    ttl: u32,
    proxied: bool,
}

#[derive(Debug, Deserialize)]
struct ListResp {
    result: Vec<ExistingRecord>,
    success: bool,
}

#[derive(Debug, Deserialize)]
struct ExistingRecord {
    id: String,
}

#[derive(Debug, Deserialize)]
struct ApiResp {
    success: bool,
    errors: serde_json::Value,
}

pub async fn upsert_a_record(zone_id: &str, token_file: &str, name: &str, ip: &str) -> Result<()> {
    let token = tokio::fs::read_to_string(expand_home(token_file))
        .await
        .with_context(|| format!("read CF token from {token_file}"))?;
    let token = token.trim();

    let client = reqwest::Client::new();
    // Find existing.
    let list_url = format!(
        "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={name}"
    );
    let existing: ListResp = client
        .get(&list_url)
        .bearer_auth(token)
        .send()
        .await?
        .json()
        .await?;
    if !existing.success {
        return Err(anyhow!("cf list dns_records failed"));
    }

    let body = ARecord {
        kind: "A",
        name,
        content: ip,
        ttl: 60,
        proxied: false,
    };

    let resp: ApiResp = if let Some(rec) = existing.result.first() {
        let url = format!(
            "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{}",
            rec.id
        );
        client
            .put(&url)
            .bearer_auth(token)
            .json(&body)
            .send()
            .await?
            .json()
            .await?
    } else {
        let url = format!("https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records");
        client
            .post(&url)
            .bearer_auth(token)
            .json(&body)
            .send()
            .await?
            .json()
            .await?
    };
    if !resp.success {
        return Err(anyhow!("cf upsert failed: {}", resp.errors));
    }
    info!(name, ip, "cloudflare A record upserted");
    Ok(())
}
