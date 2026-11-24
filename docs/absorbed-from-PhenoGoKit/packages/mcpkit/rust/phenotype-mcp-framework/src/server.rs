//! MCP Server framework

use async_trait::async_trait;
use serde_json::Value;

use crate::types::*;

/// Trait for MCP servers
///
/// Implement this trait to create a custom MCP server with specific tools.
pub trait McpServer {
    /// Get server name
    fn name(&self) -> &'static str;

    /// Get server version
    fn version(&self) -> &'static str;

    /// Get the list of tools this server provides
    fn tools(&self) -> Vec<Tool>;

    /// Handle a tool call
    ///
    /// Returns a result that will be converted to a ToolCallResult
    fn handle_tool(&self, name: String, arguments: Value) -> Result<String, String>;

    /// Handle initialization request
    fn handle_initialize(&self, id: Option<Value>) -> McpResponse {
        let server_info = ServerInfo::new(self.name(), self.version());
        let result = InitializeResult::new(server_info);
        McpResponse::success(id, serde_json::to_value(result).unwrap())
    }

    /// Handle tools/list request
    fn handle_tools_list(&self, id: Option<Value>) -> McpResponse {
        let tools = self.tools();
        let result = ToolsListResult::new(tools);
        McpResponse::success(id, serde_json::to_value(result).unwrap())
    }

    /// Handle tools/call request
    fn handle_tool_call(&self, id: Option<Value>, params: Option<Value>) -> McpResponse {
        let params = match params {
            Some(p) => p,
            None => return McpResponse::invalid_params(id, "Missing params"),
        };

        let name = params
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let arguments = params
            .get("arguments")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));

        let result = self.handle_tool(name, arguments);
        let tool_result = ToolCallResult::from_result(result);

        match serde_json::to_value(tool_result) {
            Ok(value) => McpResponse::success(id, value),
            Err(e) => McpResponse::error(
                id,
                crate::error_codes::INTERNAL_ERROR,
                format!("Failed to serialize result: {}", e),
                None,
            ),
        }
    }

    /// Handle a request
    fn handle_request(&self, request: McpRequest) -> McpResponse {
        tracing::debug!("Handling method: {}", request.method);

        match request.method.as_str() {
            "initialize" => self.handle_initialize(request.id),
            "tools/list" => self.handle_tools_list(request.id),
            "tools/call" => self.handle_tool_call(request.id, request.params),
            _ => McpResponse::method_not_found(request.id, &request.method),
        }
    }
}

/// Trait for async MCP servers
///
/// Use this when your tool handlers need to be async.
#[async_trait]
pub trait AsyncMcpServer: Send + Sync {
    /// Get server name
    fn name(&self) -> &'static str;

    /// Get server version
    fn version(&self) -> &'static str;

    /// Get the list of tools this server provides
    fn tools(&self) -> Vec<Tool>;

    /// Handle a tool call asynchronously
    async fn handle_tool(&self, name: String, arguments: Value) -> Result<String, String>;

    /// Handle initialization request
    fn handle_initialize(&self, id: Option<Value>) -> McpResponse {
        let server_info = ServerInfo::new(self.name(), self.version());
        let result = InitializeResult::new(server_info);
        McpResponse::success(id, serde_json::to_value(result).unwrap())
    }

    /// Handle tools/list request
    fn handle_tools_list(&self, id: Option<Value>) -> McpResponse {
        let tools = self.tools();
        let result = ToolsListResult::new(tools);
        McpResponse::success(id, serde_json::to_value(result).unwrap())
    }

    /// Handle tools/call request asynchronously
    async fn handle_tool_call(&self, id: Option<Value>, params: Option<Value>) -> McpResponse {
        let params = match params {
            Some(p) => p,
            None => return McpResponse::invalid_params(id, "Missing params"),
        };

        let name = params
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let arguments = params
            .get("arguments")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));

        let result = self.handle_tool(name, arguments).await;
        let tool_result = ToolCallResult::from_result(result);

        match serde_json::to_value(tool_result) {
            Ok(value) => McpResponse::success(id, value),
            Err(e) => McpResponse::error(
                id,
                crate::error_codes::INTERNAL_ERROR,
                format!("Failed to serialize result: {}", e),
                None,
            ),
        }
    }

    /// Handle a request asynchronously
    async fn handle_request(&self, request: McpRequest) -> McpResponse {
        tracing::debug!("Handling method: {}", request.method);

        match request.method.as_str() {
            "initialize" => self.handle_initialize(request.id),
            "tools/list" => self.handle_tools_list(request.id),
            "tools/call" => self.handle_tool_call(request.id, request.params).await,
            _ => McpResponse::method_not_found(request.id, &request.method),
        }
    }
}

/// Helper struct for building tool schemas
pub struct ToolSchemaBuilder;

impl ToolSchemaBuilder {
    /// Build a string property
    pub fn string_prop(description: impl Into<String>) -> Value {
        serde_json::json!({
            "type": "string",
            "description": description.into()
        })
    }

    /// Build a boolean property
    pub fn bool_prop(description: impl Into<String>, default: bool) -> Value {
        serde_json::json!({
            "type": "boolean",
            "description": description.into(),
            "default": default
        })
    }

    /// Build an integer property
    pub fn int_prop(description: impl Into<String>, default: Option<i64>) -> Value {
        let mut prop = serde_json::json!({
            "type": "integer",
            "description": description.into()
        });
        if let Some(d) = default {
            prop["default"] = d.into();
        }
        prop
    }

    /// Build an array property
    pub fn array_prop(description: impl Into<String>, item_type: &str) -> Value {
        serde_json::json!({
            "type": "array",
            "description": description.into(),
            "items": { "type": item_type }
        })
    }

    /// Build an object property
    pub fn object_prop(description: impl Into<String>) -> Value {
        serde_json::json!({
            "type": "object",
            "description": description.into()
        })
    }
}
