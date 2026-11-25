use anyhow::Result;
use chrono::Utc;
use temporal_grounding::{active_agents_path, AgentEntry};
use uuid::Uuid;

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let id = args
        .next()
        .filter(|value| !value.is_empty())
        .unwrap_or_else(gen_id);
    let label = args.next();

    let entry = AgentEntry {
        id: id.clone(),
        started_at: Utc::now().to_rfc3339(),
        label,
    };

    let path = active_agents_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    let text = if path.exists() {
        std::fs::read_to_string(&path).ok()
    } else {
        None
    };
    let mut entries: Vec<AgentEntry> = text
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_default();
    entries.push(entry);
    std::fs::write(&path, serde_json::to_string_pretty(&entries)?)?;
    println!("{id}");
    Ok(())
}

fn gen_id() -> String {
    format!("agent-{}", Uuid::new_v4())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_id_generates_agent_id() {
        let id = Some(String::new())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(gen_id);
        assert!(id.starts_with("agent-"));
        assert!(id.len() > "agent-".len());
    }

    #[test]
    fn generated_ids_do_not_collide_in_small_sample() {
        let first = gen_id();
        let second = gen_id();
        assert_ne!(first, second);
    }
}
