//! Middleware traits and implementations

use crate::domain::{Request, Response};
use async_trait::async_trait;

/// Middleware trait
#[async_trait]
pub trait Middleware<F>: Send + Sync
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync,
{
    async fn handle(&self, request: Request, next: Next<F>) -> Response;
}

/// Next handler in middleware chain
pub struct Next<F>
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync,
{
    handler: F,
}

impl<F> Next<F>
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync,
{
    pub fn new(handler: F) -> Self {
        Self { handler }
    }
}

impl<F> Next<F>
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync,
{
    pub async fn run(&self, request: Request) -> Response {
        (self.handler)(request).await
    }
}
