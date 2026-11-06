use httpora_core::builder::{HttpRequest, ResponseBuilder};
use httpora_core::middleware::cors::{CorsConfig, CorsLayer};
use std::collections::HashMap;

#[test]
fn permissive_preflight_sets_cors_headers() {
    let layer = CorsLayer::permissive();
    let mut headers = HashMap::new();
    headers.insert("Origin".to_owned(), "https://example.com".to_owned());
    let request = HttpRequest {
        method: "OPTIONS".to_owned(),
        path: "/resource".to_owned(),
        body: Vec::new(),
        headers,
        query: HashMap::new(),
    };

    let response = layer.preflight(&request);

    assert_eq!(response.status, 204);
    assert_eq!(
        response.headers.get("Access-Control-Allow-Origin"),
        Some(&"*".to_owned())
    );
    assert!(response
        .headers
        .get("Access-Control-Allow-Methods")
        .is_some_and(|value| value.contains("GET")));
}

#[test]
fn restricted_cors_decorates_allowed_origin_only() {
    let layer = CorsLayer::with_config(CorsConfig {
        allowed_origins: vec!["https://allowed.example".to_owned()],
        allow_credentials: true,
        ..Default::default()
    });
    let mut headers = HashMap::new();
    headers.insert("Origin".to_owned(), "https://allowed.example".to_owned());
    let request = HttpRequest {
        method: "GET".to_owned(),
        path: "/resource".to_owned(),
        body: Vec::new(),
        headers,
        query: HashMap::new(),
    };
    let mut response = ResponseBuilder::text(200, "ok");

    layer.decorate_response(&request, &mut response);

    assert_eq!(
        response.headers.get("Access-Control-Allow-Origin"),
        Some(&"https://allowed.example".to_owned())
    );
    assert_eq!(
        response.headers.get("Access-Control-Allow-Credentials"),
        Some(&"true".to_owned())
    );
}
