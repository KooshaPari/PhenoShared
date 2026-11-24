//! Phenotype MCP Asset - Asset management handlers for MCP servers
//!
//! Provides functionality for:
//! - Asset discovery in directories
//! - Building asset packs
//! - Validating manifests
//! - Resolving dependencies
//! - Getting asset information

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

pub mod handler;
pub mod manifest;
pub mod discovery;
pub mod build;
pub mod validation;
pub mod dependencies;
pub mod types;

pub use handler::*;
pub use manifest::*;
pub use discovery::*;
pub use build::*;
pub use validation::*;
pub use dependencies::*;
pub use types::*;

/// Version of this crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
