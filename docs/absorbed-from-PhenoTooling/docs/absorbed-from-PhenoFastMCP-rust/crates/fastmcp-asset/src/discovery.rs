//! Asset discovery — walks a directory and classifies files by extension.
//!
//! In the source crate (`KooshaPari/McpKit/rust/phenotype-mcp-asset`), this module
//! was declared but the source file was missing (the workspace sibling crate
//! was apparently abandoned mid-development). This stub implements the minimum
//! behavior that `AssetHandler::discover()` and its unit tests require:
//!
//! - Walk a directory (optionally recursive) using `walkdir`
//! - Classify each file by extension via [`AssetType::from_extension`]
//! - Build [`AssetInfo`] entries with size and inferred type
//! - Return aggregated [`DiscoveryResult`]
//!
//! See `BUILD_STATUS.md` for the full rationale and future-feature backlog.

use std::path::Path;
use thiserror::Error;
use tracing::warn;
use walkdir::WalkDir;

use crate::types::{AssetInfo, AssetType, DiscoveryResult};

/// Error type for asset discovery.
#[derive(Debug, Error)]
pub enum DiscoveryError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Walk error: {0}")]
    Walk(String),
}

/// Asset discovery component.
///
/// Walks a directory tree and produces a [`DiscoveryResult`] of [`AssetInfo`]
/// entries, one per file (excluding directories and symlink loops).
#[derive(Debug, Default, Clone)]
pub struct AssetDiscovery {
    _private: (),
}

impl AssetDiscovery {
    /// Create a new asset discovery component.
    pub fn new() -> Self {
        Self::default()
    }

    /// Discover assets in a directory.
    ///
    /// # Arguments
    ///
    /// * `path` — directory to scan
    /// * `recursive` — whether to descend into subdirectories
    pub async fn discover(
        &self,
        path: &Path,
        recursive: bool,
    ) -> Result<DiscoveryResult, DiscoveryError> {
        let path = path.to_path_buf();
        let result = tokio::task::spawn_blocking(move || -> Result<DiscoveryResult, DiscoveryError> {
            if !path.exists() {
                return Err(DiscoveryError::Io(std::io::Error::new(
                    std::io::ErrorKind::NotFound,
                    format!("Path not found: {}", path.display()),
                )));
            }

            let mut assets = Vec::new();
            let mut directories_scanned = 0usize;
            let mut errors = Vec::new();

            let walker = if recursive {
                WalkDir::new(&path)
            } else {
                WalkDir::new(&path).max_depth(1)
            };

            for entry in walker.into_iter().filter_map(|e| e.ok()) {
                let entry_path = entry.path();
                if entry_path == path {
                    continue; // skip root
                }
                if entry.file_type().is_dir() {
                    directories_scanned += 1;
                    continue;
                }
                if !entry.file_type().is_file() {
                    continue;
                }

                let metadata = match entry.metadata() {
                    Ok(m) => m,
                    Err(e) => {
                        warn!("Failed to read metadata for {}: {}", entry_path.display(), e);
                        errors.push(format!("metadata error for {}: {}", entry_path.display(), e));
                        continue;
                    }
                };

                let asset_type = entry_path
                    .extension()
                    .and_then(|e| e.to_str())
                    .map(AssetType::from_extension)
                    .unwrap_or(AssetType::Unknown);

                let name = entry_path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("")
                    .to_string();

                // Compute SHA-256 checksum (only for known types to keep this cheap).
                // We compute the checksum BEFORE moving the AssetType into AssetInfo::new,
                // because we still need `asset_type.is_known()` to gate the hashing below.
                let checksum = if asset_type.is_known() {
                    use sha2::{Digest, Sha256};
                    use std::io::Read;
                    std::fs::File::open(entry_path)
                        .ok()
                        .map(|mut f| {
                            let mut hasher = Sha256::new();
                            let mut buf = [0u8; 8192];
                            loop {
                                match f.read(&mut buf) {
                                    Ok(0) => break,
                                    Ok(n) => hasher.update(&buf[..n]),
                                    Err(_) => break,
                                }
                            }
                            hex::encode(hasher.finalize())
                        })
                } else {
                    None
                };

                let mut asset = AssetInfo::new(
                    name,
                    entry_path.to_path_buf(),
                    asset_type,
                    metadata.len(),
                );

                if let Some(digest) = checksum {
                    asset = asset.with_checksum(digest);
                }

                assets.push(asset);
            }

            Ok(DiscoveryResult {
                assets,
                total_size_bytes: 0, // filled by DiscoveryResult::new if used; left at 0 here
                directories_scanned,
                errors,
            })
        })
        .await
        .map_err(|e| DiscoveryError::Walk(e.to_string()))??;

        // Recompute total_size_bytes consistently with DiscoveryResult::new semantics.
        let total_size_bytes = result.assets.iter().map(|a| a.size_bytes).sum();
        Ok(DiscoveryResult {
            total_size_bytes,
            ..result
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_discovery_finds_files() {
        let temp = tempfile::tempdir().unwrap();
        tokio::fs::write(temp.path().join("a.py"), "print(1)").await.unwrap();
        tokio::fs::write(temp.path().join("b.js"), "console.log(1)").await.unwrap();

        let discovery = AssetDiscovery::default();
        let result = discovery.discover(temp.path(), false).await.unwrap();

        assert_eq!(result.assets.len(), 2);
    }

    #[tokio::test]
    async fn test_discovery_nonexistent_path_errors() {
        let discovery = AssetDiscovery::default();
        let result = discovery.discover(Path::new("/nonexistent/path/xyz"), false).await;
        assert!(result.is_err());
    }
}