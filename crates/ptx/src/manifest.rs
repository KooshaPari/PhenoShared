//! Manifest helpers — read/write the PTX manifest that records the
//! gate-run results under `target/ptx/manifest.json`.
//!
//! The manifest is intentionally self-describing: every field has a
//! dedicated schema-version so consumers can branch on the version
//! without parsing prose.

use std::path::{Path, PathBuf};

/// Schema-versioned manifest envelope. Bump `SCHEMA_VERSION` whenever a
/// field is added, removed, or renamed.
pub const SCHEMA_VERSION: u32 = 1;

/// Path under the workspace root where the manifest is written.
#[must_use]
pub fn manifest_path(workspace_root: &Path) -> PathBuf {
    workspace_root
        .join("target")
        .join("ptx")
        .join("manifest.json")
}

/// Result of writing the manifest — `wrote_new` distinguishes between
/// "fresh ledger" vs. "append/overwrite".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WriteOutcome {
    /// The file did not exist; it was created.
    WroteNew,
    /// The file already existed; it was overwritten.
    Overwrote,
}

/// The runtime JSON view of a manifest. Real implementations will
/// deserialize this from disk in a later phase; the stub stores the
/// schema version + sequence name + a sha256 placeholder for content
/// addressing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Manifest {
    /// Mirror of `SCHEMA_VERSION`.
    pub schema: u32,
    /// Gate run identifier (typically a UTC timestamp in RFC3339 form).
    pub run_id: String,
    /// Names of the gates that were evaluated.
    pub gates: Vec<String>,
}

impl Manifest {
    /// Construct an empty manifest — every field gets a sensible default.
    #[must_use]
    pub fn empty() -> Self {
        Self {
            schema: SCHEMA_VERSION,
            run_id: String::new(),
            gates: Vec::new(),
        }
    }

    /// Insert a gate name into the ordered sequence.
    pub fn record(&mut self, gate_name: impl Into<String>) {
        self.gates.push(gate_name.into());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schema_version_round_trips() {
        assert_eq!(SCHEMA_VERSION, 1);
    }

    #[test]
    fn manifest_path_is_under_target_ptx() {
        let p = manifest_path(Path::new("/workspace"));
        let s = p.to_string_lossy().replace('\\', "/");
        assert_eq!(s, "/workspace/target/ptx/manifest.json");
    }

    #[test]
    fn record_appends_gate_names_in_order() {
        let mut m = Manifest::empty();
        m.record("fmt");
        m.record("clippy");
        assert_eq!(m.gates, vec!["fmt".to_string(), "clippy".to_string()]);
    }
}
