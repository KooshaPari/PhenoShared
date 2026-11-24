//! `agileplus mcp` command implementation.
//!
//! Generates host-specific MCP server configuration for AgilePlus.
//! Traceability: AGP-REQ(FR-MCP-INSTALL)

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use clap::{Subcommand, ValueEnum};
use serde_json::json;

#[derive(Debug, clap::Args)]
pub struct McpArgs {
    #[command(subcommand)]
    pub command: McpCommand,
}

#[derive(Debug, Subcommand)]
pub enum McpCommand {
    /// Print or write MCP host configuration.
    Install(McpInstallArgs),
}

#[derive(Debug, clap::Args)]
pub struct McpInstallArgs {
    /// Host configuration format to generate.
    #[arg(long, value_enum)]
    pub host: McpHost,

    /// Write config snippet to a file instead of stdout.
    #[arg(long)]
    pub output: Option<PathBuf>,

    /// Override AgilePlus database path embedded in the MCP environment.
    #[arg(long, default_value = ".agileplus/agileplus.db")]
    pub db: PathBuf,

    /// Override repository root used to resolve the Python MCP project.
    #[arg(long)]
    pub repo: Option<PathBuf>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum McpHost {
    Codex,
    GenericJson,
}

pub async fn run_mcp(args: McpArgs) -> Result<()> {
    match args.command {
        McpCommand::Install(args) => run_install(args).await,
    }
}

async fn run_install(args: McpInstallArgs) -> Result<()> {
    let repo_root = match args.repo {
        Some(path) => path,
        None => std::env::current_dir().context("resolving current repository root")?,
    };
    let config = mcp_install_config(args.host, &repo_root, &args.db);

    if let Some(output_path) = args.output {
        if let Some(parent) = output_path.parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)
                    .with_context(|| format!("creating directory {}", parent.display()))?;
            }
        }
        std::fs::write(&output_path, config)
            .with_context(|| format!("writing MCP config to {}", output_path.display()))?;
        println!("MCP config written to: {}", output_path.display());
    } else {
        println!("{config}");
    }

    Ok(())
}

fn mcp_install_config(host: McpHost, repo_root: &Path, db_path: &Path) -> String {
    let repo_root = absolute_path(repo_root);
    let python_project = repo_root.join("python");
    let db_path = if db_path.is_absolute() {
        db_path.to_path_buf()
    } else {
        repo_root.join(db_path)
    };

    match host {
        McpHost::Codex => codex_toml_config(&python_project, &db_path),
        McpHost::GenericJson => generic_json_config(&python_project, &db_path),
    }
}

fn codex_toml_config(python_project: &Path, db_path: &Path) -> String {
    format!(
        r#"[mcp_servers.agileplus]
command = "uv"
args = ["run", "--project", "{}", "agileplus-mcp"]

[mcp_servers.agileplus.env]
AGILEPLUS_MCP_BACKEND = "sqlite"
AGILEPLUS_DB = "{}"
"#,
        escape_toml(python_project),
        escape_toml(db_path),
    )
}

fn generic_json_config(python_project: &Path, db_path: &Path) -> String {
    serde_json::to_string_pretty(&json!({
        "mcpServers": {
            "agileplus": {
                "command": "uv",
                "args": ["run", "--project", python_project, "agileplus-mcp"],
                "transport": "stdio",
                "env": {
                    "AGILEPLUS_MCP_BACKEND": "sqlite",
                    "AGILEPLUS_DB": db_path,
                }
            }
        }
    }))
    .expect("static MCP JSON config serializes")
}

fn absolute_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("."))
            .join(path)
    }
}

fn escape_toml(path: &Path) -> String {
    path.to_string_lossy()
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn codex_install_config_uses_codex_mcp_servers_toml_shape() {
        let config = mcp_install_config(
            McpHost::Codex,
            Path::new("/repo"),
            Path::new(".agileplus/agileplus.db"),
        );

        assert!(config.contains("[mcp_servers.agileplus]"));
        assert!(config.contains(r#"command = "uv""#));
        assert!(config.contains(r#""/repo/python""#));
        assert!(config.contains(r#"AGILEPLUS_MCP_BACKEND = "sqlite""#));
        assert!(config.contains(r#"AGILEPLUS_DB = "/repo/.agileplus/agileplus.db""#));
    }

    #[test]
    fn generic_install_config_uses_mcp_servers_json_shape() {
        let config = mcp_install_config(
            McpHost::GenericJson,
            Path::new("/repo"),
            Path::new("/tmp/agileplus.db"),
        );
        let parsed: serde_json::Value = serde_json::from_str(&config).unwrap();

        assert_eq!(parsed["mcpServers"]["agileplus"]["command"], "uv");
        assert_eq!(
            parsed["mcpServers"]["agileplus"]["env"]["AGILEPLUS_DB"],
            "/tmp/agileplus.db"
        );
    }
}
