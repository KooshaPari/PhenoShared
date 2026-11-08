//! Phenotype MCP Core - Model Context Protocol implementation
//!
//! Provides the core protocol types and handlers for MCP servers
//! and clients, following the Anthropic MCP specification.
//!
//! # Features
//!
//! - JSON-RPC 2.0 protocol support
//! - Tool definition and execution
//! - Resource management
//! - Server capabilities
//! - Transport abstractions (SSE, stdio)
//!
//! # Usage
//!
//! ```rust,ignore
//! use phenotype_mcp_core::{Server, ServerInfo, Tool};
//!
//! let server = Server::new(ServerInfo::new("my-server", "1.0.0"))
//!     .with_tool(Tool::new("echo", "Echoes input"));
//! ```

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

pub mod client;
pub mod error;
pub mod handlers;
pub mod protocol;
pub mod resources;
pub mod server;
pub mod tools;
pub mod transport;

pub use client::*;
pub use error::*;
pub use handlers::*;
pub use protocol::*;
pub use resources::*;
pub use server::*;
pub use tools::*;
pub use transport::*;

/// MCP protocol version
pub const MCP_PROTOCOL_VERSION: &str = "2024-11-05";

/// JSON-RPC version
pub const JSONRPC_VERSION: &str = "2.0";

/// MCP server information
#[derive(Debug, Clone)]
pub struct ServerInfo {
    pub name: String,
    pub version: String,
    pub protocol_version: String,
}

impl ServerInfo {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
            protocol_version: MCP_PROTOCOL_VERSION.to_string(),
        }
    }
}

/// Client information
#[derive(Debug, Clone)]
pub struct ClientInfo {
    pub name: String,
    pub version: String,
}

impl ClientInfo {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
        }
    }
}

/// Request metadata
#[derive(Debug, Clone, Default)]
pub struct RequestMeta {
    pub progress_token: Option<String>,
}

/// Initialize request
#[derive(Debug, Clone)]
pub struct InitializeRequest {
    pub protocol_version: String,
    pub capabilities: ClientCapabilities,
    pub client_info: ClientInfo,
}

/// Initialize response
#[derive(Debug, Clone)]
pub struct InitializeResponse {
    pub protocol_version: String,
    pub capabilities: ServerCapabilities,
    pub server_info: ServerInfo,
}

/// Client capabilities
#[derive(Debug, Clone, Default)]
pub struct ClientCapabilities {
    pub roots: Option<RootCapabilities>,
}

/// Root capabilities
#[derive(Debug, Clone, Default)]
pub struct RootCapabilities {
    pub list_changed: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_info() {
        let info = ServerInfo::new("test-server", "1.0.0");
        assert_eq!(info.name, "test-server");
        assert_eq!(info.version, "1.0.0");
        assert_eq!(info.protocol_version, MCP_PROTOCOL_VERSION);
    }

    #[test]
    fn test_client_info() {
        let info = ClientInfo::new("test-client", "2.0.0");
        assert_eq!(info.name, "test-client");
        assert_eq!(info.version, "2.0.0");
    }
}
