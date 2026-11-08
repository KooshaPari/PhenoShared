//! Cloudflare DNS upsert — creates or updates an A record.

use anyhow::{Context, Result, anyhow};
use oci_helpers::expand_home;
use serde::{Deserialize, Serialize};
use tracing::info;

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
    let list_url = dns_records_lookup_url(zone_id, name);
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

    let body = a_record(name, ip);

    let resp: ApiResp = if let Some(rec) = existing.result.first() {
        let url = dns_record_url(zone_id, &rec.id);
        client
            .put(&url)
            .bearer_auth(token)
            .json(&body)
            .send()
            .await?
            .json()
            .await?
    } else {
        let url = dns_records_url(zone_id);
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

/// Collection endpoint for a zone's DNS records.
fn dns_records_url(zone_id: &str) -> String {
    format!("https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records")
}

/// Lookup endpoint that filters the collection down to A records for `name`.
fn dns_records_lookup_url(zone_id: &str, name: &str) -> String {
    format!(
        "{}?type=A&name={name}",
        dns_records_url(zone_id)
    )
}

/// Endpoint for a single, already-known record.
fn dns_record_url(zone_id: &str, record_id: &str) -> String {
    format!("{}/{record_id}", dns_records_url(zone_id))
}

/// The A-record payload sent on both create and update.
fn a_record<'a>(name: &'a str, ip: &'a str) -> ARecord<'a> {
    ARecord {
        kind: "A",
        name,
        content: ip,
        ttl: 60,
        proxied: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn test_dns_records_url_targets_the_zone_collection() {
        assert_eq!(
            dns_records_url("zone123"),
            "https://api.cloudflare.com/client/v4/zones/zone123/dns_records"
        );
    }

    #[test]
    fn test_lookup_url_filters_to_a_records_for_the_name() {
        let url = dns_records_lookup_url("zone123", "oci-1.example.com");
        assert!(url.starts_with("https://api.cloudflare.com/client/v4/zones/zone123/dns_records?"));
        assert!(url.contains("type=A"), "type filter missing: {url}");
        assert!(
            url.contains("name=oci-1.example.com"),
            "name filter missing: {url}"
        );
    }

    #[test]
    fn test_record_url_appends_the_record_id() {
        assert_eq!(
            dns_record_url("zone123", "rec456"),
            "https://api.cloudflare.com/client/v4/zones/zone123/dns_records/rec456"
        );
    }

    #[test]
    fn test_a_record_body_has_the_expected_wire_shape() {
        let body = a_record("oci-1.example.com", "203.0.113.11");
        let v: Value = serde_json::to_value(&body).unwrap();
        assert_eq!(v["type"], "A");
        assert_eq!(v["name"], "oci-1.example.com");
        assert_eq!(v["content"], "203.0.113.11");
        assert_eq!(v["ttl"], 60);
        assert_eq!(v["proxied"], false);
    }

    #[test]
    fn test_a_record_is_not_proxied_and_uses_a_short_ttl() {
        // A freshly-acquired node must be reachable directly, so the record
        // stays unproxied; a short TTL lets a bad IP be corrected quickly.
        let body = a_record("n", "1.2.3.4");
        assert!(!body.proxied);
        assert!(body.ttl <= 300);
    }

    #[tokio::test]
    async fn test_upsert_fails_with_the_token_path_when_unreadable() {
        let err = upsert_a_record("zone", "/nonexistent/cf-token", "n", "1.2.3.4")
            .await
            .unwrap_err();
        let text = format!("{err:#}");
        assert!(text.contains("read CF token"), "unexpected error: {text}");
        assert!(text.contains("cf-token"), "path missing from: {text}");
    }
}
