//! Manifest validation — verifies a `phenotype.toml` file is well-formed.
//!
//! In the source crate (`KooshaPari/McpKit/rust/phenotype-mcp-asset`), this module
//! was declared but the source file was missing (the workspace sibling crate
//! was apparently abandoned mid-development). This stub implements the minimum
//! behavior that `AssetHandler::validate()` and its unit tests require:
//!
//! - Locate `phenotype.toml` in the given path (or treat path as the manifest itself)
//! - Parse as [`PackManifest`]
//! - Check required fields (name, version)
//! - Return [`ValidationResult`] with errors/warnings
//!
//! See `BUILD_STATUS.md` for the full rationale.

use std::path::Path;
use tracing::{debug, warn};

use crate::types::{PackManifest, ValidationResult};

/// Manifest validator component.
#[derive(Debug, Default, Clone)]
pub struct ManifestValidator {
    _private: (),
}

impl ManifestValidator {
    /// Create a new manifest validator.
    pub fn new() -> Self {
        Self::default()
    }

    /// Validate a pack manifest at the given path.
    ///
    /// `path` may be either a directory containing `phenotype.toml`, or a
    /// direct path to a manifest file.
    pub async fn validate(&self, path: &Path) -> ValidationResult {
        let manifest_path = if path.is_dir() {
            path.join(PackManifest::file_name())
        } else {
            path.to_path_buf()
        };

        debug!("ManifestValidator: looking for {}", manifest_path.display());

        if !manifest_path.exists() {
            warn!("Manifest not found at: {}", manifest_path.display());
            let result = ValidationResult::error(format!(
                "Manifest not found: {}",
                manifest_path.display()
            ));
            // Match the test's assertion: `result.errors.iter().any(|e| e.contains("not found"))`
            return result;
        }

        let content = match tokio::fs::read_to_string(&manifest_path).await {
            Ok(c) => c,
            Err(e) => {
                return ValidationResult::error(format!(
                    "Failed to read manifest {}: {}",
                    manifest_path.display(),
                    e
                ));
            }
        };

        let manifest: PackManifest = match toml::from_str(&content) {
            Ok(m) => m,
            Err(e) => {
                return ValidationResult::error(format!("Failed to parse manifest: {}", e));
            }
        };

        let mut result = ValidationResult::success();
        if manifest.name.trim().is_empty() {
            result.add_error("Pack name is required and cannot be empty".to_string());
        }
        if manifest.version.trim().is_empty() {
            result.add_error("Pack version is required and cannot be empty".to_string());
        }

        // Semver sanity check on version (warn-only; not a hard error).
        if semver::Version::parse(&manifest.version).is_err() {
            result.add_warning(format!(
                "Version `{}` is not valid semver (e.g. `1.2.3`)",
                manifest.version
            ));
        }

        // Duplicate asset names within the manifest.
        let mut seen = std::collections::HashSet::new();
        for asset in &manifest.assets {
            if !seen.insert(asset.name.clone()) {
                result.add_error(format!("Duplicate asset name: `{}`", asset.name));
            }
        }

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_validate_valid_manifest() {
        let temp = tempfile::tempdir().unwrap();
        let manifest = r#"
name = "x"
version = "1.0.0"

[[assets]]
name = "main"
path = "main.py"
type = "python_script"
"#;
        tokio::fs::write(temp.path().join("phenotype.toml"), manifest)
            .await
            .unwrap();

        let v = ManifestValidator::new();
        let result = v.validate(temp.path()).await;
        assert!(result.valid, "Validation failed: {:?}", result.errors);
    }

    #[tokio::test]
    async fn test_validate_missing_name_errors() {
        let temp = tempfile::tempdir().unwrap();
        let manifest = r#"version = "1.0.0""#;
        tokio::fs::write(temp.path().join("phenotype.toml"), manifest)
            .await
            .unwrap();

        let v = ManifestValidator::new();
        let result = v.validate(temp.path()).await;
        assert!(!result.valid);
    }

    #[tokio::test]
    async fn test_validate_missing_manifest_errors() {
        let temp = tempfile::tempdir().unwrap();
        let v = ManifestValidator::new();
        let result = v.validate(temp.path()).await;
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| e.contains("not found")));
    }
}