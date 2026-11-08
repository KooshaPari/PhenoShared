//! MCP Transport layer

use crate::protocol::{JsonRpcRequest, JsonRpcResponse};
use async_trait::async_trait;

/// Transport trait for MCP communication
#[async_trait]
pub trait Transport: Send + Sync {
    /// Send a request and receive a response
    async fn send(&self, request: JsonRpcRequest) -> crate::error::Result<JsonRpcResponse>;

    /// Start listening for incoming requests
    async fn listen(&self) -> crate::error::Result<()>;
}

/// SSE (Server-Sent Events) transport
pub struct SseTransport {
    #[allow(dead_code)]
    endpoint: String,
}

impl SseTransport {
    pub fn new(endpoint: impl Into<String>) -> Self {
        Self {
            endpoint: endpoint.into(),
        }
    }
}

#[async_trait]
impl Transport for SseTransport {
    async fn send(&self, _request: JsonRpcRequest) -> crate::error::Result<JsonRpcResponse> {
        unimplemented!("SSE transport not yet implemented")
    }

    async fn listen(&self) -> crate::error::Result<()> {
        unimplemented!("SSE transport not yet implemented")
    }
}

/// Stdio transport for subprocess communication
pub struct StdioTransport;

impl StdioTransport {
    pub fn new() -> Self {
        Self
    }
}

impl Default for StdioTransport {
    fn default() -> Self {
        Self::new()
    }
}
