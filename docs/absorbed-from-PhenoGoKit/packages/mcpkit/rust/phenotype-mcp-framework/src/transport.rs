//! MCP Transport - JSON-RPC stdin/stdout transport

use std::io::Write;
use tokio::io::{AsyncBufReadExt, BufReader};
use tracing::{debug, error, info};

use crate::server::{AsyncMcpServer, McpServer};
use crate::types::*;

/// Run the MCP server with stdin/stdout transport
///
/// This function reads JSON-RPC requests from stdin and writes responses to stdout.
/// It continues until EOF is reached or an error occurs.
pub async fn run_stdio_transport<S: McpServer>(server: &S) {
    info!("Starting {} server v{}", server.name(), server.version());

    let stdin = tokio::io::stdin();
    let mut reader = BufReader::new(stdin);
    let mut line = String::new();

    loop {
        line.clear();
        match reader.read_line(&mut line).await {
            Ok(0) => {
                info!("EOF received, shutting down");
                break;
            }
            Ok(_) => {
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }

                debug!("Received: {}", line);

                match serde_json::from_str::<McpRequest>(line) {
                    Ok(request) => {
                        let response = server.handle_request(request);
                        write_response(&response);
                    }
                    Err(e) => {
                        error!("Failed to parse request: {}", e);
                        let error_response = McpResponse::error(
                            None,
                            crate::error_codes::PARSE_ERROR,
                            format!("Parse error: {}", e),
                            None,
                        );
                        write_response(&error_response);
                    }
                }
            }
            Err(e) => {
                error!("Failed to read line: {}", e);
                break;
            }
        }
    }
}

/// Write a response to stdout
fn write_response(response: &McpResponse) {
    let response_json = match serde_json::to_string(response) {
        Ok(json) => json,
        Err(e) => {
            error!("Failed to serialize response: {}", e);
            return;
        }
    };

    let mut stdout = std::io::stdout();
    if let Err(e) = writeln!(stdout, "{}", response_json) {
        error!("Failed to write response: {}", e);
    }
}

/// Run the async MCP server with stdin/stdout transport
///
/// This is the async version that works with AsyncMcpServer.
pub async fn run_async_stdio_transport<S: AsyncMcpServer>(server: &S) {
    info!("Starting {} server v{}", server.name(), server.version());

    let stdin = tokio::io::stdin();
    let mut reader = BufReader::new(stdin);
    let mut line = String::new();

    loop {
        line.clear();
        match reader.read_line(&mut line).await {
            Ok(0) => {
                info!("EOF received, shutting down");
                break;
            }
            Ok(_) => {
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }

                debug!("Received: {}", line);

                match serde_json::from_str::<McpRequest>(line) {
                    Ok(request) => {
                        let response = server.handle_request(request).await;
                        write_response(&response);
                    }
                    Err(e) => {
                        error!("Failed to parse request: {}", e);
                        let error_response = McpResponse::error(
                            None,
                            crate::error_codes::PARSE_ERROR,
                            format!("Parse error: {}", e),
                            None,
                        );
                        write_response(&error_response);
                    }
                }
            }
            Err(e) => {
                error!("Failed to read line: {}", e);
                break;
            }
        }
    }
}

/// Read a single request from stdin (blocking version for sync servers)
pub fn read_request() -> Option<McpRequest> {
    let mut line = String::new();

    match std::io::stdin().read_line(&mut line) {
        Ok(0) => None,
        Ok(_) => {
            let line = line.trim();
            if line.is_empty() {
                return None;
            }
            match serde_json::from_str::<McpRequest>(line) {
                Ok(request) => Some(request),
                Err(e) => {
                    eprintln!("Parse error: {}", e);
                    let error_response = McpResponse::error(
                        None,
                        crate::error_codes::PARSE_ERROR,
                        format!("Parse error: {}", e),
                        None,
                    );
                    write_response(&error_response);
                    None
                }
            }
        }
        Err(e) => {
            eprintln!("Read error: {}", e);
            None
        }
    }
}

/// Initialize tracing subscriber with default settings
pub fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into()),
        )
        .init();
}

/// Initialize tracing with a custom default level
pub fn init_tracing_with_level(level: tracing::Level) {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env().add_directive(level.into()),
        )
        .init();
}
