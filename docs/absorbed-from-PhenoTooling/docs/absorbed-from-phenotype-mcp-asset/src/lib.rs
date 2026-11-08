//! Phenotype MCP Asset — asset management handlers for MCP servers
//!
//! Provides functionality for:
//! - Asset discovery in directories
//! - Building asset packs
//! - Validating manifests
//! - Resolving dependencies
//! - Getting asset information
//!
//! ## Origin
//!
//! Extracted from `KooshaPari/McpKit` `rust/phenotype-mcp-asset` v0.2.0 on 2026-06-18,
//! per the McpKit absorption audit (ADR-017 retire pattern, ADR-023 substrate placement).
//! This crate is the only McpKit member with no equivalent in the PhenoFastMCP family
//! (Phenotype-pack asset handling is intentionally omitted by `fastmcp_rust` upstream).
//!
//! See [`ORIGIN.md`](https://github.com/KooshaPari/phenotype-mcp-asset/blob/main/ORIGIN.md)
//! for the full extraction provenance.
//!
//! ## Substrate tier
//!
//! Per ADR-023 (app-substrate placement), this is a **`pheno-*-lib`** — a pure
//! reusable library; language-specific; single concern (file-based pack handling).
//! See ADR-042 (substrate graduation path) for promotion criteria to
//! `phenotype-*-sdk` once 2+ polyglot consumers exist.

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

pub mod handler;
pub mod types;

// Submodules originally declared in the McpKit workspace; implemented as minimal
// stubs in this standalone crate so `AssetHandler` can compile and its unit
// tests can run. See `BUILD_STATUS.md` for the full stub rationale.
pub mod manifest;
pub mod discovery;
pub mod build;
pub mod validation;
pub mod dependencies;

pub use handler::*;
pub use types::*;
// `manifest`, `discovery`, `build`, `validation`, `dependencies` are declared
// above (so they exist as siblings to `handler` + `types`) but we don't
// re-export their contents — they are minimal stubs whose types are not part
// of the public API. See BUILD_STATUS.md.

/// Version of this crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");