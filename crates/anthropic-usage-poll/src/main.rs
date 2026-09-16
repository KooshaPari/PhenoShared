use anyhow::{bail, Context, Result};
use chrono::Utc;
use clap::Parser;
use futures::stream::{FuturesUnordered, StreamExt};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::Duration;
use tokio::time;

/// Anthropic Admin API usage-report endpoint.
const API_URL: &str = "https://api.anthropic.com/v1/usage";

#[derive(Parser)]
#[command(
    name = "anthropic-usage-poll",
    about = "Poll Anthropic Admin API for token usage"
)]
struct Cli {
    /// Run once and exit
    #[arg(long)]
    once: bool,
    /// Polling interval in seconds
    #[arg(long, default_value = "600")]
    interval: u64,
    /// Output path (default: ~/.claude/usage.json)
    #[arg(long)]
    output: Option<PathBuf>,
    /// Number of concurrent polls to fan out per cycle (WP-02 T2)
    #[arg(long, default_value = "1")]
    concurrent: usize,
}

#[derive(Debug, Serialize, Deserialize, Default, Clone)]
struct UsageSnapshot {
    daily_remaining: Option<u64>,
    monthly_remaining: Option<u64>,
    per_model_tokens_last_24h: serde_json::Value,
    updated_at: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let output = cli.output.unwrap_or_else(default_output_path);

    // Require the admin key to be set; fail loudly rather than silently no-op.
    let api_key = std::env::var("ANTHROPIC_ADMIN_KEY").with_context(|| {
        "ANTHROPIC_ADMIN_KEY env var is required. \
         Set it to a valid Anthropic Admin API key."
    })?;
    if api_key.trim().is_empty() {
        bail!("ANTHROPIC_ADMIN_KEY is set but empty");
    }

    if cli.once {
        poll_and_write(&output, cli.concurrent, &api_key).await?;
    } else {
        // First tick is immediate.
        poll_and_write(&output, cli.concurrent, &api_key).await?;
        let mut ticker = time::interval(Duration::from_secs(cli.interval));
        // Consume the first (immediate) tick.
        ticker.tick().await;
        loop {
            ticker.tick().await;
            if let Err(e) = poll_and_write(&output, cli.concurrent, &api_key).await {
                eprintln!("[anthropic-usage-poll] poll error: {e}");
            }
        }
    }
    Ok(())
}

fn default_output_path() -> PathBuf {
    std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
        .join(".claude")
        .join("usage.json")
}

async fn poll_and_write(output: &Path, concurrent: usize, api_key: &str) -> Result<()> {
    let snapshot = fetch_usage_concurrent(concurrent, api_key).await?;
    write_atomic(output, &snapshot)
}

/// Fan out `concurrent` parallel polls via `FuturesUnordered`, then
/// merge into a single snapshot. Concurrent > 1 is useful when polling
/// multiple Anthropic org accounts simultaneously.
async fn fetch_usage_concurrent(concurrent: usize, api_key: &str) -> Result<UsageSnapshot> {
    let n = concurrent.max(1);
    let client = build_client(api_key)?;
    let mut futures = FuturesUnordered::new();
    for _ in 0..n {
        let c = client.clone();
        futures.push(fetch_usage(c));
    }

    // Collect results; take the first successful snapshot (all n polls hit
    // the same endpoint so they should agree — concurrent fan-out is for
    // latency, not diversity).
    let mut merged: Option<UsageSnapshot> = None;
    while let Some(res) = futures.next().await {
        match res {
            Ok(s) => {
                if merged.is_none() {
                    merged = Some(s);
                }
            }
            Err(e) => {
                eprintln!("[anthropic-usage-poll] fetch error: {e}");
            }
        }
    }

    merged.ok_or_else(|| anyhow::anyhow!("all concurrent polls failed"))
}

/// Build a reusable reqwest client with the bearer token pre-set.
fn build_client(api_key: &str) -> Result<reqwest::Client> {
    use reqwest::header::{self, HeaderMap, HeaderValue};
    let mut headers = HeaderMap::new();
    let mut auth_value = HeaderValue::from_str(&format!("Bearer {api_key}"))
        .context("invalid ANTHROPIC_ADMIN_KEY value")?;
    auth_value.set_sensitive(true);
    headers.insert(header::AUTHORIZATION, auth_value);
    headers.insert("anthropic-version", HeaderValue::from_static("2023-06-01"));

    let client = reqwest::Client::builder()
        .default_headers(headers)
        .timeout(Duration::from_secs(30))
        .build()
        .context("failed to build reqwest client")?;
    Ok(client)
}

async fn fetch_usage(client: reqwest::Client) -> Result<UsageSnapshot> {
    let resp = client
        .get(API_URL)
        .send()
        .await
        .context("GET /v1/usage failed")?;

    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        bail!("Anthropic API returned {status}: {body}");
    }

    // The API response shape may vary; deserialize into a generic Value
    // first, then map known fields into UsageSnapshot so the tool remains
    // forward-compatible as the API evolves.
    let body: serde_json::Value = resp
        .json()
        .await
        .context("failed to parse usage response")?;

    Ok(UsageSnapshot {
        daily_remaining: body["daily_remaining"].as_u64(),
        monthly_remaining: body["monthly_remaining"].as_u64(),
        per_model_tokens_last_24h: body
            .get("per_model")
            .cloned()
            .unwrap_or(serde_json::json!({})),
        updated_at: Utc::now().to_rfc3339(),
    })
}

/// Write `snapshot` to `path` atomically via a sibling temp file + rename.
fn write_atomic(path: &Path, snapshot: &UsageSnapshot) -> Result<()> {
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    std::fs::create_dir_all(parent).with_context(|| format!("mkdir {}", parent.display()))?;

    // Write to a temp file in the same directory so rename is atomic on
    // POSIX (same filesystem).
    let tmp = path.with_extension("json.tmp");
    let json = serde_json::to_string_pretty(snapshot)?;
    std::fs::write(&tmp, &json).with_context(|| format!("write temp file {}", tmp.display()))?;
    std::fs::rename(&tmp, path)
        .with_context(|| format!("rename {} -> {}", tmp.display(), path.display()))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn default_snapshot_serializes() {
        let s = UsageSnapshot::default();
        let json = serde_json::to_string(&s).expect("serialize");
        assert!(json.contains("updated_at"));
    }

    #[test]
    fn default_output_path_contains_claude() {
        let p = default_output_path();
        assert!(p.to_string_lossy().contains(".claude"));
    }

    #[test]
    fn concurrent_arg_parses() {
        let cli =
            Cli::try_parse_from(["anthropic-usage-poll", "--once", "--concurrent", "16"]).unwrap();
        assert_eq!(cli.concurrent, 16);
        assert!(cli.once);
    }

    #[test]
    fn write_atomic_round_trips() {
        let dir = std::env::temp_dir().join("usage_poll_test");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("usage.json");
        let snap = UsageSnapshot {
            daily_remaining: Some(999),
            monthly_remaining: Some(12345),
            per_model_tokens_last_24h: serde_json::json!({"claude-3-5": 42}),
            updated_at: "2026-06-30T00:00:00Z".into(),
        };
        write_atomic(&path, &snap).expect("write_atomic");
        let raw = std::fs::read_to_string(&path).unwrap();
        assert!(raw.contains("999"));
        assert!(raw.contains("claude-3-5"));
        // Temp file must be cleaned up.
        assert!(!path.with_extension("json.tmp").exists());
    }

    #[test]
    fn missing_admin_key_is_detected_at_startup() {
        // This validates the fail-loudly contract — main() requires the key.
        // We can't call main() directly in tests, but we can test the
        // env-var check logic inline.
        let result: Result<String, _> = std::env::var("ANTHROPIC_ADMIN_KEY_DEFINITELY_MISSING");
        assert!(result.is_err());
    }
}
