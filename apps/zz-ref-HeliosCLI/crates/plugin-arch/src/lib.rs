// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

use std::ffi::OsStr;
use std::path::Path;

use pheno_plugin::{Plugin, PluginError, PluginRegistry};

/// A plugin for HeliosCLI.
#[derive(Debug)]
pub struct HeliosPlugin {
    name: String,
    version: String,
}

impl HeliosPlugin {
    /// Create a new HeliosPlugin.
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self { name: name.into(), version: version.into() }
    }
}

impl Plugin for HeliosPlugin {
    fn name(&self) -> &str {
        &self.name
    }

    fn version(&self) -> &str {
        &self.version
    }
}

/// Registry for HeliosCLI plugins, wrapping [`PluginRegistry`].
pub struct HeliosPluginRegistry {
    inner: PluginRegistry,
}

impl HeliosPluginRegistry {
    /// Construct an empty registry.
    pub fn new() -> Self {
        Self { inner: PluginRegistry::new() }
    }

    /// Register a plugin.
    pub fn register(&mut self, plugin: Box<dyn Plugin>) -> Result<(), PluginError> {
        self.inner.register(plugin)
    }

    /// Scan a directory for `*.so` files and register each as a [`HeliosPlugin`].
    ///
    /// Returns [`PluginError::DuplicateName`] if a scanned plugin name collides
    /// with an already-registered plugin.
    pub fn load_from_dir(&mut self, path: &Path) -> Result<(), PluginError> {
        if !path.exists() || !path.is_dir() {
            return Ok(());
        }

        let entries = std::fs::read_dir(path)?;

        for entry in entries {
            let entry = entry?;

            let path = entry.path();
            if let Some(ext) = path.extension() {
                if ext == OsStr::new("so") {
                    if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                        let plugin = HeliosPlugin::new(stem.to_string(), "0.1.0");
                        self.inner.register(Box::new(plugin))?;
                    }
                }
            }
        }

        Ok(())
    }

    /// Return the names of all registered plugins, sorted ascending.
    pub fn names(&self) -> Vec<String> {
        self.inner.names()
    }

    /// Look up a registered plugin by name.
    pub fn get(&self, name: &str) -> Option<&dyn Plugin> {
        self.inner.get(name)
    }
}

impl Default for HeliosPluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn plugin_registry_loads_from_empty_dir() {
        let dir = TempDir::new().unwrap();
        let mut registry = HeliosPluginRegistry::new();
        registry.load_from_dir(dir.path()).unwrap();
        assert!(registry.names().is_empty());
    }

    #[test]
    fn plugin_registry_rejects_duplicate_plugins() {
        let mut registry = HeliosPluginRegistry::new();
        let p1 = HeliosPlugin::new("echo", "0.1.0");
        let p2 = HeliosPlugin::new("echo", "0.2.0");

        registry.register(Box::new(p1)).unwrap();
        let result = registry.register(Box::new(p2));

        assert!(matches!(result, Err(PluginError::DuplicateName(ref n)) if n == "echo"));
        assert_eq!(registry.names(), vec!["echo".to_string()]);
    }

    #[test]
    fn plugin_registry_loads_shared_object_stems() {
        let dir = TempDir::new().unwrap();
        std::fs::write(dir.path().join("sample.so"), b"fake").unwrap();

        let mut registry = HeliosPluginRegistry::new();
        registry.load_from_dir(dir.path()).unwrap();

        assert_eq!(registry.names(), vec!["sample".to_string()]);
        assert_eq!(registry.get("sample").unwrap().version(), "0.1.0");
    }
}
