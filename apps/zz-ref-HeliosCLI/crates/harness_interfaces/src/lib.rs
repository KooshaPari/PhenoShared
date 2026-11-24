// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Interfaces module - Protocol definitions for heliosHarness

use std::collections::HashMap;
use uuid::Uuid;

/// Request context
#[derive(Debug, Clone)]
pub struct Request {
    pub id: String,
    pub method: String,
    pub path: String,
    pub headers: HashMap<String, String>,
    pub body: Option<Vec<u8>>,
}

impl Request {
    pub fn new(method: &str, path: &str) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            method: method.to_string(),
            path: path.to_string(),
            headers: HashMap::new(),
            body: None,
        }
    }

    pub fn with_header(mut self, key: &str, val: &str) -> Self {
        self.headers.insert(key.to_string(), val.to_string());
        self
    }

    pub fn with_body(mut self, body: Vec<u8>) -> Self {
        self.body = Some(body);
        self
    }
}

/// Response
#[derive(Debug, Clone)]
pub struct Response {
    pub status: u16,
    pub headers: HashMap<String, String>,
    pub body: Option<Vec<u8>>,
}

impl Response {
    pub fn ok() -> Self {
        Self { status: 200, headers: HashMap::new(), body: None }
    }
    pub fn created() -> Self {
        Self { status: 201, headers: HashMap::new(), body: None }
    }
    pub fn error(status: u16) -> Self {
        Self { status, headers: HashMap::new(), body: None }
    }

    pub fn with_header(mut self, key: &str, val: &str) -> Self {
        self.headers.insert(key.to_string(), val.to_string());
        self
    }

    pub fn with_body(mut self, body: Vec<u8>) -> Self {
        self.body = Some(body);
        self
    }
}

/// Event for pub/sub
#[derive(Debug, Clone)]
pub struct Event {
    pub topic: String,
    pub payload: Vec<u8>,
    pub metadata: HashMap<String, String>,
}

impl Event {
    pub fn new(topic: &str, payload: Vec<u8>) -> Self {
        Self { topic: topic.to_string(), payload, metadata: HashMap::new() }
    }
}

/// Simple UUID v4 generator
/// Handler trait for request processing
pub trait Handler: Send + Sync {
    fn handle(&self, request: Request) -> Response;
}

/// Publisher trait for event systems
pub trait Publisher: Send + Sync {
    fn publish(&self, event: Event) -> Result<(), String>;
}

/// Subscriber trait for event systems
#[allow(async_fn_in_trait)]
pub trait Subscriber: Send + Sync {
    async fn on_event(&self, event: Event);
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-HELIOS-IFACE-001 (request builder)
    #[test]
    fn request_builder_sets_fields_and_unique_ids() {
        let r = Request::new("GET", "/health")
            .with_header("x-trace", "abc")
            .with_body(b"ping".to_vec());
        assert_eq!(r.method, "GET");
        assert_eq!(r.path, "/health");
        assert_eq!(r.headers.get("x-trace").map(String::as_str), Some("abc"));
        assert_eq!(r.body.as_deref(), Some(b"ping".as_ref()));
        assert!(!r.id.is_empty());

        let other = Request::new("GET", "/health");
        assert_ne!(r.id, other.id, "request ids must be unique");
    }

    // Traces to: FR-HELIOS-IFACE-002 (response constructors)
    #[test]
    fn response_constructors_carry_expected_status() {
        assert_eq!(Response::ok().status, 200);
        assert_eq!(Response::created().status, 201);
        assert_eq!(Response::error(503).status, 503);
    }

    // Traces to: FR-HELIOS-IFACE-002 (response builder)
    #[test]
    fn response_builder_sets_header_and_body() {
        let resp = Response::ok()
            .with_header("content-type", "application/json")
            .with_body(b"{}".to_vec());
        assert_eq!(resp.headers.get("content-type").map(String::as_str), Some("application/json"));
        assert_eq!(resp.body.as_deref(), Some(b"{}".as_ref()));
    }

    // Traces to: FR-HELIOS-IFACE-003 (event pub/sub payload)
    #[test]
    fn event_new_preserves_topic_and_payload() {
        let e = Event::new("orders", vec![1, 2, 3]);
        assert_eq!(e.topic, "orders");
        assert_eq!(e.payload, vec![1, 2, 3]);
        assert!(e.metadata.is_empty());
    }

    struct EchoHandler;
    impl Handler for EchoHandler {
        fn handle(&self, request: Request) -> Response {
            Response::ok().with_header("echo-path", &request.path)
        }
    }

    // Traces to: FR-HELIOS-IFACE-004 (handler trait)
    #[test]
    fn handler_trait_processes_request() {
        let handler = EchoHandler;
        let resp = handler.handle(Request::new("POST", "/echo"));
        assert_eq!(resp.status, 200);
        assert_eq!(resp.headers.get("echo-path").map(String::as_str), Some("/echo"));
    }

    struct CountingPublisher;
    impl Publisher for CountingPublisher {
        fn publish(&self, event: Event) -> Result<(), String> {
            if event.topic.is_empty() {
                Err("empty topic".to_string())
            } else {
                Ok(())
            }
        }
    }

    // Traces to: FR-HELIOS-IFACE-005 (publisher trait)
    #[test]
    fn publisher_trait_reports_errors() {
        let pubr = CountingPublisher;
        assert!(pubr.publish(Event::new("t", vec![])).is_ok());
        assert!(pubr.publish(Event::new("", vec![])).is_err());
    }
}
