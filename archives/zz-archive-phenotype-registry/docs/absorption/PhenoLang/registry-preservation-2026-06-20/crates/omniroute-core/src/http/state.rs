//! Application state management

use super::{AppState, ServerConfig, ServerState};
use crate::router::Router;
use std::sync::Arc;

/// Create a new application state
pub fn create_state(router: Router, config: ServerConfig) -> AppState {
    Arc::new(ServerState { router, config })
}

/// Create state with default configuration
pub fn create_state_with_defaults(router: Router) -> AppState {
    create_state(router, ServerConfig::default())
}
