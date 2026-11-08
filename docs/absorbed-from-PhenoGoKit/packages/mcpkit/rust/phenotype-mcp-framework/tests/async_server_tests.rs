//! MCP Async Server Trait Tests

#[cfg(test)]
mod tests {
    use async_trait::async_trait;
    use phenotype_mcp_framework::*;
    use serde_json::json;
    use std::sync::Arc;

    // Test implementation of AsyncMcpServer
    struct TestAsyncServer;

    #[async_trait]
    impl AsyncMcpServer for TestAsyncServer {
        fn name(&self) -> &'static str {
            "async-test-server"
        }

        fn version(&self) -> &'static str {
            "2.0.0"
        }

        fn tools(&self) -> Vec<Tool> {
            vec![Tool::with_properties(
                "async_echo",
                "Async echo",
                json!({"message": { "type": "string" } }),
                vec!["message".to_string()],
            )]
        }

        async fn handle_tool(
            &self,
            name: String,
            arguments: serde_json::Value,
        ) -> Result<String, String> {
            // Simulate async work
            tokio::task::yield_now().await;

            match name.as_str() {
                "async_echo" => {
                    let msg = arguments
                        .get("message")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    Ok(format!("Async echo: {}", msg))
                }
                _ => Err(format!("Unknown tool: {}", name)),
            }
        }
    }

    #[tokio::test]
    async fn test_async_server_name() {
        let server = TestAsyncServer;
        assert_eq!(server.name(), "async-test-server");
    }

    #[tokio::test]
    async fn test_async_server_version() {
        let server = TestAsyncServer;
        assert_eq!(server.version(), "2.0.0");
    }

    #[tokio::test]
    async fn test_async_server_tools() {
        let server = TestAsyncServer;
        let tools = server.tools();

        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0].name, "async_echo");
    }

    #[tokio::test]
    async fn test_async_handle_tool() {
        let server = TestAsyncServer;
        let result = server
            .handle_tool("async_echo".to_string(), json!({"message": "Hello Async!"}))
            .await;

        assert_eq!(result.unwrap(), "Async echo: Hello Async!");
    }

    #[tokio::test]
    async fn test_async_handle_tool_unknown() {
        let server = TestAsyncServer;
        let result = server.handle_tool("unknown".to_string(), json!({})).await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_async_handle_initialize() {
        let server = TestAsyncServer;
        let response = server.handle_initialize(Some(json!(1)));

        assert_eq!(response.jsonrpc, "2.0");
        assert!(response.result.is_some());

        let result = response.result.unwrap();
        assert_eq!(result["server_info"]["name"], "async-test-server");
    }

    #[tokio::test]
    async fn test_async_handle_tools_list() {
        let server = TestAsyncServer;
        let response = server.handle_tools_list(Some(json!(2)));

        assert!(response.result.is_some());
        let result = response.result.unwrap();
        let tools = result["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 1);
    }

    #[tokio::test]
    async fn test_async_handle_tool_call_success() {
        let server = TestAsyncServer;
        let response = server
            .handle_tool_call(
                Some(json!(3)),
                Some(json!({
                    "name": "async_echo",
                    "arguments": {"message": "test"}
                })),
            )
            .await;

        assert!(response.result.is_some());
        assert!(!response.result.unwrap()["is_error"].as_bool().unwrap());
    }

    #[tokio::test]
    async fn test_async_handle_tool_call_missing_params() {
        let server = TestAsyncServer;
        let response = server.handle_tool_call(Some(json!(4)), None).await;

        assert!(response.error.is_some());
        assert_eq!(response.error.unwrap().code, error_codes::INVALID_PARAMS);
    }

    #[tokio::test]
    async fn test_async_handle_request_initialize() {
        let server = TestAsyncServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(1)),
            method: "initialize".to_string(),
            params: None,
        };

        let response = server.handle_request(request).await;
        assert!(response.result.is_some());
    }

    #[tokio::test]
    async fn test_async_handle_request_tools_call() {
        let server = TestAsyncServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(2)),
            method: "tools/call".to_string(),
            params: Some(json!({
                "name": "async_echo",
                "arguments": {"message": "async test"}
            })),
        };

        let response = server.handle_request(request).await;
        assert!(response.result.is_some());
    }

    #[tokio::test]
    async fn test_async_handle_request_unknown_method() {
        let server = TestAsyncServer;
        let request = McpRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(json!(3)),
            method: "unknown".to_string(),
            params: None,
        };

        let response = server.handle_request(request).await;
        assert!(response.error.is_some());
        assert_eq!(response.error.unwrap().code, error_codes::METHOD_NOT_FOUND);
    }

    // Test concurrent async operations
    #[tokio::test]
    async fn test_concurrent_tool_calls() {
        let server = Arc::new(TestAsyncServer);

        let handles: Vec<_> = (0..10)
            .map(|i| {
                let server = Arc::clone(&server);
                tokio::spawn(async move {
                    server
                        .handle_tool(
                            "async_echo".to_string(),
                            json!({"message": format!("message {}", i)}),
                        )
                        .await
                })
            })
            .collect();

        let results = futures::future::join_all(handles).await;

        for (i, result) in results.iter().enumerate() {
            assert!(result.is_ok());
            let inner = result.as_ref().unwrap();
            assert!(inner.is_ok());
            assert!(inner.as_ref().unwrap().contains(&format!("message {}", i)));
        }
    }
}
