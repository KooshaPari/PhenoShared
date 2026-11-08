//! Phenotype MCP Framework - Shared MCP server framework
//!
//! Provides reusable types and server infrastructure for building MCP servers
//! with JSON-RPC framing and tool dispatch.

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

pub mod server;
pub mod transport;
pub mod types;

pub use server::*;
pub use transport::*;
pub use types::*;

/// MCP protocol version
pub const MCP_PROTOCOL_VERSION: &str = "2024-11-05";

/// JSON-RPC version
pub const JSONRPC_VERSION: &str = "2.0";

/// JSON-RPC error codes
pub mod error_codes {
    /// Parse error
    pub const PARSE_ERROR: i32 = -32700;
    /// Invalid request
    pub const INVALID_REQUEST: i32 = -32600;
    /// Method not found
    pub const METHOD_NOT_FOUND: i32 = -32601;
    /// Invalid params
    pub const INVALID_PARAMS: i32 = -32602;
    /// Internal error
    pub const INTERNAL_ERROR: i32 = -32603;
}
