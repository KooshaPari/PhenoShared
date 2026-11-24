//! tailscale-keygen — mint a single-use, ephemeral, tagged Tailscale auth-key
//! and print it to stdout (one line, no trailing whitespace) so it can be
//! captured by `$(tailscale-keygen)` in shell or by the oci-post-acquire hook.
//!
//! Per scripting policy (Rust default), this replaces what would otherwise be
//! a curl + jq one-liner that we'd have to harden against secret leakage,
//! retries, and TTL parsing.
//!
//! Usage:
//!   TS_API_KEY=tskey-api-... TS_TAILNET=koosha.github tailscale-keygen \
//!     --tag tag:phenotype-mesh --tag tag:oci --ttl 600
//!
//! API reference: POST /api/v2/tailnet/{tailnet}/keys
//!   https://tailscale.com/api#tag/keys/POST/api/v2/tailnet/{tailnet}/keys

use std::str::FromStr;

use anyhow::{Context, Result, bail};
use clap::Parser;
use serde::{Deserialize, Serialize};
use tracing_subscriber::EnvFilter;

/// Mint an ephemeral, single-use, tagged Tailscale auth-key.
#[derive(Parser, Debug)]
#[command(version, about)]
struct Cli {
    /// Tailscale API key (`tskey-api-...`). Required.
    #[arg(long, env = "TS_API_KEY", hide_env_values = true)]
    api_key: String,

    /// Tailnet name (e.g. `koosha.github` or `example.com`). Required.
    #[arg(long, env = "TS_TAILNET")]
    tailnet: String,

    /// Tags to attach to the new node (repeatable). Must already be declared
    /// in `tagOwners` of the ACL policy. Defaults to `tag:phenotype-mesh`.
    #[arg(long = "tag", default_values = ["tag:phenotype-mesh"])]
    tags: Vec<String>,

    /// Auth-key TTL in seconds. Default 600 (10 min) — long enough for a
    /// post-acquire bootstrap, short enough that a leaked key is near-useless.
    #[arg(long, default_value_t = 600)]
    ttl: u64,

    /// API base (override only for testing).
    #[arg(long, default_value = "https://api.tailscale.com", hide = true)]
    api_base: String,

    /// Output format for stderr logs: auto (default), text, json.
    #[arg(long, default_value = "auto", hide = true)]
    format: String,
}

/// Output format for tracing/logs.
#[derive(Debug, Clone, PartialEq)]
enum OutputFormat {
    Auto,
    Text,
    Json,
}

impl FromStr for OutputFormat {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "auto" => Ok(Self::Auto),
            "text" => Ok(Self::Text),
            "json" => Ok(Self::Json),
            _ => Err(format!(
                "unknown format '{s}': expected auto, text, or json"
            )),
        }
    }
}

#[derive(Serialize)]
struct CreateKeyRequest {
    capabilities: Capabilities,
    #[serde(rename = "expirySeconds")]
    expiry_seconds: u64,
    description: String,
}

#[derive(Serialize)]
struct Capabilities {
    devices: Devices,
}

#[derive(Serialize)]
struct Devices {
    create: CreateCaps,
}

#[derive(Serialize)]
struct CreateCaps {
    reusable: bool,
    ephemeral: bool,
    preauthorized: bool,
    tags: Vec<String>,
}

#[derive(Deserialize)]
struct CreateKeyResponse {
    key: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // NOTE: this binary must keep logs off stdout — stdout is the transport
    // for the Tailscale API key (consumed via `$(tailscale-keygen)` in shell or
    // by the oci-post-acquire hook). The local `with_writer(std::io::stderr)`
    // override is load-bearing and must stay here.
    let no_color = std::env::var_os("NO_COLOR").is_some();
    let fmt: OutputFormat = cli.format.parse().unwrap_or(OutputFormat::Auto);
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));

    if matches!(fmt, OutputFormat::Json) {
        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_writer(std::io::stderr) // never to stdout — stdout is the key
            .with_ansi(!no_color)
            .json()
            .init();
    } else {
        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_writer(std::io::stderr) // never to stdout — stdout is the key
            .with_ansi(!no_color)
            .init();
    }

    if cli.api_key.is_empty() {
        bail!("TS_API_KEY is empty (set env or pass --api-key)");
    }
    if cli.tailnet.is_empty() {
        bail!("TS_TAILNET is empty (set env or pass --tailnet)");
    }
    if cli.tags.is_empty() {
        bail!("at least one --tag is required");
    }

    let url = create_key_url(&cli.api_base, &cli.tailnet);
    let body = create_key_body(&cli.tags, cli.ttl);

    tracing::info!(url = %url, tags = ?cli.tags, ttl = cli.ttl, "minting auth-key");

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .context("build reqwest client")?;

    let resp = client
        .post(&url)
        .basic_auth(&cli.api_key, Some(""))
        .json(&body)
        .send()
        .await
        .context("POST /keys")?;

    let status = resp.status();
    if !status.is_success() {
        let text = resp.text().await.unwrap_or_default();
        bail!("tailscale API returned {}: {}", status, text);
    }

    let parsed: CreateKeyResponse = resp.json().await.context("decode CreateKeyResponse")?;
    let key = validate_key(parsed)?;

    // stdout = key only. No newline beyond `println!`'s single \n. Consumers:
    //   AUTH_KEY=$(tailscale-keygen --tag tag:oci)
    println!("{key}");
    Ok(())
}

/// Build the create-key endpoint, tolerating a trailing slash on `api_base`.
fn create_key_url(api_base: &str, tailnet: &str) -> String {
    format!(
        "{}/api/v2/tailnet/{}/keys",
        api_base.trim_end_matches('/'),
        tailnet
    )
}

/// Build the create-key request body: single-use, ephemeral, preauthorized.
fn create_key_body(tags: &[String], ttl: u64) -> CreateKeyRequest {
    CreateKeyRequest {
        capabilities: Capabilities {
            devices: Devices {
                create: CreateCaps {
                    reusable: false,     // single-use
                    ephemeral: true,     // node deregistered when offline
                    preauthorized: true, // skip admin review (gated by tags)
                    tags: tags.to_vec(),
                },
            },
        },
        expiry_seconds: ttl,
        description: format!(
            "phenotype/{} auto-mint by tailscale-keygen",
            tags.first().map(String::as_str).unwrap_or("mesh")
        ),
    }
}

/// Reject an empty key before it reaches stdout — an empty value would be
/// silently consumed by `$(tailscale-keygen)` and enroll nothing.
fn validate_key(resp: CreateKeyResponse) -> Result<String> {
    if resp.key.is_empty() {
        bail!("tailscale API returned empty key");
    }
    Ok(resp.key)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn test_create_key_url_builds_the_tailnet_endpoint() {
        assert_eq!(
            create_key_url("https://api.tailscale.com", "koosha.github"),
            "https://api.tailscale.com/api/v2/tailnet/koosha.github/keys"
        );
    }

    #[test]
    fn test_create_key_url_tolerates_a_trailing_slash() {
        assert_eq!(
            create_key_url("https://api.tailscale.com/", "t"),
            "https://api.tailscale.com/api/v2/tailnet/t/keys"
        );
    }

    #[test]
    fn test_create_key_body_is_ephemeral_single_use_and_preauthorized() {
        let tags = vec!["tag:phenotype-mesh".to_string()];
        let body = create_key_body(&tags, 600);
        let v: Value = serde_json::to_value(&body).unwrap();
        let create = &v["capabilities"]["devices"]["create"];
        assert_eq!(create["reusable"], false);
        assert_eq!(create["ephemeral"], true);
        assert_eq!(create["preauthorized"], true);
        assert_eq!(create["tags"][0], "tag:phenotype-mesh");
        assert_eq!(v["expirySeconds"], 600);
    }

    #[test]
    fn test_create_key_body_honours_the_requested_ttl_and_tags() {
        let tags = vec!["tag:oci".to_string(), "tag:extra".to_string()];
        let body = create_key_body(&tags, 120);
        let v: Value = serde_json::to_value(&body).unwrap();
        assert_eq!(v["expirySeconds"], 120);
        assert_eq!(v["capabilities"]["devices"]["create"]["tags"][1], "tag:extra");
    }

    #[test]
    fn test_description_names_the_first_tag() {
        let body = create_key_body(&["tag:oci".to_string()], 60);
        assert_eq!(
            body.description,
            "phenotype/tag:oci auto-mint by tailscale-keygen"
        );
    }

    #[test]
    fn test_description_falls_back_when_no_tag_is_given() {
        let body = create_key_body(&[], 60);
        assert_eq!(body.description, "phenotype/mesh auto-mint by tailscale-keygen");
        assert!(body.capabilities.devices.create.tags.is_empty());
    }

    #[test]
    fn test_validate_key_returns_the_minted_key() {
        let key = validate_key(CreateKeyResponse {
            key: "tskey-auth-abc123".into(),
        })
        .unwrap();
        assert_eq!(key, "tskey-auth-abc123");
    }

    #[test]
    fn test_validate_key_rejects_an_empty_key() {
        let err = validate_key(CreateKeyResponse { key: String::new() }).unwrap_err();
        assert!(
            err.to_string().contains("empty key"),
            "unexpected error: {err}"
        );
    }

    #[test]
    fn test_output_format_parse() {
        assert_eq!("auto".parse::<OutputFormat>().unwrap(), OutputFormat::Auto);
        assert_eq!("text".parse::<OutputFormat>().unwrap(), OutputFormat::Text);
        assert_eq!("json".parse::<OutputFormat>().unwrap(), OutputFormat::Json);
        assert_eq!("JSON".parse::<OutputFormat>().unwrap(), OutputFormat::Json);
        let err = "yaml".parse::<OutputFormat>().unwrap_err();
        assert!(err.contains("unknown format"), "unexpected error: {err}");
    }

    #[test]
    fn test_cli_defaults_are_safe_for_an_ephemeral_key() {
        let cli = Cli::try_parse_from([
            "tailscale-keygen",
            "--api-key",
            "tskey-api-test",
            "--tailnet",
            "example.github",
        ])
        .expect("minimal invocation must parse");

        assert_eq!(cli.ttl, 600);
        assert_eq!(cli.tags, vec!["tag:phenotype-mesh".to_string()]);
        assert_eq!(cli.api_base, "https://api.tailscale.com");
        assert_eq!(cli.tailnet, "example.github");
    }

    #[test]
    fn test_cli_accepts_repeated_tags_and_an_override_base() {
        let cli = Cli::try_parse_from([
            "tailscale-keygen",
            "--api-key",
            "k",
            "--tailnet",
            "t",
            "--tag",
            "tag:oci",
            "--tag",
            "tag:mesh",
            "--ttl",
            "90",
            "--api-base",
            "http://127.0.0.1:8080",
        ])
        .expect("full invocation must parse");

        assert_eq!(cli.tags, vec!["tag:oci".to_string(), "tag:mesh".to_string()]);
        assert_eq!(cli.ttl, 90);
        assert_eq!(cli.api_base, "http://127.0.0.1:8080");
    }

    #[test]
    fn test_cli_rejects_an_unknown_flag() {
        assert!(
            Cli::try_parse_from(["tailscale-keygen", "--definitely-not-a-flag"]).is_err(),
            "clap must reject unknown flags"
        );
    }
}
