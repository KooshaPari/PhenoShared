//! # PhenoPlugins SDK Examples
//!
//! Reference plugin implementations that exercise the
//! [`pheno-plugin-core`] SDK. These examples are deliberately small,
//! in-memory, and dependency-free so that they can be read as
//! documentation as well as compiled.
//!
//! ## Plugins in this crate
//!
//! - [`memory_vcs::MemoryVcsPlugin`] — an in-memory `VcsPlugin` that
//!   stores worktrees and artifacts in a `HashMap`. Useful for tests
//!   and for hosts that want to swap the production git adapter out
//!   in CI.
//! - [`memory_storage::MemoryStoragePlugin`] — an in-memory
//!   `StoragePlugin` that tracks features, work packages, and audit
//!   entries. Useful for tests and ephemeral CI runs.
//! - [`manifest_demo::ManifestDemo`] — a minimal example showing how
//!   to construct and validate a [`PluginManifest`].
//!
//! ## Building a real plugin
//!
//! 1. Implement [`AdapterPlugin`] for your type.
//! 2. Implement one of the port traits ([`VcsPlugin`] or
//!    [`StoragePlugin`]) if your adapter fits a known shape.
//! 3. Build a [`PluginManifest`] and call
//!    [`PluginManifest::validate`] before registering.
//! 4. Register the plugin with a [`PluginRegistry`].
//!
//! [`AdapterPlugin`]: pheno_plugin_core::traits::AdapterPlugin
//! [`VcsPlugin`]: pheno_plugin_core::traits::VcsPlugin
//! [`StoragePlugin`]: pheno_plugin_core::traits::StoragePlugin
//! [`PluginManifest`]: pheno_plugin_core::manifest::PluginManifest
//! [`PluginRegistry`]: pheno_plugin_core::registry::PluginRegistry

pub mod manifest_demo;
pub mod memory_storage;
pub mod memory_vcs;
