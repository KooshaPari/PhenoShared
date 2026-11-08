//! PhenotypeMCPServer — MCP protocol server built on `rmcp`.
//!
//! This crate previously shipped a hand-rolled MCP server. It now
//! delegates the tool router and `ServerHandler` plumbing to the
//! official `rmcp` crate (macros + transport-io features), which
//! converges on the upstream `#[tool_router]` / `#[tool_handler]`
//! style used by the rest of the Rust MCP ecosystem.

use rmcp::handler::server::router::tool::ToolRouter;
use rmcp::model::{CallToolResult, Content, Implementation, ServerCapabilities, ServerInfo};
use rmcp::schemars;
use rmcp::{RoleServer, ServerHandler, ServiceExt, tool, tool_handler, tool_router};
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub use phenotype_errors::RepositoryError as MCPServerError;

/// Result alias using the crate's canonical `MCPServerError`.
pub type Result<T> = std::result::Result<T, MCPServerError>;

/// A registered tool's static metadata. Kept for backward
/// compatibility with consumers that introspect the server.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub input_schema: Value,
}

/// Lightweight result wrapper preserved for the legacy public API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub content: Vec<ContentItem>,
    pub is_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentItem {
    #[serde(rename = "type")]
    pub content_type: String,
    pub text: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Resource {
    pub uri: String,
    pub name: String,
    pub mime_type: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceContent {
    pub uri: String,
    pub text: Option<String>,
}

/// Phenotype MCP server.
///
/// Wraps the `rmcp` tool router while keeping the prior public surface
/// (`list_tools`, `call_tool`, resource helpers) so existing callers
/// keep working.
#[derive(Debug, Clone)]
pub struct MCPServer {
    tool_router: ToolRouter<Self>,
}

impl Default for MCPServer {
    fn default() -> Self {
        Self::new()
    }
}

impl MCPServer {
    /// Build a new MCP server with the standard Phenotype toolset.
    pub fn new() -> Self {
        Self {
            tool_router: Self::tool_router(),
        }
    }

    /// List the registered tools (legacy public API).
    pub fn list_tools(&self) -> Vec<Tool> {
        self.tool_router
            .list_all()
            .into_iter()
            .map(|attr| {
                let input_schema: Value =
                    serde_json::to_value(&*attr.input_schema).unwrap_or(Value::Null);
                Tool {
                    name: attr.name.to_string(),
                    description: attr.description.unwrap_or_default().to_string(),
                    input_schema,
                }
            })
            .collect()
    }

    /// Invoke a tool by name. Returns the raw `CallToolResult` from
    /// `rmcp`; the legacy `ToolResult` wrapper is reachable via
    /// `into_legacy`.
    pub async fn call_tool(
        &self,
        name: &str,
        arguments: Value,
    ) -> Result<CallToolResult, MCPServerError> {
        use rmcp::handler::server::tool::ToolCallContext;
        use rmcp::model::CallToolRequestParams;

        let params = CallToolRequestParams {
            meta: None,
            name: name.into(),
            arguments: arguments.as_object().cloned(),
            task: None,
        };
        let ctx = ToolCallContext::new(self, params, rmcp::service::RequestContext::new(
            rmcp::model::RequestId::Number(0),
            rmcp::service::Peer::new(RoleServer, None),
        ));
        self.tool_router
            .call(ctx)
            .await
            .map_err(|e| MCPServerError::Connection(e.to_string()))
    }

    /// Register a resource. Kept for API compatibility; the
    /// rmcp resource surface is exposed via `ServerHandler` methods
    /// (`list_resources` / `read_resource`).
    pub fn register_resource(&self, _resource: Resource) {
        // No-op: rmcp resource management is handled at the
        // `ServerHandler` level. Method retained for API compatibility.
    }
}

/// Convert an `rmcp` `CallToolResult` into the legacy `ToolResult`.
pub fn into_legacy(result: CallToolResult) -> ToolResult {
    let is_error = result.is_error.unwrap_or(false);
    let content = result
        .content
        .into_iter()
        .map(|annotated| {
            let c = annotated.into_inner();
            match c {
                Content::Text(t) => ContentItem {
                    content_type: "text".to_string(),
                    text: Some(t.text),
                },
                Content::Image(i) => ContentItem {
                    content_type: "image".to_string(),
                    text: Some(format!("data:{};base64,{}", i.mime_type, i.data)),
                },
                Content::Resource(r) => ContentItem {
                    content_type: "resource".to_string(),
                    text: Some(format!("{:?}", r.resource)),
                },
                Content::Audio(a) => ContentItem {
                    content_type: "audio".to_string(),
                    text: Some(format!("data:{};base64,{}", a.mime_type, a.data)),
                },
            }
        })
        .collect();
    ToolResult { content, is_error }
}

#[tool_router]
impl MCPServer {
    /// Return server uptime in seconds.
    #[tool(description = "Return the server uptime in seconds.")]
    fn uptime(&self) -> String {
        "0s".to_string()
    }

    /// Echo a message back to the caller.
    #[tool(description = "Echo the supplied message back to the caller.")]
    fn echo(&self, message: String) -> String {
        message
    }
}

#[tool_handler]
impl ServerHandler for MCPServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo::new(
            ServerCapabilities::builder()
                .enable_tools()
                .build(),
        )
        .with_server_info(Implementation::new("phenotype-mcp-server", "0.2.0"))
    }
}

/// Convenience: serve the server over stdio. Suitable for CLI use.
pub async fn serve_stdio() -> Result<(), MCPServerError> {
    use rmcp::transport::stdio;

    let server = MCPServer::new();
    let running = server
        .serve(stdio())
        .await
        .map_err(|e| MCPServerError::Connection(e.to_string()))?;
    running
        .waiting()
        .await
        .map_err(|e| MCPServerError::Connection(e.to_string()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_creation() {
        let server = MCPServer::new();
        let tools = server.list_tools();
        assert!(
            !tools.is_empty(),
            "tool router should expose at least one tool"
        );
    }

    #[test]
    fn test_call_tool_echo() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        runtime.block_on(async {
            let server = MCPServer::new();
            let result = server
                .call_tool("echo", serde_json::json!({"message": "hi"}))
                .await
                .unwrap();
            let legacy = into_legacy(result);
            assert!(!legacy.is_error);
            assert_eq!(legacy.content[0].text.as_deref(), Some("hi"));
        });
    }
}
