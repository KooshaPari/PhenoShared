use anyhow::Result;
use clap::Parser;
use std::fs;
use std::path::PathBuf;

use acceptance_contract::{render_markdown, run_acceptance, ExecutionContext};

#[derive(Parser, Debug)]
#[command(name = "acceptance-contract")]
#[command(about = "Run acceptance contract checks")]
struct Cli {
    #[arg(short, long, default_value = "contract.yaml")]
    contract: PathBuf,

    #[arg(short, long, default_value = "acceptance-baselines.json")]
    baseline: PathBuf,

    #[arg(long, default_value = ".")]
    workspace: PathBuf,

    #[arg(long, default_value = "acceptance-scorecard.json")]
    json_output: PathBuf,

    #[arg(long, default_value = "acceptance-scorecard.md")]
    markdown_output: PathBuf,

    #[arg(long)]
    update_baseline: bool,

    #[arg(long)]
    skip_delegation: bool,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let card = run_acceptance(
        &cli.contract,
        &cli.baseline,
        &cli.workspace,
        ExecutionContext {
            skip_delegation: cli.skip_delegation,
            update_baseline: cli.update_baseline,
        },
    )?;

    let json = serde_json::to_string_pretty(&card)?;
    fs::write(&cli.json_output, json)?;
    fs::write(&cli.markdown_output, render_markdown(&card))?;

    println!(
        "hard_passed={} soft={:.2}/{:.2} ({:.1}%)\njson={}\nmarkdown={}",
        card.hard_passed,
        card.total_soft_score,
        card.max_soft_score,
        card.soft_percentage,
        cli.json_output.display(),
        cli.markdown_output.display()
    );

    if !card.hard_passed {
        std::process::exit(1);
    }

    Ok(())
}
