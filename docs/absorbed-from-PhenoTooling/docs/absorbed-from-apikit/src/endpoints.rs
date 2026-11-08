//! CRUD endpoints for domain models

use std::sync::Arc;

use async_trait::async_trait;

use crate::domain::{CreateItem, Endpoint, ItemStore, Request, Response, UpdateItem};

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
            ("GET", "/items") => {
                let items = self.store.list();
                let body = serde_json::to_vec(&items).unwrap();
                Response::ok().with_header("Content-Type", "application/json").with_body(body)
            }
            ("GET", path) if path.starts_with("/items/") => {
                let id = path.strip_prefix("/items/").and_then(|s| s.parse::<u64>().ok());
                match id {
                    Some(id) => match self.store.get(id) {
                        Some(item) => {
                            let body = serde_json::to_vec(&item).unwrap();
                            Response::ok()
                                .with_header("Content-Type", "application/json")
                                .with_body(body)
                        }
                        None => Response::not_found(),
                    },
                    None => Response::not_found(),
                }
            }
            ("POST", "/items") => {
                let body =
                    req.body.as_ref().and_then(|b| serde_json::from_slice::<CreateItem>(b).ok());
                match body {
                    Some(create) => {
                        let item = self.store.create(create);
                        let body = serde_json::to_vec(&item).unwrap();
                        Response::new(201)
                            .with_header("Content-Type", "application/json")
                            .with_body(body)
                    }
                    None => Response::new(400),
                }
            }
            ("PUT", path) if path.starts_with("/items/") => {
                let id = path.strip_prefix("/items/").and_then(|s| s.parse::<u64>().ok());
                let body =
                    req.body.as_ref().and_then(|b| serde_json::from_slice::<UpdateItem>(b).ok());
                match (id, body) {
                    (Some(id), Some(update)) => match self.store.update(id, update) {
                        Some(item) => {
                            let body = serde_json::to_vec(&item).unwrap();
                            Response::ok()
                                .with_header("Content-Type", "application/json")
                                .with_body(body)
                        }
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
