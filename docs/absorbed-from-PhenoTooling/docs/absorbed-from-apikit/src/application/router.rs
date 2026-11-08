//! Router implementation

use crate::domain::{Endpoint, Request, Response};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

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
