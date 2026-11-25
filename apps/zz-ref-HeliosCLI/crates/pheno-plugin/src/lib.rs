// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

use std::collections::HashMap;
use thiserror::Error;

/// The canonical plugin contract for the pheno-* fleet.
pub trait Plugin: Send + Sync {
    /// Stable, registry-unique name.
    fn name(&self) -> &str;

    /// Semantic-version string.
    fn version(&self) -> &str;

    /// One-shot initialization hook.
    fn init(&self) -> Result<(), PluginError> {
        Ok(())
    }
}

/// The error type returned by [`PluginRegistry`] operations.
#[derive(Debug, Error)]
pub enum PluginError {
    /// A plugin tried to register under a name that is already in the registry.
    #[error("plugin name already registered: {0}")]
    DuplicateName(String),

    /// A plugin's `init` hook returned an error.
    #[error("plugin init failed: {0}")]
    InitFailed(String),
}

impl From<std::io::Error> for PluginError {
    fn from(err: std::io::Error) -> Self {
        PluginError::InitFailed(err.to_string())
    }
}

/// The canonical name-indexed plugin store.
pub struct PluginRegistry {
    plugins: HashMap<String, Box<dyn Plugin>>,
}

impl PluginRegistry {
    /// Construct an empty registry.
    pub fn new() -> Self {
        Self { plugins: HashMap::new() }
    }

    /// Register a plugin under its [`Plugin::name()`].
    pub fn register(&mut self, p: Box<dyn Plugin>) -> Result<(), PluginError> {
        let name = p.name().to_owned();
        if self.plugins.contains_key(&name) {
            return Err(PluginError::DuplicateName(name));
        }
        self.plugins.insert(name, p);
        Ok(())
    }

    /// Look up a registered plugin by name.
    pub fn get(&self, name: &str) -> Option<&dyn Plugin> {
        self.plugins.get(name).map(|p| p.as_ref())
    }

    /// Return the names of all registered plugins, sorted ascending.
    pub fn names(&self) -> Vec<String> {
        let mut names: Vec<String> = self.plugins.keys().cloned().collect();
        names.sort();
        names
    }

    /// Invoke [`Plugin::init`] on every registered plugin.
    pub fn init_all(&self) -> Result<(), PluginError> {
        for plugin in self.plugins.values() {
            plugin.init()?;
        }
        Ok(())
    }
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_io_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let plugin_err = PluginError::from(io_err);
        assert!(
            matches!(plugin_err, PluginError::InitFailed(ref s) if s.contains("file not found"))
        );
    }

    struct DummyPlugin {
        name: String,
    }

    impl Plugin for DummyPlugin {
        fn name(&self) -> &str {
            &self.name
        }

        fn version(&self) -> &str {
            "1.0.0"
        }
    }

    #[test]
    fn registry_register_get_and_init_all() {
        let mut registry = PluginRegistry::new();
        registry.register(Box::new(DummyPlugin { name: "alpha".to_string() })).unwrap();
        assert_eq!(registry.get("alpha").unwrap().version(), "1.0.0");
        assert_eq!(registry.names(), vec!["alpha".to_string()]);
        registry.init_all().unwrap();
    }
}
