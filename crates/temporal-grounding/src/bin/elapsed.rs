use anyhow::{bail, Result};
use chrono::{DateTime, Utc};
use temporal_grounding::{active_agents_path, AgentEntry};

fn main() -> Result<()> {
    let id = std::env::args().nth(1).unwrap_or_default();
    let path = active_agents_path();
    if !path.exists() {
        bail!("~/.claude/active-agents.json not found");
    }
    let text = std::fs::read_to_string(&path)?;
    let entries: Vec<AgentEntry> = serde_json::from_str(&text)?;
    match entries.iter().find(|e| e.id == id) {
        None => bail!("agent id '{id}' not found"),
        Some(e) => {
            let started: DateTime<Utc> = e.started_at.parse()?;
            let elapsed = Utc::now() - started;
            println!("{}s", elapsed.num_seconds());
        }
    }
    Ok(())
}
