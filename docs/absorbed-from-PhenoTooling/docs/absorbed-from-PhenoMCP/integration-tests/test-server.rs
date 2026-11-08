// SPDX-License-Identifier: MIT OR Apache-2.0

//! Test MCP server for integration testing
use pheno_mcp_protocol::{MCPServer, JsonRpcRequest, JsonRpcResponse};
use std::net::SocketAddr;
use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tracing::info;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    
    let addr = "127.0.0.1:3001".parse::<SocketAddr>()?;
    let listener = TcpListener::bind(addr).await?;
    info!("Test MCP server listening on {}", addr);
    
    let server = MCPServer::new();
    
    // Register test tools
    server.register_tool("echo", "Echo tool", serde_json::json!({
        "type": "object",
        "properties": {
            "message": { "type": "string" }
        }
    }), |args| {
        Ok(args)
    }).await;
    
    server.register_tool("add", "Add numbers", serde_json::json!({
        "type": "object",
        "properties": {
            "a": { "type": "number" },
            "b": { "type": "number" }
        }
    }), |args| {
        let a = args["a"].as_f64().unwrap_or(0.0);
        let b = args["b"].as_f64().unwrap_or(0.0);
        Ok(serde_json::json!({ "result": a + b }))
    }).await;
    
    loop {
        let (mut socket, addr) = listener.accept().await?;
        info!("Connection from {}", addr);
        
        let server = server.clone();
        tokio::spawn(async move {
            if let Err(e) = handle_connection(&mut socket, &server).await {
                eprintln!("Connection error: {}", e);
            }
        });
    }
}

async fn handle_connection(socket: &mut TcpStream, server: &MCPServer) -> Result<(), Box<dyn std::error::Error>> {
    let mut buf = vec![0u8; 4096];
    let n = socket.read(&mut buf).await?;
    buf.truncate(n);
    
    let request: JsonRpcRequest = serde_json::from_slice(&buf)?;
    let response = server.handle_request(request).await;
    
    let response_json = serde_json::to_string(&response)?;
    socket.write_all(response_json.as_bytes()).await?;
    
    Ok(())
}
