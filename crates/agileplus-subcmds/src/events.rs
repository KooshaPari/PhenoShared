//! CLI events subcommand for querying the AgilePlus event log.
//!
//! Provides `agileplus events` with filtering and output format options.
//!
//! Traceability: WP14-T088

use std::path::PathBuf;

use chrono::{DateTime, Utc};
use clap::Args;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// CLI argument types
// ---------------------------------------------------------------------------

/// Output format for event listing.
#[derive(Debug, Clone, PartialEq, Eq, clap::ValueEnum, Default)]
pub enum EventOutputFormat {
    #[default]
    Table,
    Json,
    Jsonl,
}

/// Arguments for `agileplus events`.
#[derive(Debug, Args)]
pub struct EventsArgs {
    /// Read events from a Substrate JSONL export instead of the built-in sample stream.
    #[arg(long)]
    pub source: Option<PathBuf>,

    /// Filter events for a specific feature (by slug or id).
    #[arg(long)]
    pub feature: Option<String>,

    /// Show events since a duration or date (e.g. `1h`, `7d`, `2025-03-01`).
    #[arg(long)]
    pub since: Option<String>,

    /// Filter by event type (e.g. `feature_created`, `state_changed`).
    #[arg(long = "type", name = "type")]
    pub event_type: Option<String>,

    /// Filter by actor name (e.g. `spec-kitty`, `sync-oracle`).
    #[arg(long)]
    pub actor: Option<String>,

    /// Filter by entity type (e.g. `feature`, `work-package`).
    #[arg(long)]
    pub entity_type: Option<String>,

    /// Output format.
    #[arg(long, default_value = "table")]
    pub format: EventOutputFormat,

    /// Maximum number of events to return.
    #[arg(long, default_value_t = 50)]
    pub limit: usize,
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A single event record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventRecord {
    pub id: u64,
    pub timestamp: DateTime<Utc>,
    pub source: String,
    pub event_type: String,
    pub entity_type: String,
    pub entity_id: u64,
    pub actor: String,
    pub summary: String,
    pub payload: serde_json::Value,
}

/// Result set from an event query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventQueryResult {
    pub events: Vec<EventRecord>,
    pub total: usize,
}

// ---------------------------------------------------------------------------
// Filtering helpers
// ---------------------------------------------------------------------------

/// Parse a "since" string into an approximate cutoff `DateTime`.
///
/// Supports:
/// - Simple durations: `30m`, `1h`, `2h`, `7d`, `24h`
/// - ISO date strings: `2025-03-01`
pub fn parse_since(since: &str) -> Option<DateTime<Utc>> {
    let now = Utc::now();
    let s = since.trim();
    // Try duration shorthand.
    if let Some(rest) = s.strip_suffix('m') {
        if let Ok(mins) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::minutes(mins));
        }
    }
    if let Some(rest) = s.strip_suffix('h') {
        if let Ok(hours) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::hours(hours));
        }
    }
    if let Some(rest) = s.strip_suffix('d') {
        if let Ok(days) = rest.parse::<i64>() {
            return Some(now - chrono::Duration::days(days));
        }
    }
    // Try ISO date.
    if let Ok(dt) = chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d") {
        return Some(DateTime::<Utc>::from_naive_utc_and_offset(
            dt.and_hms_opt(0, 0, 0).unwrap(),
            Utc,
        ));
    }
    None
}

/// Apply `EventsArgs` filters to a list of events.
pub fn filter_events(events: &[EventRecord], args: &EventsArgs) -> Vec<EventRecord> {
    let cutoff = args.since.as_deref().and_then(parse_since);
    events
        .iter()
        .filter(|e| {
            if let Some(ref cutoff_dt) = cutoff {
                if e.timestamp < *cutoff_dt {
                    return false;
                }
            }
            if let Some(ref et) = args.event_type {
                if &e.event_type != et {
                    return false;
                }
            }
            if let Some(ref actor) = args.actor {
                if &e.actor != actor {
                    return false;
                }
            }
            if let Some(ref ent) = args.entity_type {
                if &e.entity_type != ent {
                    return false;
                }
            }
            if let Some(ref feat) = args.feature {
                // Match entity_type == "feature" and entity_id or summary containing slug.
                if e.entity_type != "feature" {
                    return false;
                }
                if !e.summary.to_lowercase().contains(&feat.to_lowercase())
                    && e.entity_id.to_string() != *feat
                {
                    return false;
                }
            }
            true
        })
        .take(args.limit)
        .cloned()
        .collect()
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

/// Render events as a human-readable table.
pub fn render_table(events: &[EventRecord]) -> String {
    if events.is_empty() {
        return "No events found.\n".to_string();
    }
    let mut out = format!(
        "{:<21} | {:<17} | {:<18} | {:<11} | {}\n",
        "Time", "Entity", "Type", "Actor", "Summary"
    );
    out.push_str(&"─".repeat(89));
    out.push('\n');
    for e in events {
        let ts = e.timestamp.format("%Y-%m-%d %H:%M:%S").to_string();
        let entity = format!("{}: {}", capitalise(&e.entity_type), e.entity_id);
        out.push_str(&format!(
            "{:<21} | {:<17} | {:<18} | {:<11} | {}\n",
            ts, entity, e.event_type, e.actor, e.summary,
        ));
    }
    out
}

fn capitalise(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
    }
}

/// Render events as a JSON array string.
pub fn render_json(events: &[EventRecord]) -> anyhow::Result<String> {
    Ok(serde_json::to_string_pretty(events)?)
}

/// Render events as newline-delimited JSON (one object per line).
pub fn render_jsonl(events: &[EventRecord]) -> anyhow::Result<String> {
    let mut out = String::new();
    for e in events {
        out.push_str(&serde_json::to_string(e)?);
        out.push('\n');
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

/// Run the `events` command.
///
/// In production this would query an agileplus-store or agileplus-events crate.
/// Here we use a stub that returns an empty result set, demonstrating the full
/// filter + render pipeline.
pub fn run_events(args: EventsArgs) -> anyhow::Result<()> {
    let all_events = load_events(&args)?;
    let filtered = filter_events(&all_events, &args);
    let result = EventQueryResult {
        total: filtered.len(),
        events: filtered.clone(),
    };

    let output = match args.format {
        EventOutputFormat::Table => render_table(&result.events),
        EventOutputFormat::Json => render_json(&result.events)?,
        EventOutputFormat::Jsonl => render_jsonl(&result.events)?,
    };
    print!("{output}");
    Ok(())
}

fn load_events(args: &EventsArgs) -> anyhow::Result<Vec<EventRecord>> {
    match args.source.as_ref() {
        Some(path) => load_substrate_jsonl(path),
        None => Ok(load_events_stub()),
    }
}

#[derive(Debug, Deserialize)]
struct SubstrateJsonlRecord {
    timestamp_ms: i64,
    #[serde(default)]
    run_id: Option<String>,
    #[serde(default)]
    agent: Option<String>,
    kind: String,
    #[serde(default)]
    summary: Option<String>,
    #[serde(default)]
    progress: Option<f64>,
    #[serde(flatten)]
    extra: serde_json::Map<String, serde_json::Value>,
}

fn load_substrate_jsonl(path: &std::path::Path) -> anyhow::Result<Vec<EventRecord>> {
    let content = std::fs::read_to_string(path)?;
    let mut events = Vec::new();
    for (idx, line) in content.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let parsed: SubstrateJsonlRecord = serde_json::from_str(trimmed)
            .map_err(|err| anyhow::anyhow!("parsing {} line {}: {err}", path.display(), idx + 1))?;
        let timestamp = chrono::DateTime::<Utc>::from_timestamp_millis(parsed.timestamp_ms)
            .ok_or_else(|| {
                anyhow::anyhow!(
                    "invalid timestamp_ms at {} line {}",
                    path.display(),
                    idx + 1
                )
            })?;

        let mut payload = serde_json::Map::new();
        if let Some(run_id) = &parsed.run_id {
            payload.insert(
                "run_id".to_string(),
                serde_json::Value::String(run_id.clone()),
            );
        }
        if let Some(agent) = &parsed.agent {
            payload.insert(
                "agent".to_string(),
                serde_json::Value::String(agent.clone()),
            );
        }
        if let Some(progress) = parsed.progress {
            payload.insert("progress".to_string(), serde_json::json!(progress));
        }
        payload.extend(parsed.extra);

        events.push(EventRecord {
            id: (idx + 1) as u64,
            timestamp,
            source: "substrate".to_string(),
            event_type: parsed.kind,
            entity_type: "run".to_string(),
            entity_id: parsed.run_id.as_deref().map(stable_entity_id).unwrap_or(0),
            actor: parsed.agent.unwrap_or_else(|| "substrate".to_string()),
            summary: parsed.summary.unwrap_or_default(),
            payload: serde_json::Value::Object(payload),
        });
    }
    Ok(events)
}

fn stable_entity_id(value: &str) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    value.hash(&mut hasher);
    hasher.finish()
}

/// Stub event loader — returns a small canned dataset for tests and demos.
fn load_events_stub() -> Vec<EventRecord> {
    use chrono::TimeZone;
    vec![
        EventRecord {
            id: 1234,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 45, 30).unwrap(),
            source: "agileplus".to_string(),
            event_type: "feature_created".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 5,
            actor: "spec-kitty".to_string(),
            summary: "Auth Flow created".to_string(),
            payload: serde_json::json!({"title": "Auth Flow", "state": "created"}),
        },
        EventRecord {
            id: 1233,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 44, 15).unwrap(),
            source: "agileplus".to_string(),
            event_type: "state_changed".to_string(),
            entity_type: "work-package".to_string(),
            entity_id: 8,
            actor: "sync-oracle".to_string(),
            summary: "database-schema: specified → implementing".to_string(),
            payload: serde_json::json!({"from": "specified", "to": "implementing"}),
        },
        EventRecord {
            id: 1232,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 43, 0).unwrap(),
            source: "agileplus".to_string(),
            event_type: "sync_conflict".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 5,
            actor: "platform".to_string(),
            summary: "Conflict detected (resolved: LocalWins)".to_string(),
            payload: serde_json::json!({"resolution": "LocalWins"}),
        },
        EventRecord {
            id: 1231,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 30, 0).unwrap(),
            source: "agileplus".to_string(),
            event_type: "updated".to_string(),
            entity_type: "work-package".to_string(),
            entity_id: 7,
            actor: "user".to_string(),
            summary: "api-endpoints: description updated".to_string(),
            payload: serde_json::json!({}),
        },
        EventRecord {
            id: 1230,
            timestamp: Utc.with_ymd_and_hms(2026, 3, 2, 12, 20, 45).unwrap(),
            source: "agileplus".to_string(),
            event_type: "state_changed".to_string(),
            entity_type: "feature".to_string(),
            entity_id: 3,
            actor: "system".to_string(),
            summary: "api-design: researched → specified".to_string(),
            payload: serde_json::json!({"from": "researched", "to": "specified"}),
        },
    ]
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests;
