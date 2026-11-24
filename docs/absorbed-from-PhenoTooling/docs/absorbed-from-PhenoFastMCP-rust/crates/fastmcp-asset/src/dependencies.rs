//! Dependency resolution — reads a pack's declared dependencies and marks them.
//!
//! In the source crate (`KooshaPari/McpKit/rust/phenotype-mcp-asset`), this module
//! was declared but the source file was missing (the workspace sibling crate
//! was apparently abandoned mid-development). This stub implements the minimum
//! behavior that `AssetHandler::resolve_dependencies()` and its unit tests
//! require:
//!
//! - Read `phenotype.toml`
//! - Enumerate declared dependencies
//! - **Mark all as unresolved** (no registry is wired up)
//!
//! This stub is intentionally pessimistic so that callers must explicitly
//! configure a registry before `BuildResult::success` is reachable. A real
//! registry implementation is a future-feature backlog item; see
//! `BUILD_STATUS.md`.
//!
//! Why pessimistic-by-default? In a fleet-wide substrate, "trust nothing you
//! can't verify" is the safer default — a stub that silently marked all deps
//! as resolved would let builds succeed with phantom dependencies.

use std::path::Path;
use thiserror::Error;
use tracing::{debug, info};

use crate::types::{DependencyResolution, PackManifest};

/// Error type for dependency resolution.
#[derive(Debug, Error)]
pub enum ResolutionError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Parse error: {0}")]
    Parse(String),
}

/// Dependency resolver component.
#[derive(Debug, Default, Clone)]
pub struct DependencyResolver {
    _private: (),
}

impl DependencyResolver {
    /// Create a new dependency resolver.
    pub fn new() -> Self {
        Self::default()
    }

    /// Resolve dependencies for the pack at the given path.
    ///
    /// Stub behavior: parses the manifest, then marks every declared
    /// dependency as **unresolved** (with the constraint included for
    /// debuggability). No registry lookup is performed.
    pub async fn resolve(&self, path: &Path) -> Result<DependencyResolution, ResolutionError> {
        let manifest_path = if path.is_dir() {
            path.join(PackManifest::file_name())
        } else {
            path.to_path_buf()
        };

        debug!(
            "DependencyResolver: reading manifest at {}",
            manifest_path.display()
        );

        if !manifest_path.exists() {
            return Ok(DependencyResolution::new()); // empty; nothing to resolve
        }

        let content = tokio::fs::read_to_string(&manifest_path).await?;
        let manifest: PackManifest = toml::from_str(&content)
            .map_err(|e| ResolutionError::Parse(e.to_string()))?;

        let mut resolution = DependencyResolution::new();
        for dep in &manifest.dependencies {
            resolution.add_unresolved(format!(
                "{} (constraint: `{}`, source: stub-resolver)",
                dep.name, dep.version_constraint
            ));
        }

        info!(
            "Stub resolution: {} deps declared, {} unresolved, 0 resolved, 0 conflicts",
            manifest.dependencies.len(),
            resolution.unresolved.len()
        );

        Ok(resolution)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_resolve_empty_manifest() {
        let temp = tempfile::tempdir().unwrap();
        tokio::fs::write(
            temp.path().join("phenotype.toml"),
            "name = \"x\"\nversion = \"1.0.0\"\n",
        )
        .await
        .unwrap();

        let r = DependencyResolver::new();
        let resolution = r.resolve(temp.path()).await.unwrap();
        assert!(resolution.fully_resolved()); // no deps = nothing to fail
    }

    #[tokio::test]
    async fn test_resolve_with_deps_all_unresolved() {
        let temp = tempfile::tempdir().unwrap();
        let manifest = r#"
name = "x"
version = "1.0.0"

[[dependencies]]
name = "base"
version_constraint = ">=1.0.0"

[[dependencies]]
name = "extras"
version_constraint = "^2.0.0"
"#;
        tokio::fs::write(temp.path().join("phenotype.toml"), manifest)
            .await
            .unwrap();

        let r = DependencyResolver::new();
        let resolution = r.resolve(temp.path()).await.unwrap();
        assert!(!resolution.fully_resolved());
        assert_eq!(resolution.unresolved.len(), 2);
    }

    #[tokio::test]
    async fn test_resolve_missing_manifest_is_empty() {
        let temp = tempfile::tempdir().unwrap();
        let r = DependencyResolver::new();
        let resolution = r.resolve(temp.path()).await.unwrap();
        assert!(resolution.fully_resolved());
        assert!(resolution.unresolved.is_empty());
    }
}