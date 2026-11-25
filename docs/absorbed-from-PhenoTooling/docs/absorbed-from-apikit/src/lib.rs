//! Main library entry point for apikit

pub mod adapters;
pub mod application;
pub mod domain;
pub mod endpoints;
pub mod infrastructure;

pub use adapters::*;
pub use application::*;
pub use domain::*;
pub use endpoints::*;
pub use infrastructure::*;

/// Main library entry point (placeholder)
pub struct ApiKit;

impl Default for ApiKit {
    fn default() -> Self {
        Self::new()
    }
}

impl ApiKit {
    pub fn new() -> Self {
        ApiKit
    }
}
