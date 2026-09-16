#!/usr/bin/env -S cargo +stable -Zscript
---
[package]
name = "restore-rulesets"
version = "0.1.0"
edition = "2021"

[dependencies]
anyhow = "1"
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
---
//! restore-rulesets: re-add ruleset rules that were dropped during the
//! GitHub Actions billing outage (see
//! `repos/docs/governance/billing-blocked-rule-compensating-controls.md`).
//!
//! Reads `iac/data/billing-blocked-rules.json`, fetches each ruleset's current
//! state via `gh api`, and idempotently PATCHes any missing dropped rules back
//! into the ruleset. Additive only — never removes rules.
//!
//! Usage:
//!   ./restore-rulesets.rs --data ../data/billing-blocked-rules.json [--dry-run] [--owner KooshaPari]
//!
//! Scripting-policy justification: Rust per repos/docs/governance/scripting_policy.md
//! (default tier; uses clap + anyhow + serde + std::process::Command for `gh`).

use anyhow::{anyhow, Context, Result};
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;

#[derive(Parser, Debug)]
#[command(about = "Restore ruleset rules dropped during the Actions billing outage", long_about = None)]
struct Cli {
    /// Path to billing-blocked-rules.json
    #[arg(long, default_value = "iac/data/billing-blocked-rules.json")]
    data: PathBuf,

    /// GitHub owner (org or user) that owns the repos
    #[arg(long, default_value = "KooshaPari")]
    owner: String,

    /// Show what would change without calling the GitHub API
    #[arg(long)]
    dry_run: bool,

    /// Restrict to a single repo name (optional)
    #[arg(long)]
    repo: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct DataFile {
    entries: Vec<Entry>,
}

#[derive(Debug, Deserialize, Serialize)]
struct Entry {
    repo: String,
    ruleset_id: u64,
    dropped_rules: Vec<String>,
    #[serde(default)]
    restored_at: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Ruleset {
    #[serde(default)]
    rules: Vec<Rule>,
    name: Option<String>,
    target: Option<String>,
    enforcement: Option<String>,
    conditions: Option<serde_json::Value>,
    bypass_actors: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize, Clone)]
struct Rule {
    #[serde(rename = "type")]
    kind: String,
    #[serde(default)]
    parameters: Option<serde_json::Value>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let raw = std::fs::read_to_string(&cli.data)
        .with_context(|| format!("reading {}", cli.data.display()))?;
    let data: DataFile = serde_json::from_str(&raw).context("parsing billing-blocked-rules.json")?;

    let mut total_added = 0usize;
    let mut total_skipped = 0usize;

    for entry in &data.entries {
        if let Some(ref filter) = cli.repo {
            if filter != &entry.repo {
                continue;
            }
        }
        if entry.restored_at.is_some() {
            println!(
                "skip {}/{} (already restored {})",
                entry.repo,
                entry.ruleset_id,
                entry.restored_at.as_deref().unwrap_or("?")
            );
            total_skipped += entry.dropped_rules.len();
            continue;
        }

        let current = fetch_ruleset(&cli.owner, &entry.repo, entry.ruleset_id)
            .with_context(|| format!("fetching {}/{}", entry.repo, entry.ruleset_id))?;
        let present: std::collections::HashSet<&str> =
            current.rules.iter().map(|r| r.kind.as_str()).collect();

        let missing: Vec<&String> = entry
            .dropped_rules
            .iter()
            .filter(|r| !present.contains(r.as_str()))
            .collect();

        if missing.is_empty() {
            println!(
                "ok   {}/{} — all {} rules already present",
                entry.repo,
                entry.ruleset_id,
                entry.dropped_rules.len()
            );
            continue;
        }

        println!(
            "add  {}/{} — {} missing rule(s): {:?}",
            entry.repo,
            entry.ruleset_id,
            missing.len(),
            missing
        );

        if cli.dry_run {
            total_skipped += missing.len();
            continue;
        }

        let new_rules: Vec<serde_json::Value> = current
            .rules
            .iter()
            .map(rule_to_json)
            .chain(missing.iter().map(|name| {
                serde_json::json!({
                    "type": name,
                    "parameters": default_parameters_for(name),
                })
            }))
            .collect();

        let body = serde_json::json!({
            "rules": new_rules,
        });
        update_ruleset(&cli.owner, &entry.repo, entry.ruleset_id, &body)?;
        total_added += missing.len();
    }

    println!(
        "\nsummary: added {} rule(s); skipped {} (already-restored or dry-run)",
        total_added, total_skipped
    );
    Ok(())
}

fn fetch_ruleset(owner: &str, repo: &str, id: u64) -> Result<Ruleset> {
    let path = format!("repos/{owner}/{repo}/rulesets/{id}");
    let out = Command::new("gh")
        .args(["api", "-H", "Accept: application/vnd.github+json", &path])
        .output()
        .context("invoking gh api")?;
    if !out.status.success() {
        return Err(anyhow!(
            "gh api {path} failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    let parsed: Ruleset = serde_json::from_slice(&out.stdout).context("parsing ruleset JSON")?;
    Ok(parsed)
}

fn update_ruleset(owner: &str, repo: &str, id: u64, body: &serde_json::Value) -> Result<()> {
    let path = format!("repos/{owner}/{repo}/rulesets/{id}");
    let body_str = serde_json::to_string(body)?;
    let status = Command::new("gh")
        .args([
            "api",
            "-X",
            "PUT",
            "-H",
            "Accept: application/vnd.github+json",
            "--input",
            "-",
            &path,
        ])
        .stdin(std::process::Stdio::piped())
        .spawn()
        .and_then(|mut child| {
            use std::io::Write;
            if let Some(mut stdin) = child.stdin.take() {
                stdin.write_all(body_str.as_bytes())?;
            }
            child.wait()
        })
        .context("invoking gh api PUT")?;
    if !status.success() {
        return Err(anyhow!("gh api PUT {path} failed (exit {status})"));
    }
    Ok(())
}

fn rule_to_json(r: &Rule) -> serde_json::Value {
    let mut obj = serde_json::Map::new();
    obj.insert("type".into(), serde_json::Value::String(r.kind.clone()));
    if let Some(p) = &r.parameters {
        obj.insert("parameters".into(), p.clone());
    }
    serde_json::Value::Object(obj)
}

/// Conservative default parameter blocks for rule types that require them.
/// Operators should review and tighten these in the GitHub UI after restoration.
fn default_parameters_for(rule: &str) -> serde_json::Value {
    match rule {
        "required_status_checks" => serde_json::json!({
            "required_status_checks": [],
            "strict_required_status_checks_policy": false
        }),
        "code_scanning" => serde_json::json!({
            "code_scanning_tools": []
        }),
        // code_quality, copilot_code_review, required_deployments take no params
        // or use parameter-less defaults; leave empty object.
        _ => serde_json::json!({}),
    }
}
