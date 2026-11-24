//! Shared arg structs that 60+ CLIs re-implement.

use clap::{Args, ValueEnum};
use std::path::PathBuf;

/// `-c, --config <path>` arg, used by all 60+ CLIs.
#[derive(Debug, Args, Clone)]
pub struct ConfigArg {
    /// Path to the config file (YAML/TOML/JSON)
    #[arg(short, long, env = "PHENOTYPE_CONFIG")]
    pub config: Option<PathBuf>,
}

/// `-v, --verbose` and `-q, --quiet` flags, mutually exclusive.
///
/// Use as `#[command(flatten)] verbosity: Verbosity` on the top-level CLI struct.
#[derive(Debug, Args, Clone, Copy, Default)]
#[group(multiple = false)]
pub struct Verbosity {
    /// Increase log verbosity (-v, -vv, -vvv)
    #[arg(short, long, action = clap::ArgAction::Count)]
    pub verbose: u8,

    /// Suppress non-error output
    #[arg(short, long)]
    pub quiet: bool,
}

impl Verbosity {
    /// Convert to a tracing-subscriber EnvFilter directive.
    ///
    /// - `--quiet`         → ERROR
    /// - (default)         → INFO
    /// - `-v`              → DEBUG
    /// - `-vv` (or more)   → TRACE
    pub fn to_filter(&self) -> tracing_subscriber::filter::LevelFilter {
        match (self.verbose, self.quiet) {
            (_, true) => tracing_subscriber::filter::LevelFilter::ERROR,
            (0, false) => tracing_subscriber::filter::LevelFilter::INFO,
            (1, false) => tracing_subscriber::filter::LevelFilter::DEBUG,
            _ => tracing_subscriber::filter::LevelFilter::TRACE,
        }
    }
}

/// Output format flag: human, json, yaml.
#[derive(Debug, Clone, Copy, ValueEnum, Default, PartialEq, Eq)]
pub enum OutputFormat {
    #[default]
    Human,
    Json,
    Yaml,
}

impl std::fmt::Display for OutputFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OutputFormat::Human => write!(f, "human"),
            OutputFormat::Json => write!(f, "json"),
            OutputFormat::Yaml => write!(f, "yaml"),
        }
    }
}
