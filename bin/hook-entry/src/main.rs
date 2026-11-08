//! Claude Code PreToolUse hook.
//! Reads the hook event from stdin, writes a budget+quota annotation to stdout.
use anyhow::Result;
use phenotype_tooling_observability::prelude::{info, init_tracing, instrument};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::Read;
use std::path::PathBuf;

#[derive(Deserialize)]
struct UsageSnapshot {
    daily_remaining: Option<u64>,
    monthly_remaining: Option<u64>,
    updated_at: Option<String>,
}

#[derive(Serialize)]
struct HookOutput {
    budget_line: String,
}

#[instrument(skip_all, fields(component = "hook-entry"))]
fn main() -> Result<()> {
    let otlp_endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:4317".to_string());
    init_tracing("hook-entry", &otlp_endpoint).ok();
    info!(version = env!("CARGO_PKG_VERSION"), "hook-entry starting");
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input)?;

    // Parse but don't fail on bad input — hooks must not block agents
    let _event: Value = serde_json::from_str(&input).unwrap_or_default();

    let usage = read_usage();
    let budget_line = format!(
        "[observability] daily_remaining={} monthly_remaining={} | {} | {} | updated={}",
        fmt_opt(usage.as_ref().and_then(|u| u.daily_remaining)),
        fmt_opt(usage.as_ref().and_then(|u| u.monthly_remaining)),
        read_forecast_hint(),
        read_elapsed_hint(),
        usage
            .as_ref()
            .and_then(|u| u.updated_at.as_deref())
            .unwrap_or("unknown"),
    );

    println!("{}", serde_json::to_string(&HookOutput { budget_line })?);
    Ok(())
}

fn fmt_opt(v: Option<u64>) -> String {
    v.map_or_else(|| String::from("?"), |n| n.to_string())
}

fn claude_dir() -> PathBuf {
    std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
        .join(".claude")
}

fn read_usage() -> Option<UsageSnapshot> {
    let path = claude_dir().join("usage.json");
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

fn read_forecast_hint() -> String {
    // TODO: invoke agent-forecast binary for current prompt category
    String::from("forecast=p50:? p90:?")
}

fn read_elapsed_hint() -> String {
    // TODO: read active-agents.json, compute elapsed for current session
    String::from("elapsed=?")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fmt_opt_some() {
        assert_eq!(fmt_opt(Some(42_000)), "42000");
    }

    #[test]
    fn fmt_opt_none() {
        assert_eq!(fmt_opt(None), "?");
    }

    #[test]
    fn hook_output_serializes() {
        let o = HookOutput {
            budget_line: "test line".to_string(),
        };
        let json = serde_json::to_string(&o).unwrap();
        assert!(json.contains("budget_line"));
        assert!(json.contains("test line"));
    }
}
