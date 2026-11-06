//! Shared subcommand structs that 60+ CLIs re-implement.

use clap::{Args, Subcommand};
use std::path::PathBuf;

/// `init` subcommand: scaffold a new project.
#[derive(Debug, Args)]
pub struct InitCmd {
    /// Path to initialize (defaults to cwd)
    #[arg(default_value = ".")]
    pub path: PathBuf,

    /// Force overwrite if path exists
    #[arg(short, long)]
    pub force: bool,

    /// Template to use (defaults to "default")
    #[arg(short, long, default_value = "default")]
    pub template: String,
}

/// `validate` subcommand: check a config or project file.
#[derive(Debug, Args)]
pub struct ValidateCmd {
    /// Path to validate
    pub path: PathBuf,

    /// Strict mode: warnings are errors
    #[arg(long)]
    pub strict: bool,
}

/// `version` subcommand: print version + build info.
#[derive(Debug, Args)]
pub struct VersionCmd {}

/// Helper: register all 3 common subcommands on a `clap::Command`.
///
/// This is a convenience for CLIs that build their `clap::Command`
/// imperatively (not via `#[derive(Subcommand)]`). For derived
/// subcommands, use `common_subcommands::InitCmd` etc. as variants.
pub fn add_common_subcommands(cmd: clap::Command) -> clap::Command {
    cmd.subcommand(
        clap::Command::new("init")
            .about("Initialize a new project")
            .arg(
                clap::arg!([path] "Path to initialize")
                    .default_value("."),
            )
            .arg(clap::arg!(-f --force "Force overwrite"))
            .arg(
                clap::arg!(-t --template <TEMPLATE> "Template to use")
                    .default_value("default"),
            ),
    )
    .subcommand(
        clap::Command::new("validate")
            .about("Validate a config or project")
            .arg(clap::arg!([path] "Path to validate"))
            .arg(clap::arg!(--strict "Strict mode: warnings are errors")),
    )
    .subcommand(
        clap::Command::new("version").about("Print version + build info"),
    )
}

/// Trait alias: CLIs with common subcommands can implement this to
/// get a uniform match arm signature.
pub trait CommonSubcommand {}
impl CommonSubcommand for InitCmd {}
impl CommonSubcommand for ValidateCmd {}
impl CommonSubcommand for VersionCmd {}

/// Convenience subcommand enum that bundles all 3 common subcommands
/// plus a free-form `Other` variant for app-specific commands.
///
/// Use this when a CLI has no app-specific subcommands and just wants
/// the 3 common ones uniformly.
#[derive(Debug, Subcommand)]
pub enum CommonCommands {
    /// Initialize a new project
    Init(InitCmd),
    /// Validate a config or project
    Validate(ValidateCmd),
    /// Print version + build info
    Version(VersionCmd),
}
