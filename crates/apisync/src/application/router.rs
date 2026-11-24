//! Router implementation

use std::collections::HashMap;
use std::sync::Arc;

use async_trait::async_trait;

use crate::domain::{Endpoint, Request, Response};

pub struct Router {
    routes: HashMap<String, Arc<dyn Endpoint>>,
}

impl Default for Router {
    fn default() -> Self {
        Self::new()
    }
}

impl Router {
    pub fn new() -> Self {
        Self { routes: HashMap::new() }
    }

    pub fn route<E: Endpoint + 'static>(&mut self, path: impl Into<String>, endpoint: E) {
        self.routes.insert(path.into(), Arc::new(endpoint));
    }

    pub async fn handle(&self, req: Request) -> Response {
        if let Some(ep) = self.routes.get(&req.path) {
            ep.handle(req).await
        } else {
            crate::domain::Response::not_found()
        }
    }
}

#[async_trait]
impl Endpoint for Router {
    async fn handle(&self, req: Request) -> Response {
        Router::handle(self, req).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct EchoEndpoint;

    #[async_trait]
    impl Endpoint for EchoEndpoint {
        async fn handle(&self, _req: Request) -> Response {
            Response::ok()
        }
    }

    #[tokio::test]
    async fn default_router_has_no_routes() {
        let router = Router::default();
        let res = router.handle(Request::new("/anything", "GET")).await;
        assert_eq!(res.status, 404);
    }

    #[tokio::test]
    async fn routes_to_registered_endpoint() {
        let mut router = Router::new();
        router.route("/items", EchoEndpoint);
        let res = router.handle(Request::new("/items", "GET")).await;
        assert_eq!(res.status, 200);
    }

    #[tokio::test]
    async fn returns_404_for_unregistered_path() {
        let mut router = Router::new();
        router.route("/items", EchoEndpoint);
        let res = router.handle(Request::new("/missing", "GET")).await;
        assert_eq!(res.status, 404);
    }

    #[tokio::test]
    async fn router_itself_implements_endpoint() {
        let mut router = Router::new();
        router.route("/items", EchoEndpoint);
        let res = Endpoint::handle(&router, Request::new("/items", "GET")).await;
        assert_eq!(res.status, 200);
    }
}
