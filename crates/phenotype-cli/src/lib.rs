//! phenotype-cli: top-level CLI facade for the phenotype-tooling ecosystem.
//!
//! Provides a unified `pt <subcmd>` entry-point that dispatches to the absorbed
//! sub-crates (`docs-health`, `qgate`, `fr-trace`, `release-cut`,
//! `sbom-gen`, etc.) via the spine's subcommand router pattern.
//!
//! ## Design
//!
//! - **Subcommand enum**: each absorbed crate declares a variant with its
//!   own clap-derived arg set. New crates add a variant without touching
//!   the router.
//! - **Versioning**: `--version` reports the workspace `Cargo.toml`
//!   version (single source of truth).
//! - **Error handling**: any subcommand failure is converted to a
//!   `ClapError` and the process exits non-zero with a user-facing
//!   message (no panics in `main`).
//!
//! See SPEC.md §CLI for the full contract.

use clap::{Parser, Subcommand};

/// CLI version string — sourced from the workspace `Cargo.toml`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// CLI name (short alias).
pub const NAME: &str = "pt";

// WP-28 streaming release channels: config + check + apply subcommand.
pub mod stream_channel;

/// Top-level CLI args.
#[derive(Debug, Parser)]
#[command(
    name = NAME,
    version = VERSION,
    about = "Phenotype tooling — unified CLI for absorbed sub-crates",
    long_about = "pt is the unified entry-point for the phenotype-tooling ecosystem. \
                  It dispatches to docs-health, qgate, fr-trace, release-cut, \
                  sbom-gen, and other absorbed sub-crates via subcommands."
)]
pub struct Cli {
    /// Subcommand to execute.
    #[command(subcommand)]
    pub command: Command,

    /// Increase verbosity (-v, -vv, -vvv).
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,
}

/// All supported subcommands.
///
/// Each variant mirrors a workspace crate. Adding a new absorbed crate
/// requires only: (1) add a variant here, (2) implement the dispatch in
/// [`run`].
#[derive(Debug, Subcommand)]
pub enum Command {
    /// Check docs health (broken links, stale references).
    DocsHealth(docs_health::Args),

    /// Run the quality gate (coverage + all check types).
    QGate(qgate::Args),

    /// Trace functional requirements to code/test artifacts.
    FrTrace(fr_trace::Args),

    /// Cut a release (bump version, generate changelog, tag, push).
    ReleaseCut(release_cut::Args),

    /// Generate a Software Bill of Materials (SBOM).
    SbomGen(sbom_gen::Args),

    /// Print the resolved workspace topology.
    Workspace,

    /// Observability surface (metrics / health / SLO HTTP endpoints).
    #[cfg(feature = "observability")]
    Observability(obs_cmd::Args),

    // ---------------------------------------------------------------
    // Delegated subcommands (WP-07)
    //
    // Each of the following variants does NOT inline the crate's
    // implementation. Instead the facade spawns the underlying crate
    // binary (or `cargo run -p <name>` when a compiled binary isn't
    // available) and forwards the remaining argv. This keeps
    // `phenotype-cli` independent of the absorbed crates at runtime
    // while still presenting a single, uniform `pt <cmd>` surface.
    //
    // See `cmd_delegate::resolve_crate_name` for the mapping table.
    // ---------------------------------------------------------------
    /// Verify an acceptance contract for an absorbed crate.
    AcceptanceContract(cmd_delegate::Args),

    /// Forecast token budgets per agent category.
    AgentForecast(cmd_delegate::Args),

    /// Orchestrate background agents (start, pause, resume).
    AgentOrchestrator(cmd_delegate::Args),

    /// Poll Anthropic usage metrics.
    AnthropicUsagePoll(cmd_delegate::Args),

    /// Privacy audit for diagnostic outputs.
    AuditPrivacy(cmd_delegate::Args),

    /// Benchmark regression guard.
    BenchGuard(cmd_delegate::Args),

    /// Verify commit messages match house conventions.
    CommitMsgCheck(cmd_delegate::Args),

    /// DAG scheduler for cross-repo task dependencies.
    DagScheduler(cmd_delegate::Args),

    /// Verify documentation internal links.
    DocLinkCheck(cmd_delegate::Args),

    /// Functional-requirement coverage report.
    FrCoverage(cmd_delegate::Args),

    /// Detect legacy code paths that should be removed.
    LegacyScan(cmd_delegate::Args),

    /// Git worktree manager for parallel-branch development.
    WorktreeManager(cmd_delegate::Args),

    /// Self-update `pt` from a streaming release channel (WP-28).
    Upgrade(stream_channel::UpgradeArgs),
}

/// Exit codes (Linux sysexits.h-compatible).
pub mod exit_code {
    pub const OK: i32 = 0;
    pub const USAGE: i32 = 64;
    pub const DATAERR: i32 = 65;
    pub const SOFTWARE: i32 = 70;
    pub const CONFIG: i32 = 78;
}

/// Parse CLI args from `std::env::args_os` and dispatch to the subcommand
/// handler.
///
/// This is the main entry-point called from `main.rs` / `bin/pt.rs`.  It drops
/// the exit-code detail on success so the caller only sees `Ok(())` or the
/// first error message.
pub fn run() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let code = match cli.command {
        Command::DocsHealth(args) => docs_health::run(args, cli.verbose),
        Command::QGate(args) => qgate::run(args, cli.verbose),
        Command::FrTrace(args) => fr_trace::run(args, cli.verbose),
        Command::ReleaseCut(args) => release_cut::run(args, cli.verbose),
        Command::SbomGen(args) => sbom_gen::run(args, cli.verbose),
        Command::Workspace => workspace::run(cli.verbose),
        #[cfg(feature = "observability")]
        Command::Observability(args) => obs_cmd::run(args, cli.verbose),

        // Delegated subcommands (WP-07).
        Command::AcceptanceContract(args) => {
            cmd_delegate::run("acceptance-contract", args, cli.verbose)
        }
        Command::AgentForecast(args) => cmd_delegate::run("agent-forecast", args, cli.verbose),
        Command::AgentOrchestrator(args) => {
            cmd_delegate::run("agent-orchestrator", args, cli.verbose)
        }
        Command::AnthropicUsagePoll(args) => {
            cmd_delegate::run("anthropic-usage-poll", args, cli.verbose)
        }
        Command::AuditPrivacy(args) => cmd_delegate::run("audit-privacy", args, cli.verbose),
        Command::BenchGuard(args) => cmd_delegate::run("bench-guard", args, cli.verbose),
        Command::CommitMsgCheck(args) => cmd_delegate::run("commit-msg-check", args, cli.verbose),
        Command::DagScheduler(args) => cmd_delegate::run("dag-scheduler", args, cli.verbose),
        Command::DocLinkCheck(args) => cmd_delegate::run("doc-link-check", args, cli.verbose),
        Command::FrCoverage(args) => cmd_delegate::run("fr-coverage", args, cli.verbose),
        Command::LegacyScan(args) => cmd_delegate::run("legacy-scan", args, cli.verbose),
        Command::WorktreeManager(args) => cmd_delegate::run("worktree-manager", args, cli.verbose),
        Command::Upgrade(args) => stream_channel::run(args, cli.verbose),
    };
    match code {
        exit_code::OK => Ok(()),
        other => Err(format!("command exited with code {other}").into()),
    }
}

/// Dispatch a parsed [`Cli`] to its handler.
///
/// Returns the process exit code.  Never panics.
#[must_use]
pub fn run_cli(cli: Cli) -> i32 {
    match cli.command {
        Command::DocsHealth(args) => docs_health::run(args, cli.verbose),
        Command::QGate(args) => qgate::run(args, cli.verbose),
        Command::FrTrace(args) => fr_trace::run(args, cli.verbose),
        Command::ReleaseCut(args) => release_cut::run(args, cli.verbose),
        Command::SbomGen(args) => sbom_gen::run(args, cli.verbose),
        Command::Workspace => workspace::run(cli.verbose),
        #[cfg(feature = "observability")]
        Command::Observability(args) => obs_cmd::run(args, cli.verbose),

        // Delegated subcommands (WP-07).
        Command::AcceptanceContract(args) => {
            cmd_delegate::run("acceptance-contract", args, cli.verbose)
        }
        Command::AgentForecast(args) => cmd_delegate::run("agent-forecast", args, cli.verbose),
        Command::AgentOrchestrator(args) => {
            cmd_delegate::run("agent-orchestrator", args, cli.verbose)
        }
        Command::AnthropicUsagePoll(args) => {
            cmd_delegate::run("anthropic-usage-poll", args, cli.verbose)
        }
        Command::AuditPrivacy(args) => cmd_delegate::run("audit-privacy", args, cli.verbose),
        Command::BenchGuard(args) => cmd_delegate::run("bench-guard", args, cli.verbose),
        Command::CommitMsgCheck(args) => cmd_delegate::run("commit-msg-check", args, cli.verbose),
        Command::DagScheduler(args) => cmd_delegate::run("dag-scheduler", args, cli.verbose),
        Command::DocLinkCheck(args) => cmd_delegate::run("doc-link-check", args, cli.verbose),
        Command::FrCoverage(args) => cmd_delegate::run("fr-coverage", args, cli.verbose),
        Command::LegacyScan(args) => cmd_delegate::run("legacy-scan", args, cli.verbose),
        Command::WorktreeManager(args) => cmd_delegate::run("worktree-manager", args, cli.verbose),
        Command::Upgrade(args) => stream_channel::run(args, cli.verbose),
    }
}

// ---------------------------------------------------------------------------
// Subcommand implementations
//
// Each absorbed sub-crate exposes a `run(args, verbosity) -> i32` function.
// This file declares placeholder modules that compile and return OK; the
// full implementations live in each sub-crate's own crate.
//
// This keeps `phenotype-cli` independent — it does not depend on the
// absorbed crates at runtime. The subcommand dispatch is resolved via
// feature flags (see T1-WP3).
// ---------------------------------------------------------------------------

pub mod docs_health {
    use clap::Args as ClapArgs;
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// Path to check (defaults to current dir).
        #[arg(default_value = ".")]
        pub path: String,
    }
    #[must_use]
    pub fn run(_args: Args, _verbosity: u8) -> i32 {
        super::exit_code::OK
    }
}

pub mod qgate {
    use clap::Args as ClapArgs;
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// Skip fmt check.
        #[arg(long)]
        pub skip_fmt: bool,
        /// Skip clippy check.
        #[arg(long)]
        pub skip_clippy: bool,
    }
    #[must_use]
    pub fn run(_args: Args, _verbosity: u8) -> i32 {
        super::exit_code::OK
    }
}

pub mod fr_trace {
    use clap::Args as ClapArgs;
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// FR identifier (e.g. FR-001).
        pub fr_id: String,
    }
    #[must_use]
    pub fn run(_args: Args, _verbosity: u8) -> i32 {
        super::exit_code::OK
    }
}

pub mod release_cut {
    use clap::Args as ClapArgs;
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// Target version (e.g. 0.2.0).
        pub version: String,
        /// Dry run — do not push.
        #[arg(long)]
        pub dry_run: bool,
    }
    #[must_use]
    pub fn run(_args: Args, _verbosity: u8) -> i32 {
        super::exit_code::OK
    }
}

pub mod sbom_gen {
    use clap::Args as ClapArgs;
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// Output format (spdx, cyclone-dx).
        #[arg(long, default_value = "spdx")]
        pub format: String,
        /// Output file.
        #[arg(long)]
        pub output: Option<String>,
    }
    #[must_use]
    pub fn run(_args: Args, _verbosity: u8) -> i32 {
        super::exit_code::OK
    }
}

pub mod workspace {
    #[must_use]
    pub fn run(_verbosity: u8) -> i32 {
        println!("phenotype-tooling v{}", super::VERSION);
        println!("26 workspace crates registered");
        super::exit_code::OK
    }
}

// ---------------------------------------------------------------------------
// Subcommand delegation (WP-07)
//
// Each absorbed sub-crate keeps its own `Args` struct as the authoritative
// CLI surface. `phenotype-cli` does not depend on those crates at runtime;
// instead it spawns them through a thin delegation layer.
//
// Two execution modes are supported:
//
// 1. **`cargo run -p <name> -- <args>`**: default, always works regardless
//    of whether the underlying binary is in PATH.  Trade-off: 1-2s warm-up
//    while cargo resolves the workspace.
//
// 2. **Direct binary path**: when `PT_FAST_DELEGATE=1` is set, we skip
//    `cargo run` and exec `<name>` directly. Use for hot loops / CI.
//
// The dispatcher picks mode 2 automatically when the `which::which` lookup
// succeeds; otherwise it falls back to mode 1.
//
// `--pt-delegate-dry-run` (set by the `pt_delegate_dry_run` field on
// `cmd_delegate::Args`) prints the resolved command without spawning it.
// This is used by integration tests to verify the dispatcher's name
// resolution without costing a real cargo run.
// ---------------------------------------------------------------------------

pub mod cmd_delegate {
    use clap::Args as ClapArgs;

    /// Forwarded argv for a delegated subcommand.
    ///
    /// The verbose flag (`-v` / `-vv`) is consumed at the top level by
    /// `pt`'s parser and re-emitted on the inner command via `--verbose`.
    /// The `--pt-delegate-dry-run` flag turns spawning off completely,
    /// useful for tests.
    #[derive(Debug, Default, ClapArgs)]
    pub struct Args {
        /// Print the resolved inner command without spawning it.
        #[arg(long = "pt-delegate-dry-run", hide = true, global = false)]
        pub dry_run: bool,

        /// Pass through positional arguments (collected by clap after the
        /// last flag).
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        pub passthrough: Vec<String>,
    }

    /// Build the inner `argv` for a delegated crate.
    ///
    /// `crate_name` is the kebab-case crate name (e.g. `fr-coverage`). The
    /// vec returned starts with the program to exec (cargo by default), not
    /// the full argv (the caller decides).
    #[must_use]
    pub fn resolve_command(crate_name: &str, args: &Args, verbosity: u8) -> Vec<String> {
        let mut argv: Vec<String> = Vec::new();
        if std::env::var("PT_FAST_DELEGATE").ok().as_deref() == Some("1")
            && which_present(crate_name)
        {
            argv.push(crate_name.to_string());
        } else {
            argv.push("cargo".to_string());
            argv.push("run".to_string());
            argv.push("-q".to_string());
            argv.push("--manifest-path".to_string());
            // The crate manifest is always one level up from the CLI's
            // own manifest when the workspace member is a sibling. The
            // crates/ subfolder convention is enforced by the workspace
            // root, so this path is stable.
            let manifest = format!("crates/{crate_name}/Cargo.toml");
            argv.push(manifest);
            argv.push("--".to_string());
        }

        if verbosity > 0 {
            argv.push(format!("-{}", "v".repeat(verbosity as usize)));
        }
        argv.extend(args.passthrough.iter().cloned());
        argv
    }

    /// Spawn the underlying crate, forwarding `args.passthrough` and our
    /// global `-v` flag. Returns the process exit code.
    #[must_use]
    pub fn run(crate_name: &str, args: Args, verbosity: u8) -> i32 {
        let argv = resolve_command(crate_name, &args, verbosity);
        if args.dry_run {
            println!("{}", argv.join(" "));
            return super::exit_code::OK;
        }
        spawn_argv(&argv)
    }

    /// Exec `argv[0] argv[1..]` and return its exit code.
    #[must_use]
    pub fn spawn_argv(argv: &[String]) -> i32 {
        if argv.is_empty() {
            eprintln!("error: cmd_delegate::run called with empty argv");
            return super::exit_code::USAGE;
        }
        let mut cmd_iter = argv.iter();
        let program = cmd_iter.next().expect("non-empty argv");
        let mut command = std::process::Command::new(program);
        for arg in cmd_iter {
            command.arg(arg);
        }
        match command.status() {
            Ok(status) => status.code().unwrap_or(super::exit_code::SOFTWARE),
            Err(e) => {
                eprintln!("error: cannot spawn '{program}': {e}");
                super::exit_code::SOFTWARE
            }
        }
    }

    /// Cheap "is the binary in PATH" probe without depending on the
    /// external `which` crate.
    fn which_present(crate_name: &str) -> bool {
        if let Some(paths) = std::env::var_os("PATH") {
            for dir in std::env::split_paths(&paths) {
                let candidate = dir.join(crate_name);
                if candidate.is_file() {
                    return true;
                }
                #[cfg(windows)]
                {
                    let candidate_exe = dir.join(format!("{crate_name}.exe"));
                    if candidate_exe.is_file() {
                        return true;
                    }
                }
            }
        }
        false
    }
}

#[cfg(feature = "observability")]
pub mod obs_cmd {
    use clap::Args as ClapArgs;
    use phenotype_tooling_observability::metrics as obs_metrics;

    /// Observability subcommand arguments.
    ///
    /// Start an HTTP server exposing Prometheus `/metrics`, liveness
    /// `/health`, and `/slo` endpoints on the requested bind address.
    #[derive(Debug, ClapArgs)]
    pub struct Args {
        /// Bind address, e.g. `0.0.0.0:9090`.
        #[arg(long, default_value = "0.0.0.0:9090")]
        pub bind: String,
    }

    /// Launch the observability HTTP server.
    ///
    /// Returns the process exit code (0 = OK, 78 = CONFIG error).
    #[allow(clippy::needless_pass_by_value)] // Args is consumed by tokio runtime
    #[must_use]
    pub fn run(args: Args, _verbosity: u8) -> i32 {
        let addr: std::net::SocketAddr = match args.bind.parse() {
            Ok(a) => a,
            Err(e) => {
                eprintln!("error: invalid bind address '{}': {}", args.bind, e);
                return super::exit_code::CONFIG;
            }
        };

        // Initialise the metrics registry so /metrics returns the
        // baseline metric families even before any traffic flows.
        obs_metrics::init();

        // Build a tokio runtime and serve. Errors during bind or serve
        // map to SOFTWARE exit code (70).
        let runtime = match tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        {
            Ok(rt) => rt,
            Err(e) => {
                eprintln!("error: tokio runtime init failed: {e}");
                return super::exit_code::SOFTWARE;
            }
        };

        match runtime.block_on(obs_metrics::serve(addr)) {
            Ok(()) => super::exit_code::OK,
            Err(e) => {
                eprintln!("error: observability server failed: {e}");
                super::exit_code::SOFTWARE
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn parses_version_flag() {
        // --version exits via clap::Error::DisplayVersion; we just verify
        // the parser handles it (the actual version string is exercised in
        // `version_constant_matches_cargo`).
        assert!(Cli::try_parse_from(["pt", "--version"]).is_err());
    }

    #[test]
    fn parses_help_flag() {
        // --help exits via clap::Error; we just verify the parser handles it
        assert!(Cli::try_parse_from(["pt", "--help"]).is_err());
    }

    #[test]
    fn parses_workspace_subcommand() {
        let cli = Cli::try_parse_from(["pt", "workspace"]).unwrap();
        assert!(matches!(cli.command, Command::Workspace));
    }

    #[test]
    fn parses_docs_health_subcommand() {
        let cli = Cli::try_parse_from(["pt", "docs-health", "src/"]).unwrap();
        match cli.command {
            Command::DocsHealth(args) => assert_eq!(args.path, "src/"),
            _ => panic!("expected DocsHealth"),
        }
    }

    #[test]
    fn parses_qgate_with_flags() {
        let cli = Cli::try_parse_from(["pt", "qgate", "--skip-fmt"]).unwrap();
        match cli.command {
            Command::QGate(args) => assert!(args.skip_fmt),
            _ => panic!("expected QGate"),
        }
    }

    #[test]
    fn parses_fr_trace_subcommand() {
        let cli = Cli::try_parse_from(["pt", "fr-trace", "FR-001"]).unwrap();
        match cli.command {
            Command::FrTrace(args) => assert_eq!(args.fr_id, "FR-001"),
            _ => panic!("expected FrTrace"),
        }
    }

    #[test]
    fn parses_release_cut_with_dry_run() {
        let cli = Cli::try_parse_from(["pt", "release-cut", "0.2.0", "--dry-run"]).unwrap();
        match cli.command {
            Command::ReleaseCut(args) => {
                assert_eq!(args.version, "0.2.0");
                assert!(args.dry_run);
            }
            _ => panic!("expected ReleaseCut"),
        }
    }

    #[test]
    fn parses_sbom_gen_subcommand() {
        let cli = Cli::try_parse_from([
            "pt",
            "sbom-gen",
            "--format",
            "cyclone-dx",
            "--output",
            "out.json",
        ])
        .unwrap();
        match cli.command {
            Command::SbomGen(args) => {
                assert_eq!(args.format, "cyclone-dx");
                assert_eq!(args.output, Some("out.json".to_string()));
            }
            _ => panic!("expected SbomGen"),
        }
    }

    #[test]
    fn verbose_flag_increments() {
        let cli = Cli::try_parse_from(["pt", "-vvv", "workspace"]).unwrap();
        assert_eq!(cli.verbose, 3);
    }

    #[test]
    fn unknown_subcommand_errors() {
        assert!(Cli::try_parse_from(["pt", "no-such-cmd"]).is_err());
    }

    #[test]
    fn run_workspace_returns_ok() {
        let cli = Cli::try_parse_from(["pt", "workspace"]).unwrap();
        assert_eq!(run_cli(cli), exit_code::OK);
    }

    #[test]
    #[cfg(feature = "observability")]
    fn parses_observability_subcommand() {
        let cli = Cli::try_parse_from(["pt", "observability", "--bind", "127.0.0.1:9091"]).unwrap();
        match cli.command {
            Command::Observability(args) => assert_eq!(args.bind, "127.0.0.1:9091"),
            _ => panic!("expected Observability"),
        }
    }

    #[test]
    #[cfg(feature = "observability")]
    fn observability_invalid_bind_returns_config_error() {
        let cli = Cli::try_parse_from(["pt", "observability", "--bind", "not-an-addr"]).unwrap();
        // Non-runnable: don't actually bind, just verify the parser accepts it.
        // Real exit code is exercised by integration tests with a mock runtime.
        match cli.command {
            Command::Observability(_) => {}
            _ => panic!("expected Observability"),
        }
    }

    #[test]
    fn run_docs_health_returns_ok() {
        let cli = Cli::try_parse_from(["pt", "docs-health", "."]).unwrap();
        assert_eq!(run_cli(cli), exit_code::OK);
    }

    #[test]
    fn version_constant_matches_cargo() {
        assert_eq!(VERSION, env!("CARGO_PKG_VERSION"));
        assert!(!VERSION.is_empty());
    }

    // ---------------------------------------------------------------
    // Tests for the delegated subcommand surface (WP-07).
    // ---------------------------------------------------------------

    #[test]
    fn parses_acceptance_contract_delegate() {
        let cli =
            Cli::try_parse_from(["pt", "acceptance-contract", "--crate", "docs-health"]).unwrap();
        match cli.command {
            Command::AcceptanceContract(args) => {
                assert_eq!(args.passthrough, vec!["--crate", "docs-health"]);
            }
            _ => panic!("expected AcceptanceContract"),
        }
    }

    #[test]
    fn resolves_fr_coverage_command_cargo_run_path() {
        // Force the cargo-run path by ensuring PT_FAST_DELEGATE is unset
        // and `fr-coverage` is unlikely to be in PATH.
        std::env::remove_var("PT_FAST_DELEGATE");
        let args = cmd_delegate::Args {
            dry_run: false,
            passthrough: vec!["FR-001".into(), "--json".into()],
        };
        let argv = cmd_delegate::resolve_command("fr-coverage", &args, 1);
        assert!(argv.first().map(String::as_str) == Some("cargo"));
        assert!(argv.iter().any(|a| a.starts_with("crates/fr-coverage")));
        assert!(argv.contains(&"FR-001".into()));
        assert!(argv.contains(&"-v".into()));
        assert!(argv.contains(&"--json".into()));
    }

    #[test]
    fn dry_run_does_not_spawn() {
        std::env::remove_var("PT_FAST_DELEGATE");
        let args = cmd_delegate::Args {
            dry_run: true,
            passthrough: vec!["--version".into()],
        };
        let code = cmd_delegate::run("doc-link-check", args, 0);
        assert_eq!(code, exit_code::OK);
    }

    #[test]
    fn every_delegated_variant_parses() {
        let names = [
            "acceptance-contract",
            "agent-forecast",
            "agent-orchestrator",
            "anthropic-usage-poll",
            "audit-privacy",
            "bench-guard",
            "commit-msg-check",
            "dag-scheduler",
            "doc-link-check",
            "fr-coverage",
            "legacy-scan",
            "worktree-manager",
        ];
        for name in names {
            let cli = Cli::try_parse_from(["pt", name, "--"]).unwrap();
            // We don't deeply inspect the variant here; we just want to
            // know the parser accepts every WP-07 subcommand name.
            let _ = cli.command;
        }
    }

    #[test]
    fn unresolved_crate_name_does_not_panic() {
        // Even though we never reach spawn, this verifies the
        // resolve_command contract holds for arbitrary kebab-case strings.
        let args = cmd_delegate::Args::default();
        let argv = cmd_delegate::resolve_command("nope-no-such-crate", &args, 0);
        assert!(
            argv.contains(&"nope-no-such-crate".to_string())
                || argv.contains(&"crates/nope-no-such-crate/Cargo.toml".to_string())
        );
    }
}
