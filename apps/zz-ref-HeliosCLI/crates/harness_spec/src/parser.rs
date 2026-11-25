// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Specification parser

use crate::error::{Result, SpecError};
use crate::models::*;
use std::path::Path;
use tracing::{debug, instrument};

/// Parse specification from YAML content
#[instrument(skip(content), fields(len = content.len()))]
pub fn parse_yaml(content: &str) -> Result<Specification> {
    let spec: Specification =
        serde_yaml::from_str(content).map_err(|e| SpecError::ParseError(e.to_string()))?;
    debug!(name = %spec.spec.name, "parsed YAML spec");
    Ok(spec)
}

/// Parse specification from JSON content
#[instrument(skip(content), fields(len = content.len()))]
pub fn parse_json(content: &str) -> Result<Specification> {
    let spec: Specification =
        serde_json::from_str(content).map_err(|e| SpecError::JsonParseError(e.to_string()))?;
    debug!(name = %spec.spec.name, "parsed JSON spec");
    Ok(spec)
}

/// Parse specification with automatic format detection
#[instrument(skip(content), fields(format = ?format, len = content.len()))]
pub fn parse(content: &str, format: SpecFormat) -> Result<Specification> {
    match format {
        SpecFormat::Yaml => parse_yaml(content),
        SpecFormat::Json => parse_json(content),
    }
}

/// Auto-detect format from content
#[instrument(skip(content), fields(len = content.len()))]
pub fn parse_auto(content: &str) -> Result<Specification> {
    let trimmed = content.trim();

    if trimmed.starts_with('{') {
        parse_json(trimmed)
    } else {
        parse_yaml(trimmed)
    }
}

/// Read a specification from a file path, auto-detecting the format from
/// the file extension. Returns [`SpecError::Io`] on filesystem errors via
/// the `From<io::Error>` impl, and the appropriate parse error otherwise.
#[instrument(skip(path))]
pub fn parse_file(path: &Path) -> Result<Specification> {
    let content = std::fs::read_to_string(path)?;
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_ascii_lowercase();
    match ext.as_str() {
        "json" => parse_json(&content),
        _ => parse_yaml(&content),
    }
}

/// Specification format
#[derive(Debug, Clone, Copy, Default)]
pub enum SpecFormat {
    #[default]
    Yaml,
    Json,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_valid_yaml() {
        let yaml = r#"
spec:
  name: test-spec
  version: "1.0.0"
  owner: test-team
  verification:
    - type: test
      name: unit_tests
  rollback:
    strategy: git_revert
    checkpoint_required: true
"#;
        let spec = parse_yaml(yaml).unwrap();
        assert_eq!(spec.spec.name, "test-spec");
        assert_eq!(spec.spec.version, "1.0.0");
    }

    #[test]
    fn test_parse_json() {
        let json = r#"{
            "spec": {
                "name": "test-spec",
                "version": "1.0.0",
                "verification": []
            }
        }"#;
        let spec = parse_json(json).unwrap();
        assert_eq!(spec.spec.name, "test-spec");
    }

    #[test]
    fn test_auto_detect_yaml() {
        let content = "spec:\n  name: test\n  verification: []";
        let spec = parse_auto(content).unwrap();
        assert_eq!(spec.spec.name, "test");
    }

    #[test]
    fn test_auto_detect_json() {
        let content = r#"{"spec": {"name": "test", "verification": []}}"#;
        let spec = parse_auto(content).unwrap();
        assert_eq!(spec.spec.name, "test");
    }

    /// Traces to: FR-HELIOS-IO-002
    /// `parse_file` should auto-detect JSON from the extension.
    #[test]
    fn test_parse_file_json() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_parser_test_spec.json");
        std::fs::write(&path, r#"{"spec": {"name": "from-file", "verification": []}}"#).unwrap();
        let spec = parse_file(&path).expect("parse_file failed for JSON");
        assert_eq!(spec.spec.name, "from-file");
        let _ = std::fs::remove_file(&path);
    }

    /// Traces to: FR-HELIOS-IO-002
    /// `parse_file` should default to YAML for non-`.json` extensions.
    #[test]
    fn test_parse_file_yaml_default() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_parser_test_spec.yaml");
        std::fs::write(&path, "spec:\n  name: from-yaml\n  verification: []\n").unwrap();
        let spec = parse_file(&path).expect("parse_file failed for YAML");
        assert_eq!(spec.spec.name, "from-yaml");
        let _ = std::fs::remove_file(&path);
    }

    /// Traces to: FR-HELIOS-IO-002
    /// Missing files must surface as `SpecError::Io`, not a generic string.
    #[test]
    fn test_parse_file_missing_yields_io() {
        let path = std::path::PathBuf::from("/nonexistent/helios_parser_missing.yaml");
        let err = parse_file(&path).expect_err("expected error for missing file");
        assert!(matches!(err, SpecError::Io(_)));
    }
}
