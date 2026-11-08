//! MCP Protocol Types Tests

#[cfg(test)]
mod tests {
    use phenotype_mcp_framework::*;
    use serde_json::json;

    #[test]
    fn test_constants() {
        assert_eq!(MCP_PROTOCOL_VERSION, "2024-11-05");
        assert_eq!(JSONRPC_VERSION, "2.0");
    }

    #[test]
    fn test_error_codes() {
        assert_eq!(error_codes::PARSE_ERROR, -32700);
        assert_eq!(error_codes::INVALID_REQUEST, -32600);
        assert_eq!(error_codes::METHOD_NOT_FOUND, -32601);
        assert_eq!(error_codes::INVALID_PARAMS, -32602);
        assert_eq!(error_codes::INTERNAL_ERROR, -32603);
    }

    #[test]
    fn test_mcp_request_deserialization() {
        let json = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05"
            }
        });

        let request: McpRequest = serde_json::from_value(json).unwrap();
        assert_eq!(request.jsonrpc, "2.0");
        assert_eq!(request.id, Some(json!(1)));
        assert_eq!(request.method, "initialize");
        assert!(request.params.is_some());
    }

    #[test]
    fn test_mcp_request_deserialization_without_params() {
        let json = json!({
            "jsonrpc": "2.0",
            "id": null,
            "method": "tools/list"
        });

        let request: McpRequest = serde_json::from_value(json).unwrap();
        assert_eq!(request.jsonrpc, "2.0");
        assert_eq!(request.id, Some(json!(null)));
        assert_eq!(request.method, "tools/list");
        assert!(request.params.is_none());
    }

    #[test]
    fn test_mcp_request_deserialization_notification() {
        let json = json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        });

        let request: McpRequest = serde_json::from_value(json).unwrap();
        assert_eq!(request.jsonrpc, "2.0");
        assert!(request.id.is_none());
        assert_eq!(request.method, "notifications/initialized");
    }

    #[test]
    fn test_mcp_response_success_serialization() {
        let response = McpResponse::success(Some(json!(1)), json!({"tools": []}));
        let json = serde_json::to_value(&response).unwrap();

        assert_eq!(json["jsonrpc"], "2.0");
        assert_eq!(json["id"], 1);
        assert!(json["result"].is_object());
        assert!(json["error"].is_null());
    }

    #[test]
    fn test_mcp_response_error_serialization() {
        let response = McpResponse::error(
            Some(json!(2)),
            error_codes::METHOD_NOT_FOUND,
            "Method not found".to_string(),
            Some(json!({"method": "unknown"})),
        );
        let json = serde_json::to_value(&response).unwrap();

        assert_eq!(json["jsonrpc"], "2.0");
        assert_eq!(json["id"], 2);
        assert!(json["result"].is_null());
        assert_eq!(json["error"]["code"], -32601);
        assert_eq!(json["error"]["message"], "Method not found");
    }

    #[test]
    fn test_mcp_response_method_not_found() {
        let response = McpResponse::method_not_found(Some(json!(3)), "unknown_method");
        let json = serde_json::to_value(&response).unwrap();

        assert_eq!(json["error"]["code"], -32601);
        assert_eq!(json["error"]["message"], "Method not found: unknown_method");
    }

    #[test]
    fn test_mcp_response_invalid_params() {
        let response = McpResponse::invalid_params(Some(json!(4)), "Missing required field");
        let json = serde_json::to_value(&response).unwrap();

        assert_eq!(json["error"]["code"], -32602);
        assert_eq!(json["error"]["message"], "Missing required field");
    }

    #[test]
    fn test_server_capabilities_default() {
        let caps = ServerCapabilities::default();
        assert!(!caps.tools.list_changed);
    }

    #[test]
    fn test_tool_capabilities() {
        let caps = ToolCapabilities { list_changed: true };
        assert!(caps.list_changed);
    }

    #[test]
    fn test_tool_new() {
        let schema = json!({
            "type": "object",
            "properties": {}
        });
        let tool = Tool::new("echo", "Echoes input", schema.clone());

        assert_eq!(tool.name, "echo");
        assert_eq!(tool.description, "Echoes input");
        assert_eq!(tool.input_schema, schema);
    }

    #[test]
    fn test_tool_with_properties() {
        let tool = Tool::with_properties(
            "greet",
            "Greets a person",
            json!({
                "name": { "type": "string" }
            }),
            vec!["name".to_string()],
        );

        assert_eq!(tool.name, "greet");
        assert_eq!(tool.description, "Greets a person");
        assert_eq!(tool.input_schema["type"], "object");
        assert_eq!(tool.input_schema["properties"]["name"]["type"], "string");
        assert_eq!(tool.input_schema["required"][0], "name");
    }

    #[test]
    fn test_server_info() {
        let info = ServerInfo::new("test-server", "1.0.0");
        assert_eq!(info.name, "test-server");
        assert_eq!(info.version, "1.0.0");
    }

    #[test]
    fn test_initialize_result() {
        let server_info = ServerInfo::new("test", "1.0.0");
        let result = InitializeResult::new(server_info);

        assert_eq!(result.protocol_version, "2024-11-05");
        assert_eq!(result.server_info.name, "test");
        assert!(!result.capabilities.tools.list_changed);
    }

    #[test]
    fn test_initialize_result_with_capabilities() {
        let server_info = ServerInfo::new("test", "1.0.0");
        let caps = ServerCapabilities {
            tools: ToolCapabilities { list_changed: true },
        };
        let result = InitializeResult::new(server_info).with_capabilities(caps);

        assert!(result.capabilities.tools.list_changed);
    }

    #[test]
    fn test_tools_list_result() {
        let tools = vec![
            Tool::new("tool1", "First tool", json!({})),
            Tool::new("tool2", "Second tool", json!({})),
        ];
        let result = ToolsListResult::new(tools);

        assert_eq!(result.tools.len(), 2);
        assert_eq!(result.tools[0].name, "tool1");
    }

    #[test]
    fn test_tool_content_text() {
        let content = ToolContent::text("Hello, world!");
        assert_eq!(content.content_type, "text");
        assert_eq!(content.text, "Hello, world!");
    }

    #[test]
    fn test_tool_call_result_success() {
        let result = ToolCallResult::success("Operation completed");
        assert!(!result.is_error);
        assert_eq!(result.content.len(), 1);
        assert_eq!(result.content[0].text, "Operation completed");
    }

    #[test]
    fn test_tool_call_result_error() {
        let result = ToolCallResult::error("Something went wrong");
        assert!(result.is_error);
        assert_eq!(result.content.len(), 1);
        assert_eq!(result.content[0].text, "Something went wrong");
    }

    #[test]
    fn test_tool_call_result_from_result_ok() {
        let result = ToolCallResult::from_result(Ok("success".to_string()));
        assert!(!result.is_error);
        assert_eq!(result.content[0].text, "success");
    }

    #[test]
    fn test_tool_call_result_from_result_err() {
        let result = ToolCallResult::from_result(Err("failure".to_string()));
        assert!(result.is_error);
        assert_eq!(result.content[0].text, "failure");
    }

    #[test]
    fn test_mcp_error_serialization() {
        let error = McpError {
            code: -32600,
            message: "Invalid request".to_string(),
            data: Some(json!({"details": "Missing method"})),
        };
        let json = serde_json::to_value(&error).unwrap();

        assert_eq!(json["code"], -32600);
        assert_eq!(json["message"], "Invalid request");
        assert!(json["data"].is_object());
    }

    #[test]
    fn test_mcp_error_without_data() {
        let error = McpError {
            code: -32600,
            message: "Invalid request".to_string(),
            data: None,
        };
        let json = serde_json::to_value(&error).unwrap();

        assert!(json.get("data").is_none());
    }

    // Roundtrip tests
    #[test]
    fn test_request_roundtrip() {
        let original = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(42)),
            method: "tools/call".to_string(),
            params: Some(json!({"name": "test"})),
        };

        let serialized = serde_json::to_string(&original).unwrap();
        let deserialized: McpRequest = serde_json::from_str(&serialized).unwrap();

        assert_eq!(deserialized.jsonrpc, original.jsonrpc);
        assert_eq!(deserialized.id, original.id);
        assert_eq!(deserialized.method, original.method);
    }

    #[test]
    fn test_complex_params_serialization() {
        let params = json!({
            "name": "complex_tool",
            "arguments": {
                "nested": {
                    "array": [1, 2, 3],
                    "boolean": true,
                    "null_value": null
                }
            }
        });

        let response = McpResponse::success(Some(json!(1)), params);
        let serialized = serde_json::to_string(&response).unwrap();
        let json: serde_json::Value = serde_json::from_str(&serialized).unwrap();

        assert_eq!(json["result"]["arguments"]["nested"]["array"][1], 2);
        assert_eq!(json["result"]["arguments"]["nested"]["boolean"], true);
        assert!(json["result"]["arguments"]["nested"]["null_value"].is_null());
    }
}
