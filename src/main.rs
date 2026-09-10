use clap::Parser;

/// Scaffold placeholder for the historical `phenotype-forge` CLI.
///
/// This binary does not execute tasks, resolve dependencies, watch files,
/// load plugins, cache results, or talk to remote workers. It exists only
/// to preserve the historical command name (`phenotype-forge`) and to
/// surface the truthful scaffold state at runtime.
///
/// See `README.md`, `FUNCTIONAL_REQUIREMENTS.md`, and `ARCHIVED.md` for
/// the full audit closure (2026-09-08).
#[derive(Parser, Debug)]
#[command(
    name = "forge",
    about = "Phenotype Forge — scaffold-only placeholder CLI",
    long_about = "This binary is a documentation scaffold, not a task runner. \
                  See README.md and FUNCTIONAL_REQUIREMENTS.md for the truthful \
                  implementation status of every feature."
)]
struct Args {
    /// Accepted but not wired up to a filesystem observer. Prints a
    /// scaffold-only message and exits. See FR-OBS-002 / FR-OBS-003.
    #[arg(short, long)]
    watch: bool,
    /// Echoed back in the "Running task:" banner. See FR-OBS-001.
    #[arg(default_value = "test")]
    task: String,
}

fn main() {
    let args = Args::parse();
    println!("Running task: {} (scaffold placeholder)", args.task);
    if args.watch {
        println!(
            "scaffold placeholder: --watch accepted but no filesystem observer is \
             registered; this binary exits immediately after printing this line. \
             See FUNCTIONAL_REQUIREMENTS.md (FR-OBS-003) and Cargo.toml (notify = \"6.0\")."
        );
    }
}
