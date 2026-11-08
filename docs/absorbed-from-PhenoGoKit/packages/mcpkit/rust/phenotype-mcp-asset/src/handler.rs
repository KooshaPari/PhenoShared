//! Asset handler for MCP servers

use std::path::{Path, PathBuf};
use tracing::{debug, info, warn, error};

use crate::types::*;
use crate::discovery::AssetDiscovery;
use crate::build::PackBuilder;
use crate::validation::ManifestValidator;
use crate::dependencies::DependencyResolver;

/// Asset handler for managing phenotype packs and assets
pub struct AssetHandler {
    /// Root directory for operations
    root_dir: PathBuf,
    /// Discovery component
    discovery: AssetDiscovery,
    /// Builder component
    builder: PackBuilder,
    /// Validator component
    validator: ManifestValidator,
    /// Dependency resolver
    dependency_resolver: DependencyResolver,
}

impl AssetHandler {
    /// Create a new asset handler
    pub fn new(root_dir: impl AsRef<Path>) -> Self {
        let root = root_dir.as_ref().to_path_buf();
        Self {
            root_dir: root.clone(),
            discovery: AssetDiscovery::default(),
            builder: PackBuilder::new(&root),
            validator: ManifestValidator::new(),
            dependency_resolver: DependencyResolver::new(),
        }
    }

    /// Create with custom root directory
    pub fn with_root(root_dir: impl AsRef<Path>) -> Self {
        Self::new(root_dir)
    }

    /// Get the root directory
    pub fn root_dir(&self) -> &Path {
        &self.root_dir
    }

    /// Discover assets in a directory
    ///
    /// # Arguments
    ///
    /// * `path` - Directory to scan (relative to root or absolute)
    /// * `recursive` - Whether to scan subdirectories
    ///
    /// # Returns
    ///
    /// Discovery result containing found assets
    pub async fn discover(
        &self,
        path: impl AsRef<Path>,
        recursive: bool,
    ) -> DiscoveryResult {
        let scan_path = if path.as_ref().is_absolute() {
            path.as_ref().to_path_buf()
        } else {
            self.root_dir.join(path)
        };

        info!("Discovering assets in: {}", scan_path.display());

        match self.discovery.discover(&scan_path, recursive).await {
            Ok(result) => {
                info!("Discovered {} assets", result.assets.len());
                result
            }
            Err(e) => {
                error!("Discovery failed: {}", e);
                let mut result = DiscoveryResult::default();
                result.add_error(format!("Discovery failed: {}", e));
                result
            }
        }
    }

    /// Build a pack from a directory
    ///
    /// # Arguments
    ///
    /// * `source_dir` - Directory containing the pack
    /// * `output_path` - Where to write the built pack
    ///
    /// # Returns
    ///
    /// Build result with success status and artifacts
    pub async fn build(
        &self,
        source_dir: impl AsRef<Path>,
        output_path: impl AsRef<Path>,
    ) -> BuildResult {
        let source = if source_dir.as_ref().is_absolute() {
            source_dir.as_ref().to_path_buf()
        } else {
            self.root_dir.join(source_dir)
        };

        info!("Building pack from: {}", source.display());

        // First validate the manifest
        let validation = self.validate(&source).await;
        if !validation.valid {
            let mut result = BuildResult::error("Validation failed");
            for err in validation.errors {
                result.add_error(err);
            }
            return result;
        }

        // Resolve dependencies
        let resolution = self.resolve_dependencies(&source).await;
        if !resolution.fully_resolved() {
            let mut result = BuildResult::error("Dependency resolution failed");
            for unresolved in resolution.unresolved {
                result.add_error(format!("Unresolved dependency: {}", unresolved));
            }
            for conflict in resolution.conflicts {
                result.add_error(format!("Dependency conflict: {}", conflict.description));
            }
            return result;
        }

        // Perform the build
        match self.builder.build(&source, output_path.as_ref()).await {
            Ok(result) => {
                info!("Build successful: {:?}", result.output_path);
                result
            }
            Err(e) => {
                error!("Build failed: {}", e);
                BuildResult::error(format!("Build failed: {}", e))
            }
        }
    }

    /// Validate a pack manifest
    ///
    /// # Arguments
    ///
    /// * `pack_path` - Path to pack directory or manifest file
    ///
    /// # Returns
    ///
    /// Validation result
    pub async fn validate(&self, pack_path: impl AsRef<Path>) -> ValidationResult {
        let path = if pack_path.as_ref().is_absolute() {
            pack_path.as_ref().to_path_buf()
        } else {
            self.root_dir.join(pack_path)
        };

        debug!("Validating pack at: {}", path.display());

        let result = self.validator.validate(&path).await;

        if result.valid {
            info!("Validation passed for: {}", path.display());
        } else {
            warn!("Validation failed for: {}", path.display());
        }

        result
    }

    /// Resolve dependencies for a pack
    ///
    /// # Arguments
    ///
    /// * `pack_path` - Path to pack directory or manifest file
    ///
    /// # Returns
    ///
    /// Dependency resolution result
    pub async fn resolve_dependencies(
        &self,
        pack_path: impl AsRef<Path>,
    ) -> DependencyResolution {
        let path = if pack_path.as_ref().is_absolute() {
            pack_path.as_ref().to_path_buf()
        } else {
            self.root_dir.join(pack_path)
        };

        debug!("Resolving dependencies for: {}", path.display());

        match self.dependency_resolver.resolve(&path).await {
            Ok(resolution) => {
                info!(
                    "Resolved {} dependencies, {} unresolved, {} conflicts",
                    resolution.resolved.len(),
                    resolution.unresolved.len(),
                    resolution.conflicts.len()
                );
                resolution
            }
            Err(e) => {
                error!("Dependency resolution failed: {}", e);
                let mut resolution = DependencyResolution::new();
                resolution.add_unresolved(format!("Resolution error: {}", e));
                resolution
            }
        }
    }

    /// Get information about a pack
    ///
    /// # Arguments
    ///
    /// * `pack_path` - Path to pack directory or manifest file
    ///
    /// # Returns
    ///
    /// Pack information if found
    pub async fn get_info(&self, pack_path: impl AsRef<Path>) -> Option<PackInfo> {
        let path = if pack_path.as_ref().is_absolute() {
            pack_path.as_ref().to_path_buf()
        } else {
            self.root_dir.join(pack_path)
        };

        debug!("Getting info for: {}", path.display());

        // Try to read the manifest
        let manifest_path = if path.is_dir() {
            path.join(PackManifest::file_name())
        } else {
            path.clone()
        };

        if !manifest_path.exists() {
            warn!("Manifest not found: {}", manifest_path.display());
            return None;
        }

        match tokio::fs::read_to_string(&manifest_path).await {
            Ok(content) => {
                match toml::from_str::<PackManifest>(&content) {
                    Ok(manifest) => {
                        // Count assets
                        let asset_counts = manifest.assets.iter()
                            .fold(std::collections::HashMap::new(), |mut acc, asset| {
                                *acc.entry(asset.asset_type.clone()).or_insert(0) += 1;
                                acc
                            });

                        // Calculate total size if possible
                        let total_size = self.calculate_pack_size(&path, &manifest).await;

                        Some(PackInfo {
                            name: manifest.name,
                            version: manifest.version,
                            author: manifest.author,
                            description: manifest.description,
                            asset_count: manifest.assets.len(),
                            dependency_count: manifest.dependencies.len(),
                            asset_counts,
                            total_size_bytes: total_size,
                            path: path.to_string_lossy().to_string(),
                        })
                    }
                    Err(e) => {
                        warn!("Failed to parse manifest: {}", e);
                        None
                    }
                }
            }
            Err(e) => {
                warn!("Failed to read manifest: {}", e);
                None
            }
        }
    }

    /// Calculate total pack size
    async fn calculate_pack_size(&self, pack_dir: &Path, manifest: &PackManifest) -> u64 {
        let mut total = 0u64;

        for asset in &manifest.assets {
            let asset_path = pack_dir.join(&asset.path);
            if let Ok(metadata) = tokio::fs::metadata(&asset_path).await {
                total += metadata.len();
            }
        }

        // Include manifest size
        let manifest_path = pack_dir.join(PackManifest::file_name());
        if let Ok(metadata) = tokio::fs::metadata(&manifest_path).await {
            total += metadata.len();
        }

        total
    }
}

/// Pack information summary
#[derive(Debug, Clone)]
pub struct PackInfo {
    /// Pack name
    pub name: String,
    /// Pack version
    pub version: String,
    /// Pack author
    pub author: Option<String>,
    /// Pack description
    pub description: Option<String>,
    /// Number of assets
    pub asset_count: usize,
    /// Number of dependencies
    pub dependency_count: usize,
    /// Counts by asset type
    pub asset_counts: std::collections::HashMap<String, usize>,
    /// Total size in bytes
    pub total_size_bytes: u64,
    /// Pack path
    pub path: String,
}

impl PackInfo {
    /// Get a human-readable size string
    pub fn size_human_readable(&self) -> String {
        let size = self.total_size_bytes;
        if size < 1024 {
            format!("{} B", size)
        } else if size < 1024 * 1024 {
            format!("{:.1} KB", size as f64 / 1024.0)
        } else if size < 1024 * 1024 * 1024 {
            format!("{:.1} MB", size as f64 / (1024.0 * 1024.0))
        } else {
            format!("{:.1} GB", size as f64 / (1024.0 * 1024.0 * 1024.0))
        }
    }

    /// Format as markdown for display
    pub fn to_markdown(&self) -> String {
        let mut md = format!("## {} v{}\n\n", self.name, self.version);
        
        if let Some(author) = &self.author {
            md.push_str(&format!("**Author:** {}\n\n", author));
        }
        
        if let Some(desc) = &self.description {
            md.push_str(&format!("{}\n\n", desc));
        }
        
        md.push_str(&format!("- **Assets:** {}\n", self.asset_count));
        md.push_str(&format!("- **Dependencies:** {}\n", self.dependency_count));
        md.push_str(&format!("- **Size:** {}\n", self.size_human_readable()));
        md.push_str(&format!("- **Path:** `{}`\n", self.path));
        
        if !self.asset_counts.is_empty() {
            md.push_str("\n### Asset Breakdown\n\n");
            for (asset_type, count) in &self.asset_counts {
                md.push_str(&format!("- {}: {}\n", asset_type, count));
            }
        }
        
        md
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[tokio::test]
    async fn test_asset_handler_new() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        assert_eq!(handler.root_dir(), temp_dir.path());
    }

    #[tokio::test]
    async fn test_asset_handler_discover_empty() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        let result = handler.discover(".", false).await;
        assert_eq!(result.assets.len(), 0);
    }

    #[tokio::test]
    async fn test_asset_handler_discover_with_files() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        // Create some test files
        let file1 = temp_dir.path().join("test.py");
        let file2 = temp_dir.path().join("test.js");
        tokio::fs::write(&file1, "# python").await.unwrap();
        tokio::fs::write(&file2, "// js").await.unwrap();
        
        let result = handler.discover(".", false).await;
        
        // Should find at least 2 files (python and js)
        let py_assets: Vec<_> = result.assets.iter()
            .filter(|a| a.asset_type == AssetType::PythonScript)
            .collect();
        let js_assets: Vec<_> = result.assets.iter()
            .filter(|a| a.asset_type == AssetType::JavaScriptModule)
            .collect();
        
        assert!(!py_assets.is_empty() || !js_assets.is_empty(), 
            "Should find at least Python or JS assets. Found: {:?}", result.assets);
    }

    #[tokio::test]
    async fn test_asset_handler_validate_valid_manifest() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        // Create a valid manifest
        let manifest_content = r#"
name = "test-pack"
version = "1.0.0"
author = "Test Author"
description = "A test pack"

[[assets]]
name = "main"
path = "main.py"
type = "python_script"
"#;
        
        let manifest_path = temp_dir.path().join("phenotype.toml");
        tokio::fs::write(&manifest_path, manifest_content).await.unwrap();
        
        let result = handler.validate(temp_dir.path()).await;
        assert!(result.valid, "Validation failed: {:?}", result.errors);
    }

    #[tokio::test]
    async fn test_asset_handler_validate_invalid_manifest() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        // Create an invalid manifest (missing required fields)
        let manifest_content = r#"
author = "Test Author"
"#;
        
        let manifest_path = temp_dir.path().join("phenotype.toml");
        tokio::fs::write(&manifest_path, manifest_content).await.unwrap();
        
        let result = handler.validate(temp_dir.path()).await;
        assert!(!result.valid);
    }

    #[tokio::test]
    async fn test_asset_handler_validate_missing_manifest() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        let result = handler.validate(temp_dir.path()).await;
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| e.contains("not found")));
    }

    #[tokio::test]
    async fn test_asset_handler_get_info() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        // Create a manifest and a dummy asset
        let manifest_content = r#"
name = "my-pack"
version = "2.0.0"
author = "Developer"
description = "My awesome pack"

[[assets]]
name = "script"
path = "script.py"
type = "python_script"
"#;
        
        tokio::fs::write(
            temp_dir.path().join("phenotype.toml"),
            manifest_content
        ).await.unwrap();
        
        tokio::fs::write(
            temp_dir.path().join("script.py"),
            "print('hello')"
        ).await.unwrap();
        
        let info = handler.get_info(temp_dir.path()).await;
        
        assert!(info.is_some());
        let info = info.unwrap();
        assert_eq!(info.name, "my-pack");
        assert_eq!(info.version, "2.0.0");
        assert_eq!(info.author, Some("Developer".to_string()));
        assert_eq!(info.asset_count, 1);
    }

    #[tokio::test]
    async fn test_asset_handler_get_info_not_found() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        let info = handler.get_info("nonexistent").await;
        assert!(info.is_none());
    }

    #[tokio::test]
    async fn test_asset_handler_resolve_dependencies() {
        let temp_dir = tempfile::tempdir().unwrap();
        let handler = AssetHandler::new(temp_dir.path());
        
        // Create a manifest with dependencies
        let manifest_content = r#"
name = "dependent-pack"
version = "1.0.0"

[[dependencies]]
name = "base-pack"
version_constraint = ">=1.0.0"
"#;
        
        tokio::fs::write(
            temp_dir.path().join("phenotype.toml"),
            manifest_content
        ).await.unwrap();
        
        let result = handler.resolve_dependencies(temp_dir.path()).await;
        // Since we don't have a registry, this will be unresolved
        assert!(!result.fully_resolved());
        assert!(!result.unresolved.is_empty());
    }

    #[tokio::test]
    async fn test_pack_info_size_human_readable() {
        let info = PackInfo {
            name: "test".to_string(),
            version: "1.0.0".to_string(),
            author: None,
            description: None,
            asset_count: 0,
            dependency_count: 0,
            asset_counts: std::collections::HashMap::new(),
            total_size_bytes: 512,
            path: "/test".to_string(),
        };
        assert_eq!(info.size_human_readable(), "512 B");
        
        let info = PackInfo {
            total_size_bytes: 1536,
            ..info
        };
        assert_eq!(info.size_human_readable(), "1.5 KB");
        
        let info = PackInfo {
            total_size_bytes: 2 * 1024 * 1024,
            ..info
        };
        assert_eq!(info.size_human_readable(), "2.0 MB");
        
        let info = PackInfo {
            total_size_bytes: 3 * 1024 * 1024 * 1024,
            ..info
        };
        assert_eq!(info.size_human_readable(), "3.0 GB");
    }

    #[test]
    fn test_pack_info_to_markdown() {
        let info = PackInfo {
            name: "my-pack".to_string(),
            version: "1.0.0".to_string(),
            author: Some("Author".to_string()),
            description: Some("Description".to_string()),
            asset_count: 5,
            dependency_count: 2,
            asset_counts: [("python_script".to_string(), 3)].into_iter().collect(),
            total_size_bytes: 1024,
            path: "/path".to_string(),
        };
        
        let md = info.to_markdown();
        assert!(md.contains("my-pack"));
        assert!(md.contains("1.0.0"));
        assert!(md.contains("Author"));
        assert!(md.contains("5"));
        assert!(md.contains("2"));
    }
}
