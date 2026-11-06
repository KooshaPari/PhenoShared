//! MCP IDL bindings for Rust.
//!
//! Generated from `core/mcp-idl/proto/*.proto` by `tools/codegen.sh`.
//! DO NOT EDIT — regenerate instead.

#![allow(clippy::all, clippy::pedantic, clippy::nursery)]

include!(concat!(env!("OUT_DIR"), "/mcp.rs"));

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
