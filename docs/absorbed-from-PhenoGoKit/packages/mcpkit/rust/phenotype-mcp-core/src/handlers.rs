//! MCP Request Handlers
//!
//! Provides handlers for MCP protocol methods

use crate::{
    protocol::{JsonRpcError, JsonRpcRequest, JsonRpcResponse},
    resources::{Resource, ResourceContent},
    server::ServerCapabilities,
    tools::{CallToolRequest, CallToolResult, Tool, ToolContent},
    ErrorCode, McpError, McpResult,
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Tool handler trait
#[async_trait]
pub trait ToolHandler: Send + Sync {
    /// Get tool name
    fn name(&self) -> &str;

    /// Get tool description
    fn description(&self) -> &str;

    /// Get input schema
    fn input_schema(&self) -> serde_json::Value;

    /// Execute the tool
    async fn execute(
        &self,
        arguments: Option<HashMap<String, serde_json::Value>>,
    ) -> McpResult<Vec<ToolContent>>;
}

/// Resource handler trait
#[async_trait]
pub trait ResourceHandler: Send + Sync {
    /// Get resource URI
    fn uri(&self) -> &str;

    /// Get resource name
    fn name(&self) -> &str;

    /// Get resource description
    fn description(&self) -> Option<&str>;

    /// Read resource content
    async fn read(&self) -> McpResult<ResourceContent>;
}

/// Request router for handling MCP methods
pub struct RequestRouter {
    tools: Arc<RwLock<HashMap<String, Box<dyn ToolHandler>>>>,
    resources: Arc<RwLock<HashMap<String, Box<dyn ResourceHandler>>>>,
    #[allow(dead_code)]
    capabilities: ServerCapabilities,
}

impl RequestRouter {
    /// Create a new request router
    pub fn new(capabilities: ServerCapabilities) -> Self {
        Self {
            tools: Arc::new(RwLock::new(HashMap::new())),
            resources: Arc::new(RwLock::new(HashMap::new())),
            capabilities,
        }
    }

    /// Register a tool handler
    pub async fn register_tool(&self, handler: Box<dyn ToolHandler>) {
        let mut tools = self.tools.write().await;
        tools.insert(handler.name().to_string(), handler);
    }

    /// Register a resource handler
    pub async fn register_resource(&self, handler: Box<dyn ResourceHandler>) {
        let mut resources = self.resources.write().await;
        resources.insert(handler.uri().to_string(), handler);
    }

    /// Handle a JSON-RPC request
    pub async fn handle(&self, request: JsonRpcRequest) -> JsonRpcResponse {
        let id = request.id;

        let result = match request.method.as_str() {
            "tools/list" => self.handle_tools_list().await,
            "tools/call" => self.handle_tool_call(request).await,
            "resources/list" => self.handle_resources_list().await,
            "resources/read" => self.handle_resource_read(request).await,
            _ => Err(McpError::new(
                ErrorCode::MethodNotFound,
                format!("Method not found: {}", request.method),
            )),
        };

        match result {
            Ok(r) => JsonRpcResponse {
                jsonrpc: crate::JSONRPC_VERSION.to_string(),
                id,
                result: Some(serde_json::to_value(r).unwrap_or_default()),
                error: None,
            },
            Err(e) => JsonRpcResponse {
                jsonrpc: crate::JSONRPC_VERSION.to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: e.code() as i32,
                    message: e.message().to_string(),
                    data: None,
                }),
            },
        }
    }

    /// Handle tools/list method
    async fn handle_tools_list(&self) -> McpResult<serde_json::Value> {
        let tools = self.tools.read().await;
        let tool_list: Vec<Tool> = tools
            .values()
            .map(|h| Tool {
                name: h.name().to_string(),
                description: Some(h.description().to_string()),
                input_schema: h.input_schema(),
            })
            .collect();

        Ok(serde_json::to_value(tool_list).unwrap_or_default())
    }

    /// Handle tools/call method
    async fn handle_tool_call(&self, request: JsonRpcRequest) -> McpResult<serde_json::Value> {
        let params: CallToolRequest = serde_json::from_value(request.params.unwrap_or_default())
            .map_err(|e| McpError::new(ErrorCode::InvalidParams, e.to_string()))?;

        let tools = self.tools.read().await;
        let handler = tools.get(&params.name).ok_or_else(|| {
            McpError::new(
                ErrorCode::InvalidParams,
                format!("Tool not found: {}", params.name),
            )
        })?;

        let content = handler.execute(params.arguments).await?;

        let content_text: Vec<ToolContent> = content
            .into_iter()
            .map(|c| match c {
                ToolContent::Text { text } => ToolContent::Text { text },
            })
            .collect();

        let result = CallToolResult {
            content: content_text,
            is_error: None,
        };
        Ok(serde_json::to_value(result).unwrap_or_default())
    }

    /// Handle resources/list method
    async fn handle_resources_list(&self) -> McpResult<serde_json::Value> {
        let resources = self.resources.read().await;
        let resource_list: Vec<Resource> = resources
            .values()
            .map(|h| Resource {
                uri: h.uri().to_string(),
                name: h.name().to_string(),
                description: h.description().map(|s| s.to_string()),
                mime_type: None,
            })
            .collect();

        Ok(serde_json::to_value(resource_list).unwrap_or_default())
    }

    /// Handle resources/read method
    async fn handle_resource_read(&self, request: JsonRpcRequest) -> McpResult<serde_json::Value> {
        let uri = request
            .params
            .as_ref()
            .and_then(|p| p.get("uri"))
            .and_then(|v| v.as_str())
            .ok_or_else(|| McpError::new(ErrorCode::InvalidParams, "Missing uri parameter"))?;

        let resources = self.resources.read().await;
        let handler = resources.get(uri).ok_or_else(|| {
            McpError::new(
                ErrorCode::InvalidParams,
                format!("Resource not found: {}", uri),
            )
        })?;

        let content: ResourceContent = handler.read().await?;
        Ok(serde_json::to_value(content).unwrap_or_default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_router_creation() {
        let _router = RequestRouter::new(ServerCapabilities::default());
        // Should create without panicking
    }
}
