//! worktree-manager - Git worktree automation
//!
//! A hexagonal architecture implementation for git worktree management.

pub mod application;
pub mod cli;
pub mod domain;
pub mod infrastructure;
pub mod ports;

// Re-exports for convenience
pub use application::WorktreeService;
pub use domain::*;
pub use infrastructure::{GitWorktreeAdapter, SimpleFilesystemAdapter};
pub use pheno_vcs_core::{CommitId, RefName, VersionedPath, VcsError, VcsResult};
pub use ports::*;
