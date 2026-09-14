//! Endpoint implementations shipped with `apisync`.
//!
//! Each endpoint implements the [`crate::domain::Endpoint`] trait so callers
//! can mount them on any router (the in-tree [`crate::application::Router`] or
//! a downstream consumer's own routing layer).

use std::sync::Arc;

use async_trait::async_trait;
use serde::Serialize;

use crate::domain::{CreateItem, Endpoint, ItemStore, Request, Response, UpdateItem};

/// Serialize `value` as JSON and return a response with the given status code.
///
/// Falls back to a `500 Internal Server Error` response if serialization fails,
/// rather than panicking on the hot path (which would tear down the connection
/// task and propagate poison to every subsequent request; see L4/L25 in the
/// audit). This mirrors the safe-fallback pattern used by `convert_response`
/// in the hyper adapter.
fn json_response<T: Serialize + ?Sized>(value: &T, status: u16) -> Response {
    match serde_json::to_vec(value) {
        Ok(body) => {
            Response::new(status).with_header("Content-Type", "application/json").with_body(body)
        }
        Err(_) => Response::server_error(),
    }
}

/// REST endpoint that handles all CRUD operations for `Item`.
pub struct ItemCrudEndpoint {
    store: Arc<ItemStore>,
}

impl ItemCrudEndpoint {
    pub fn new() -> Self {
        Self { store: Arc::new(ItemStore::new()) }
    }
}

impl Default for ItemCrudEndpoint {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Endpoint for ItemCrudEndpoint {
    async fn handle(&self, req: Request) -> Response {
        match (req.method.as_str(), req.path.as_str()) {
            ("GET", "/items") => json_response(&self.store.list(), 200),
            ("GET", path) if path.starts_with("/items/") => {
                let id = path.strip_prefix("/items/").and_then(|s| s.parse::<u64>().ok());
                match id {
                    Some(id) => match self.store.get(id) {
                        Some(item) => json_response(&item, 200),
                        None => Response::not_found(),
                    },
                    None => Response::not_found(),
                }
            }
            ("POST", "/items") => {
                let body =
                    req.body.as_ref().and_then(|b| serde_json::from_slice::<CreateItem>(b).ok());
                match body {
                    Some(create) => json_response(&self.store.create(create), 201),
                    None => Response::new(400),
                }
            }
            ("PUT", path) if path.starts_with("/items/") => {
                let id = path.strip_prefix("/items/").and_then(|s| s.parse::<u64>().ok());
                let body =
                    req.body.as_ref().and_then(|b| serde_json::from_slice::<UpdateItem>(b).ok());
                match (id, body) {
                    (Some(id), Some(update)) => match self.store.update(id, update) {
                        Some(item) => json_response(&item, 200),
                        None => Response::not_found(),
                    },
                    _ => Response::new(400),
                }
            }
            ("DELETE", path) if path.starts_with("/items/") => {
                let id = path.strip_prefix("/items/").and_then(|s| s.parse::<u64>().ok());
                match id {
                    Some(id) => match self.store.delete(id) {
                        Some(_) => Response::ok(),
                        None => Response::not_found(),
                    },
                    None => Response::new(400),
                }
            }
            _ => Response::not_found(),
        }
    }
}

/// `Endpoint` that answers `GET /healthz` with `200 OK`.
///
/// Suitable for liveness probes; it succeeds as long as the runtime is
/// reachable, regardless of downstream dependency state.
pub struct HealthzEndpoint;

#[async_trait]
impl Endpoint for HealthzEndpoint {
    async fn handle(&self, req: Request) -> Response {
        if req.method == "GET" && req.path == "/healthz" {
            Response::ok()
        } else {
            Response::not_found()
        }
    }
}

/// `Endpoint` that answers `GET /readyz` with `200 OK`.
///
/// A readiness probe should be cheap and side-effect-free, so this returns
/// `ok` by default. Downstream services can wrap this with dependency-aware
/// checks when they need stricter gating.
pub struct ReadyzEndpoint;

#[async_trait]
impl Endpoint for ReadyzEndpoint {
    async fn handle(&self, req: Request) -> Response {
        if req.method == "GET" && req.path == "/readyz" {
            Response::ok()
        } else {
            Response::not_found()
        }
    }
}

#[cfg(test)]
mod tests {
    use serde::ser::Error as _;
    use serde::{Serialize, Serializer};

    use super::*;

    /// A `Serialize` impl that always returns a custom error, used to prove
    /// `json_response` falls back to 500 instead of panicking.
    struct Unserializable;

    impl Serialize for Unserializable {
        fn serialize<S: Serializer>(&self, _serializer: S) -> Result<S::Ok, S::Error> {
            Err(S::Error::custom("intentional serialization failure"))
        }
    }

    #[test]
    fn json_response_serializes_normal_value() {
        let resp = json_response(&"hello", 200);
        assert_eq!(resp.status, 200);
        assert_eq!(
            resp.headers.iter().find(|(k, _)| k == "Content-Type").map(|(_, v)| v.as_str()),
            Some("application/json")
        );
        let body = resp.body.expect("body should be set on success");
        assert_eq!(body, br#""hello""#);
    }

    #[test]
    fn json_response_falls_back_to_500_on_serialization_error() {
        let resp = json_response(&Unserializable, 201);
        assert_eq!(resp.status, 500);
        assert!(resp.body.is_none(), "500 fallback must not include a partial body");
    }

    #[test]
    fn json_response_preserves_status_on_success() {
        let ok = json_response(&vec![1u32, 2, 3], 200);
        assert_eq!(ok.status, 200);
        let created = json_response(&vec![1u32, 2, 3], 201);
        assert_eq!(created.status, 201);
    }

    #[tokio::test]
    async fn healthz_returns_ok() {
        let resp = HealthzEndpoint.handle(Request::new("/healthz", "GET")).await;
        assert_eq!(resp.status, 200);
    }

    #[tokio::test]
    async fn healthz_rejects_other_methods() {
        let resp = HealthzEndpoint.handle(Request::new("/healthz", "POST")).await;
        assert_eq!(resp.status, 404);
    }

    #[tokio::test]
    async fn readyz_returns_ok() {
        let resp = ReadyzEndpoint.handle(Request::new("/readyz", "GET")).await;
        assert_eq!(resp.status, 200);
    }

    #[tokio::test]
    async fn readyz_rejects_other_paths() {
        let resp = ReadyzEndpoint.handle(Request::new("/nope", "GET")).await;
        assert_eq!(resp.status, 404);
    }
}
