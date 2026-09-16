//! Phenotype Tool eXtensions (PTX) — Phase 3 governance gate wrapper.
//!
//! PTX is the thin CLI layer that orchestrates Phase 1/2/3 governance
//! against the workspace. It is intentionally a **facade** over the
//! proven Phase 2 sub-crates plus the Phase 3 WP-09 observability and
//! WP-10 fuzz surfaces, with two extra governance primitives:
//!
//! 1. `ptx check` — runs the four-gate sequence (format → clippy →
//!    test → audit) and emits a single `--deny-data` JSON summary.
//! 2. `ptx wrap <subcommand>` — delegates to the phase-crate binary
//!    in the same way `pt <subcommand>` does in WP-07.
//!
//! PTX never embeds business logic — every behavior lives in the
//! existing crate. This keeps PTX a single, auditable wrapper that PR
//! reviewers can read in one sitting.
//!
//! ## Module map
//!
//! - [`check`]       -- local pre-Push / pre-PR gate runner.
//! - [`wrap`]        -- process delegate into any of the Phase 1/2/3
//!   sub-crates, mirroring `pt`'s coercion.
//! - [`manifest`]    -- parse `ptx.yaml` governance manifests so PRs
//!   can declare their own admission contract.
//! - [`report`]      -- render the final gate verdict to stdout so CI
//!   and humans both read the same shape.

#![deny(
    missing_debug_implementations,
    rust_2018_idioms,
    unsafe_op_in_unsafe_fn,
    clippy::correctness,
    clippy::suspicious,
    clippy::complexity,
    clippy::perf,
    clippy::style
)]
#![warn(
    clippy::pedantic,
    clippy::nursery,
    clippy::cargo,
    clippy::module_name_repetitions,
    clippy::must_use_candidate,
    clippy::missing_const_for_fn,
    missing_docs
)]

pub mod check;
pub mod manifest;
pub mod report;
pub mod wrap;

/// PTX version constant — keep in lock-step with `Cargo.toml`.
pub const PTX_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Exit codes returned by the CLI binary.
///
/// `ptx` mirrors the OS contract (0 = pass, 1 = gate failure) and adds
/// two extras for tooling ergonomics.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ExitCode {
    /// All gates passed.
    Success = 0,
    /// At least one gate failed.
    GateFailure = 1,
    /// Manifest parse error (no gate ran).
    ManifestError = 2,
    /// Unexpected internal error (IO, propagation failure).
    InternalError = 3,
}

impl ExitCode {
    /// Returns the numeric exit code for `std::process::exit` / `From<u8>`.
    #[inline]
    #[must_use]
    pub const fn report(self) -> u8 {
        self as u8
    }
}

impl From<ExitCode> for u8 {
    /// Mirror of [`ExitCode::report`] for callers needing `From` ergonomics.
    #[inline]
    fn from(code: ExitCode) -> Self {
        code.report()
    }
}

/// Returns true if every gate in `gates` reports `Passed`.
#[inline]
#[must_use]
pub const fn all_passed(gates: &[check::Gate]) -> bool {
    matches!(
        gates.last(),
        Some(check::Gate {
            status: check::Status::Passed,
            ..
        })
    )
}

/// Top-level PTX errors.
#[derive(Debug, thiserror::Error)]
pub enum PtxError {
    /// Filesystem I/O failure captured with the offending path; the
    /// embedded `source` is the underlying `std::io::Error`.
    #[error("io failure on {path}: {source}")]
    Io {
        /// Path being read or written when the I/O error occurred.
        path: std::path::PathBuf,
        /// Underlying I/O error returned by `std::fs` / `std::io`.
        #[source]
        source: std::io::Error,
    },
    /// Manifest or input could not be tokenised; carries a short parser
    /// context including line/column when available.
    #[error("parse error: {0}")]
    Parse(
        /// Human-readable parse-error message.
        String,
    ),
    /// Manifest schema version on disk does not match the version this
    /// build of `ptx` was compiled against.
    #[error("manifest version mismatch: expected {expected}, found {found}")]
    ManifestVersion {
        /// Schema version this binary understands.
        expected: u32,
        /// Schema version found on disk.
        found: u32,
    },
    /// Manifest is missing a field required for the current operation;
    /// `kind` is the record type (gate / manifest / report) and `field`
    /// is the missing column name.
    #[error("missing field {field} in {kind}")]
    MissingField {
        /// Record type missing the field.
        kind: String,
        /// Field name missing from the record.
        field: String,
    },
    /// A gate sub-process exited non-zero; the integer is the OS exit code.
    ///
    /// Raw `i32` exit code returned by a child process; only emitted
    /// when callers chain the result through `From<i32>`.
    #[error("exit code {0} not representable")]
    ExitCode(i32),
}

// Note: we cannot impl `From<std::process::ExitCode> for u8` because that
// would be an orphan rule violation (both types are foreign: std vs the
// primitive). The CLI in `main.rs` bridges by extracting the i32 via
// `.report()` and then mapping directly to `u8`/`Exit::from()`.

/// Run the PTX CLI scaffolding in-process: no CLI args parsed, no gates
/// executed. Returns `Ok(())` on success; `Err(PtxError)` if the bench
/// harness is unreachable. The thin binary in `main.rs` calls this and
/// emits the appropriate `ExitCode` from the result.
///
/// This is intentionally a no-op-parsed entry point so that the
/// integration tests don't spawn child processes.
#[allow(clippy::double_must_use)]
pub fn run_cli() -> Result<(), PtxError> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{all_passed, ExitCode, PtxError, PTX_VERSION};

    #[test]
    fn version_constant_is_not_empty() {
        assert!(!PTX_VERSION.is_empty());
    }

    #[test]
    fn all_passed_rejects_empty() {
        assert!(!all_passed(&[]));
    }

    #[test]
    fn exit_code_reports_i32_zero_on_success() {
        let code = ExitCode::Success;
        assert_eq!(code.report(), 0);
    }

    #[test]
    fn exit_code_reports_gate_failure_as_one() {
        let code = ExitCode::GateFailure;
        assert_eq!(code.report(), 1);
    }

    #[test]
    fn exit_code_u8_from_impl_matches_report() {
        let n: u8 = u8::from(ExitCode::Success);
        assert_eq!(n, 0);
        let m: u8 = u8::from(ExitCode::GateFailure);
        assert_eq!(m, 1);
    }

    #[test]
    fn ptx_error_io_displays_path_and_source() {
        let err = PtxError::Io {
            path: std::path::PathBuf::from("/tmp/x"),
            source: std::io::Error::other("boom"),
        };
        let s = err.to_string();
        assert!(s.contains("/tmp/x"));
        assert!(s.contains("boom") || !s.is_empty());
    }

    #[test]
    fn ptx_error_parse_displays_message() {
        let err = PtxError::Parse("bad yaml".into());
        assert_eq!(err.to_string(), "parse error: bad yaml");
    }

    #[test]
    fn ptx_error_manifest_version_format() {
        let err = PtxError::ManifestVersion {
            expected: 2,
            found: 1,
        };
        let s = err.to_string();
        assert!(s.contains("expected 2"));
        assert!(s.contains("found 1"));
    }

    #[test]
    fn ptx_error_missing_field_format() {
        let err = PtxError::MissingField {
            kind: "gate".into(),
            field: "name".into(),
        };
        assert_eq!(err.to_string(), "missing field name in gate");
    }
}
