// SPDX-License-Identifier: MIT OR Apache-2.0

use pheno_mcp_defs::{ToolDefinition, ToolError};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Internal plain registry of tools by name.
#[derive(Debug, Default)]
pub struct ToolRegistry {
    tools: HashMap<String, ToolDefinition>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register(&mut self, tool: ToolDefinition) -> Result<(), ToolError> {
        if self.tools.contains_key(&tool.name) {
            return Err(ToolError::Duplicate(tool.name.clone()));
        }
        self.tools.insert(tool.name.clone(), tool);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.tools.get(name)
    }

    pub fn list(&self) -> Vec<&ToolDefinition> {
        self.tools.values().collect()
    }
}

/// Extensible MCP tool registry that wraps a [`ToolRegistry`].
#[derive(Debug, Default)]
pub struct McpToolRegistry {
    inner: ToolRegistry,
}

impl McpToolRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Register tools from a JSON manifest file.
    ///
    /// The manifest must contain a top-level `"tools"` array of [`ToolDefinition`] objects.
    pub fn register_from_manifest(&mut self, path: &Path) -> Result<(), ToolError> {
        let content = fs::read_to_string(path)?;
        let manifest: serde_json::Value = serde_json::from_str(&content)?;
        let tools_array = manifest
            .get("tools")
            .and_then(|v| v.as_array())
            .ok_or_else(|| ToolError::Parse("missing 'tools' array in manifest".to_string()))?;

        for tool_value in tools_array {
            let tool: ToolDefinition = serde_json::from_value(tool_value.clone())?;
            self.inner.register(tool)?;
        }
        Ok(())
    }

    /// Scan a directory for JSON manifest files and return all discovered tool definitions.
    ///
    /// Only files ending in `.json` are considered. Each file is parsed as a manifest with a
    /// `"tools"` array. Errors reading or parsing individual files are silently ignored.
    pub fn discover_tools(dir: &Path) -> Vec<ToolDefinition> {
        let mut discovered = Vec::new();
        let Ok(entries) = fs::read_dir(dir) else {
            return discovered;
        };
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let content = match fs::read_to_string(&path) {
                Ok(c) => c,
                Err(_) => continue,
            };
            let manifest: serde_json::Value = match serde_json::from_str(&content) {
                Ok(m) => m,
                Err(_) => continue,
            };
            let tools_array = match manifest.get("tools").and_then(|v| v.as_array()) {
                Some(arr) => arr,
                None => continue,
            };
            for tool_value in tools_array {
                let tool: ToolDefinition = match serde_json::from_value(tool_value.clone()) {
                    Ok(t) => t,
                    Err(_) => continue,
                };
                discovered.push(tool);
            }
        }
        discovered
    }

    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.inner.get(name)
    }

    pub fn list(&self) -> Vec<&ToolDefinition> {
        self.inner.list()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    #[test]
    fn registry_loads_manifest() {
        let dir = TempDir::new().unwrap();
        let manifest_path = dir.path().join("tools.json");
        let mut file = fs::File::create(&manifest_path).unwrap();
        file.write_all(
            br#"{
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echoes input back",
                        "parameters": { "input": "string" }
                    },
                    {
                        "name": "cat",
                        "description": "Concatenates strings",
                        "parameters": { "a": "string", "b": "string" }
                    }
                ]
            }"#,
        )
        .unwrap();

        let mut registry = McpToolRegistry::new();
        registry.register_from_manifest(&manifest_path).unwrap();

        let echo = registry.get("echo").unwrap();
        assert_eq!(echo.name, "echo");
        assert_eq!(echo.description, "Echoes input back");
        assert_eq!(echo.parameters.get("input"), Some(&"string".to_string()));

        let cat = registry.get("cat").unwrap();
        assert_eq!(cat.name, "cat");
        assert_eq!(cat.description, "Concatenates strings");
    }

    #[test]
    fn discover_tools_scans_directory() {
        let dir = TempDir::new().unwrap();

        let manifest_a = dir.path().join("alpha.json");
        let mut file_a = fs::File::create(&manifest_a).unwrap();
        file_a
            .write_all(
                br#"{
                    "tools": [
                        {
                            "name": "alpha_tool",
                            "description": "Alpha does things",
                            "parameters": {}
                        }
                    ]
                }"#,
            )
            .unwrap();

        let manifest_b = dir.path().join("beta.json");
        let mut file_b = fs::File::create(&manifest_b).unwrap();
        file_b
            .write_all(
                br#"{
                    "tools": [
                        {
                            "name": "beta_tool",
                            "description": "Beta does other things",
                            "parameters": {}
                        }
                    ]
                }"#,
            )
            .unwrap();

        // Write a non-JSON file that should be ignored.
        let ignored = dir.path().join("readme.txt");
        let mut file_ignored = fs::File::create(&ignored).unwrap();
        file_ignored.write_all(b"not a manifest").unwrap();

        let tools = McpToolRegistry::discover_tools(dir.path());
        assert_eq!(tools.len(), 2);

        let names: Vec<_> = tools.iter().map(|t| t.name.as_str()).collect();
        assert!(names.contains(&"alpha_tool"));
        assert!(names.contains(&"beta_tool"));
    }

    #[test]
    fn register_duplicate_tool_fails() {
        let mut registry = McpToolRegistry::new();
        let tool = ToolDefinition {
            name: "dup".to_string(),
            description: "duplicate".to_string(),
            parameters: HashMap::new(),
        };
        registry.inner.register(tool.clone()).unwrap();
        let result = registry.inner.register(tool);
        assert_eq!(result, Err(ToolError::Duplicate("dup".to_string())));
    }

    /// Focused unit test for the pure `list()` function.
    #[test]
    fn list_returns_all_registered_tools() {
        let mut registry = ToolRegistry::new();
        assert!(registry.list().is_empty());

        let alpha = ToolDefinition {
            name: "alpha".to_string(),
            description: "Alpha tool".to_string(),
            parameters: HashMap::new(),
        };
        let beta = ToolDefinition {
            name: "beta".to_string(),
            description: "Beta tool".to_string(),
            parameters: HashMap::new(),
        };

        registry.register(alpha).unwrap();
        registry.register(beta).unwrap();

        let listed = registry.list();
        assert_eq!(listed.len(), 2);

        let names: Vec<&str> = listed.iter().map(|t| t.name.as_str()).collect();
        assert!(names.contains(&"alpha"));
        assert!(names.contains(&"beta"));
    }
}
