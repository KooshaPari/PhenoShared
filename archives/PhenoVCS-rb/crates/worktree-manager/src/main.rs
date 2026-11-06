//! worktree-manager CLI entry point

use clap::Parser;
use phenovcs_observability::{self, SERVICE_NAME};

use tracing::{error, info, warn};

use worktree_manager::{
    application::WorktreeService,
    cli::{Cli, Commands},
    domain::BranchName,
    infrastructure::GitWorktreeAdapter,
};

fn main() -> anyhow::Result<()> {
    let otlp_endpoint = phenovcs_observability::otlp_endpoint();
    let mut attrs = std::collections::HashMap::new();
    attrs.insert("service".to_string(), SERVICE_NAME.to_string());
    attrs.insert("otlp_endpoint".to_string(), otlp_endpoint.clone());
    // Emit the OTLP span synchronously via a one-shot tokio runtime.
    // This avoids blocking startup while still producing a span before any
    // user-visible work happens.
    let rt = tokio::runtime::Runtime::new().expect("tokio runtime");
    rt.block_on(phenovcs_observability::emit_span("phenovcs.start", attrs));
    tracing::info!(service = SERVICE_NAME, otlp_endpoint = %otlp_endpoint, "phenovcs starting");

    let cli = Cli::parse();
    // Use clap-ext's tracing setup. Returns anyhow::Result because the
    // worktree-manager domain errors (WorktreeError) are not part of
    // clap_ext's CliError enum and forcing a hand-rolled From impl would
    // leak domain types into the shared library.
    clap_ext::prelude::setup_tracing(cli.verbosity.to_filter());

    // Determine repo path
    let repo_path = cli.repo.map(Ok).unwrap_or_else(std::env::current_dir)?;

    // Create adapter and service
    let adapter = GitWorktreeAdapter::new();
    let service = WorktreeService::new(adapter.clone(), adapter);

    match cli.command {
        Commands::List { json } => {
            let listing = service.list_worktrees(&repo_path)?;
            info!(worktree_count = listing.total_count, "Listed worktrees");

            if json {
                println!("{}", serde_json::to_string_pretty(&listing)?);
            } else {
                println!("Main: {}", listing.main.path.display());
                println!("Worktrees ({}):", listing.worktrees.len());
                for wt in &listing.worktrees {
                    let status = if wt.locked { "🔒" } else { "   " };
                    println!(
                        "  {} {} -> {}",
                        status,
                        wt.branch.as_str(),
                        wt.path.display()
                    );
                }
            }
        }

        Commands::Create {
            branch,
            path,
            start_point,
        } => {
            let branch_name = BranchName::new(branch);
            let result =
                service.create_worktree(&repo_path, branch_name, &path, start_point.as_deref());

            if result.success {
                if let Some(worktree) = result.worktree {
                    println!("Created worktree: {}", worktree.path.display());
                }
                for warning in result.warnings {
                    warn!("{}", warning);
                    eprintln!("Warning: {}", warning);
                }
            } else {
                let error_msg = result.error.as_deref().unwrap_or("Unknown error");
                error!("{}", error_msg);
                eprintln!("Failed: {}", error_msg);
                std::process::exit(1);
            }
        }

        Commands::Remove { path, force } => {
            service.remove_worktree(&path, force)?;
            info!("Removed worktree: {}", path.display());
            println!("Removed worktree: {}", path.display());
        }

        Commands::Lock { path, reason } => {
            service.lock_worktree(&path, &reason)?;
            info!("Locked worktree: {}", path.display());
            println!("Locked: {}", path.display());
        }

        Commands::Unlock { path } => {
            service.unlock_worktree(&path)?;
            info!("Unlocked worktree: {}", path.display());
            println!("Unlocked: {}", path.display());
        }

        Commands::Prune => {
            service.prune(&repo_path)?;
            info!("Pruned stale worktrees");
            println!("Pruned stale worktree references");
        }

        Commands::Branch => {
            let branch = service.current_branch(&repo_path)?;
            info!(branch = branch.as_str(), "Queried current branch");
            println!("{}", branch.as_str());
        }

        // Cleanup commands - simplified, just prune for now
        Commands::Cleanup { dry_run, .. } => {
            if dry_run {
                info!("Dry run cleanup - no changes made");
                println!("Dry run - no changes made");
            } else {
                service.prune(&repo_path)?;
                info!("Pruned stale worktrees via cleanup");
                println!("Pruned stale worktree references");
            }
        }
    }

    Ok(())
}
