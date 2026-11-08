//! MCP Transport Tests

#[cfg(test)]
mod tests {
    use phenotype_mcp_framework::*;
    use serde_json::json;
    use std::sync::{Arc, Mutex};

    // Mock server for testing
    struct MockServer {
        call_count: Arc<Mutex<u32>>,
    }

    impl MockServer {
        fn new() -> Self {
            Self {
                call_count: Arc::new(Mutex::new(0)),
            }
        }

        fn get_call_count(&self) -> u32 {
            *self.call_count.lock().unwrap()
        }
    }

    impl McpServer for MockServer {
        fn name(&self) -> &'static str {
            "mock-server"
        }

        fn version(&self) -> &'static str {
            "1.0.0"
        }

        fn tools(&self) -> Vec<Tool> {
            vec![]
        }

        fn handle_tool(
            &self,
            _name: String,
            _arguments: serde_json::Value,
        ) -> Result<String, String> {
            let mut count = self.call_count.lock().unwrap();
            *count += 1;
            Ok("ok".to_string())
        }
    }

    #[test]
    fn test_mcp_request_parsing_valid() {
        let json_str = r#"{"jsonrpc":"2.0","id":1,"method":"initialize"}"#;
        let request: Result<McpRequest, _> = serde_json::from_str(json_str);

        assert!(request.is_ok());
        let req = request.unwrap();
        assert_eq!(req.method, "initialize");
        assert_eq!(req.id, Some(json!(1)));
    }

    #[test]
    fn test_mcp_request_parsing_invalid_json() {
        let json_str = r#"{invalid json}"#;
        let request: Result<McpRequest, _> = serde_json::from_str(json_str);

        assert!(request.is_err());
    }

    #[test]
    fn test_mcp_request_parsing_missing_method() {
        let json_str = r#"{"jsonrpc":"2.0","id":1}"#;
        let request: Result<McpRequest, _> = serde_json::from_str(json_str);

        assert!(request.is_err());
    }

    #[test]
    fn test_mcp_request_parsing_notification() {
        let json_str = r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#;
        let request: Result<McpRequest, _> = serde_json::from_str(json_str);

        assert!(request.is_ok());
        let req = request.unwrap();
        assert!(req.id.is_none());
    }

    #[test]
    fn test_mcp_response_serialization_success() {
        let response = McpResponse::success(Some(json!(42)), json!({"tools": [{"name": "test"}]}));

        let json_str = serde_json::to_string(&response).unwrap();
        assert!(json_str.contains("\"jsonrpc\":\"2.0\""));
        assert!(json_str.contains("\"id\":42"));
        assert!(json_str.contains("\"tools\""));
    }

    #[test]
    fn test_mcp_response_serialization_error() {
        let response = McpResponse::error(
            Some(json!(1)),
            error_codes::PARSE_ERROR,
            "Parse error".to_string(),
            None,
        );

        let json_str = serde_json::to_string(&response).unwrap();
        assert!(json_str.contains("\"code\":-32700"));
        assert!(json_str.contains("\"message\":\"Parse error\""));
    }

    #[test]
    fn test_server_handle_initialize() {
        let server = MockServer::new();
        let response = server.handle_initialize(Some(json!(1)));

        assert!(response.result.is_some());
        let result = response.result.unwrap();
        assert_eq!(result["protocol_version"], "2024-11-05");
        assert_eq!(result["server_info"]["name"], "mock-server");
    }

    #[test]
    fn test_server_handle_tools_list() {
        let server = MockServer::new();
        let response = server.handle_tools_list(Some(json!(2)));

        assert!(response.result.is_some());
        let result = response.result.unwrap();
        let tools = result["tools"].as_array().unwrap();
        assert!(tools.is_empty());
    }

    #[test]
    fn test_server_handle_tool_call() {
        let server = MockServer::new();
        let params = json!({
            "name": "test_tool",
            "arguments": {}
        });

        let response = server.handle_tool_call(Some(json!(3)), Some(params));

        assert!(response.result.is_some());
        assert_eq!(server.get_call_count(), 1);
    }

    #[test]
    fn test_server_handle_tool_call_missing_params() {
        let server = MockServer::new();
        let response = server.handle_tool_call(Some(json!(4)), None);

        assert!(response.error.is_some());
        assert_eq!(response.error.unwrap().code, error_codes::INVALID_PARAMS);
    }

    #[test]
    fn test_server_handle_request_initialize() {
        let server = MockServer::new();
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
    fn test_server_handle_request_unknown() {
        let server = MockServer::new();
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(5)),
            method: "unknown/method".to_string(),
            params: None,
        };

        let response = server.handle_request(request);
        assert!(response.error.is_some());
        assert_eq!(response.error.unwrap().code, error_codes::METHOD_NOT_FOUND);
    }

    #[test]
    fn test_server_handle_request_tools_call() {
        let server = MockServer::new();
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(6)),
            method: "tools/call".to_string(),
            params: Some(json!({
                "name": "test",
                "arguments": {}
            })),
        };

        let response = server.handle_request(request);
        assert!(response.result.is_some());
        assert_eq!(server.get_call_count(), 1);
    }

    // Error handling tests
    #[test]
    fn test_error_response_structure() {
        let error = McpError {
            code: error_codes::INTERNAL_ERROR,
            message: "Internal server error".to_string(),
            data: Some(json!({"trace": "stack trace here"})),
        };

        let json = serde_json::to_value(&error).unwrap();
        assert_eq!(json["code"], -32603);
        assert_eq!(json["message"], "Internal server error");
        assert!(json["data"].is_object());
    }

    #[test]
    fn test_error_response_without_data() {
        let error = McpError {
            code: error_codes::INVALID_REQUEST,
            message: "Invalid".to_string(),
            data: None,
        };

        let json = serde_json::to_value(&error).unwrap();
        assert!(json.get("data").is_none());
    }

    // Batch request tests (future consideration)
    #[test]
    fn test_single_request_in_array_format() {
        // Some clients might send single requests as arrays
        let json_str = r#"[{"jsonrpc":"2.0","id":1,"method":"initialize"}]"#;
        let requests: Vec<McpRequest> = serde_json::from_str(json_str).unwrap();

        assert_eq!(requests.len(), 1);
        assert_eq!(requests[0].method, "initialize");
    }

    // JSON-RPC compliance tests
    #[test]
    fn test_jsonrpc_version_compliance() {
        // Valid version
        let json_str = r#"{"jsonrpc":"2.0","id":1,"method":"test"}"#;
        let request: McpRequest = serde_json::from_str(json_str).unwrap();
        assert_eq!(request.jsonrpc, "2.0");
    }

    #[test]
    fn test_id_types() {
        // String id
        let json_str = r#"{"jsonrpc":"2.0","id":"abc123","method":"test"}"#;
        let request: McpRequest = serde_json::from_str(json_str).unwrap();
        assert_eq!(request.id, Some(json!("abc123")));

        // Number id
        let json_str = r#"{"jsonrpc":"2.0","id":42,"method":"test"}"#;
        let request: McpRequest = serde_json::from_str(json_str).unwrap();
        assert_eq!(request.id, Some(json!(42)));

        // Null id
        let json_str = r#"{"jsonrpc":"2.0","id":null,"method":"test"}"#;
        let request: McpRequest = serde_json::from_str(json_str).unwrap();
        assert_eq!(request.id, Some(json!(null)));
    }
}
