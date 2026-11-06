//! T77: PhenoVCS hexagonal port — Vcs.
//!
//! Adapters: [`crate::adapters::git::GitBackend`], [`crate::adapters::jj::JjBackend`].

use async_trait::async_trait;
use pheno_vcs_core::VcsError;

#[derive(Debug, Clone)]
pub struct Commit {
    pub sha: String,
    pub author: String,
    pub message: String,
    pub timestamp: i64,
}

#[derive(Debug, Clone)]
pub struct Diff {
    pub from: String,
    pub to: String,
    pub patch: String,
}

#[async_trait]
pub trait Vcs: Send + Sync {
    fn backend(&self) -> &str;
    async fn log(&self, n: usize) -> Result<Vec<Commit>, VcsError>;
    async fn diff(&self, from: &str, to: &str) -> Result<Diff, VcsError>;
    async fn commit(&self, msg: &str) -> Result<String, VcsError>;
}
