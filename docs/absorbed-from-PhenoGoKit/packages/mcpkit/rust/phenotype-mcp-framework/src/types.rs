//! MCP Protocol types

use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;

fn deserialize_jsonrpc_id<'de, D>(deserializer: D) -> Result<Option<Value>, D::Error>
where
    D: Deserializer<'de>,
{
    Value::deserialize(deserializer).map(Some)
}

/// MCP request structure (JSON-RPC)
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct McpRequest {
    pub jsonrpc: String,
    #[serde(default, deserialize_with = "deserialize_jsonrpc_id")]
    pub id: Option<Value>,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
}

/// MCP response structure (JSON-RPC)
#[derive(Debug, Clone, Serialize)]
pub struct McpResponse {
    pub jsonrpc: &'static str,
    pub id: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<McpError>,
}

impl McpResponse {
    /// Create a successful response
    pub fn success(id: Option<Value>, result: Value) -> Self {
        Self {
            jsonrpc: crate::JSONRPC_VERSION,
            id,
            result: Some(result),
            error: None,
        }
    }

    /// Create an error response
    pub fn error(id: Option<Value>, code: i32, message: String, data: Option<Value>) -> Self {
        Self {
            jsonrpc: crate::JSONRPC_VERSION,
            id,
            result: None,
            error: Some(McpError {
                code,
                message,
                data,
            }),
        }
    }

    /// Create a "method not found" error response
    pub fn method_not_found(id: Option<Value>, method: &str) -> Self {
        Self::error(
            id,
            crate::error_codes::METHOD_NOT_FOUND,
            format!("Method not found: {}", method),
            None,
        )
    }

    /// Create an "invalid params" error response
    pub fn invalid_params(id: Option<Value>, message: &str) -> Self {
        Self::error(
            id,
            crate::error_codes::INVALID_PARAMS,
            message.to_string(),
            None,
        )
    }
}

/// MCP error structure
#[derive(Debug, Clone, Serialize)]
pub struct McpError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

/// Server capabilities
#[derive(Debug, Clone, Default, Serialize)]
pub struct ServerCapabilities {
    pub tools: ToolCapabilities,
}

/// Tool capabilities
#[derive(Debug, Clone, Default, Serialize)]
pub struct ToolCapabilities {
    pub list_changed: bool,
}

/// Tool definition
#[derive(Debug, Clone, Serialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub input_schema: Value,
}

impl Tool {
    /// Create a new tool definition
    pub fn new(
        name: impl Into<String>,
        description: impl Into<String>,
        input_schema: Value,
    ) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            input_schema,
        }
    }

    /// Create a tool with a simple object schema
    pub fn with_properties(
        name: impl Into<String>,
        description: impl Into<String>,
        properties: Value,
        required: Vec<String>,
    ) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            input_schema: serde_json::json!({
                "type": "object",
                "properties": properties,
                "required": required,
            }),
        }
    }
}

/// Server information
#[derive(Debug, Clone, Serialize)]
pub struct ServerInfo {
    pub name: String,
    pub version: String,
}

impl ServerInfo {
    /// Create new server info
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
        }
    }
}

/// Initialize result
#[derive(Debug, Clone, Serialize)]
pub struct InitializeResult {
    pub protocol_version: &'static str,
    pub capabilities: ServerCapabilities,
    pub server_info: ServerInfo,
}

impl InitializeResult {
    /// Create a new initialize result
    pub fn new(server_info: ServerInfo) -> Self {
        Self {
            protocol_version: crate::MCP_PROTOCOL_VERSION,
            capabilities: ServerCapabilities::default(),
            server_info,
        }
    }

    /// Create with custom capabilities
    pub fn with_capabilities(mut self, capabilities: ServerCapabilities) -> Self {
        self.capabilities = capabilities;
        self
    }
}

/// Tools list result
#[derive(Debug, Clone, Serialize)]
pub struct ToolsListResult {
    pub tools: Vec<Tool>,
}

impl ToolsListResult {
    /// Create a new tools list result
    pub fn new(tools: Vec<Tool>) -> Self {
        Self { tools }
    }
}

/// Tool content item
#[derive(Debug, Clone, Serialize)]
pub struct ToolContent {
    #[serde(rename = "type")]
    pub content_type: &'static str,
    pub text: String,
}

impl ToolContent {
    /// Create text content
    pub fn text(text: impl Into<String>) -> Self {
        Self {
            content_type: "text",
            text: text.into(),
        }
    }
}

/// Tool call result
#[derive(Debug, Clone, Serialize)]
pub struct ToolCallResult {
    pub content: Vec<ToolContent>,
    pub is_error: bool,
}

impl ToolCallResult {
    /// Create a successful tool result
    pub fn success(text: impl Into<String>) -> Self {
        Self {
            content: vec![ToolContent::text(text)],
            is_error: false,
        }
    }

    /// Create an error tool result
    pub fn error(text: impl Into<String>) -> Self {
        Self {
            content: vec![ToolContent::text(text)],
            is_error: true,
        }
    }

    /// Create from a Result
    pub fn from_result(result: Result<String, String>) -> Self {
        match result {
            Ok(text) => Self::success(text),
            Err(text) => Self::error(text),
        }
    }
}
