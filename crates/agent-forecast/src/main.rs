use anyhow::Result;
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

const CATEGORIES: &[&str] = &[
    "sweep",
    "audit",
    "refactor",
    "dependabot",
    "scaffold",
    "extract",
    "merge",
    "docs",
    "test",
    "eval",
    "fork",
    "cleanup",
];

#[derive(Parser)]
#[command(
    name = "agent-forecast",
    about = "Forecast token budgets per agent category",
    arg_required_else_help = true
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
    /// Path to agent history JSONL (default: ~/.claude/agent-history.jsonl)
    #[arg(long, global = true)]
    history: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Command {
    /// Classify a prompt to one of the 12 categories by keyword matching
    Categorize { prompt: String },
    /// Print p50/p90 token forecast for a category
    Budget { category: String },
}

#[derive(Deserialize)]
struct HistoryEntry {
    prompt_hash_category: String,
    total_tokens: u64,
}

#[derive(Serialize)]
struct Forecast {
    category: String,
    p50_tokens: u64,
    p90_tokens: u64,
    sample_count: usize,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let history_path = cli.history.unwrap_or_else(|| {
        std::env::var_os("HOME")
            .or_else(|| std::env::var_os("USERPROFILE"))
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".claude")
            .join("agent-history.jsonl")
    });

    match cli.command {
        Command::Categorize { prompt } => println!("{}", categorize(&prompt)),
        Command::Budget { category } => {
            let tokens = load_history(&history_path, &category)?;
            let f = compute_forecast(&category, &tokens);
            println!("{}", serde_json::to_string_pretty(&f)?);
        }
    }
    Ok(())
}

fn categorize(prompt: &str) -> &'static str {
    let lower = prompt.to_lowercase();
    for &cat in CATEGORIES {
        if lower.contains(cat) {
            return cat;
        }
    }
    // keyword heuristics for prompts that don't mention the category literally
    if lower.contains("depend") || lower.contains("bump") || lower.contains("upgrade") {
        return "dependabot";
    }
    if lower.contains("rename") || lower.contains("restructure") || lower.contains("reorganize") {
        return "refactor";
    }
    if lower.contains("spec") || lower.contains("assert") || lower.contains("coverage") {
        return "test";
    }
    if lower.contains("readme") || lower.contains("comment") || lower.contains("document") {
        return "docs";
    }
    "sweep"
}

fn load_history(path: &Path, category: &str) -> Result<Vec<u64>> {
    if !path.exists() {
        return Ok(vec![]);
    }
    let text = std::fs::read_to_string(path)?;
    let tokens = text
        .lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|l| serde_json::from_str::<HistoryEntry>(l).ok())
        .filter(|e| e.prompt_hash_category.contains(category))
        .map(|e| e.total_tokens)
        .collect();
    Ok(tokens)
}

fn compute_forecast(category: &str, tokens: &[u64]) -> Forecast {
    if tokens.is_empty() {
        return Forecast {
            category: category.to_string(),
            p50_tokens: 0,
            p90_tokens: 0,
            sample_count: 0,
        };
    }
    let mut sorted = tokens.to_vec();
    sorted.sort_unstable();
    Forecast {
        category: category.to_string(),
        p50_tokens: percentile(&sorted, 50),
        p90_tokens: percentile(&sorted, 90),
        sample_count: tokens.len(),
    }
}

fn percentile(sorted: &[u64], pct: usize) -> u64 {
    let rank = (sorted.len() * pct).div_ceil(100);
    sorted[rank.saturating_sub(1).min(sorted.len() - 1)]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn categorize_exact_match() {
        assert_eq!(categorize("sweep the codebase for dead code"), "sweep");
        assert_eq!(categorize("run test suite"), "test");
    }

    #[test]
    fn categorize_heuristic() {
        assert_eq!(
            categorize("upgrade all packages to new versions"),
            "dependabot"
        );
        assert_eq!(categorize("update readme with new examples"), "docs");
    }

    #[test]
    fn forecast_empty_history() {
        let f = compute_forecast("sweep", &[]);
        assert_eq!(f.p50_tokens, 0);
        assert_eq!(f.sample_count, 0);
    }

    #[test]
    fn percentile_basic() {
        let data = vec![100u64, 200, 300, 400, 500];
        assert_eq!(percentile(&data, 50), 300);
        assert_eq!(percentile(&data, 90), 500);
    }

    #[test]
    fn percentile_uses_nearest_rank_without_one_based_offset() {
        let data = vec![10u64, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        assert_eq!(percentile(&data, 50), 50);
        assert_eq!(percentile(&data, 90), 90);
    }
}
