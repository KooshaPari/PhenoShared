//! Plugin manifest — the declared contract for an adapter.
//!
//! The manifest is what the host reads *before* loading a plugin. It
//! answers four questions:
//!
//! 1. **Who** is this plugin? (`name`, `version`)
//! 2. **What** does it do? (`description`, `kind`)
//! 3. **What does it need?** (`capabilities`, `min_host_version`)
//! 4. **Is it well-formed?** (validation via [`PluginManifest::validate`])
//!
//! A manifest that fails validation must be rejected at registration time
//! — see [`crate::guardrails`] for the runtime checks.

use serde::{Deserialize, Serialize};

use crate::capabilities::Capability;
use crate::error::{PluginError, PluginResult};

/// The kind of adapter this manifest declares.
///
/// Used by the host to pick which trait object (`VcsPlugin` or
/// `StoragePlugin`) to materialize. A plugin that does not match its
/// declared kind cannot be registered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PluginKind {
    /// Version-control-system adapter (`VcsPlugin`).
    Vcs,
    /// Persistent-storage adapter (`StoragePlugin`).
    Storage,
    /// General-purpose adapter (does not implement a core trait).
    Generic,
}

impl PluginKind {
    /// Stable string identifier used in serialized manifests and logs.
    pub fn as_str(self) -> &'static str {
        match self {
            PluginKind::Vcs => "vcs",
            PluginKind::Storage => "storage",
            PluginKind::Generic => "generic",
        }
    }

    /// Parse a plugin kind from its stable string identifier.
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "vcs" => Some(PluginKind::Vcs),
            "storage" => Some(PluginKind::Storage),
            "generic" => Some(PluginKind::Generic),
            _ => None,
        }
    }
}

/// Declared contract for a plugin.
///
/// Hosts should call [`PluginManifest::validate`] before accepting a
/// manifest into a registry. The validation step is intentionally strict:
/// the cost of a bad manifest is paid once at registration, but the cost
/// of a manifest that "mostly works" leaks into every plugin call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginManifest {
    /// Stable, unique name (e.g. `"git"`, `"sqlite"`).
    pub name: String,
    /// Semantic version of the plugin, e.g. `"0.1.0"`.
    pub version: String,
    /// Human-readable description.
    #[serde(default)]
    pub description: String,
    /// What the plugin implements.
    pub kind: PluginKind,
    /// Capabilities the plugin intends to use.
    #[serde(default)]
    pub capabilities: Vec<Capability>,
    /// Minimum host version required (semver). Optional.
    #[serde(default)]
    pub min_host_version: Option<String>,
    /// Other plugins this plugin depends on. Optional.
    #[serde(default)]
    pub depends_on: Vec<String>,
}

impl PluginManifest {
    /// Build a new manifest with the minimum required fields and validate
    /// it. Returns the validated manifest, or the first validation error.
    pub fn new(
        name: impl Into<String>,
        version: impl Into<String>,
        kind: PluginKind,
    ) -> PluginResult<Self> {
        let m = Self {
            name: name.into(),
            version: version.into(),
            description: String::new(),
            kind,
            capabilities: Vec::new(),
            min_host_version: None,
            depends_on: Vec::new(),
        };
        m.validate()?;
        Ok(m)
    }

    /// Builder-style setter for `description`.
    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = description.into();
        self
    }

    /// Builder-style setter for `capabilities`.
    pub fn with_capabilities(mut self, capabilities: Vec<Capability>) -> Self {
        self.capabilities = capabilities;
        self
    }

    /// Builder-style setter for `min_host_version`.
    pub fn with_min_host_version(mut self, v: impl Into<String>) -> Self {
        self.min_host_version = Some(v.into());
        self
    }

    /// Builder-style setter for `depends_on`.
    pub fn with_depends_on(mut self, deps: Vec<String>) -> Self {
        self.depends_on = deps;
        self
    }

    /// Validate every field. Returns the first failure.
    ///
    /// Validation rules:
    /// - `name` matches the safe-name regex (see
    ///   [`crate::guardrails::validate_plugin_name`]).
    /// - `version` is a parseable semver triple (`X.Y.Z`).
    /// - `description`, if present, is ≤ 512 chars.
    /// - `capabilities` does not contain duplicates.
    /// - `depends_on` entries are themselves valid plugin names.
    /// - A plugin does not list itself in `depends_on`.
    pub fn validate(&self) -> PluginResult<()> {
        crate::guardrails::validate_plugin_name(&self.name)?;
        crate::guardrails::validate_semver(&self.version)?;

        if self.description.len() > 512 {
            return Err(PluginError::Validation(format!(
                "description too long: {} bytes (max 512)",
                self.description.len()
            )));
        }

        if let Some(v) = &self.min_host_version {
            crate::guardrails::validate_semver(v)?;
        }

        // Duplicates in the capabilities list are almost always a sign of
        // a copy/paste bug. We fail fast rather than silently dedupe.
        let mut seen = std::collections::HashSet::new();
        for cap in &self.capabilities {
            if !seen.insert(cap) {
                return Err(PluginError::Validation(format!(
                    "duplicate capability: {:?}",
                    cap
                )));
            }
        }

        for dep in &self.depends_on {
            crate::guardrails::validate_plugin_name(dep)?;
            if dep == &self.name {
                return Err(PluginError::Validation(format!(
                    "plugin '{}' cannot depend on itself",
                    self.name
                )));
            }
        }

        Ok(())
    }

    /// Returns true if the manifest declares a capability.
    pub fn has_capability(&self, cap: Capability) -> bool {
        self.capabilities.contains(&cap)
    }

    /// Number of distinct capabilities declared.
    pub fn capability_count(&self) -> usize {
        self.capabilities.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_minimal_manifest_validates() {
        let m = PluginManifest::new("git", "0.1.0", PluginKind::Vcs).unwrap();
        assert_eq!(m.name, "git");
        assert_eq!(m.version, "0.1.0");
        assert_eq!(m.kind, PluginKind::Vcs);
        assert!(m.capabilities.is_empty());
        assert!(m.description.is_empty());
        assert!(m.depends_on.is_empty());
        assert!(m.min_host_version.is_none());
    }

    #[test]
    fn test_builder_accumulates_fields() {
        let m = PluginManifest::new("sqlite", "0.2.1", PluginKind::Storage)
            .unwrap()
            .with_description("SQLite storage adapter".to_string())
            .with_capabilities(vec![Capability::Storage, Capability::Audit])
            .with_min_host_version("0.1.0".to_string())
            .with_depends_on(vec!["core".to_string()]);
        assert_eq!(m.description, "SQLite storage adapter");
        assert_eq!(m.capability_count(), 2);
        assert_eq!(m.min_host_version.as_deref(), Some("0.1.0"));
        assert_eq!(m.depends_on, vec!["core".to_string()]);
    }

    #[test]
    fn test_invalid_name_rejected() {
        let err = PluginManifest::new("Bad Name!", "0.1.0", PluginKind::Vcs);
        assert!(err.is_err());
    }

    #[test]
    fn test_invalid_version_rejected() {
        let err = PluginManifest::new("ok", "not-semver", PluginKind::Vcs);
        assert!(err.is_err());
    }

    #[test]
    fn test_duplicate_capability_rejected() {
        let m = PluginManifest::new("dup", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_capabilities(vec![Capability::Network, Capability::Network]);
        let err = m.validate();
        assert!(err.is_err(), "duplicate capability should fail");
    }

    #[test]
    fn test_self_dependency_rejected() {
        let m = PluginManifest::new("loop", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_depends_on(vec!["loop".to_string()]);
        let err = m.validate();
        assert!(err.is_err());
    }

    #[test]
    fn test_description_too_long_rejected() {
        let big = "a".repeat(513);
        let m = PluginManifest::new("ok", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_description(big);
        let err = m.validate();
        assert!(err.is_err());
    }

    #[test]
    fn test_description_at_limit_accepted() {
        let just_enough = "a".repeat(512);
        let m = PluginManifest::new("ok", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_description(just_enough);
        assert!(m.validate().is_ok());
    }

    #[test]
    fn test_serde_roundtrip() {
        let m = PluginManifest::new("git", "1.2.3", PluginKind::Vcs)
            .unwrap()
            .with_description("Git adapter")
            .with_capabilities(vec![Capability::FilesystemRead, Capability::WorkingTree]);
        let json = serde_json::to_string(&m).unwrap();
        let parsed: PluginManifest = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.name, m.name);
        assert_eq!(parsed.version, m.version);
        assert_eq!(parsed.kind, m.kind);
        assert_eq!(parsed.capabilities, m.capabilities);
        assert_eq!(parsed.description, m.description);
    }

    #[test]
    fn test_serde_deserialize_minimal() {
        // Only required fields present; everything else defaults.
        let json = r#"{"name":"git","version":"0.1.0","kind":"vcs"}"#;
        let m: PluginManifest = serde_json::from_str(json).unwrap();
        assert_eq!(m.name, "git");
        assert_eq!(m.version, "0.1.0");
        assert_eq!(m.kind, PluginKind::Vcs);
        assert!(m.capabilities.is_empty());
        assert!(m.description.is_empty());
    }

    #[test]
    fn test_serde_rejects_unknown_kind() {
        let json = r#"{"name":"x","version":"0.1.0","kind":"warp_drive"}"#;
        let result: Result<PluginManifest, _> = serde_json::from_str(json);
        assert!(result.is_err());
    }

    #[test]
    fn test_has_capability_works() {
        let m = PluginManifest::new("net", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_capabilities(vec![Capability::Network]);
        assert!(m.has_capability(Capability::Network));
        assert!(!m.has_capability(Capability::Storage));
    }

    #[test]
    fn test_plugin_kind_roundtrip() {
        for k in [PluginKind::Vcs, PluginKind::Storage, PluginKind::Generic] {
            let s = k.as_str();
            let parsed = PluginKind::parse(s).unwrap();
            assert_eq!(parsed, k);
        }
        assert!(PluginKind::parse("not-a-kind").is_none());
    }

    #[test]
    fn test_invalid_min_host_version_rejected() {
        let m = PluginManifest::new("ok", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_min_host_version("garbage");
        assert!(m.validate().is_err());
    }

    #[test]
    fn test_invalid_dependency_name_rejected() {
        let m = PluginManifest::new("ok", "0.1.0", PluginKind::Generic)
            .unwrap()
            .with_depends_on(vec!["has spaces".to_string()]);
        assert!(m.validate().is_err());
    }

    #[test]
    fn test_validate_idempotent() {
        // Calling validate() twice should give the same result.
        let m = PluginManifest::new("git", "0.1.0", PluginKind::Vcs).unwrap();
        assert!(m.validate().is_ok());
        assert!(m.validate().is_ok());
    }
}
