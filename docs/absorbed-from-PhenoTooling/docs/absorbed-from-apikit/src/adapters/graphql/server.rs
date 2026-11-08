//! GraphQL server adapter that integrates with the existing `Router`.

use std::sync::Arc;

use async_trait::async_trait;

use crate::domain::{Endpoint, Request, Response};

use super::schema::GraphQLSchema;

/// HTTP endpoint that serves GraphQL queries and mutations.
pub struct GraphQLEndpoint {
    schema: GraphQLSchema,
}

impl GraphQLEndpoint {
    /// Create a new endpoint from an existing schema.
    pub fn new(schema: GraphQLSchema) -> Self {
        Self { schema }
    }

    /// Convenience constructor that builds a schema from an `ItemStore`.
    pub fn with_store(store: Arc<crate::domain::ItemStore>) -> Self {
        Self::new(super::schema::build_schema(store))
    }
}

#[derive(serde::Deserialize)]
struct GraphQLRequestBody {
    query: String,
    #[serde(default)]
    variables: Option<serde_json::Value>,
    #[serde(default)]
    operation_name: Option<String>,
}

#[async_trait]
impl Endpoint for GraphQLEndpoint {
    async fn handle(&self, req: Request) -> Response {
        if req.method == "POST" {
            let body = match req.body {
                Some(body) => body,
                None => return Response::new(400),
            };

            let gql_req: GraphQLRequestBody = match serde_json::from_slice(&body) {
                Ok(r) => r,
                Err(_) => return Response::new(400),
            };

            let mut request = async_graphql::Request::new(gql_req.query);
            if let Some(vars) = gql_req.variables {
                request = request.variables(async_graphql::Variables::from_json(vars));
            }
            if let Some(op) = gql_req.operation_name {
                request = request.operation_name(op);
            }

            let response = self.schema.execute(request).await;
            let json = match serde_json::to_vec(&response) {
                Ok(bytes) => bytes,
                Err(_) => return Response::server_error(),
            };

            Response::ok()
                .with_header("Content-Type", "application/json")
                .with_body(json)
        } else if req.method == "GET" {
            let html = r#"<!DOCTYPE html>
<html>
<head><title>GraphQL</title></head>
<body><h1>GraphQL Endpoint</h1><p>Send POST requests with JSON-encoded GraphQL queries.</p></body>
</html>"#;
            Response::ok()
                .with_header("Content-Type", "text/html")
                .with_body(html.as_bytes().to_vec())
        } else {
            Response::new(405)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::ItemStore;

    fn setup_endpoint() -> GraphQLEndpoint {
        let store = Arc::new(ItemStore::new());
        GraphQLEndpoint::with_store(store)
    }

    #[tokio::test]
    async fn test_post_query() {
        let endpoint = setup_endpoint();
        let body = serde_json::json!({
            "query": "{ items { id name description } }"
        })
        .to_string()
        .into_bytes();
        let req = Request::new("/graphql", "POST").with_body(body);
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);
        let body = res.body.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(json["data"]["items"].as_array().unwrap().is_empty());
    }

    #[tokio::test]
    async fn test_post_mutation() {
        let endpoint = setup_endpoint();
        let body = serde_json::json!({
            "query": r#"mutation { createItem(input: { name: "Test", description: "Desc" }) { id name description } }"#
        })
        .to_string()
        .into_bytes();
        let req = Request::new("/graphql", "POST").with_body(body);
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);
        let body = res.body.unwrap();
        let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(json["data"]["createItem"]["name"], "Test");
    }

    #[tokio::test]
    async fn test_get_request() {
        let endpoint = setup_endpoint();
        let req = Request::new("/graphql", "GET");
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 200);
        let body = res.body.unwrap();
        let html = String::from_utf8(body).unwrap();
        assert!(html.contains("GraphQL"));
    }

    #[tokio::test]
    async fn test_invalid_method() {
        let endpoint = setup_endpoint();
        let req = Request::new("/graphql", "DELETE");
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 405);
    }

    #[tokio::test]
    async fn test_invalid_json_body() {
        let endpoint = setup_endpoint();
        let req = Request::new("/graphql", "POST").with_body(b"not-json".to_vec());
        let res = endpoint.handle(req).await;
        assert_eq!(res.status, 400);
    }
}

