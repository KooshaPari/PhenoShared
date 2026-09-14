//! Middleware traits and implementations.

pub mod request_id;

use async_trait::async_trait;
pub use request_id::RequestIdMiddleware;

use crate::domain::{Request, Response};

/// Middleware trait.
///
/// The `F: 'static` bound keeps the trait object simple — most middleware
/// closures are `'static` (e.g. capturing `Arc<SomeService>`) and this lets
/// us sidestep the trickier lifetime plumbing that `async_trait` introduces
/// for borrowed closure types.
#[async_trait]
pub trait Middleware<F>: Send + Sync
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync
        + 'static,
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
