//! Multi-backend VCS hexagonal ports for PhenoVCS.
//!
//! Domain-facing types live in `pheno-vcs-core`; this crate owns the
//! `Vcs` port trait and backend adapters (git, jj).

pub mod adapters;
pub mod vcs;

pub use vcs::{Commit, Diff, Vcs};
