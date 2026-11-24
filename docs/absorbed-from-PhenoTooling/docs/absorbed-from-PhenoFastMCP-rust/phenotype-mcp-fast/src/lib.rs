//! Phenotype MCP Fast — FastMCP-equivalent high-level framework for Rust
//!
//! A high-level, ergonomic framework for building Model Context Protocol (MCP)
//! servers in Rust. Inspired by FastMCP's decorator-based API, but idiomatic
//! to Rust's type system and async runtime.
//!
//! # Quick Start
//!
//! ```rust,ignore
//! use phenotype_mcp_fast::{FastMcp, tool};
//! use schemars::JsonSchema;
//! use serde::Deserialize;
//!
//! #[derive(JsonSchema, Deserialize)]
//! struct AddParams {
//!     a: i32,
//!     b: i32,
//! }
//!
//! #[tool]
//! fn add(params: AddParams) -> Result<i32, String> {
//!     Ok(params.a + params.b)
//! }
//!
//! #[tokio::main]
//! async fn main() {
//!     FastMcp::new("calculator", "1.0.0")
//!         .with_tool(add__Tool::tool_def(), add__Tool::call)
//!         .run_stdio()
//!         .await;
//! }
//! ```

#![cfg_attr(docsrs, feature(doc_auto_cfg))]

// Re-export proc macros
pub use phenotype_mcp_fast_macros::{tool, resource, prompt};

// Re-export core types for user convenience
pub use phenotype_mcp_core::{ServerInfo, ClientInfo, ClientCapabilities};
pub use phenotype_mcp_framework::{McpServer, AsyncMcpServer, Tool, McpRequest, McpResponse, McpError};

// Re-export schemars and serde for user convenience
pub use schemars;
pub use serde;
pub use serde_json;

/// Internal re-exports for the proc macros to use.
///
/// Not part of the public API. Do not use directly.
#[doc(hidden)]
pub mod internal {
    pub use phenotype_mcp_framework::Tool;
    pub use schemars::{schema_for, JsonSchema};
    pub use serde::{Deserialize, Serialize};
    pub use serde_json;
}

use std::collections::HashMap;
use std::sync::Arc;

use serde_json::Value;
use tokio::sync::Mutex;

/// Type alias for a tool handler function.
pub type ToolHandler = Arc<dyn Fn(&Value) -> Result<Value, String> + Send + Sync>;

/// High-level MCP server builder — the FastMCP equivalent for Rust.
///
/// Build a server by chaining `.with_tool()` calls, then run it with
/// `.run_stdio()` or `.run_sse()`.
///
/// # Example
///
/// ```rust,ignore
/// FastMcp::new("my-server", "1.0.0")
///     .with_tool(my_tool_def, my_tool_handler)
///     .run_stdio()
///     .await;
/// ```
pub struct FastMcp {
    name: &'static str,
    version: &'static str,
    tools: Vec<Tool>,
    handlers: HashMap<String, ToolHandler>,
}

impl FastMcp {
    /// Create a new FastMcp server builder.
    pub fn new(name: &'static str, version: &'static str) -> Self {
        Self {
            name,
            version,
            tools: Vec::new(),
            handlers: HashMap::new(),
        }
    }

    /// Register a tool with its handler.
    ///
    /// The `tool_def` is the [`Tool`] metadata used for `tools/list`.
    /// The `handler` is a function that receives JSON params and returns
    /// a JSON result or error string.
    pub fn with_tool(
        mut self,
        tool_def: Tool,
        handler: impl Fn(&Value) -> Result<Value, String> + Send + Sync + 'static,
    ) -> Self {
        let name = tool_def.name.clone();
        self.tools.push(tool_def);
        self.handlers.insert(name, Arc::new(handler));
        self
    }

    /// Run the server with stdin/stdout transport (the default for MCP).
    ///
    /// Reads newline-delimited JSON-RPC 2.0 requests from stdin and writes
    /// responses to stdout.
    pub async fn run_stdio(self) {
        let server = self.build();
        phenotype_mcp_framework::transport::run_async_stdio_transport(&server).await;
    }

    /// Build an async MCP server from the configured tools.
    fn build(self) -> FastMcpServer {
        FastMcpServer {
            name: self.name,
            version: self.version,
            tools: self.tools,
            handlers: Arc::new(Mutex::new(self.handlers)),
        }
    }
}

/// Internal async server implementation used by [`FastMcp`].
struct FastMcpServer {
    name: &'static str,
    version: &'static str,
    tools: Vec<Tool>,
    handlers: Arc<Mutex<HashMap<String, ToolHandler>>>,
}

#[async_trait::async_trait]
impl AsyncMcpServer for FastMcpServer {
    fn name(&self) -> &'static str {
        self.name
    }

    fn version(&self) -> &'static str {
        self.version
    }

    fn tools(&self) -> Vec<Tool> {
        self.tools.clone()
    }

    async fn handle_tool(&self, name: String, arguments: Value) -> Result<String, String> {
        let handlers = self.handlers.lock().await;
        let handler = handlers
            .get(&name)
            .ok_or_else(|| format!("Tool '{}' not found", name))?;

        let result = handler(&arguments)?;
        serde_json::to_string(&result)
            .map_err(|e| format!("Failed to serialize result: {}", e))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use phenotype_mcp_framework::Tool;
    use serde_json::json;

    #[test]
    fn test_fastmcp_builder() {
        let mcp = FastMcp::new("test", "1.0.0")
            .with_tool(
                Tool::new("echo", "Echoes input", json!({"type": "object"})),
                |_params| Ok(json!("hello")),
            );

        assert_eq!(mcp.tools.len(), 1);
        assert_eq!(mcp.tools[0].name, "echo");
        assert!(mcp.handlers.contains_key("echo"));
    }

    #[test]
    fn test_tool_handler_roundtrip() {
        let handler = |_params: &Value| -> Result<Value, String> {
            Ok(json!({"result": "ok"}))
        };

        let result = handler(&json!({"input": "test"})).unwrap();
        assert_eq!(result, json!({"result": "ok"}));
    }
}
