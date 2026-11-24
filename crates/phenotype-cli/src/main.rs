// Phenotype tooling CLI facade — `pt <subcmd>` entrypoint.
//
// This binary is intentionally a thin wrapper around `phenotype_cli::run()` so
// that the entire behaviour is unit-testable from `lib.rs` without spawning a
// subprocess. Keeping `main` minimal is the standard pattern for CLI design.

use std::process::ExitCode;

fn main() -> ExitCode {
    // Delegate all behaviour to the library entry point so that integration
    // tests can exercise the same code path via `phenotype_cli::run`.
    match phenotype_cli::run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            // Print errors to stderr in a stable format so that downstream
            // tooling (CI logs, wrappers) can grep for `error:` reliably.
            eprintln!("error: {err}");
            // Use a non-zero exit code that the error can hint at via Debug
            // (we deliberately avoid Display-with-newlines to keep parsing
            // stable for scripting).
            ExitCode::FAILURE
        }
    }
}
