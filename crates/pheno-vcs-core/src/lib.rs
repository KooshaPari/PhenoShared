//! Core VCS primitives for PhenoVCS.
//!
//! Shared domain types and thin port traits consumed by `worktree-manager`,
//! the multi-backend `ports` crate, and downstream agent dispatchers.
//! Keep this crate hexagonal: types + traits only — no git/jj subprocesses.

use std::fmt;
use std::path::{Path, PathBuf};

use thiserror::Error;

/// Backend kind for multi-VCS adapters.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BackendKind {
    Git,
    Jj,
    Sapling,
}

impl BackendKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Git => "git",
            Self::Jj => "jj",
            Self::Sapling => "sapling",
        }
    }
}

impl fmt::Display for BackendKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A filesystem path that is (or will be) under version control.
///
/// Distinguishes VCS-managed paths from arbitrary OS paths at the type layer.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct VersionedPath(PathBuf);

impl VersionedPath {
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self(path.into())
    }

    pub fn as_path(&self) -> &Path {
        &self.0
    }

    pub fn into_path_buf(self) -> PathBuf {
        self.0
    }
}

impl AsRef<Path> for VersionedPath {
    fn as_ref(&self) -> &Path {
        self.as_path()
    }
}

impl From<PathBuf> for VersionedPath {
    fn from(path: PathBuf) -> Self {
        Self::new(path)
    }
}

impl From<&Path> for VersionedPath {
    fn from(path: &Path) -> Self {
        Self::new(path.to_path_buf())
    }
}

impl fmt::Display for VersionedPath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0.display())
    }
}

/// Opaque commit / change identifier (git SHA, jj change-id, etc.).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CommitId(String);

impl CommitId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for CommitId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Named ref (branch, bookmark, tag).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RefName(String);

impl RefName {
    pub fn new(name: impl Into<String>) -> Self {
        Self(name.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for RefName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Shared VCS error surface for core + ports + worktree-manager.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum VcsError {
    #[error("path not found: {0}")]
    PathNotFound(String),

    #[error("invalid path: {0}")]
    InvalidPath(String),

    #[error("ref not found: {0}")]
    RefNotFound(String),

    #[error("ref already exists: {0}")]
    RefExists(String),

    #[error("backend '{backend}' operation failed: {message}")]
    Backend { backend: String, message: String },

    #[error("unsupported operation: {0}")]
    Unsupported(String),

    #[error("io error: {0}")]
    Io(String),
}

impl VcsError {
    pub fn backend(backend: impl Into<String>, message: impl Into<String>) -> Self {
        Self::Backend {
            backend: backend.into(),
            message: message.into(),
        }
    }
}

impl From<std::io::Error> for VcsError {
    fn from(err: std::io::Error) -> Self {
        Self::Io(err.to_string())
    }
}

/// Result alias for core VCS operations.
pub type VcsResult<T> = Result<T, VcsError>;

/// Thin port: resolve a ref to a commit id (backend-agnostic).
pub trait RefResolver: Send + Sync {
    fn resolve(&self, repo: &VersionedPath, name: &RefName) -> VcsResult<CommitId>;
}

/// Thin port: report which backend is in use.
pub trait BackendIdentity: Send + Sync {
    fn kind(&self) -> BackendKind;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn versioned_path_roundtrip() {
        let vp = VersionedPath::new("/repo/wt/feature");
        assert_eq!(vp.as_path(), Path::new("/repo/wt/feature"));
        assert_eq!(vp.to_string(), "/repo/wt/feature");
    }

    #[test]
    fn backend_kind_display() {
        assert_eq!(BackendKind::Git.as_str(), "git");
        assert_eq!(BackendKind::Jj.to_string(), "jj");
    }

    #[test]
    fn vcs_error_backend_helper() {
        let err = VcsError::backend("git", "worktree add failed");
        assert!(err.to_string().contains("git"));
        assert!(err.to_string().contains("worktree add failed"));
    }

    #[test]
    fn commit_id_and_ref_name() {
        let id = CommitId::new("abc123");
        let r = RefName::new("main");
        assert_eq!(id.as_str(), "abc123");
        assert_eq!(r.as_str(), "main");
    }
}
