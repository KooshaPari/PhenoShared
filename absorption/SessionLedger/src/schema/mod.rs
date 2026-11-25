//! Versioned on-disk schema scaffold for durable [`MemoryStore`] persistence.
//!
//! The root crate keeps domain logic pure; this module defines the forward-only
//! SQL migrations that a future SQLite-backed store adapter can apply at open
//! time. Apply migrations through [`migrate::apply_all`] when the `sqlite`
//! feature is enabled.

#[cfg(feature = "sqlite")]
pub mod migrate;

/// Current schema version after all bundled migrations are applied.
pub const CURRENT_VERSION: u32 = 2;

/// One forward-only migration entry in the manifest.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Migration {
    /// Monotonic schema version (1-based).
    pub version: u32,
    /// Stable migration name (`snake_case`).
    pub name: &'static str,
    /// SQL executed when upgrading to this version.
    pub sql: &'static str,
}

/// Ordered migration manifest — the SSOT for durable schema evolution.
#[must_use]
pub fn migrations() -> &'static [Migration] {
    &[
        Migration {
            version: 1,
            name: "initial_memory_facts",
            sql: include_str!("migrations/001_initial.sql"),
        },
        Migration {
            version: 2,
            name: "memory_fact_insertion_order",
            sql: include_str!("migrations/002_memory_fact_insertion_order.sql"),
        },
    ]
}

/// Returns the highest bundled migration version.
#[must_use]
pub fn latest_version() -> u32 {
    migrations().iter().map(|migration| migration.version).max().unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manifest_versions_are_strictly_increasing() {
        let versions = migrations().iter().map(|m| m.version).collect::<Vec<_>>();
        for window in versions.windows(2) {
            assert!(window[0] < window[1], "migration versions must increase");
        }
        assert_eq!(latest_version(), CURRENT_VERSION);
    }

    #[test]
    fn each_migration_has_nonempty_sql() {
        for migration in migrations() {
            assert!(!migration.name.is_empty());
            assert!(!migration.sql.trim().is_empty(), "migration {}", migration.version);
        }
    }
}
