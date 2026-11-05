//! Read-only viewer: it shows exactly one live lease, and refuses to guess.
//!
//! Every route is keyed by lease id. There is no "show me a browser" endpoint
//! that resolves a process by heuristics, because that is how an observer ends
//! up looking at somebody else's authenticated session.

use std::sync::Arc;

use axum::{
    extract::{Path, State},
    http::{header, HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use base64::Engine;
use serde_json::json;

use crate::{Broker, Result};

/// How to serve the viewer.
#[derive(Debug, Clone)]
pub struct ViewerConfig {
    /// Address to bind, for example `127.0.0.1:8787`.
    pub bind: String,
    /// When set, every request must carry `Authorization: Bearer <token>`.
    pub token: Option<String>,
}

impl ViewerConfig {
    /// Local-only, unauthenticated configuration.
    pub fn local(bind: impl Into<String>) -> Self {
        Self {
            bind: bind.into(),
            token: None,
        }
    }

    /// Require a bearer token, for example when binding beyond loopback.
    pub fn with_token(mut self, token: impl Into<String>) -> Self {
        self.token = Some(token.into());
        self
    }
}

struct AppState {
    broker: Arc<Broker>,
    token: Option<String>,
}

impl AppState {
    fn authorised(&self, headers: &HeaderMap) -> bool {
        let Some(expected) = &self.token else {
            return true;
        };
        let Some(presented) = headers
            .get(header::AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .and_then(|value| value.strip_prefix("Bearer "))
        else {
            return false;
        };
        // Constant-time compare keeps the token out of timing oracles.
        let expected = expected.as_bytes();
        let presented = presented.as_bytes();
        if expected.len() != presented.len() {
            return false;
        }
        expected
            .iter()
            .zip(presented)
            .fold(0u8, |acc, (a, b)| acc | (a ^ b))
            == 0
    }
}

/// Build the viewer router.
pub fn router(broker: Arc<Broker>, token: Option<String>) -> Router {
    let state = Arc::new(AppState { broker, token });
    Router::new()
        .route("/healthz", get(healthz))
        .route("/v1/leases", get(leases))
        .route("/v1/sessions", get(sessions))
        .route("/v1/view/{lease_id}", get(view))
        .route("/v1/view/{lease_id}/png", get(view_png))
        .with_state(state)
}

/// Serve the viewer until the process is stopped.
pub async fn serve(broker: Arc<Broker>, config: ViewerConfig) -> Result<()> {
    let app = router(broker, config.token.clone());
    let listener = tokio::net::TcpListener::bind(&config.bind)
        .await
        .map_err(substrate_browser_cdp::CdpError::Io)?;
    axum::serve(listener, app)
        .await
        .map_err(substrate_browser_cdp::CdpError::Io)?;
    Ok(())
}

fn unauthorised() -> Response {
    (
        StatusCode::UNAUTHORIZED,
        Json(json!({ "error": "unauthorised", "detail": "missing or invalid bearer token" })),
    )
        .into_response()
}

async fn healthz() -> Response {
    Json(json!({ "status": "ok" })).into_response()
}

async fn leases(State(state): State<Arc<AppState>>, headers: HeaderMap) -> Response {
    if !state.authorised(&headers) {
        return unauthorised();
    }
    match state.broker.leases().list() {
        Ok(list) => Json(json!({ "leases": list })).into_response(),
        Err(err) => internal(err.to_string()),
    }
}

async fn sessions(State(state): State<Arc<AppState>>, headers: HeaderMap) -> Response {
    if !state.authorised(&headers) {
        return unauthorised();
    }
    Json(json!({ "sessions": state.broker.live().await })).into_response()
}

async fn view(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(lease_id): Path<String>,
) -> Response {
    if !state.authorised(&headers) {
        return unauthorised();
    }

    let session = state
        .broker
        .live()
        .await
        .into_iter()
        .find(|session| session.lease_id == lease_id);

    let Some(session) = session else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "no live session", "lease_id": lease_id })),
        )
            .into_response();
    };

    match state.broker.screenshot(&lease_id).await {
        Ok(png) => Json(json!({
            "lease_id": session.lease_id,
            "holder": session.holder,
            "scope": session.scope,
            "generation": session.generation,
            "png_base64": base64::engine::general_purpose::STANDARD.encode(png),
        }))
        .into_response(),
        Err(err) => internal(err.to_string()),
    }
}

async fn view_png(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(lease_id): Path<String>,
) -> Response {
    if !state.authorised(&headers) {
        return unauthorised();
    }
    match state.broker.screenshot(&lease_id).await {
        Ok(png) => ([(header::CONTENT_TYPE, "image/png")], png).into_response(),
        Err(crate::BrokerError::NoSession(_)) => (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "no live session", "lease_id": lease_id })),
        )
            .into_response(),
        Err(err) => internal(err.to_string()),
    }
}

fn internal(detail: String) -> Response {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({ "error": "internal", "detail": detail })),
    )
        .into_response()
}
