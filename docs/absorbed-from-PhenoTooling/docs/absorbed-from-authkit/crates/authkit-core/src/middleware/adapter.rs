use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::task::{Context, Poll};

use axum::body::Body;
use axum::http::{header, Request, StatusCode};
use axum::response::IntoResponse;
use axum::Json;
use http::header::HeaderValue;
use serde::Serialize;
use tower::{Layer, Service};
use tower::util::ServiceExt;

use crate::application::Authenticator;
use crate::domain::Claims;

/// Tower layer that injects `AuthKitMiddleware`.
#[derive(Clone)]
pub struct AuthKitMiddlewareAdapter {
    authenticator: Arc<Authenticator>,
}

impl AuthKitMiddlewareAdapter {
    /// Create a new middleware adapter.
    pub fn new(authenticator: Authenticator) -> Self {
        Self { authenticator: Arc::new(authenticator) }
    }

    /// Create a new middleware adapter from a shared authenticator.
    pub fn from_shared(authenticator: Arc<Authenticator>) -> Self {
        Self { authenticator }
    }
}

impl<S> Layer<S> for AuthKitMiddlewareAdapter {
    type Service = AuthKitMiddleware<S>;

    fn layer(&self, inner: S) -> Self::Service {
        AuthKitMiddleware { inner, authenticator: Arc::clone(&self.authenticator) }
    }
}

/// Tower service that validates `Authorization: Bearer` before calling the inner service.
#[derive(Clone)]
pub struct AuthKitMiddleware<S> {
    inner: S,
    authenticator: Arc<Authenticator>,
}

impl<S, B> Service<Request<B>> for AuthKitMiddleware<S>
where
    S: Service<Request<B>, Response = axum::response::Response, Error = Infallible>
        + Clone
        + Send
        + 'static,
    S::Future: Send + 'static,
    B: Send + 'static,
{
    type Response = axum::response::Response;
    type Error = Infallible;
    type Future = Pin<Box<dyn Future<Output = Result<Self::Response, Self::Error>> + Send>>;

    fn poll_ready(&mut self, cx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        self.inner.poll_ready(cx)
    }

    fn call(&mut self, mut req: Request<B>) -> Self::Future {
        let mut inner = self.inner.clone();
        let authenticator = Arc::clone(&self.authenticator);

        Box::pin(async move {
            let response = match authorize_request(&authenticator, &mut req) {
                Some(response) => response,
                None => match inner.call(req).await {
                    Ok(response) => response,
                    Err(err) => match err {},
                },
            };

            Ok(response)
        })
    }
}

#[derive(Debug, Serialize)]
struct UnauthorizedResponse {
    error: &'static str,
    message: String,
}

fn authorize_request<B>(
    authenticator: &Authenticator,
    request: &mut Request<B>,
) -> Option<axum::response::Response> {
    let header_value = match request.headers().get(header::AUTHORIZATION) {
        Some(header_value) => header_value,
        None => return Some(unauthorized("missing Authorization header")),
    };

    let header_value = match header_value.to_str() {
        Ok(value) => value,
        Err(_) => return Some(unauthorized("invalid Authorization header")),
    };

    let token = match extract_bearer_token(header_value) {
        Some(token) => token,
        None => return Some(unauthorized("Authorization must use the Bearer scheme")),
    };

    let claims = match authenticator.validate_bearer_token(&format!("Bearer {token}")) {
        Ok(claims) => claims,
        Err(_) => return Some(unauthorized("invalid bearer token")),
    };

    request.extensions_mut().insert(claims);
    None
}

fn extract_bearer_token(value: &str) -> Option<&str> {
    let mut parts = value.split_whitespace();
    let scheme = parts.next()?;
    let token = parts.next()?;

    if parts.next().is_some() || !scheme.eq_ignore_ascii_case("Bearer") || token.is_empty() {
        return None;
    }

    Some(token)
}

fn unauthorized(message: impl Into<String>) -> axum::response::Response {
    (
        StatusCode::UNAUTHORIZED,
        Json(UnauthorizedResponse { error: "unauthorized", message: message.into() }),
    )
        .into_response()
}

#[cfg(test)]
mod tests {
    use std::convert::Infallible;

    use axum::body::{to_bytes, Body};
    use http::Request;
    use tower::util::ServiceExt;

    use super::*;

    fn authenticator() -> Authenticator {
        Authenticator::new(
            crate::adapters::InMemoryUserRepository::default(),
            crate::adapters::InMemorySessionStore::default(),
            crate::adapters::Argon2Hasher::default(),
            crate::adapters::InMemoryKms::default(),
            crate::adapters::InMemoryVaultStore::default(),
            crate::adapters::InMemoryRevocationList::default(),
            crate::adapters::InMemoryRefreshTokenFamilyStore::default(),
            "test-secret-key-for-unit-tests-only",
        )
        .unwrap()
    }

    fn adapter() -> AuthKitMiddlewareAdapter {
        AuthKitMiddlewareAdapter::new(authenticator())
    }

    fn token_header(token: &str) -> String {
        format!("Bearer {token}")
    }

    async fn body_text(response: axum::response::Response) -> String {
        let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        String::from_utf8(bytes.to_vec()).unwrap()
    }

    #[tokio::test]
    async fn injects_claims_into_request_extensions() {
        let authenticator = authenticator();
        let user_id = "user-123".to_string();
        let token = authenticator.issue_access_token(&user_id, None).unwrap();

        let app = service_fn(|req: Request<Body>| async move {
            let claims = req.extensions().get::<Claims>().cloned().unwrap();
            Ok::<_, Infallible>(axum::response::Response::new(Body::from(
                claims.user_id().to_string(),
            )))
        });

        let response = adapter()
            .layer(app)
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::AUTHORIZATION, format!("bearer {token}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(body_text(response).await, user_id.to_string());
    }

    #[tokio::test]
    async fn accepts_lowercase_bearer_scheme() {
        let authenticator = authenticator();
        let user_id = "user-456".to_string();
        let token = authenticator.issue_access_token(&user_id, None).unwrap();

        let app = service_fn(|req: Request<Body>| async move {
            let claims = req.extensions().get::<Claims>().cloned().unwrap();
            Ok::<_, Infallible>(axum::response::Response::new(Body::from(
                claims.user_id().to_string(),
            )))
        });

        let response = adapter()
            .layer(app)
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::AUTHORIZATION, format!("bearer {token}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(body_text(response).await, user_id.to_string());
    }

    #[tokio::test]
    async fn rejects_missing_authorization_header() {
        let app = service_fn(|_req: Request<Body>| async move {
            Ok::<_, Infallible>(axum::response::Response::new(Body::from("reachable")))
        });

        let response = adapter()
            .layer(app)
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        assert_eq!(response.headers().get(header::CONTENT_TYPE).unwrap(), "application/json");
        let body = body_text(response).await;
        assert!(body.contains("missing Authorization header"));
    }

    #[tokio::test]
    async fn rejects_non_bearer_scheme() {
        let app = service_fn(|_req: Request<Body>| async move {
            Ok::<_, Infallible>(axum::response::Response::new(Body::from("reachable")))
        });

        let response = adapter()
            .layer(app)
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::AUTHORIZATION, "Basic abc123")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        let body = body_text(response).await;
        assert!(body.contains("Bearer scheme"));
    }

    #[tokio::test]
    async fn rejects_malformed_bearer_value() {
        let app = service_fn(|_req: Request<Body>| async move {
            Ok::<_, Infallible>(axum::response::Response::new(Body::from("reachable")))
        });

        let response = adapter()
            .layer(app)
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::AUTHORIZATION, "Bearer")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        let body = body_text(response).await;
        assert!(body.contains("Bearer scheme"));
    }

    #[tokio::test]
    async fn rejects_invalid_bearer_token() {
        let app = service_fn(|_req: Request<Body>| async move {
            Ok::<_, Infallible>(axum::response::Response::new(Body::from("reachable")))
        });

        let response = adapter()
            .layer(app)
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::AUTHORIZATION, "Bearer not-a-real-token")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        let body = body_text(response).await;
        assert!(body.contains("invalid bearer token"));
    }

    #[test]
    fn extract_bearer_token_parsing() {
        assert_eq!(extract_bearer_token("Bearer abc123"), Some("abc123"));
        assert_eq!(extract_bearer_token("bearer abc123"), Some("abc123"));
        assert_eq!(extract_bearer_token("BEARER abc123"), Some("abc123"));
        assert_eq!(extract_bearer_token("Bearer"), None);
        assert_eq!(extract_bearer_token("Bearer abc 123"), None);
        assert_eq!(extract_bearer_token("Basic abc123"), None);
        assert_eq!(extract_bearer_token("Bearer "), None);
        assert_eq!(extract_bearer_token(""), None);
    }
}
