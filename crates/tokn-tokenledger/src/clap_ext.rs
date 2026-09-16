//! Simple clap extensions for common CLI patterns.
//! This is a minimal local implementation until the phenotype-cli clap_ext crate is published.

use clap::Args;
use std::path::PathBuf;

/// Provides verbosity control via -v/--verbose and -q/--quiet flags.
#[derive(Args, Debug, Clone)]
pub struct Verbosity {
    /// Increase verbosity level (-v, -vv, -vvv, etc.)
    #[arg(short, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,

    /// Decrease verbosity level (-q for quiet)
    #[arg(short, action = clap::ArgAction::Count, global = true)]
    pub quiet: u8,
}

impl Verbosity {
    /// Convert to a tracing-subscriber filter level string.
    /// Default is "info", -v -> "debug", -vv -> "trace", -q -> "warn", -qq -> "error"
    pub fn to_filter(&self) -> &'static str {
        match self.verbose.saturating_sub(self.quiet) {
            0 => "info",
            1 => "debug",
            2.. => "trace",
        }
    }
}

/// Configuration file argument override.
#[derive(Args, Debug, Clone)]
pub struct ConfigArg {
    /// Optional config file path (overrides PHENOTYPE_CONFIG env var)
    #[arg(long, global = true)]
    pub config: Option<PathBuf>,
}

pub mod prelude {
    pub use super::{ConfigArg, Verbosity, setup_tracing};
}

/// Initialize tracing with the given filter level string.
pub fn setup_tracing(filter_level: &str) {
    use tracing_subscriber::EnvFilter;
    use tracing_subscriber::fmt;

    let env_filter = EnvFilter::try_from_default_env()
        .or_else(|_| EnvFilter::try_new(filter_level))
        .unwrap_or_else(|_| EnvFilter::new("info"));

    fmt()
        .with_env_filter(env_filter)
        .with_writer(std::io::stderr)
        .init();
}
