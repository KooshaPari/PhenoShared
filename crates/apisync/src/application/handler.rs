//! Request handlers for the application layer

use crate::domain::{Request, Response};

/// Default handler trait for processing requests
pub trait Handler: Send + Sync {
    /// Handle a request and return a response
    fn handle(&self, request: Request) -> Response;
}
