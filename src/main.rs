//! pheno-agents-md CLI: render an AGENTS.md and write to a path.

use anyhow::Result;
use clap::Parser;
use pheno_agents_md::{load_config, write_agents_md};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "pheno-agents-md", version, about = "Generate AGENTS.md (agent constitution)")]
struct Args {
    /// Path to write AGENTS.md (defaults to ./AGENTS.md)
    #[arg(long, default_value = "AGENTS.md")]
    out: PathBuf,

    /// Path to config YAML (defaults to ./pheno-agents-md.yaml)
    #[arg(long, default_value = "pheno-agents-md.yaml")]
    config: PathBuf,

    /// Repo name (defaults to the current directory name)
    #[arg(long)]
    repo: Option<String>,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let cfg = load_config(&args.config)?;
    let cwd = std::env::current_dir()?;
    let repo_name = args
        .repo
        .or_else(|| {
            cfg.repo_name
                .clone()
                .or_else(|| cwd.file_name().and_then(|n| n.to_str().map(String::from)))
        })
        .unwrap_or_else(|| "repo".into());
    write_agents_md(&cfg, &repo_name, &args.out)?;
    println!("Wrote {}", args.out.display());
    Ok(())
}
