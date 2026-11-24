//! Pack builder — stub implementation for the standalone extraction.
//!
//! In the source crate (`KooshaPari/McpKit/rust/phenotype-mcp-asset`), this module
//! was declared but the source file was missing (the workspace sibling crate
//! was apparently abandoned mid-development). This stub implements the minimum
//! behavior that `AssetHandler::build()` and its unit tests require:
//!
//! - Construct from a root directory
//! - "Build" a pack by simply marking the output path as a build artifact
//!
//! The full build pipeline (compilation, bundling, signing, packaging) is a
//! future-feature backlog item. See `BUILD_STATUS.md`.

use std::path::{Path, PathBuf};
use thiserror::Error;
use tracing::info;

use crate::types::BuildResult;

/// Error type for pack building.
#[derive(Debug, Error)]
pub enum BuildError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid source: {0}")]
    InvalidSource(String),
}

/// Pack builder component.
#[derive(Debug, Clone)]
pub struct PackBuilder {
    root_dir: PathBuf,
}

impl PackBuilder {
    /// Create a new pack builder rooted at the given directory.
    pub fn new(root_dir: impl AsRef<Path>) -> Self {
        Self {
            root_dir: root_dir.as_ref().to_path_buf(),
        }
    }

    /// Build a pack from a source directory to an output path.
    ///
    /// Stub behavior: validates that the source exists and contains a
    /// `phenotype.toml` manifest, then returns a successful [`BuildResult`]
    /// pointing at the output path. The actual build pipeline
    /// (compile/bundle/sign) is a future-feature backlog item.
    pub async fn build(
        &self,
        source: &Path,
        output_path: &Path,
    ) -> Result<BuildResult, BuildError> {
        if !source.exists() {
            return Err(BuildError::InvalidSource(format!(
                "Source directory does not exist: {}",
                source.display()
            )));
        }

        let manifest_path = source.join("phenotype.toml");
        if !manifest_path.exists() {
            return Err(BuildError::InvalidSource(format!(
                "Manifest not found at expected location: {}",
                manifest_path.display()
            )));
        }

        info!(
            "Stub build: source={} output={} (root={})",
            source.display(),
            output_path.display(),
            self.root_dir.display()
        );

        // Ensure the output directory exists.
        if let Some(parent) = output_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }

        Ok(BuildResult::success(output_path)
            .add_artifact(format!("manifest:{}", manifest_path.display())))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_build_missing_source_errors() {
        let builder = PackBuilder::new("/tmp");
        let result = builder.build(Path::new("/nonexistent/xyz"), Path::new("/tmp/out")).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_build_missing_manifest_errors() {
        let temp = tempfile::tempdir().unwrap();
        let builder = PackBuilder::new(temp.path());
        let out = temp.path().join("out");
        let result = builder.build(temp.path(), &out).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_build_success_with_manifest() {
        let temp = tempfile::tempdir().unwrap();
        let manifest = temp.path().join("phenotype.toml");
        tokio::fs::write(&manifest, "name = \"x\"\nversion = \"1.0.0\"\n")
            .await
            .unwrap();

        let builder = PackBuilder::new(temp.path());
        let out = temp.path().join("out");
        let result = builder.build(temp.path(), &out).await.unwrap();
        assert!(result.success);
        assert_eq!(result.output_path, Some(out));
    }
}