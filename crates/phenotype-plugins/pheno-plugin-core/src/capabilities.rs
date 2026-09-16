//! Plugin capability declarations.
//!
//! Capabilities model the **principle of least privilege** for adapters:
//! each plugin must declare, up front, which side-effects it intends to
//! perform. The host can then audit, gate, or rate-limit a plugin based on
//! the capabilities it claims.
//!
//! Capabilities are surfaced through the [`Manifest`](crate::manifest::PluginManifest)
//! and the runtime guard-rail checks in
//! [`guardrails`](crate::guardrails). Adapters are not *forced* to use
//! capabilities, but a plugin that ignores the contract loses the host's
//! trust guarantees (and is a red flag during review).

use serde::{Deserialize, Serialize};

/// Side-effecting surface area that a plugin may exercise.
///
/// Capabilities are *coarse-grained* on purpose: a single flag may unlock a
/// handful of methods, but every flag must be justified by the adapter
/// documentation. We intentionally avoid per-method capability flags because
/// that would balloon the enum to dozens of variants and defeat the goal of
/// a quick, human-readable manifest review.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Capability {
    /// Read-only access to host resources (no writes, no network).
    Read,
    /// Local filesystem reads.
    FilesystemRead,
    /// Local filesystem writes (creates, modifies, deletes).
    FilesystemWrite,
    /// Outbound network access.
    Network,
    /// Spawns child processes.
    Process,
    /// Modifies the working tree (e.g. worktrees, branches, commits).
    WorkingTree,
    /// Reads/writes persistent state in a backing store.
    Storage,
    /// Emits audit-trail entries.
    Audit,
    /// Accesses environment variables from the host.
    Environment,
    /// May execute user-supplied shell commands. **Dangerous — review carefully.**
    ShellExec,
}

impl Capability {
    /// Stable string identifier used in serialized manifests and logs.
    pub fn as_str(self) -> &'static str {
        match self {
            Capability::Read => "read",
            Capability::FilesystemRead => "filesystem_read",
            Capability::FilesystemWrite => "filesystem_write",
            Capability::Network => "network",
            Capability::Process => "process",
            Capability::WorkingTree => "working_tree",
            Capability::Storage => "storage",
            Capability::Audit => "audit",
            Capability::Environment => "environment",
            Capability::ShellExec => "shell_exec",
        }
    }

    /// Parse a capability from its stable string identifier.
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "read" => Some(Capability::Read),
            "filesystem_read" => Some(Capability::FilesystemRead),
            "filesystem_write" => Some(Capability::FilesystemWrite),
            "network" => Some(Capability::Network),
            "process" => Some(Capability::Process),
            "working_tree" => Some(Capability::WorkingTree),
            "storage" => Some(Capability::Storage),
            "audit" => Some(Capability::Audit),
            "environment" => Some(Capability::Environment),
            "shell_exec" => Some(Capability::ShellExec),
            _ => None,
        }
    }

    /// All defined capabilities. Useful for tests and tooling.
    pub const ALL: &'static [Capability] = &[
        Capability::Read,
        Capability::FilesystemRead,
        Capability::FilesystemWrite,
        Capability::Network,
        Capability::Process,
        Capability::WorkingTree,
        Capability::Storage,
        Capability::Audit,
        Capability::Environment,
        Capability::ShellExec,
    ];
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn test_capability_as_str_is_stable() {
        // Pin the on-the-wire names. If any of these strings change,
        // manifests serialized by older builds will silently break.
        assert_eq!(Capability::Read.as_str(), "read");
        assert_eq!(Capability::FilesystemRead.as_str(), "filesystem_read");
        assert_eq!(Capability::FilesystemWrite.as_str(), "filesystem_write");
        assert_eq!(Capability::Network.as_str(), "network");
        assert_eq!(Capability::Process.as_str(), "process");
        assert_eq!(Capability::WorkingTree.as_str(), "working_tree");
        assert_eq!(Capability::Storage.as_str(), "storage");
        assert_eq!(Capability::Audit.as_str(), "audit");
        assert_eq!(Capability::Environment.as_str(), "environment");
        assert_eq!(Capability::ShellExec.as_str(), "shell_exec");
    }

    #[test]
    fn test_capability_roundtrip() {
        for cap in Capability::ALL {
            let s = cap.as_str();
            let parsed = Capability::parse(s).unwrap_or_else(|| panic!("failed to parse {}", s));
            assert_eq!(parsed, *cap, "roundtrip mismatch for {:?}", cap);
        }
    }

    #[test]
    fn test_capability_from_str_unknown_returns_none() {
        assert!(Capability::parse("nope").is_none());
        assert!(Capability::parse("").is_none());
        assert!(Capability::parse("READ").is_none()); // case-sensitive
    }

    #[test]
    fn test_capability_serde_json_roundtrip() {
        let cap = Capability::ShellExec;
        let json = serde_json::to_string(&cap).unwrap();
        assert_eq!(json, "\"shell_exec\"");
        let parsed: Capability = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed, cap);
    }

    #[test]
    fn test_capability_serde_json_all_variants() {
        for cap in Capability::ALL {
            let json = serde_json::to_string(cap).unwrap();
            let parsed: Capability = serde_json::from_str(&json).unwrap();
            assert_eq!(parsed, *cap);
        }
    }

    #[test]
    fn test_capability_hash_eq_consistent() {
        let mut set = HashSet::new();
        set.insert(Capability::Network);
        set.insert(Capability::Network);
        set.insert(Capability::Storage);
        assert_eq!(set.len(), 2);
        assert!(set.contains(&Capability::Network));
        assert!(set.contains(&Capability::Storage));
    }

    #[test]
    fn test_capability_copy_semantics() {
        // Verify the enum is `Copy` (this won't compile otherwise).
        let a = Capability::Network;
        let b = a; // Copy, not move
        let c = a;
        assert_eq!(b, c);
    }

    #[test]
    fn test_capability_all_count() {
        // If you add a new capability, this forces you to also update `as_str`,
        // `from_str`, and the roundtrip test.
        assert_eq!(Capability::ALL.len(), 10);
    }
}
