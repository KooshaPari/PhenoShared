//! `trace-gate.toml` manifest parsing.
//!
//! Example manifest:
//! ```toml
//! [[requirement]]
//! fr_id = "FR-001"
//! description = "User can log in"
//!
//! [[requirement]]
//! fr_id = "FR-002"
//! description = "User can register"
//! spec_id = "SPEC-002"
//! ```

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// A single requirement entry in `trace-gate.toml`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ManifestRequirement {
    /// Functional-requirement id to enforce (e.g. `FR-001`).
    pub fr_id: String,
    /// Optional human description (informational only).
    #[serde(default)]
    pub description: String,
    /// Optional spec/ADR reference for richer reporting.
    #[serde(default)]
    pub spec_id: String,
}

/// Parsed `trace-gate.toml`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    /// All requirements that must be traced in source.
    #[serde(default)]
    pub requirement: Vec<ManifestRequirement>,
}

/// Errors from manifest parsing.
#[derive(Debug, Error)]
pub enum ManifestError {
    /// File could not be read.
    #[error("cannot read manifest {path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    /// TOML parse error.
    #[error("invalid manifest TOML in {path}: {source}")]
    Toml {
        path: String,
        #[source]
        source: toml::de::Error,
    },
}

impl Manifest {
    /// Load from a TOML file path.
    pub fn load(path: &str) -> Result<Self, ManifestError> {
        let text = std::fs::read_to_string(path).map_err(|e| ManifestError::Io {
            path: path.to_string(),
            source: e,
        })?;
        toml::from_str(&text).map_err(|e| ManifestError::Toml {
            path: path.to_string(),
            source: e,
        })
    }
}
