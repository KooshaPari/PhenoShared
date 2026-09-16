//! `phinbox install` / `phinbox uninstall` subcommand implementations.

use std::path::PathBuf;

/// Install phinbox: copy the binaries to ~/.local/bin (or $PREFIX/bin),
/// register the inbox daemon with the OS launcher, and set up
/// `~/.local/share/phinbox`.
#[derive(Debug, clap::Args, Default)]
pub struct InstallArgs {
    /// Install into this directory instead of ~/.local/bin.
    #[arg(long)]
    pub prefix: Option<PathBuf>,
    /// Skip registering the inbox daemon as a launchd / systemd service.
    #[arg(long)]
    pub no_launch_agent: bool,
    /// Also append the prefix to your shell rc files.
    #[arg(long)]
    pub with_shell_rc: bool,
    /// Print what would happen without writing anything.
    #[arg(long)]
    pub dry_run: bool,
}

/// Remove the binaries and launcher registration installed by `install`.
#[derive(Debug, clap::Args, Default)]
pub struct UninstallArgs {
    /// Prefix to remove from.
    #[arg(long)]
    pub prefix: Option<PathBuf>,
    /// Don't print — just do it.
    #[arg(long, default_value_t = false)]
    pub yes: bool,
}

pub fn cmd_install(args: InstallArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    use phinbox::installer;
    installer::install(&installer::InstallOptions {
        prefix: args.prefix.clone(),
        inbox_dir: inbox_dir.clone(),
        register_launch_agent: !args.no_launch_agent,
        dry_run: args.dry_run,
        update_shell_rc: args.with_shell_rc,
    })
    .map(|report| {
        println!("{}", serde_json::to_string_pretty(&report).unwrap_or_default());
    })
    .map_err(|e| e.clone())
}

pub fn cmd_uninstall(args: UninstallArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    use phinbox::installer;
    installer::uninstall(&installer::UninstallOptions {
        prefix: args.prefix.clone(),
        inbox_dir: inbox_dir.clone(),
        assume_yes: args.yes,
    })
    .map(|report| {
        println!("{}", serde_json::to_string_pretty(&report).unwrap_or_default());
    })
    .map_err(|e| e.clone())
}
