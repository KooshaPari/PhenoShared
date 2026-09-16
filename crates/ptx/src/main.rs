//! PTX binary entrypoint — thin shim that delegates to [`ptx`].
//!
//! Keeps `main` minimal so all behaviour remains unit-testable via the
//! library crate. Mirrors the contract used in `phenotype-cli/src/main.rs`.

use std::process::ExitCode;

fn main() -> ExitCode {
    match ptx::run_cli() {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("error: {err}");
            ExitCode::FAILURE
        }
    }
}
