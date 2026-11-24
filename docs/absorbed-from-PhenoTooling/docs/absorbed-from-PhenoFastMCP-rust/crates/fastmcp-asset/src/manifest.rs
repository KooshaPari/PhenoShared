//! Manifest module — re-export shim for `PackManifest`.
//!
//! In the source crate (`KooshaPari/McpKit/rust/phenotype-mcp-asset`),
//! `manifest.rs` was declared as a separate sibling module. In this folded
//! extraction, `PackManifest` and its related types live in [`crate::types`];
//! this module is preserved as a re-export shim so downstream code referencing
//! `phenotype_mcp_asset::manifest::*` continues to work.
//!
//! See `BUILD_STATUS.md` for the full rationale.

pub use crate::types::{AssetSpec, DependencySpec, PackManifest};
