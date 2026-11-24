//! Viewer and authority: the daemon shows its leases, and is the only thing
//! that mutates them.
//!
//! Reads are keyed by lease id. There is no "show me a browser" endpoint that
//! resolves a process by heuristics, because that is how an observer ends up
//! looking at somebody else's authenticated session.
//!
//! # Mutations
//!
//! `POST /v1/leases`, `POST /v1/leases/{id}/release`, `POST /v1/leases/reap` and
//! `POST /v1/profiles/purge` let a remote client act *through* the daemon instead
//! of opening a second authority over the same state root. They are the same
//! [`Broker`] calls the in-process tools make, behind the same credential:
//!
//! * every route resolves the bearer token first and answers `401` before it
//!   reads a body or touches state,
//! * a lease owned by another principal is reported as `404`, never `403`, so a
//!   caller cannot learn that it exists,
//! * release validates the fencing token **before** mutating anything, the same
//!   fail-closed ordering [`Broker::release`] uses, and
//! * purge requires `confirm: true` and refuses while the profile is live or
//!   leased.

use std::{sync::Arc, time::Duration};

use axum::{
    body::Bytes,
    extract::{Path, State},
    http::{header, HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use base64::Engine;
use serde_json::json;

use substrate_browser::{BrowserError, Scope};

use crate::{Acquired, Broker, BrokerError, Result};

/// Lease lifetime applied when `POST /v1/leases` is sent without `ttl_ms`.
///
/// Chosen to match `substrate-browser-mcp`'s `DEFAULT_TTL_MS`, so a raw HTTP
/// caller and an MCP client get the same lifetime. The client sends its value
/// explicitly; this default is for everyone else.
pub const DEFAULT_TTL_MS: u64 = 60_000;

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
        .route("/v1/leases", get(leases).post(acquire))
        .route("/v1/leases/reap", post(reap))
        .route("/v1/leases/{lease_id}/release", post(release))
        .route("/v1/profiles/purge", post(purge))
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

/// Body of `POST /v1/leases`.
#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct AcquireBody {
    principal: String,
    profile: String,
    #[serde(default)]
    session: Option<String>,
    #[serde(default)]
    holder: Option<String>,
    #[serde(default)]
    ttl_ms: Option<u64>,
}

/// Body of `POST /v1/leases/{id}/release`.
#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct ReleaseBody {
    fencing_token: u64,
}

/// Body of `POST /v1/profiles/purge`.
#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct PurgeBody {
    principal: String,
    profile: String,
    /// Defaulted to `false`, so an omitted flag fails closed at the guard.
    #[serde(default)]
    confirm: bool,
}

/// Acquire an exclusive browser and let the daemon keep it.
///
/// The daemon is the holder: the browser stays registered under its lease in
/// this process after the response is written, so the caller drives it through
/// `POST`/`GET` on this same authority rather than owning it locally.
async fn acquire(State(state): State<Arc<AppState>>, headers: HeaderMap, body: Bytes) -> Response {
    // Credential first: never parse a body, never touch state, before this.
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    let body = match serde_json::from_slice::<AcquireBody>(&body) {
        Ok(body) => body,
        Err(err) => {
            return bad_request(format!(
                "body must be {{principal, profile, session?, holder?, ttl_ms?}}: {err}"
            ));
        },
    };
    if !state.allows(&grant, &body.principal) {
        // Same reasoning as the read side: 404 rather than 403, because
        // "you may not touch this principal's profile" would confirm that the
        // profile exists under another tenant.
        return no_such_profile(&body.principal, &body.profile);
    }

    let ttl_ms = body.ttl_ms.unwrap_or(DEFAULT_TTL_MS);
    if ttl_ms == 0 {
        return bad_request("ttl_ms must be greater than zero".to_string());
    }
    let session = body.session.unwrap_or_else(|| "default".to_string());
    let holder = body
        .holder
        .unwrap_or_else(|| format!("brokerd:{}", body.principal));
    let scope = match Scope::new(&body.principal, &body.profile, &session) {
        Ok(scope) => scope,
        Err(err) => return bad_request(err.to_string()),
    };

    match state
        .broker
        .acquire(&scope, holder, Duration::from_millis(ttl_ms))
        .await
    {
        // The handle is dropped here on purpose: the broker's session map holds
        // its own clone, so the daemon keeps the browser alive under this lease
        // and a caller cannot orphan it by disconnecting.
        Ok(acquired) => Json(json!({
            "id": acquired.lease.id,
            "fencing_token": acquired.lease.fencing_token,
            "expires_at_unix_ms": acquired.lease.expires_at_unix_ms,
            "generation": acquired.generation,
            "data_dir": acquired.data_dir.display().to_string(),
        }))
        .into_response(),
        Err(err) => broker_error(err),
    }
}

/// Release a lease, tearing the browser down.
async fn release(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Path(lease_id): Path<String>,
    body: Bytes,
) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    let body = match serde_json::from_slice::<ReleaseBody>(&body) {
        Ok(body) => body,
        Err(err) => return bad_request(format!("body must be {{fencing_token}}: {err}")),
    };

    // Fail-closed ordering: prove the fence before anything is mutated. A stale,
    // wrong, expired or unknown token returns here, having torn down nothing.
    let lease = match state
        .broker
        .leases()
        .validate(&lease_id, body.fencing_token)
    {
        Ok(lease) => lease,
        Err(err) => return broker_error(err.into()),
    };
    if !state.allows(&grant, &lease.principal) {
        return no_such_lease(&lease_id);
    }

    let live = state
        .broker
        .live()
        .await
        .into_iter()
        .find(|session| session.lease_id == lease_id);

    let teardown = match live {
        Some(session) => {
            let data_dir = state.broker.profiles().data_dir(
                &lease.principal,
                &lease.profile,
                session.generation,
            );
            let browser = match state.broker.browser(&lease_id).await {
                Ok(browser) => browser,
                Err(err) => return broker_error(err),
            };
            let acquired = Acquired {
                lease,
                generation: session.generation,
                data_dir,
                browser,
            };
            // Closes the browser, revokes the lease, then seals the generation.
            if let Err(err) = state.broker.release(acquired).await {
                return broker_error(err);
            }
            "browser closed; lease revoked; generation sealed"
        },
        None => {
            // No session in this daemon (it restarted, or the browser was
            // reaped). Revoking the record is the whole action, and it is still
            // gated on the fence that was just validated.
            match state.broker.leases().revoke(&lease_id) {
                Ok(()) | Err(BrowserError::UnknownLease(_)) => {},
                Err(err) => return broker_error(err.into()),
            }
            "no live session in this daemon; lease record revoked"
        },
    };

    Json(json!({ "released": true, "lease_id": lease_id, "teardown": teardown })).into_response()
}

/// Reap expired sessions and expired lease records.
///
/// Global maintenance, so a principal-scoped token is refused: reaping would
/// otherwise sweep other principals' records.
async fn reap(State(state): State<Arc<AppState>>, headers: HeaderMap) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    if let Grant::Principal(principal) = &grant {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "error": "refused",
                "detail": format!(
                    "reap is global maintenance; the token scoped to `{principal}` may not reap \
                     another principal's leases"
                ),
            })),
        )
            .into_response();
    }

    let reaped = state.broker.reap_expired().await;
    let leases_reaped = match state.broker.leases().sweep_expired() {
        Ok(count) => count,
        Err(err) => return broker_error(err.into()),
    };
    let live_sessions_after = state.broker.live().await.len();
    Json(json!({
        "reaped": reaped,
        "leases_reaped": leases_reaped,
        "live_sessions_after": live_sessions_after,
    }))
    .into_response()
}

/// Delete every generation of a profile. Destructive and fail-closed.
async fn purge(State(state): State<Arc<AppState>>, headers: HeaderMap, body: Bytes) -> Response {
    let Some(grant) = state.grant(&headers) else {
        return unauthorised();
    };
    let body = match serde_json::from_slice::<PurgeBody>(&body) {
        Ok(body) => body,
        Err(err) => {
            return bad_request(format!(
                "body must be {{principal, profile, confirm}}: {err}"
            ));
        },
    };
    if !state.allows(&grant, &body.principal) {
        return no_such_profile(&body.principal, &body.profile);
    }
    if !body.confirm {
        return bad_request(
            "purge is destructive: pass confirm: true to delete profile data".to_string(),
        );
    }
    let scope = match Scope::new(&body.principal, &body.profile, "default") {
        Ok(scope) => scope,
        Err(err) => return bad_request(err.to_string()),
    };
    let key = scope.profile_key();

    // A live session's scope string is `principal/profile/session`, so match the
    // profile key as a prefix: comparing for equality would miss every session.
    let live = state
        .broker
        .live()
        .await
        .into_iter()
        .any(|session| session.scope == key || session.scope.starts_with(&format!("{key}/")));
    if live {
        return conflict(
            "refused",
            format!("profile {key} has a live session; release it before purging"),
        );
    }
    match state
        .broker
        .leases()
        .active_for(&body.principal, &body.profile)
    {
        Ok(Some(lease)) => {
            return conflict(
                "refused",
                format!(
                    "profile {key} is leased by `{}` until {}; release it before purging",
                    lease.holder, lease.expires_at_unix_ms
                ),
            );
        },
        Ok(None) => {},
        Err(err) => return broker_error(err.into()),
    }

    let path = state
        .broker
        .profiles()
        .profile_dir(&body.principal, &body.profile);
    let rendered = path.display().to_string();
    if !path.exists() {
        return Json(json!({ "purged": false, "path": rendered, "existed": false }))
            .into_response();
    }
    if let Err(err) = std::fs::remove_dir_all(&path) {
        return internal(err.to_string());
    }
    Json(json!({ "purged": true, "path": rendered, "existed": true })).into_response()
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

fn bad_request(detail: String) -> Response {
    (
        StatusCode::BAD_REQUEST,
        Json(json!({ "error": "invalid", "detail": detail })),
    )
        .into_response()
}

fn conflict(error: &str, detail: String) -> Response {
    (
        StatusCode::CONFLICT,
        Json(json!({ "error": error, "detail": detail })),
    )
        .into_response()
}

/// A lease this caller may not act on.
///
/// Deliberately indistinguishable from a lease that does not exist: a holder
/// must not learn that another principal's lease is there.
fn no_such_lease(lease_id: &str) -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(json!({
            "error": "unknown_lease",
            "detail": format!("no lease {lease_id} under this credential"),
            "lease_id": lease_id,
        })),
    )
        .into_response()
}

fn no_such_profile(principal: &str, profile: &str) -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(json!({
            "error": "unknown_profile",
            "detail": format!("no profile {principal}/{profile} under this credential"),
        })),
    )
        .into_response()
}

/// Map a broker failure onto a status a remote caller can act on.
///
/// `409` is the "refused, nothing was mutated" answer for fence and lease
/// problems: the request was well formed and the caller was authorised, but the
/// authority declined. `500` is reserved for real storage failures.
fn broker_error(err: BrokerError) -> Response {
    let detail = err.to_string();
    match &err {
        BrokerError::State(BrowserError::Scope(_)) => bad_request(detail),
        BrokerError::State(BrowserError::UnknownLease(_))
        | BrokerError::NoSession(_)
        | BrokerError::Released { .. } => (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "unknown_lease", "detail": detail })),
        )
            .into_response(),
        BrokerError::State(BrowserError::StaleFence { .. }) => conflict("stale_fence", detail),
        BrokerError::State(BrowserError::LeaseUnusable { .. }) => {
            conflict("lease_unusable", detail)
        },
        BrokerError::State(BrowserError::Refused(_))
        | BrokerError::ProfileBusy { .. }
        | BrokerError::NotHolder { .. } => conflict("refused", detail),
        BrokerError::Busy { .. } => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({ "error": "busy", "detail": detail })),
        )
            .into_response(),
        BrokerError::State(_) | BrokerError::Browser(_) => internal(detail),
    }
}
