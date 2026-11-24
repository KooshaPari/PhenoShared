//! Client-side adapters for making outbound requests.
//!
//! This module provides convenience wrappers for HTTP, GraphQL, and WebSocket
//! clients that pair with the server-side adapters in [`crate::adapters`].

pub mod graphql;
pub mod rest;
pub mod websocket;

pub use graphql::GraphQlClient;
pub use rest::RestClient;
pub use websocket::WsConnection;
