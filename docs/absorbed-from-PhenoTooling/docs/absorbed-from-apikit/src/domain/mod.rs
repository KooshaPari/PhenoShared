//! Domain layer - Core types and traits

pub mod middleware;

pub use middleware::{Middleware, Next};

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    pub path: String,
    pub method: String,
    pub headers: Vec<(String, String)>,
    pub body: Option<Vec<u8>>,
}

impl Request {
    pub fn new(path: impl Into<String>, method: impl Into<String>) -> Self {
        Self { path: path.into(), method: method.into(), headers: Vec::new(), body: None }
    }

    pub fn with_header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.push((key.into(), value.into()));
        self
    }

    pub fn with_body(mut self, body: Vec<u8>) -> Self {
        self.body = Some(body);
        self
    }
}

#[derive(Debug, Clone)]
pub struct Response {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: Option<Vec<u8>>,
}

impl Response {
    pub fn new(status: u16) -> Self {
        Self { status, headers: Vec::new(), body: None }
    }

    pub fn ok() -> Self {
        Self::new(200)
    }

    pub fn not_found() -> Self {
        Self::new(404)
    }

    pub fn server_error() -> Self {
        Self::new(500)
    }

    pub fn with_header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.push((key.into(), value.into()));
        self
    }

    pub fn with_body(mut self, body: Vec<u8>) -> Self {
        self.body = Some(body);
        self
    }
}

#[async_trait]
pub trait Endpoint: Send + Sync {
    async fn handle(&self, req: Request) -> Response;
}

#[async_trait]
impl<E: Endpoint + Send + Sync> Endpoint for Box<E> {
    async fn handle(&self, req: Request) -> Response {
        self.as_ref().handle(req).await
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Item {
    pub id: u64,
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateItem {
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateItem {
    pub name: Option<String>,
    pub description: Option<String>,
}

pub struct ItemStore {
    items: std::sync::Mutex<std::collections::HashMap<u64, Item>>,
    next_id: std::sync::Mutex<u64>,
}

impl Default for ItemStore {
    fn default() -> Self {
        Self::new()
    }
}

impl ItemStore {
    pub fn new() -> Self {
        Self {
            items: std::sync::Mutex::new(std::collections::HashMap::new()),
            next_id: std::sync::Mutex::new(1),
        }
    }

    pub fn list(&self) -> Vec<Item> {
        let items = self.items.lock().unwrap();
        let mut result: Vec<Item> = items.values().cloned().collect();
        result.sort_by_key(|item| item.id);
        result
    }

    pub fn get(&self, id: u64) -> Option<Item> {
        let items = self.items.lock().unwrap();
        items.get(&id).cloned()
    }

    pub fn create(&self, create: CreateItem) -> Item {
        let mut next_id = self.next_id.lock().unwrap();
        let id = *next_id;
        *next_id += 1;

        let item = Item { id, name: create.name, description: create.description };

        let mut items = self.items.lock().unwrap();
        items.insert(id, item.clone());
        item
    }

    pub fn update(&self, id: u64, update: UpdateItem) -> Option<Item> {
        let mut items = self.items.lock().unwrap();
        items.get_mut(&id).map(|item| {
            if let Some(name) = update.name {
                item.name = name;
            }
            if let Some(description) = update.description {
                item.description = description;
            }
            item.clone()
        })
    }

    pub fn delete(&self, id: u64) -> Option<Item> {
        let mut items = self.items.lock().unwrap();
        items.remove(&id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_request_new() {
        let req = Request::new("/users", "GET");
        assert_eq!(req.path, "/users");
        assert_eq!(req.method, "GET");
        assert!(req.headers.is_empty());
        assert!(req.body.is_none());
    }

    #[test]
    fn test_request_with_header() {
        let req = Request::new("/users", "GET").with_header("Content-Type", "application/json");
        assert_eq!(req.headers.len(), 1);
        assert_eq!(req.headers[0], ("Content-Type".into(), "application/json".into()));
    }

    #[test]
    fn test_request_with_body() {
        let req = Request::new("/users", "POST").with_body(vec![1, 2, 3]);
        assert!(req.body.is_some());
        assert_eq!(req.body.as_ref().unwrap(), &[1, 2, 3]);
    }

    #[test]
    fn test_response_ok() {
        let res = Response::ok();
        assert_eq!(res.status, 200);
        assert!(res.headers.is_empty());
    }

    #[test]
    fn test_response_not_found() {
        let res = Response::not_found();
        assert_eq!(res.status, 404);
    }

    #[test]
    fn test_response_server_error() {
        let res = Response::server_error();
        assert_eq!(res.status, 500);
    }

    #[test]
    fn test_response_with_header() {
        let res = Response::ok().with_header("Content-Type", "application/json");
        assert_eq!(res.headers.len(), 1);
    }

    #[test]
    fn test_response_with_body() {
        let res = Response::ok().with_body(b"hello".to_vec());
        assert!(res.body.is_some());
        assert_eq!(res.body.unwrap(), b"hello");
    }

    #[derive(Clone)]
    struct TestEndpoint(u16);

    #[async_trait]
    impl Endpoint for TestEndpoint {
        async fn handle(&self, _req: Request) -> Response {
            Response::new(self.0)
        }
    }

    #[tokio::test]
    async fn test_endpoint_trait() {
        let ep = TestEndpoint(200);
        let req = Request::new("/test", "GET");
        let res = ep.handle(req).await;
        assert_eq!(res.status, 200);
    }

    #[tokio::test]
    async fn test_boxed_endpoint() {
        let ep: Box<dyn Endpoint> = Box::new(TestEndpoint(201));
        let req = Request::new("/test", "GET");
        let res = ep.handle(req).await;
        assert_eq!(res.status, 201);
    }
}
