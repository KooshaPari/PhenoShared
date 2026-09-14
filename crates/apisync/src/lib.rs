//! Main library entry point for apisync

pub mod adapters;
pub mod application;
pub mod clients;
pub mod domain;
pub mod endpoints;
pub mod error;
pub mod infrastructure;

// Stable public prelude — explicit re-exports rather than glob wildcards so
// downstream crates get a predictable API surface and rustdoc renders clearly.
// Client adapters
pub use clients::{GraphQlClient, RestClient, WsConnection};
// GraphQL adapter — schema types are re-exported through adapters::graphql
pub use adapters::graphql::{
    build_schema, GraphItem, GraphQLSchema, MutationRoot, QueryRoot, SubscriptionRoot,
};
// REST adapter
pub use adapters::rest::HyperServer;
// WebSocket adapter — types are re-exported through adapters::websocket
pub use adapters::websocket::{BroadcastHub, WebSocketEndpoint, WebSocketServer, WsMessage};
// Application layer
pub use application::router::Router;
// Domain types
pub use domain::middleware::{Middleware, Next, RequestIdMiddleware};
pub use domain::{CreateItem, Endpoint, Item, ItemStore, Request, Response, UpdateItem};
// Error type
pub use error::{Error, Result};
// CRUD endpoint
pub use endpoints::{HealthzEndpoint, ItemCrudEndpoint, ReadyzEndpoint};
// Logging initializer (re-export the module so callers can call `apisync::logging::init()`)
pub use infrastructure::logging;

/// Top-level handle for the apisync library.
///
/// Construct with [`ApiKit::new`] to obtain a configured instance that can
/// spawn [`HyperServer`]s, attach [`Endpoint`] implementations, and create
/// outbound client connections ([`RestClient`], [`GraphQlClient`], [`WsConnection`]).
///
/// # Examples
///
/// ```no_run
/// use apisync::ApiKit;
///
/// let kit = ApiKit::new();
/// let client = kit.rest_client("https://api.example.com");
/// ```
pub struct ApiKit;

impl Default for ApiKit {
    fn default() -> Self {
        Self::new()
    }
}

impl ApiKit {
    /// Create a new ApiKit instance.
    pub fn new() -> Self {
        ApiKit
    }

    /// Create a [`RestClient`] targeting the given base URL.
    pub fn rest_client(&self, base_url: impl Into<String>) -> RestClient {
        RestClient::new(base_url)
    }

    /// Create a [`GraphQlClient`] targeting the given endpoint URL.
    pub fn graphql_client(&self, endpoint: impl Into<String>) -> GraphQlClient {
        GraphQlClient::new(endpoint)
    }

    /// Create a [`WsConnection`] to the given WebSocket URL.
    pub async fn ws_connect(&self, url: &str) -> error::Result<WsConnection> {
        WsConnection::connect(url).await
    }
}
