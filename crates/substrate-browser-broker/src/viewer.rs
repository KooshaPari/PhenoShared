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

use crate::{Broker, BrokerError, Result};

/// How to serve the viewer.
#[derive(Debug, Clone)]
pub struct ViewerConfig {
    /// Address to bind, for example `127.0.0.1:8787`.
    pub bind: String,
    /// When set, every request must carry `Authorization: Bearer <token>`.
    ///
    /// This single token grants every session. It is kept for local use and for
    /// backwards compatibility; prefer [`ViewerConfig::principal_tokens`].
    pub token: Option<String>,
    /// Per-principal tokens. When non-empty, each token sees only its own
    /// principal's sessions and `token` is ignored.
    pub principal_tokens: std::collections::BTreeMap<String, String>,
}

impl ViewerConfig {
    /// Local-only, unauthenticated configuration.
    pub fn local(bind: impl Into<String>) -> Self {
        Self {
            bind: bind.into(),
            token: None,
            principal_tokens: std::collections::BTreeMap::new(),
        }
    }

    /// Grant `token` access to exactly `principal`'s sessions.
    ///
    /// Adding any principal token switches the viewer to per-principal mode,
    /// where a token can only see leases owned by its own principal.
    pub fn with_principal_token(
        mut self,
        principal: impl Into<String>,
        token: impl Into<String>,
    ) -> Self {
        self.principal_tokens.insert(principal.into(), token.into());
        self
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
    principal_tokens: std::collections::BTreeMap<String, String>,
}

/// What a presented credential is allowed to see.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Grant {
    /// Every session (legacy single-token mode, or no token configured).
    Everything,
    /// Only the named principal's sessions.
    Principal(String),
}

fn constant_time_eq(expected: &str, presented: &str) -> bool {
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

fn bearer(headers: &HeaderMap) -> Option<&str> {
    headers
        .get(header::AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
}

impl AppState {
    /// Resolve the credential to the set of sessions it may see.
    fn grant(&self, headers: &HeaderMap) -> Option<Grant> {
        if !self.principal_tokens.is_empty() {
            let presented = bearer(headers)?;
            for (principal, expected) in &self.principal_tokens {
                if constant_time_eq(expected, presented) {
                    return Some(Grant::Principal(principal.clone()));
                }
            }
            return None;
        }
        match &self.token {
            None => Some(Grant::Everything),
            Some(expected) => {
                let presented = bearer(headers)?;
                if constant_time_eq(expected, presented) {
                    Some(Grant::Everything)
                } else {
                    None
                }
            },
        }
    }

    /// Whether this grant may see a lease owned by `principal`.
    fn allows(&self, grant: &Grant, principal: &str) -> bool {
        match grant {
            Grant::Everything => true,
            Grant::Principal(owner) => owner == principal,
        }
    }
}

/// Build the viewer router.
pub fn router(broker: Arc<Broker>, token: Option<String>) -> Router {
    router_with(broker, token, std::collections::BTreeMap::new())
}

/// Build the viewer router with per-principal tokens.
pub fn router_with(
    broker: Arc<Broker>,
    token: Option<String>,
    principal_tokens: std::collections::BTreeMap<String, String>,
) -> Router {
    let state = Arc::new(AppState {
        broker,
        token,
        principal_tokens,
    });
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
    let app = router_with(
        broker,
        config.token.clone(),
        config.principal_tokens.clone(),
    );
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
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    match state.broker.leases().list() {
        Ok(list) => {
            let visible: Vec<_> = list
                .into_iter()
                .filter(|lease| state.allows(&grant, &lease.principal))
                .collect();
            Json(json!({ "leases": visible })).into_response()
        },
        Err(err) => internal(err.to_string()),
    }
}

fn scope_principal(scope: &str) -> &str {
    scope.split('/').next().unwrap_or(scope)
}

async fn sessions(State(state): State<Arc<AppState>>, headers: HeaderMap) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    let live = state.broker.live().await;
    let visible: Vec<_> = live
        .into_iter()
        .filter(|session| state.allows(&grant, scope_principal(&session.scope)))
        .collect();
    Json(json!({ "sessions": visible })).into_response()
}

async fn view(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(lease_id): Path<String>,
) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };

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

    if !state.allows(&grant, scope_principal(&session.scope)) {
        // 404 rather than 403: a caller should not learn that another
        // principal's lease exists.
        return (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "no live session", "lease_id": lease_id })),
        )
            .into_response();
    }

    match state.broker.screenshot(&lease_id).await {
        Ok(png) => Json(json!({
            "lease_id": session.lease_id,
            "holder": session.holder,
            "scope": session.scope,
            "generation": session.generation,
            "png_base64": base64::engine::general_purpose::STANDARD.encode(png),
        }))
        .into_response(),
        Err(
            err
            @ (BrokerError::NoSession(_) | BrokerError::Released { .. } | BrokerError::State(_)),
        ) => no_longer_live(err.to_string(), lease_id),
        Err(err) => internal(err.to_string()),
    }
}

async fn view_png(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(lease_id): Path<String>,
) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    // Resolve the owner before touching the browser: a cross-principal read must
    // not even take the frame.
    let owner = state
        .broker
        .live()
        .await
        .into_iter()
        .find(|session| session.lease_id == lease_id)
        .map(|session| scope_principal(&session.scope).to_string());
    if !matches!(&owner, Some(principal) if state.allows(&grant, principal)) {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "no live session", "lease_id": lease_id })),
        )
            .into_response();
    }
    match state.broker.screenshot(&lease_id).await {
        Ok(png) => ([(header::CONTENT_TYPE, "image/png")], png).into_response(),
        Err(
            err
            @ (BrokerError::NoSession(_) | BrokerError::Released { .. } | BrokerError::State(_)),
        ) => no_longer_live(err.to_string(), lease_id),
        Err(err) => internal(err.to_string()),
    }
}

/// A lease that no longer validates is indistinguishable from one that never
/// existed: never disclose a superseded holder's browser.
fn no_longer_live(detail: String, lease_id: String) -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(json!({ "error": "no live session", "lease_id": lease_id, "detail": detail })),
    )
        .into_response()
}

fn internal(detail: String) -> Response {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({ "error": "internal", "detail": detail })),
    )
        .into_response()
}
