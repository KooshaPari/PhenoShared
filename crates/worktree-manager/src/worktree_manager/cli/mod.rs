//! CLI module for worktree-manager

use clap::{Parser, Subcommand};
use clap_ext::prelude::Verbosity;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "wtm")]
#[command(about = "Git worktree automation and management", long_about = None)]
pub struct Cli {
    /// Repository path (defaults to current directory)
    #[arg(short, long)]
    pub repo: Option<PathBuf>,

    /// Verbosity (use -v, -vv, -vvv for more, -q to silence)
    #[command(flatten)]
    pub verbosity: Verbosity,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// List all worktrees
    List {
        /// Show JSON output
        #[arg(long)]
        json: bool,
    },

    /// Create a new worktree
    Create {
        /// Branch name
        #[arg(short, long)]
        branch: String,

        /// Worktree path
        #[arg(short, long)]
        path: PathBuf,

        /// Starting point (commit/branch)
        #[arg(short, long)]
        start_point: Option<String>,
    },

    /// Remove a worktree
    Remove {
        /// Worktree path
        path: PathBuf,

        /// Force removal
        #[arg(short, long)]
        force: bool,
    },

    /// Lock a worktree
    Lock {
        /// Worktree path
        path: PathBuf,

        /// Lock reason
        #[arg(short, long)]
        reason: String,
    },

    /// Unlock a worktree
    Unlock {
        /// Worktree path
        path: PathBuf,
    },

    /// Clean up stale worktrees
    Cleanup {
        /// Remove unmerged changes
        #[arg(long)]
        remove_unmerged: bool,

        /// Remove stale worktrees
        #[arg(long)]
        remove_stale: bool,

        /// Remove worktrees on deleted branches
        #[arg(long)]
        remove_deleted: bool,

        /// Dry run (don't actually remove)
        #[arg(long)]
        dry_run: bool,
    },

    /// Prune worktree references
    Prune,

    /// Show current branch
    Branch,
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    /// Smoke test: ensure the Cli struct with the clap_ext::Verbosity flatten
    /// parses cleanly (this would fail to compile if the types mismatch).
    #[test]
    fn cli_parses_with_verbosity() {
        let cli = Cli::try_parse_from(["wtm", "--quiet", "branch"]).unwrap();
        assert!(cli.verbosity.quiet);
        assert!(matches!(cli.command, Commands::Branch));
    }

    /// Verbosity::to_filter() should map --quiet to LevelFilter::ERROR
    /// and -v to LevelFilter::DEBUG.
    #[test]
    fn verbosity_filter_mapping() {
        let quiet = Verbosity {
            verbose: 0,
            quiet: true,
        };
        assert_eq!(
            quiet.to_filter(),
            tracing_subscriber::filter::LevelFilter::ERROR
        );

        let verbose = Verbosity {
            verbose: 1,
            quiet: false,
        };
        assert_eq!(
            verbose.to_filter(),
            tracing_subscriber::filter::LevelFilter::DEBUG
        );
    }
}
