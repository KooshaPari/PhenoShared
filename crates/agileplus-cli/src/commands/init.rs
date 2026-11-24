//! `agileplus init` command implementation.
//!
//! Creates the docs-native AgilePlus project layout and local config.
//! Traceability: AGP-REQ(FR-INIT-DOCS-NATIVE)

use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::ValueEnum;

#[derive(Debug, clap::Args)]
pub struct InitArgs {
    /// Project artifact layout to initialize.
    #[arg(long, value_enum, default_value_t = InitLayout::DocsNative)]
    pub layout: InitLayout,

    /// Include local traceability hook template.
    #[arg(long)]
    pub with_hooks: bool,

    /// Mark Substrate integration as enabled in config.
    #[arg(long)]
    pub with_substrate: bool,

    /// Mark Tracaera export integration as enabled in config.
    #[arg(long)]
    pub with_tracaera: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum InitLayout {
    DocsNative,
}

pub async fn run_init(args: InitArgs) -> Result<()> {
    match args.layout {
        InitLayout::DocsNative => init_docs_native(args),
    }
}

fn init_docs_native(args: InitArgs) -> Result<()> {
    let dirs = [
        "docs/specs",
        "docs/designs",
        "docs/adr",
        "docs/plans",
        "docs/research",
        "docs/audits",
        "docs/reports",
        "docs/retros",
        "docs/traces",
        "docs/sessions",
        ".agileplus/cache",
        ".agileplus/exports",
    ];
    for dir in dirs {
        std::fs::create_dir_all(dir).with_context(|| format!("creating {dir}"))?;
    }

    if args.with_hooks {
        std::fs::create_dir_all(".agileplus/hooks").context("creating .agileplus/hooks")?;
    }

    let config_path = PathBuf::from(".agileplus").join("config.toml");
    let config = docs_native_config(args.with_hooks, args.with_substrate, args.with_tracaera);
    std::fs::write(&config_path, config)
        .with_context(|| format!("writing {}", config_path.display()))?;

    println!("AgilePlus docs-native layout initialized.");
    println!("  Config: {}", config_path.display());
    println!("  Artifact root: docs");
    println!("  Machine state: .agileplus/agileplus.db");
    Ok(())
}

fn docs_native_config(with_hooks: bool, with_substrate: bool, with_tracaera: bool) -> String {
    format!(
        r#"artifact_root = "docs"
spec_root = "docs/specs"
adr_root = "docs/adr"
machine_state = ".agileplus/agileplus.db"

[integrations]
hooks = {}
substrate = {}
tracaera = {}
"#,
        with_hooks, with_substrate, with_tracaera
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn docs_native_config_contains_wp02_defaults() {
        let config = docs_native_config(true, true, true);

        assert!(config.contains(r#"artifact_root = "docs""#));
        assert!(config.contains(r#"spec_root = "docs/specs""#));
        assert!(config.contains(r#"adr_root = "docs/adr""#));
        assert!(config.contains(r#"machine_state = ".agileplus/agileplus.db""#));
        assert!(config.contains("hooks = true"));
        assert!(config.contains("substrate = true"));
        assert!(config.contains("tracaera = true"));
    }
}
