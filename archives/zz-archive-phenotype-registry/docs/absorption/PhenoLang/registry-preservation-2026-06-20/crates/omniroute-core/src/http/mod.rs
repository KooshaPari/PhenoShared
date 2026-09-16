//! HTTP server module for OmniRoute Core
//!
//! Provides the HTTP API layer using axum.

pub mod routes;
pub mod state;
pub mod streaming;

use crate::router::Router;
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::info;

/// Application state shared across handlers
pub type AppState = Arc<ServerState>;

/// Server state containing the router and configuration
#[derive(Clone)]
pub struct ServerState {
    /// The LLM request router
    pub router: Router,
    /// Server configuration
    pub config: ServerConfig,
}

/// Server configuration
#[derive(Clone, Debug)]
pub struct ServerConfig {
    /// Whether to allow CORS
    pub allow_cors: bool,
    /// Request timeout in seconds
    pub timeout_secs: u64,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            allow_cors: true,
            timeout_secs: 300,
        }
    }
}

/// Build the axum router with all routes and middleware
pub fn build_router(state: AppState) -> axum::Router {
    use axum::routing::{get, post};
    use routes::{chat_completions, embeddings, health, list_models, root};

    // Check CORS config before consuming state
    let allow_cors = state.config.allow_cors;

    let mut app = axum::Router::new()
        // OpenAI-compatible endpoints
        .route("/", get(root))
        .route("/health", get(health))
        .route("/v1/chat/completions", post(chat_completions))
        .route("/v1/embeddings", post(embeddings))
        .route("/v1/models", get(list_models))
        // Streaming endpoint
        .route("/v1/chat/completions/stream", post(routes::chat_completions_stream))
        .with_state(state)
        .layer(TraceLayer::new_for_http());

    // Add CORS if enabled
    if allow_cors {
        let cors = CorsLayer::new()
            .allow_origin(Any)
            .allow_methods(Any)
            .allow_headers(Any);
        app = app.layer(cors);
    }

    app
}

/// Start the HTTP server
pub async fn start(addr: &str, state: AppState) -> crate::Result<()> {
    let router = build_router(state);

    info!("Starting OmniRoute HTTP server on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.map_err(|e| {
        crate::Error::Internal(format!("Failed to bind to {}: {}", addr, e))
    })?;
    axum::serve(listener, router).await?;

    Ok(())
}
