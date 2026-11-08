//! MCP Server Trait Tests

#[cfg(test)]
mod tests {
    use phenotype_mcp_framework::*;
    use serde_json::json;

    // Test implementation of McpServer
    struct TestServer;

    impl McpServer for TestServer {
        fn name(&self) -> &'static str {
            "test-server"
        }

        fn version(&self) -> &'static str {
            "1.0.0"
        }

        fn tools(&self) -> Vec<Tool> {
            vec![
                Tool::with_properties(
                    "echo",
                    "Echoes the input",
                    json!({
                        "message": {
                            "type": "string",
                            "description": "Message to echo"
                        }
                    }),
                    vec!["message".to_string()],
                ),
                Tool::with_properties(
                    "add",
                    "Adds two numbers",
                    json!({
                        "a": { "type": "number" },
                        "b": { "type": "number" }
                    }),
                    vec!["a".to_string(), "b".to_string()],
                ),
            ]
        }

        fn handle_tool(
            &self,
            name: String,
            arguments: serde_json::Value,
        ) -> Result<String, String> {
            match name.as_str() {
                "echo" => {
                    let msg = arguments
                        .get("message")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    Ok(format!("Echo: {}", msg))
                }
                "add" => {
                    let a = arguments.get("a").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let b = arguments.get("b").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    Ok((a + b).to_string())
                }
                _ => Err(format!("Unknown tool: {}", name)),
            }
        }
    }

    #[test]
    fn test_server_name() {
        let server = TestServer;
        assert_eq!(server.name(), "test-server");
    }

    #[test]
    fn test_server_version() {
        let server = TestServer;
        assert_eq!(server.version(), "1.0.0");
    }

    #[test]
    fn test_server_tools() {
        let server = TestServer;
        let tools = server.tools();

        assert_eq!(tools.len(), 2);
        assert_eq!(tools[0].name, "echo");
        assert_eq!(tools[1].name, "add");
    }

    #[test]
    fn test_handle_tool_echo() {
        let server = TestServer;
        let result = server.handle_tool("echo".to_string(), json!({"message": "Hello, World!"}));

        assert_eq!(result.unwrap(), "Echo: Hello, World!");
    }

    #[test]
    fn test_handle_tool_add() {
        let server = TestServer;
        let result = server.handle_tool("add".to_string(), json!({"a": 5.0, "b": 3.0}));

        assert_eq!(result.unwrap(), "8");
    }

    #[test]
    fn test_handle_tool_unknown() {
        let server = TestServer;
        let result = server.handle_tool("unknown".to_string(), json!({}));

        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Unknown tool"));
    }

    #[test]
    fn test_handle_initialize() {
        let server = TestServer;
        let response = server.handle_initialize(Some(json!(1)));

        assert_eq!(response.jsonrpc, "2.0");
        assert_eq!(response.id, Some(json!(1)));
        assert!(response.result.is_some());
        assert!(response.error.is_none());

        let result = response.result.unwrap();
        assert_eq!(result["protocol_version"], "2024-11-05");
        assert_eq!(result["server_info"]["name"], "test-server");
        assert_eq!(result["server_info"]["version"], "1.0.0");
    }

    #[test]
    fn test_handle_tools_list() {
        let server = TestServer;
        let response = server.handle_tools_list(Some(json!(2)));

        assert_eq!(response.jsonrpc, "2.0");
        assert!(response.result.is_some());

        let result = response.result.unwrap();
        let tools = result["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 2);
        assert_eq!(tools[0]["name"], "echo");
    }

    #[test]
    fn test_handle_tool_call_success() {
        let server = TestServer;
        let params = json!({
            "name": "echo",
            "arguments": {
                "message": "Test message"
            }
        });

        let response = server.handle_tool_call(Some(json!(3)), Some(params));

        assert!(response.result.is_some());
        assert!(response.error.is_none());

        let result = response.result.unwrap();
        assert!(!result["is_error"].as_bool().unwrap());
        assert_eq!(result["content"][0]["text"], "Echo: Test message");
    }

    #[test]
    fn test_handle_tool_call_missing_params() {
        let server = TestServer;
        let response = server.handle_tool_call(Some(json!(4)), None);

        assert!(response.result.is_none());
        assert!(response.error.is_some());

        let error = response.error.unwrap();
        assert_eq!(error.code, error_codes::INVALID_PARAMS);
        assert_eq!(error.message, "Missing params");
    }

    #[test]
    fn test_handle_tool_call_unknown_tool() {
        let server = TestServer;
        let params = json!({
            "name": "unknown_tool",
            "arguments": {}
        });

        let response = server.handle_tool_call(Some(json!(5)), Some(params));

        assert!(response.result.is_some());
        let result = response.result.unwrap();
        assert!(result["is_error"].as_bool().unwrap());
    }

    #[test]
    fn test_handle_request_initialize() {
        let server = TestServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(1)),
            method: "initialize".to_string(),
            params: None,
        };

        let response = server.handle_request(request);
        assert!(response.result.is_some());
    }

    #[test]
    fn test_handle_request_tools_list() {
        let server = TestServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(2)),
            method: "tools/list".to_string(),
            params: None,
        };

        let response = server.handle_request(request);
        assert!(response.result.is_some());
    }

    #[test]
    fn test_handle_request_tools_call() {
        let server = TestServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(3)),
            method: "tools/call".to_string(),
            params: Some(json!({
                "name": "echo",
                "arguments": {"message": "test"}
            })),
        };

        let response = server.handle_request(request);
        assert!(response.result.is_some());
        assert!(!response.result.unwrap()["is_error"].as_bool().unwrap());
    }

    #[test]
    fn test_handle_request_unknown_method() {
        let server = TestServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(4)),
            method: "unknown/method".to_string(),
            params: None,
        };

        let response = server.handle_request(request);
        assert!(response.error.is_some());
        assert_eq!(response.error.unwrap().code, error_codes::METHOD_NOT_FOUND);
    }

    // ToolSchemaBuilder tests
    #[test]
    fn test_tool_schema_builder_string_prop() {
        let prop = ToolSchemaBuilder::string_prop("A description");
        assert_eq!(prop["type"], "string");
        assert_eq!(prop["description"], "A description");
    }

    #[test]
    fn test_tool_schema_builder_bool_prop() {
        let prop = ToolSchemaBuilder::bool_prop("Enable feature", true);
        assert_eq!(prop["type"], "boolean");
        assert_eq!(prop["default"], true);
    }

    #[test]
    fn test_tool_schema_builder_int_prop() {
        let prop = ToolSchemaBuilder::int_prop("Count", Some(42));
        assert_eq!(prop["type"], "integer");
        assert_eq!(prop["default"], 42);
    }

    #[test]
    fn test_tool_schema_builder_int_prop_no_default() {
        let prop = ToolSchemaBuilder::int_prop("Count", None);
        assert_eq!(prop["type"], "integer");
        assert!(prop.get("default").is_none());
    }

    #[test]
    fn test_tool_schema_builder_array_prop() {
        let prop = ToolSchemaBuilder::array_prop("List of items", "string");
        assert_eq!(prop["type"], "array");
        assert_eq!(prop["items"]["type"], "string");
    }

    #[test]
    fn test_tool_schema_builder_object_prop() {
        let prop = ToolSchemaBuilder::object_prop("Configuration object");
        assert_eq!(prop["type"], "object");
        assert_eq!(prop["description"], "Configuration object");
    }
}
