//! Asset types and structures

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// Asset type enumeration
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssetType {
    /// Python script asset
    PythonScript,
    /// JavaScript/TypeScript module
    JavaScriptModule,
    /// WebAssembly module
    WasmModule,
    /// Content pack manifest
    ContentPack,
    /// Configuration file
    Config,
    /// Data file
    Data,
    /// Unknown type
    Unknown,
}

impl AssetType {
    /// Get asset type from file extension
    pub fn from_extension(ext: &str) -> Self {
        match ext.to_lowercase().as_str() {
            "py" | "pyw" => AssetType::PythonScript,
            "js" | "mjs" | "ts" | "mts" => AssetType::JavaScriptModule,
            "wasm" => AssetType::WasmModule,
            "toml" => AssetType::ContentPack,
            "json" | "yaml" | "yml" => AssetType::Config,
            "csv" | "jsonl" | "parquet" => AssetType::Data,
            _ => AssetType::Unknown,
        }
    }

    /// Get file extensions for this asset type
    pub fn extensions(&self) -> Vec<&'static str> {
        match self {
            AssetType::PythonScript => vec!["py", "pyw"],
            AssetType::JavaScriptModule => vec!["js", "mjs", "ts", "mts"],
            AssetType::WasmModule => vec!["wasm"],
            AssetType::ContentPack => vec!["toml"],
            AssetType::Config => vec!["json", "yaml", "yml"],
            AssetType::Data => vec!["csv", "jsonl", "parquet"],
            AssetType::Unknown => vec![],
        }
    }

    /// Check if this is a valid/known type
    pub fn is_known(&self) -> bool {
        !matches!(self, AssetType::Unknown)
    }
}

/// Discovered asset information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetInfo {
    /// Asset name
    pub name: String,
    /// Full path to asset
    pub path: PathBuf,
    /// Asset type
    pub asset_type: AssetType,
    /// Size in bytes
    pub size_bytes: u64,
    /// Optional metadata
    #[serde(skip_serializing_if = "HashMap::is_empty", default)]
    pub metadata: HashMap<String, String>,
    /// Checksum (SHA-256)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub checksum: Option<String>,
}

impl AssetInfo {
    /// Create a new asset info
    pub fn new(
        name: impl Into<String>,
        path: impl Into<PathBuf>,
        asset_type: AssetType,
        size_bytes: u64,
    ) -> Self {
        Self {
            name: name.into(),
            path: path.into(),
            asset_type,
            size_bytes,
            metadata: HashMap::new(),
            checksum: None,
        }
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Set checksum
    pub fn with_checksum(mut self, checksum: impl Into<String>) -> Self {
        self.checksum = Some(checksum.into());
        self
    }
}

/// Asset discovery result
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DiscoveryResult {
    /// Discovered assets
    pub assets: Vec<AssetInfo>,
    /// Total size in bytes
    pub total_size_bytes: u64,
    /// Number of directories scanned
    pub directories_scanned: usize,
    /// Any errors encountered
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub errors: Vec<String>,
}

impl DiscoveryResult {
    /// Create a new discovery result
    pub fn new(assets: Vec<AssetInfo>) -> Self {
        let total_size = assets.iter().map(|a| a.size_bytes).sum();
        Self {
            assets,
            total_size_bytes: total_size,
            directories_scanned: 0,
            errors: Vec::new(),
        }
    }

    /// Get assets by type
    pub fn get_by_type(&self, asset_type: AssetType) -> Vec<&AssetInfo> {
        self.assets
            .iter()
            .filter(|a| a.asset_type == asset_type)
            .collect()
    }

    /// Count assets by type
    pub fn count_by_type(&self) -> HashMap<AssetType, usize> {
        let mut counts = HashMap::new();
        for asset in &self.assets {
            *counts.entry(asset.asset_type.clone()).or_insert(0) += 1;
        }
        counts
    }

    /// Add an error
    pub fn add_error(&mut self, error: impl Into<String>) {
        self.errors.push(error.into());
    }
}

/// Pack manifest structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackManifest {
    /// Pack name
    pub name: String,
    /// Pack version (semver)
    pub version: String,
    /// Pack author
    #[serde(skip_serializing_if = "Option::is_none")]
    pub author: Option<String>,
    /// Pack description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// List of assets
    #[serde(default)]
    pub assets: Vec<AssetSpec>,
    /// Dependencies
    #[serde(default)]
    pub dependencies: Vec<DependencySpec>,
    /// Additional metadata
    #[serde(skip_serializing_if = "HashMap::is_empty", default)]
    pub metadata: HashMap<String, String>,
}

impl PackManifest {
    /// Create a new pack manifest
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
            author: None,
            description: None,
            assets: Vec::new(),
            dependencies: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Set author
    pub fn with_author(mut self, author: impl Into<String>) -> Self {
        self.author = Some(author.into());
        self
    }

    /// Set description
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    /// Add an asset
    pub fn add_asset(mut self, asset: AssetSpec) -> Self {
        self.assets.push(asset);
        self
    }

    /// Add a dependency
    pub fn add_dependency(mut self, dep: DependencySpec) -> Self {
        self.dependencies.push(dep);
        self
    }

    /// Get manifest file name
    pub const fn file_name() -> &'static str {
        "phenotype.toml"
    }
}

/// Asset specification in a pack
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetSpec {
    /// Asset name
    pub name: String,
    /// Path relative to pack root
    pub path: String,
    /// Asset type
    #[serde(rename = "type")]
    pub asset_type: String,
    /// Optional description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

impl AssetSpec {
    /// Create a new asset spec
    pub fn new(
        name: impl Into<String>,
        path: impl Into<String>,
        asset_type: impl Into<String>,
    ) -> Self {
        Self {
            name: name.into(),
            path: path.into(),
            asset_type: asset_type.into(),
            description: None,
        }
    }

    /// Set description
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }
}

/// Dependency specification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencySpec {
    /// Dependency name
    pub name: String,
    /// Version constraint
    pub version_constraint: String,
    /// Optional registry URL
    #[serde(skip_serializing_if = "Option::is_none")]
    pub registry: Option<String>,
}

impl DependencySpec {
    /// Create a new dependency spec
    pub fn new(name: impl Into<String>, version_constraint: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version_constraint: version_constraint.into(),
            registry: None,
        }
    }

    /// Set registry
    pub fn with_registry(mut self, registry: impl Into<String>) -> Self {
        self.registry = Some(registry.into());
        self
    }
}

/// Validation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    /// Whether validation passed
    pub valid: bool,
    /// Validation errors
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub errors: Vec<String>,
    /// Validation warnings
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub warnings: Vec<String>,
}

impl ValidationResult {
    /// Create a successful validation result
    pub fn success() -> Self {
        Self {
            valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    /// Create a failed validation result
    pub fn error(error: impl Into<String>) -> Self {
        Self {
            valid: false,
            errors: vec![error.into()],
            warnings: Vec::new(),
        }
    }

    /// Add an error
    pub fn add_error(&mut self, error: impl Into<String>) {
        self.valid = false;
        self.errors.push(error.into());
    }

    /// Add a warning
    pub fn add_warning(&mut self, warning: impl Into<String>) {
        self.warnings.push(warning.into());
    }

    /// Merge another validation result
    pub fn merge(&mut self, other: ValidationResult) {
        if !other.valid {
            self.valid = false;
        }
        self.errors.extend(other.errors);
        self.warnings.extend(other.warnings);
    }
}

/// Build result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildResult {
    /// Whether build succeeded
    pub success: bool,
    /// Output path
    pub output_path: Option<PathBuf>,
    /// Build artifacts
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub artifacts: Vec<String>,
    /// Build errors
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub errors: Vec<String>,
    /// Build warnings
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub warnings: Vec<String>,
}

impl BuildResult {
    /// Create a successful build result
    pub fn success(output_path: impl Into<PathBuf>) -> Self {
        Self {
            success: true,
            output_path: Some(output_path.into()),
            artifacts: Vec::new(),
            errors: Vec::new(),
            warnings: Vec::new(),
        }
    }

    /// Create a failed build result
    pub fn error(error: impl Into<String>) -> Self {
        Self {
            success: false,
            output_path: None,
            artifacts: Vec::new(),
            errors: vec![error.into()],
            warnings: Vec::new(),
        }
    }

    /// Add an artifact
    pub fn add_artifact(mut self, artifact: impl Into<String>) -> Self {
        self.artifacts.push(artifact.into());
        self
    }

    /// Add an error
    pub fn add_error(&mut self, error: impl Into<String>) {
        self.success = false;
        self.errors.push(error.into());
    }
}

/// Dependency resolution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyResolution {
    /// Resolved dependencies
    pub resolved: Vec<ResolvedDependency>,
    /// Unresolved dependencies
    pub unresolved: Vec<String>,
    /// Conflicts
    pub conflicts: Vec<DependencyConflict>,
}

impl DependencyResolution {
    /// Create a new empty resolution
    pub fn new() -> Self {
        Self {
            resolved: Vec::new(),
            unresolved: Vec::new(),
            conflicts: Vec::new(),
        }
    }

    /// Check if all dependencies were resolved
    pub fn fully_resolved(&self) -> bool {
        self.unresolved.is_empty() && self.conflicts.is_empty()
    }

    /// Add a resolved dependency
    pub fn add_resolved(&mut self, dep: ResolvedDependency) {
        self.resolved.push(dep);
    }

    /// Add an unresolved dependency
    pub fn add_unresolved(&mut self, name: impl Into<String>) {
        self.unresolved.push(name.into());
    }
}

impl Default for DependencyResolution {
    fn default() -> Self {
        Self::new()
    }
}

/// Resolved dependency
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolvedDependency {
    /// Dependency name
    pub name: String,
    /// Resolved version
    pub version: String,
    /// Path to resolved package
    pub path: Option<PathBuf>,
    /// Source (registry, local, etc.)
    pub source: String,
}

/// Dependency conflict
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyConflict {
    /// Package name with conflict
    pub name: String,
    /// Conflicting version constraints
    pub constraints: Vec<String>,
    /// Conflict description
    pub description: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_asset_type_from_extension() {
        assert_eq!(AssetType::from_extension("py"), AssetType::PythonScript);
        assert_eq!(AssetType::from_extension("js"), AssetType::JavaScriptModule);
        assert_eq!(AssetType::from_extension("ts"), AssetType::JavaScriptModule);
        assert_eq!(AssetType::from_extension("wasm"), AssetType::WasmModule);
        assert_eq!(AssetType::from_extension("toml"), AssetType::ContentPack);
        assert_eq!(AssetType::from_extension("json"), AssetType::Config);
        assert_eq!(AssetType::from_extension("unknown"), AssetType::Unknown);
    }

    #[test]
    fn test_asset_type_extensions() {
        assert_eq!(AssetType::PythonScript.extensions(), vec!["py", "pyw"]);
        assert_eq!(
            AssetType::JavaScriptModule.extensions(),
            vec!["js", "mjs", "ts", "mts"]
        );
        assert!(AssetType::Unknown.extensions().is_empty());
    }

    #[test]
    fn test_asset_type_is_known() {
        assert!(AssetType::PythonScript.is_known());
        assert!(AssetType::JavaScriptModule.is_known());
        assert!(!AssetType::Unknown.is_known());
    }

    #[test]
    fn test_asset_info_new() {
        let asset = AssetInfo::new("test", "/path/to/test.py", AssetType::PythonScript, 100);
        assert_eq!(asset.name, "test");
        assert_eq!(asset.path, PathBuf::from("/path/to/test.py"));
        assert_eq!(asset.asset_type, AssetType::PythonScript);
        assert_eq!(asset.size_bytes, 100);
    }

    #[test]
    fn test_asset_info_with_metadata() {
        let asset = AssetInfo::new("test", "/path/test.py", AssetType::PythonScript, 100)
            .with_metadata("author", "tester");
        assert_eq!(asset.metadata.get("author"), Some(&"tester".to_string()));
    }

    #[test]
    fn test_discovery_result() {
        let assets = vec![
            AssetInfo::new("a", "/a.py", AssetType::PythonScript, 100),
            AssetInfo::new("b", "/b.js", AssetType::JavaScriptModule, 200),
        ];
        let result = DiscoveryResult::new(assets);
        assert_eq!(result.total_size_bytes, 300);
        assert_eq!(result.get_by_type(AssetType::PythonScript).len(), 1);
    }

    #[test]
    fn test_pack_manifest() {
        let manifest = PackManifest::new("test-pack", "1.0.0")
            .with_author("Test Author")
            .with_description("A test pack")
            .add_asset(AssetSpec::new("main", "main.py", "python_script"));

        assert_eq!(manifest.name, "test-pack");
        assert_eq!(manifest.version, "1.0.0");
        assert_eq!(manifest.author, Some("Test Author".to_string()));
        assert_eq!(manifest.assets.len(), 1);
    }

    #[test]
    fn test_validation_result() {
        let mut result = ValidationResult::success();
        assert!(result.valid);

        result.add_error("Test error");
        assert!(!result.valid);
        assert_eq!(result.errors.len(), 1);
    }

    #[test]
    fn test_validation_result_merge() {
        let mut result1 = ValidationResult::success();
        let result2 = ValidationResult::error("Second error");

        result1.merge(result2);
        assert!(!result1.valid);
        assert_eq!(result1.errors.len(), 1);
    }

    #[test]
    fn test_build_result() {
        let result = BuildResult::success("/output").add_artifact("file.py");
        assert!(result.success);
        assert_eq!(result.output_path, Some(PathBuf::from("/output")));
        assert_eq!(result.artifacts.len(), 1);
    }

    #[test]
    fn test_dependency_resolution() {
        let mut resolution = DependencyResolution::new();
        assert!(resolution.fully_resolved());

        resolution.add_unresolved("missing");
        assert!(!resolution.fully_resolved());
    }
}
