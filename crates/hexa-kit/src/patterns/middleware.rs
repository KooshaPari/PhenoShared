// <!-- Migrated from <REDACTED>/Apisync (archived 2026-06-19) — original commit d981353 -->

//! Middleware traits and implementations
//!
//! Reference pattern from Apisync's hexagonal `src/domain/middleware.rs`.
//! This file is documentation/reference-quality and is intentionally NOT
//! compiled as part of the HexaKit library crate (it depends on `async_trait`
//! and serde-derived Request/Response types that do not exist in HexaKit).
//!
//! See `domain_mod.rs` in this directory for the related `Request`, `Response`,
//! and `Endpoint` types that compose with `Middleware`.

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
