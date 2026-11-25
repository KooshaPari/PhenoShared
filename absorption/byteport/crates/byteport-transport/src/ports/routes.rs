//! Route registry — owner-scoped path routing for the BytePort API surface.
//!
//! A [`Router`] holds a list of [`Route`] entries and can look them up by
//! `(path, method)` or perform an authorisation check that also verifies the
//! request owner matches the route's owner.

use thiserror::Error;

/// A single route definition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Route {
    /// URL path (e.g. `"/v1/upload"`).
    pub path: String,
    /// HTTP method (e.g. `"POST"`).
    pub method: String,
    /// Optional owner.  When `Some`, only the matching owner may access the
    /// route.
    pub owner: Option<String>,
    /// Name of the handler that processes this route.
    pub handler: String,
}

/// Errors produced by router look-ups and authorization checks.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum RouteError {
    #[error("no route found for the given path and method")]
    NotFound,
    #[error("request owner is not authorised for this route")]
    Forbidden,
    #[error("method not allowed for this path")]
    MethodNotAllowed,
}

/// A simple, append-order route registry.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Router {
    routes: Vec<Route>,
}

impl Router {
    /// Create an empty router.
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a route.
    pub fn add_route(&mut self, route: Route) {
        self.routes.push(route);
    }

    /// Find a route matching `path` and `method`.
    pub fn find_route(&self, path: &str, method: &str) -> Result<&Route, RouteError> {
        let matching_path: Vec<&Route> = self.routes.iter().filter(|r| r.path == path).collect();

        if matching_path.is_empty() {
            return Err(RouteError::NotFound);
        }

        matching_path
            .iter()
            .find(|r| r.method.eq_ignore_ascii_case(method))
            .copied()
            .ok_or(RouteError::MethodNotAllowed)
    }

    /// Authorise a request: find the route **and** verify that
    /// `request_owner` is allowed to access it.
    pub fn authorize(&self, path: &str, method: &str, request_owner: &str) -> Result<&Route, RouteError> {
        let route = self.find_route(path, method)?;
        match &route.owner {
            Some(owner) if owner != request_owner => Err(RouteError::Forbidden),
            _ => Ok(route),
        }
    }

    /// Return all registered routes.
    pub fn list_routes(&self) -> &[Route] {
        &self.routes
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_route(path: &str) -> Route {
        Route {
            path: path.to_string(),
            method: "GET".to_string(),
            owner: Some("alice".to_string()),
            handler: "get_resource".to_string(),
        }
    }

    #[test]
    fn test_add_and_find_route() {
        let mut router = Router::new();
        let route = sample_route("/v1/data");
        router.add_route(route.clone());

        let found = router.find_route("/v1/data", "GET").unwrap();
        assert_eq!(found.path, route.path);
        assert_eq!(found.method, route.method);
    }

    #[test]
    fn test_find_route_not_found() {
        let router = Router::new();
        assert_eq!(router.find_route("/nonexistent", "GET"), Err(RouteError::NotFound));
    }

    #[test]
    fn test_authorize_owner_match() {
        let mut router = Router::new();
        router.add_route(sample_route("/v1/data"));

        let result = router.authorize("/v1/data", "GET", "alice");
        assert!(result.is_ok());
        assert_eq!(result.unwrap().handler, "get_resource");
    }

    #[test]
    fn test_authorize_owner_mismatch_forbidden() {
        let mut router = Router::new();
        router.add_route(sample_route("/v1/data"));

        assert_eq!(router.authorize("/v1/data", "GET", "bob"), Err(RouteError::Forbidden));
    }
}
