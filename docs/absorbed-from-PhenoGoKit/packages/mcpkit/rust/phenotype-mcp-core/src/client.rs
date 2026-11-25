//! MCP Client implementation
//!
//! Provides a client for connecting to MCP servers

use crate::{
    transport::Transport, ClientCapabilities, ClientInfo, InitializeRequest, InitializeResponse,
    McpResult,
};
use std::sync::Arc;
use tokio::sync::RwLock;

/// MCP Client for connecting to servers
#[allow(dead_code)]
pub struct Client {
    #[allow(dead_code)]
    transport: Box<dyn Transport>,
    client_info: ClientInfo,
    server_info: Option<InitializeResponse>,
    #[allow(dead_code)]
    request_id: Arc<RwLock<u64>>,
}

impl Client {
    /// Create a new MCP client
    pub fn new(transport: Box<dyn Transport>, client_info: ClientInfo) -> Self {
        Self {
            transport,
            client_info,
            server_info: None,
            request_id: Arc::new(RwLock::new(0)),
        }
    }

    /// Initialize the connection
    pub async fn initialize(&mut self) -> McpResult<InitializeResponse> {
        let _request = InitializeRequest {
            protocol_version: crate::MCP_PROTOCOL_VERSION.to_string(),
            capabilities: ClientCapabilities::default(),
            client_info: self.client_info.clone(),
        };

        // This would send the initialize request and parse response
        // Simplified for now
        let response = InitializeResponse {
            protocol_version: crate::MCP_PROTOCOL_VERSION.to_string(),
            capabilities: crate::ServerCapabilities::default(),
            server_info: crate::ServerInfo::new("server", "1.0.0"),
        };

        self.server_info = Some(response.clone());
        Ok(response)
    }

    /// Get server info
    pub fn server_info(&self) -> Option<&InitializeResponse> {
        self.server_info.as_ref()
    }

    /// Check if initialized
    pub fn is_initialized(&self) -> bool {
        self.server_info.is_some()
    }

    /// Generate next request ID
    #[allow(dead_code)]
    async fn next_id(&self) -> u64 {
        let mut id = self.request_id.write().await;
        *id += 1;
        *id
    }
}

/// Client builder
pub struct ClientBuilder {
    client_info: ClientInfo,
    capabilities: ClientCapabilities,
}

impl ClientBuilder {
    /// Create a new client builder
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            client_info: ClientInfo::new(name, version),
            capabilities: ClientCapabilities::default(),
        }
    }

    /// Set client capabilities
    pub fn with_capabilities(mut self, capabilities: ClientCapabilities) -> Self {
        self.capabilities = capabilities;
        self
    }

    /// Build the client
    pub fn build(self, transport: Box<dyn Transport>) -> Client {
        Client {
            transport,
            client_info: self.client_info,
            server_info: None,
            request_id: Arc::new(RwLock::new(0)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_client_builder() {
        let builder = ClientBuilder::new("test-client", "1.0.0");
        assert_eq!(builder.client_info.name, "test-client");
    }
}
