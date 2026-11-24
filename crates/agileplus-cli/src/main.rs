//! AgilePlus CLI entry point.
//!
//! Parses CLI arguments, initialises adapters, and routes to command handlers.
//! Traceability: WP11-T060, T065 / WP12-T072

use std::path::PathBuf;
use std::process;

use agileplus_cli::agent_runtime::ConfiguredAgentAdapter;
use agileplus_cli::commands::branch::BranchArgs;
use agileplus_cli::commands::cycle::CycleArgs;
use agileplus_cli::commands::hooks::HooksArgs;
use agileplus_cli::commands::implement::ImplementArgs;
use agileplus_cli::commands::init::InitArgs;
use agileplus_cli::commands::mcp::McpArgs;
use agileplus_cli::commands::migrate_artifacts::MigrateArtifactsArgs;
use agileplus_cli::commands::module::ModuleArgs;
use agileplus_cli::commands::plan::PlanArgs;
use agileplus_cli::commands::queue::QueueArgs;
use agileplus_cli::commands::research::ResearchArgs;
use agileplus_cli::commands::retrospective::RetrospectiveArgs;
use agileplus_cli::commands::ship::ShipArgs;
use agileplus_cli::commands::specify::SpecifyArgs;
use agileplus_cli::commands::tracaera::TracaeraArgs;
use agileplus_cli::commands::triage::TriageArgs;
use agileplus_cli::commands::validate::ValidateArgs;
use agileplus_git::GitVcsAdapter;
use agileplus_sqlite::SqliteStorageAdapter;
use agileplus_subcmds::{
    run_dashboard, run_events, run_platform, DashboardArgs, EventsArgs, PlatformArgs,
};
use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

/// Spec-driven development engine.
#[derive(Parser)]
#[command(name = "agileplus", version, about = "Spec-driven development engine")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Increase verbosity (-v, -vv, -vvv)
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    verbose: u8,

    /// Path to SQLite database
    #[arg(long, global = true, default_value = ".agileplus/agileplus.db")]
    db: PathBuf,

    /// Path to git repository root (defaults to current directory)
    #[arg(long, global = true)]
    repo: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize AgilePlus project layout and config.
    Init(InitArgs),
    /// Manage cycles (time-boxed delivery units).
    Cycle(CycleArgs),
    /// Branch management: create, checkout, delete, list, and sync.
    Branch(BranchArgs),
    /// Create or revise a feature specification.
    Specify(SpecifyArgs),
    /// Research a feature (pre-specify codebase scan or post-specify feasibility).
    Research(ResearchArgs),
    /// Generate a plan (work packages) for a researched feature.
    Plan(PlanArgs),
    /// Implement work packages for a planned feature.
    Implement(ImplementArgs),
    /// Validate governance compliance for an implementing feature.
    Validate(ValidateArgs),
    /// Ship a validated feature by merging all WP branches.
    Ship(ShipArgs),
    /// Generate a retrospective report for a shipped feature.
    Retrospective(RetrospectiveArgs),
    /// Classify and route incoming items (bug, feature, idea, task).
    Triage(TriageArgs),
    /// Manage the triage backlog queue.
    Queue(QueueArgs),
    /// Manage modules (product-area groupings of features).
    Module(ModuleArgs),
    /// Open or configure the web dashboard.
    Dashboard(DashboardArgs),
    /// Query AgilePlus and Substrate event streams.
    Events(EventsArgs),
    /// Manage platform services (up, down, status, logs).
    Platform(PlatformArgs),
    /// Install, verify, and remove AgilePlus hooks.
    Hooks(HooksArgs),
    /// Generate MCP host configuration.
    Mcp(McpArgs),
    /// Normalize brownfield artifacts into docs-native locations.
    MigrateArtifacts(MigrateArtifactsArgs),
    /// Export trace graph snapshots for Tracaera.
    Tracaera(TracaeraArgs),
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    // Configure logging based on verbosity
    let log_level = match cli.verbose {
        0 => tracing::Level::INFO,
        1 => tracing::Level::DEBUG,
        _ => tracing::Level::TRACE,
    };
    tracing_subscriber::fmt()
        .with_max_level(log_level)
        .with_target(false)
        .compact()
        .init();

    if let Err(e) = run(cli).await {
        eprintln!("Error: {e:#}");
        process::exit(1);
    }
}

async fn run(cli: Cli) -> Result<()> {
    // Triage command doesn't need full storage/VCS setup
    match cli.command {
        Commands::Init(args) => return agileplus_cli::commands::init::run_init(args).await,
        Commands::Triage(args) => return agileplus_cli::commands::triage::run_triage(args).await,
        Commands::Dashboard(args) => return run_dashboard(args),
        Commands::Events(args) => return run_events(args),
        Commands::Platform(args) => return run_platform(args),
        Commands::Mcp(args) => return agileplus_cli::commands::mcp::run_mcp(args).await,
        Commands::MigrateArtifacts(args) => {
            return agileplus_cli::commands::migrate_artifacts::run_migrate_artifacts(args).await;
        }
        _ => {}
    }

    // Module command only needs storage (no VCS)
    if let Commands::Module(args) = cli.command {
        // Initialise storage adapter early for module commands
        if let Some(parent) = cli.db.parent() {
            if !parent.as_os_str().is_empty() && !parent.exists() {
                std::fs::create_dir_all(parent)
                    .with_context(|| format!("creating directory {}", parent.display()))?;
            }
        }
        let storage = SqliteStorageAdapter::new(&cli.db)
            .with_context(|| format!("opening database at {}", cli.db.display()))?;
        return agileplus_cli::commands::module::run(args, &storage).await;
    }

    // Initialise storage adapter (create DB directory if needed)
    if let Some(parent) = cli.db.parent() {
        if !parent.as_os_str().is_empty() && !parent.exists() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating directory {}", parent.display()))?;
        }
    }

    let storage = SqliteStorageAdapter::new(&cli.db)
        .with_context(|| format!("opening database at {}", cli.db.display()))?;

    if let Commands::Tracaera(args) = cli.command {
        return agileplus_cli::commands::tracaera::run(args, &storage).await;
    }

    // Initialise VCS adapter
    let vcs = match cli.repo {
        Some(ref path) => {
            GitVcsAdapter::new(path.clone()).context("opening git repository at specified path")?
        }
        None => GitVcsAdapter::from_current_dir()
            .context("Not inside a git repository. Run agileplus from your project root.")?,
    };

    let agent = ConfiguredAgentAdapter::from_env();

    match cli.command {
        Commands::Branch(args) => {
            agileplus_cli::commands::branch::run(args, &vcs).await?;
        }
        Commands::Cycle(args) => {
            agileplus_cli::commands::cycle::run(args, &storage).await?;
        }
        Commands::Queue(args) => {
            agileplus_cli::commands::queue::run_queue(args, &storage).await?;
        }
        Commands::Specify(args) => {
            agileplus_cli::commands::specify::run_specify(args, &storage, &vcs).await?;
        }
        Commands::Research(args) => {
            agileplus_cli::commands::research::run_research(args, &storage, &vcs).await?;
        }
        Commands::Plan(args) => {
            agileplus_cli::commands::plan::run_plan(args, &storage, &vcs).await?;
        }
        Commands::Implement(args) => {
            agileplus_cli::commands::implement::run_implement(args, &storage, &vcs, &agent).await?;
        }
        Commands::Validate(args) => {
            agileplus_cli::commands::validate::run_validate(args, &storage, &vcs).await?;
        }
        Commands::Hooks(args) => {
            agileplus_cli::commands::hooks::run_hooks(args, &vcs).await?;
        }
        Commands::Ship(args) => {
            agileplus_cli::commands::ship::run_ship(args, &storage, &vcs).await?;
        }
        Commands::Retrospective(args) => {
            agileplus_cli::commands::retrospective::run_retrospective(args, &storage, &vcs).await?;
        }
        Commands::Triage(_)
        | Commands::Init(_)
        | Commands::Module(_)
        | Commands::Tracaera(_)
        | Commands::Mcp(_)
        | Commands::MigrateArtifacts(_)
        | Commands::Dashboard(_)
        | Commands::Events(_)
        | Commands::Platform(_) => unreachable!("handled above"),
    }

    Ok(())
}
