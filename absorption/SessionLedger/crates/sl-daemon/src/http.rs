//! HTTP bridge for the sl-daemon OKF pipeline.
//!
//! Exposes three endpoints:
//!
//! * `GET /healthz` — liveness probe; returns `200 ok`.
//! * `GET /readyz` — readiness probe; returns `200` when `out_dir` is usable.
//! * `GET /api/bundles` — reads all `*.okf.json` files currently in the output
//!   directory and returns them as a JSON array. Each element is the parsed
//!   document as a [`serde_json::Value`] so the response is decoupled from any
//!   viewer-side type definitions.
//! * `GET /api/stream` — SSE endpoint (`text/event-stream`) that emits a
//!   `data: <path>\n\n` event whenever a new `*.okf.json` is written. Driven by
//!   a [`tokio::sync::broadcast`] channel whose sender is populated by the ETL
//!   consumer after each successful write.
//!
//! CORS is enabled with a permissive policy so WASM-based viewers (e.g. Dioxus)
//! running on a different origin can call these endpoints.

use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::convert::Infallible;
use std::hash::{Hash, Hasher};
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use axum::body::to_bytes;
use axum::extract::Request;
use axum::extract::{Path as AxumPath, Query, State};
use axum::http::{header::AUTHORIZATION, header::CONTENT_TYPE, HeaderMap, HeaderValue};
use axum::middleware::{self, Next};
use axum::response::sse::{Event, KeepAlive, Sse};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use futures_core::Stream;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::sync::{broadcast, Semaphore};

use crate::audit::{self, AuditSink};
use crate::export::BundleMeta;
use crate::filter::{apply_filters, FilterSpec};
use crate::metrics::{compute_metrics, normalize_http_route, HttpMetrics};
use crate::resilience::ApiCircuitBreaker;
use crate::resolver::{ResolveRequest, ResolveResponse, Resolver};
use crate::validation::{validate_okf_bundle, PostBundle, ValidationResult};
#[cfg(feature = "otel")]
use opentelemetry::trace::{
    SpanContext, SpanId, TraceContextExt as _, TraceFlags, TraceId, TraceState,
};
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt as _;
use tower_http::cors::{Any, CorsLayer};
use tracing::{error, info, warn, Instrument as _};
#[cfg(feature = "otel")]
use tracing_opentelemetry::OpenTelemetrySpanExt as _;

const DEFAULT_INGEST_MAX_BODY_BYTES: usize = 1_048_576;
const DEFAULT_INGEST_MAX_CONCURRENCY: usize = 8;
/// Largest explicit full-document page served by `/api/bundles`.
///
/// The unparameterized route remains backward compatible for existing local
/// clients. New interactive consumers should request an explicit bound.
const MAX_BUNDLE_LIST_LIMIT: usize = 500;
/// Default `/api/*` throttle when the shared-key / non-loopback path is active.
const DEFAULT_API_RATE_LIMIT: u64 = 60;
/// Default throttle window (tower-style: N requests per period).
const DEFAULT_API_RATE_WINDOW: Duration = Duration::from_secs(1);
const SL_API_RATE_LIMIT: &str = "SL_API_RATE_LIMIT";
const SL_API_RATE_WINDOW_MS: &str = "SL_API_RATE_WINDOW_MS";
/// HTTP methods and paths documented in `docs/api/openapi.yaml`.
///
/// Debug-only pprof routes are intentionally omitted. Keep in sync with the
/// stable routes registered in [`router_with_pprof`] and validated by
/// `scripts/openapi-drift-check.ps1`.
#[allow(dead_code)]
const OPENAPI_ROUTE_SURFACE: &[(&str, &str)] = &[
    ("GET", "/healthz"),
    ("GET", "/readyz"),
    ("GET", "/api/bundles"),
    ("GET", "/api/search"),
    ("GET", "/api/stream"),
    ("GET", "/api/replay/{bundle_id}"),
    ("POST", "/api/ingest"),
    ("POST", "/api/native-sessions/resolve"),
    ("GET", "/api/metrics"),
    ("GET", "/metrics"),
];
const SL_API_KEY: &str = "SL_API_KEY";
const SL_ENABLE_PPROF: &str = "SL_ENABLE_PPROF";
const X_API_KEY: &str = "x-api-key";
const IDEMPOTENCY_KEY: &str = "idempotency-key";

/// Shared-secret authentication for HTTP API routes.
///
/// On loopback, a configured key gates mutating routes only (`POST /api/ingest`).
/// On non-loopback binds, startup requires a key and [`Self::protect_all_api`]
/// gates every `/api/*` route.
#[derive(Clone, Debug, Default)]
pub(crate) struct ApiKeyAuth {
    expected: Option<Arc<str>>,
    /// When true, all `/api/*` routes require a matching key (non-loopback bind).
    protect_all_api: bool,
}

impl ApiKeyAuth {
    pub(crate) fn from_env() -> Self {
        Self::from_value(std::env::var(SL_API_KEY).ok())
    }

    pub(crate) fn from_value(value: Option<String>) -> Self {
        let expected = value
            .map(|value| value.trim().to_owned())
            .filter(|value| !value.is_empty())
            .map(Arc::<str>::from);
        Self { expected, protect_all_api: false }
    }

    pub(crate) fn is_configured(&self) -> bool {
        self.expected.is_some()
    }

    pub(crate) fn with_protect_all_api(mut self, protect: bool) -> Self {
        self.protect_all_api = protect;
        self
    }

    pub(crate) fn protects_all_api(&self) -> bool {
        self.protect_all_api
    }

    fn allows(&self, headers: &HeaderMap) -> bool {
        let Some(expected) = self.expected.as_deref() else {
            return true;
        };
        bearer_token_matches(headers, expected) || x_api_key_matches(headers, expected)
    }
}

/// Process-local admission controls for `POST /api/ingest`.
#[derive(Clone)]
pub(crate) struct IngestAdmission {
    max_body_bytes: usize,
    semaphore: Arc<Semaphore>,
}

impl IngestAdmission {
    pub(crate) fn from_env() -> Result<Self, String> {
        Self::from_values(
            std::env::var("SL_INGEST_MAX_BODY_BYTES").ok(),
            std::env::var("SL_INGEST_MAX_CONCURRENCY").ok(),
        )
    }

    fn from_values(
        max_body_bytes: Option<String>,
        max_concurrency: Option<String>,
    ) -> Result<Self, String> {
        let max_body_bytes = parse_positive_limit(
            "SL_INGEST_MAX_BODY_BYTES",
            max_body_bytes.as_deref(),
            DEFAULT_INGEST_MAX_BODY_BYTES,
        )?;
        let max_concurrency = parse_positive_limit(
            "SL_INGEST_MAX_CONCURRENCY",
            max_concurrency.as_deref(),
            DEFAULT_INGEST_MAX_CONCURRENCY,
        )?;
        Ok(Self { max_body_bytes, semaphore: Arc::new(Semaphore::new(max_concurrency)) })
    }
}

/// Process-wide tower-style rate throttle for `/api/*` (beyond ingest bulkhead).
///
/// Native `tower::limit::RateLimitLayer` is not used: axum clones layers per
/// connection, so those counters would not share process-wide state. This type
/// keeps an `Arc`-shared fixed window so every connection sees the same budget.
#[derive(Clone)]
pub(crate) struct ApiRateLimit {
    /// `None` disables the throttle (loopback DX default when no shared key).
    inner: Option<Arc<Mutex<RateWindow>>>,
    pub(crate) limit: u64,
    pub(crate) window: Duration,
}

#[derive(Debug)]
struct RateWindow {
    window_start: Instant,
    count: u64,
}

impl ApiRateLimit {
    /// Build from env.
    ///
    /// When `enforce_default` is true (non-loopback bind or `SL_API_KEY` set),
    /// an unset `SL_API_RATE_LIMIT` enables the default tower-style budget.
    /// Loopback without a shared key leaves the throttle off unless the env is
    /// set explicitly. `SL_API_RATE_LIMIT=0` (or `off`) disables it.
    pub(crate) fn from_env(enforce_default: bool) -> Result<Self, String> {
        Self::from_values(
            enforce_default,
            std::env::var(SL_API_RATE_LIMIT).ok(),
            std::env::var(SL_API_RATE_WINDOW_MS).ok(),
        )
    }

    fn from_values(
        enforce_default: bool,
        rate_limit: Option<String>,
        window_ms: Option<String>,
    ) -> Result<Self, String> {
        let window = match window_ms.as_deref() {
            None => DEFAULT_API_RATE_WINDOW,
            Some(raw) => {
                let ms = parse_positive_limit(SL_API_RATE_WINDOW_MS, Some(raw), 0)?;
                Duration::from_millis(ms as u64)
            }
        };

        let limit = match rate_limit.as_deref().map(str::trim) {
            None if enforce_default => DEFAULT_API_RATE_LIMIT,
            None => return Ok(Self::disabled()),
            Some("0") | Some("off") | Some("Off") | Some("OFF") => return Ok(Self::disabled()),
            Some(raw) => parse_positive_u64(SL_API_RATE_LIMIT, raw)?,
        };

        Ok(Self::enabled(limit, window))
    }

    fn disabled() -> Self {
        Self { inner: None, limit: 0, window: DEFAULT_API_RATE_WINDOW }
    }

    fn enabled(limit: u64, window: Duration) -> Self {
        Self {
            inner: Some(Arc::new(Mutex::new(RateWindow {
                window_start: Instant::now(),
                count: 0,
            }))),
            limit,
            window,
        }
    }

    pub(crate) fn is_enabled(&self) -> bool {
        self.inner.is_some()
    }

    fn try_acquire(&self) -> bool {
        let Some(inner) = &self.inner else {
            return true;
        };
        let mut state = inner.lock().expect("api rate limit poisoned");
        let now = Instant::now();
        if now.duration_since(state.window_start) >= self.window {
            state.window_start = now;
            state.count = 0;
        }
        if state.count >= self.limit {
            return false;
        }
        state.count += 1;
        true
    }
}

fn parse_positive_u64(name: &str, value: &str) -> Result<u64, String> {
    let parsed = value
        .parse::<u64>()
        .map_err(|_| format!("{name} must be a positive integer, got {value:?}"))?;
    if parsed == 0 {
        return Err(format!("{name} must be greater than zero (use 0/off only as the full value)"));
    }
    Ok(parsed)
}

/// Process-local replay cache for successful `POST /api/ingest` idempotency keys.
///
/// The map is bounded: unique `Idempotency-Key` values arriving at a long-running
/// daemon used to accumulate without eviction. When the cap is hit the cache is
/// reset (idempotency replay is an optimization, not a durability contract —
/// stale keys are re-validated against the body hash on the next request).
#[derive(Clone, Default)]
pub(crate) struct IngestIdempotencyCache {
    entries: Arc<Mutex<HashMap<String, IdempotentIngest>>>,
}

/// Maximum distinct `Idempotency-Key` values retained process-wide.
const IDEMPOTENCY_CACHE_MAX_ENTRIES: usize = 4096;

#[derive(Clone)]
struct IdempotentIngest {
    body_hash: u64,
    response: ValidationResult,
}

impl IngestIdempotencyCache {
    fn get(&self, key: &str) -> Option<IdempotentIngest> {
        self.entries.lock().expect("idempotency cache poisoned").get(key).cloned()
    }

    fn record_success(
        &self,
        key: String,
        body_hash: u64,
        response: ValidationResult,
    ) -> Result<ValidationResult, ()> {
        let mut entries = self.entries.lock().expect("idempotency cache poisoned");
        if let Some(previous) = entries.get(&key) {
            return if previous.body_hash == body_hash {
                Ok(previous.response.clone())
            } else {
                Err(())
            };
        }
        if entries.len() >= IDEMPOTENCY_CACHE_MAX_ENTRIES {
            // Bound memory instead of growing without limit.
            entries.clear();
        }
        entries.insert(key, IdempotentIngest { body_hash, response: response.clone() });
        Ok(response)
    }
}

fn parse_positive_limit(name: &str, value: Option<&str>, default: usize) -> Result<usize, String> {
    let Some(value) = value else {
        return Ok(default);
    };
    let parsed = value
        .parse::<usize>()
        .map_err(|_| format!("{name} must be a positive integer, got {value:?}"))?;
    if parsed == 0 {
        return Err(format!("{name} must be greater than zero"));
    }
    Ok(parsed)
}

/// Shared state threaded into every handler.
#[derive(Clone)]
pub(crate) struct AppState {
    pub resolver: Resolver,
    /// Directory that the ETL consumer writes `*.okf.json` files into.
    pub out_dir: Arc<PathBuf>,
    /// Broadcast receiver factory: each SSE connection subscribes to a fresh
    /// receiver. The sender lives in the ETL consumer task.
    pub broadcast_tx: broadcast::Sender<PathBuf>,
    /// Process-local RED counters for the Prometheus scrape endpoint.
    pub http_metrics: Arc<HttpMetrics>,
    /// Body-size and in-flight request limits for ingest.
    pub ingest_admission: IngestAdmission,
    /// Process-wide `/api/*` rate throttle (tower-style; shared across connections).
    pub api_rate_limit: ApiRateLimit,
    /// Process-wide `/api/*` circuit breaker (trips on consecutive 5xx).
    pub api_circuit_breaker: ApiCircuitBreaker,
    /// Optional shared-secret authentication for HTTP API routes.
    pub api_key_auth: ApiKeyAuth,
    /// Durable local audit sink for structured actor/action events.
    pub audit_sink: Arc<AuditSink>,
    /// Successful ingest responses keyed by process-local Idempotency-Key values.
    pub idempotency_cache: IngestIdempotencyCache,
    /// Optional durable memory store probed by `/readyz` when configured.
    #[cfg(feature = "sqlite")]
    pub memory_store: Option<Arc<session_ledger::SqliteMemoryStore>>,
}

/// Build the axum [`Router`].
pub(crate) fn router(state: AppState) -> Router {
    router_with_pprof(state, pprof_enabled_from_env())
}

fn router_with_pprof(state: AppState, pprof_enabled: bool) -> Router {
    let cors = CorsLayer::new().allow_origin(Any).allow_methods(Any).allow_headers(Any);
    let http_metrics = state.http_metrics.clone();
    let api_auth_state = state.clone();
    let api_rate_state = state.clone();
    let api_circuit_state = state.clone();

    // Ingest admission (body size + semaphore bulkhead) stays in the handler.
    // General `/api/*` throttle uses [`ApiRateLimit`] (Arc-shared fixed window),
    // not tower `RateLimitLayer`, so the budget is process-wide across connections.
    // Circuit breaker is likewise Arc-shared and trips on consecutive 5xx.
    let router = Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/api/bundles", get(list_bundles))
        .route("/api/search", get(search_bundles))
        .route("/api/stream", get(sse_stream))
        .route("/api/replay/{bundle_id}", get(replay_bundle))
        .route("/api/ingest", post(ingest_bundle))
        .route("/api/native-sessions/resolve", post(resolve_native_session))
        .route("/api/metrics", get(metrics_handler))
        .route("/metrics", get(prometheus_metrics));

    let router = if pprof_enabled {
        router
            .route("/debug/pprof/cmdline", get(pprof_cmdline))
            .route("/debug/pprof/profile", get(pprof_profile))
    } else {
        router
    };

    router
        .fallback(not_found)
        .with_state(state)
        .layer(middleware::from_fn_with_state(api_auth_state, enforce_api_key_policy))
        .layer(middleware::from_fn_with_state(api_rate_state, enforce_api_rate_limit))
        .layer(middleware::from_fn_with_state(api_circuit_state, enforce_api_circuit_breaker))
        .layer(middleware::from_fn_with_state(http_metrics, observe_request))
        .layer(cors)
}

async fn resolve_native_session(
    State(state): State<AppState>,
    Json(request): Json<ResolveRequest>,
) -> Json<ResolveResponse> {
    Json(state.resolver.resolve(&request.evidence))
}

/// When non-loopback protection is enabled, require a valid API key on `/api/*`.
async fn enforce_api_key_policy(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Response {
    if state.api_key_auth.protects_all_api()
        && request.uri().path().starts_with("/api/")
        && !state.api_key_auth.allows(request.headers())
    {
        let request_id = request_id_from_headers(request.headers());
        return api_error(
            axum::http::StatusCode::UNAUTHORIZED,
            "unauthorized",
            "missing or invalid API key",
            &request_id,
        );
    }
    next.run(request).await
}

/// Tower-style process-wide throttle for `/api/*` (probes and `/metrics` stay open).
async fn enforce_api_rate_limit(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Response {
    if request.uri().path().starts_with("/api/") && !state.api_rate_limit.try_acquire() {
        let request_id = request_id_from_headers(request.headers());
        return api_error(
            axum::http::StatusCode::TOO_MANY_REQUESTS,
            "rate_limited",
            format!(
                "API rate limit exceeded ({} requests per {}ms)",
                state.api_rate_limit.limit,
                state.api_rate_limit.window.as_millis()
            ),
            &request_id,
        );
    }
    next.run(request).await
}

/// Process-wide circuit breaker for `/api/*` (probes and `/metrics` stay open).
///
/// Trips after consecutive handler 5xx responses; while open, returns `503`
/// with `Retry-After` and `error.code="circuit_open"`. Half-open allows a single
/// probe after the cooldown. Client 4xx responses do not trip the breaker.
async fn enforce_api_circuit_breaker(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Response {
    let is_api = request.uri().path().starts_with("/api/");
    if is_api {
        if let Some(retry_after) = state.api_circuit_breaker.deny_if_open() {
            let request_id = request_id_from_headers(request.headers());
            let secs = retry_after.as_secs().max(1);
            let mut response = api_error(
                axum::http::StatusCode::SERVICE_UNAVAILABLE,
                "circuit_open",
                format!(
                    "API circuit breaker open after {} consecutive 5xx; retry after {}s",
                    state.api_circuit_breaker.failure_threshold, secs
                ),
                &request_id,
            );
            if let Ok(value) = HeaderValue::from_str(&secs.to_string()) {
                response.headers_mut().insert(axum::http::header::RETRY_AFTER, value);
            }
            return response;
        }
    }

    let response = next.run(request).await;
    if is_api {
        let status = response.status();
        if status.is_server_error() {
            state.api_circuit_breaker.record_failure();
        } else if status.is_success() || status.is_client_error() {
            // Treat 2xx/4xx as healthy from the server's perspective.
            state.api_circuit_breaker.record_success();
        }
    }
    response
}

fn pprof_enabled_from_env() -> bool {
    std::env::var(SL_ENABLE_PPROF).is_ok_and(|value| value.trim() == "1")
}

/// Run the axum HTTP server on `addr` until `shutdown` resolves.
///
/// Returns immediately if binding fails (caller logs the error).
#[tracing::instrument(skip(state, shutdown), fields(addr = %addr))]
pub async fn serve(
    addr: SocketAddr,
    state: AppState,
    shutdown: impl std::future::Future<Output = ()> + Send + 'static,
) -> std::io::Result<()> {
    let listener = bind(addr).await?;
    serve_listener(listener, state, shutdown).await
}

/// Bind the daemon listener before spawning the serving task.
///
/// Keeping binding separate lets the CLI fail fast on an occupied/unusable
/// port instead of logging a misleading "listening" message while the
/// background HTTP task has already exited.
pub async fn bind(addr: SocketAddr) -> std::io::Result<tokio::net::TcpListener> {
    tokio::net::TcpListener::bind(addr).await
}

/// Serve an already-bound listener until shutdown resolves.
pub async fn serve_listener(
    listener: tokio::net::TcpListener,
    state: AppState,
    shutdown: impl std::future::Future<Output = ()> + Send + 'static,
) -> std::io::Result<()> {
    let app = router(state);
    if let Ok(addr) = listener.local_addr() {
        info!(%addr, "HTTP server bound");
    } else {
        info!("HTTP server bound");
    }
    axum::serve(listener, app).with_graceful_shutdown(shutdown).await.map_err(std::io::Error::other)
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// `GET /healthz` — liveness probe.
#[tracing::instrument]
async fn healthz() -> Response {
    "ok".into_response()
}

/// `GET /readyz` — readiness probe (output directory and optional memory DB).
#[tracing::instrument(skip(state), fields(out_dir = %state.out_dir.display()))]
async fn readyz(headers: HeaderMap, State(state): State<AppState>) -> Response {
    let path = state.out_dir.as_path();
    if !path.is_dir() {
        warn!(out_dir = %path.display(), "readyz: out_dir not ready");
        return api_error(
            axum::http::StatusCode::SERVICE_UNAVAILABLE,
            "not_ready",
            format!("out_dir not ready: {}", path.display()),
            request_id_from_headers(&headers),
        );
    }

    #[cfg(feature = "sqlite")]
    if let Some(store) = &state.memory_store {
        if let Err(error) = store.ping() {
            warn!(error = %error, "readyz: memory_db not ready");
            return api_error(
                axum::http::StatusCode::SERVICE_UNAVAILABLE,
                "memory_db_not_ready",
                format!("memory_db not ready: {error}"),
                request_id_from_headers(&headers),
            );
        }
    }

    "ready".into_response()
}

/// Query parameters accepted by `GET /api/bundles`.
#[derive(Debug, Default, Deserialize)]
struct BundleListParams {
    /// Optional cap for full OKF documents. Explicit requests are capped to
    /// prevent an interactive viewer from accidentally loading an entire corpus.
    limit: Option<usize>,
}

/// `GET /api/bundles` — return all or a bounded page of `*.okf.json` documents.
#[tracing::instrument(skip(state), fields(out_dir = %state.out_dir.display()))]
async fn list_bundles(
    headers: HeaderMap,
    State(state): State<AppState>,
    Query(params): Query<BundleListParams>,
) -> Response {
    let limit = params.limit.map(|limit| limit.min(MAX_BUNDLE_LIST_LIMIT));
    match read_all_bundles(&state.out_dir, limit) {
        Ok(values) => {
            info!(count = values.len(), ?limit, "list_bundles");
            Json(values).into_response()
        }
        Err(e) => {
            error!(error = %e, "failed to read bundles");
            api_error(
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                "bundle_read_failed",
                format!("failed to read bundles: {e}"),
                request_id_from_headers(&headers),
            )
        }
    }
}

/// `GET /api/metrics` — aggregate token/model stats over the output directory.
#[tracing::instrument(skip(state), fields(out_dir = %state.out_dir.display()))]
async fn metrics_handler(State(state): State<AppState>) -> impl IntoResponse {
    Json(compute_metrics(&state.out_dir))
}

/// `GET /metrics` — process-local HTTP RED metrics in Prometheus text format.
async fn prometheus_metrics(State(state): State<AppState>) -> Response {
    (
        [(CONTENT_TYPE, HeaderValue::from_static("text/plain; version=0.0.4; charset=utf-8"))],
        state.http_metrics.render_prometheus(),
    )
        .into_response()
}

/// `GET /debug/pprof/cmdline` — null-delimited process argv for pprof clients.
async fn pprof_cmdline() -> Response {
    let mut body = Vec::new();
    for arg in std::env::args_os() {
        if !body.is_empty() {
            body.push(0);
        }
        body.extend(arg.to_string_lossy().as_bytes());
    }

    ([(CONTENT_TYPE, HeaderValue::from_static("application/octet-stream"))], body).into_response()
}

/// Default CPU sample window when `?seconds=` is omitted (kept short for local smoke).
const DEFAULT_PPROF_SECONDS: u64 = 1;
/// Hard cap so a single request cannot block the process for minutes.
const MAX_PPROF_SECONDS: u64 = 30;

#[derive(Debug, Deserialize)]
struct PprofProfileParams {
    #[serde(default = "default_pprof_seconds")]
    seconds: u64,
}

fn default_pprof_seconds() -> u64 {
    DEFAULT_PPROF_SECONDS
}

/// `GET /debug/pprof/profile` — CPU profile protobuf (unix) when `SL_ENABLE_PPROF=1`.
///
/// Optional `?seconds=N` (clamped to 1..=30, default 1). Loopback bind remains the
/// process-level gate; this handler only runs when the env gate registered the route.
async fn pprof_profile(Query(params): Query<PprofProfileParams>) -> Response {
    let seconds = params.seconds.clamp(1, MAX_PPROF_SECONDS);

    #[cfg(unix)]
    {
        match sample_cpu_profile(seconds).await {
            Ok(body) => {
                ([(CONTENT_TYPE, HeaderValue::from_static("application/octet-stream"))], body)
                    .into_response()
            }
            Err(PprofSampleError::Busy) => (
                axum::http::StatusCode::SERVICE_UNAVAILABLE,
                [(CONTENT_TYPE, HeaderValue::from_static("text/plain; charset=utf-8"))],
                "CPU profiler is already running; retry after the in-flight sample completes.",
            )
                .into_response(),
            Err(PprofSampleError::Failed(message)) => {
                warn!(%message, seconds, "cpu pprof sample failed");
                (
                    axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                    [(CONTENT_TYPE, HeaderValue::from_static("text/plain; charset=utf-8"))],
                    format!("CPU profiling failed: {message}"),
                )
                    .into_response()
            }
        }
    }

    #[cfg(not(unix))]
    {
        let _ = seconds;
        (
            axum::http::StatusCode::NOT_IMPLEMENTED,
            [(CONTENT_TYPE, HeaderValue::from_static("text/plain; charset=utf-8"))],
            "CPU profiling via pprof is not supported on this platform (unix SIGPROF sampler). \
             Enable SL_ENABLE_PPROF=1 on Linux/macOS for protobuf profiles.",
        )
            .into_response()
    }
}

#[cfg(unix)]
enum PprofSampleError {
    Busy,
    Failed(String),
}

/// Serialize CPU samples for one window. The `pprof` crate owns a process-global
/// profiler, so concurrent requests are rejected with [`PprofSampleError::Busy`].
#[cfg(unix)]
async fn sample_cpu_profile(seconds: u64) -> Result<Vec<u8>, PprofSampleError> {
    tokio::task::spawn_blocking(move || {
        use std::sync::TryLockError;

        use pprof::protos::Message;

        static PPROF_LOCK: Mutex<()> = Mutex::new(());

        let _guard = match PPROF_LOCK.try_lock() {
            Ok(guard) => guard,
            Err(TryLockError::WouldBlock) => return Err(PprofSampleError::Busy),
            Err(TryLockError::Poisoned(poisoned)) => poisoned.into_inner(),
        };

        let profiler = pprof::ProfilerGuardBuilder::default()
            .frequency(99)
            .blocklist(&["libc", "libgcc", "pthread", "vdso"])
            .build()
            .map_err(|error| PprofSampleError::Failed(error.to_string()))?;

        std::thread::sleep(Duration::from_secs(seconds));

        let report = profiler
            .report()
            .build()
            .map_err(|error| PprofSampleError::Failed(error.to_string()))?;
        let profile =
            report.pprof().map_err(|error| PprofSampleError::Failed(error.to_string()))?;

        let mut body = Vec::new();
        profile.encode(&mut body).map_err(|error| PprofSampleError::Failed(error.to_string()))?;
        Ok(body)
    })
    .await
    .map_err(|error| PprofSampleError::Failed(error.to_string()))?
}

use sl_daemon::traceparent::{TraceParent, HEADER as TRACEPARENT};

#[cfg(feature = "otel")]
const TRACESTATE: &str = "tracestate";
const X_REQUEST_ID: &str = "x-request-id";

fn parse_traceparent(value: &str) -> Option<TraceParent> {
    TraceParent::parse(value)
}

fn request_id_from_headers(headers: &HeaderMap) -> String {
    headers
        .get(X_REQUEST_ID)
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .or_else(|| {
            headers
                .get(TRACEPARENT)
                .and_then(|value| value.to_str().ok())
                .and_then(parse_traceparent)
                .map(|parsed| parsed.trace_id)
        })
        .unwrap_or_else(audit::local_request_id)
}

fn idempotency_key_from_headers(headers: &HeaderMap) -> Option<String> {
    headers
        .get(IDEMPOTENCY_KEY)
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
}

fn hash_body(bytes: &[u8]) -> u64 {
    let mut hasher = DefaultHasher::new();
    bytes.hash(&mut hasher);
    hasher.finish()
}

#[cfg(feature = "otel")]
fn remote_parent_context(
    headers: &HeaderMap,
    traceparent: &TraceParent,
) -> Option<opentelemetry::Context> {
    let trace_id = TraceId::from_hex(&traceparent.trace_id).ok()?;
    let span_id = SpanId::from_hex(&traceparent.parent_id).ok()?;
    let flags = u8::from_str_radix(&traceparent.flags, 16).ok()?;
    let trace_flags =
        if flags & 0x01 == 0x01 { TraceFlags::SAMPLED } else { TraceFlags::default() };
    let trace_state = headers
        .get(TRACESTATE)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<TraceState>().ok())
        .unwrap_or_default();
    let span_context = SpanContext::new(trace_id, span_id, trace_flags, true, trace_state);

    Some(opentelemetry::Context::current().with_remote_span_context(span_context))
}

/// Count and trace every HTTP request while preserving valid upstream context.
async fn observe_request(
    State(metrics): State<Arc<HttpMetrics>>,
    request: Request,
    next: Next,
) -> Response {
    metrics.request_started();
    let started = Instant::now();
    let method = request.method().clone();
    let path = request.uri().path().to_owned();
    let propagated = request
        .headers()
        .get(TRACEPARENT)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| parse_traceparent(value).map(|parsed| (value.to_owned(), parsed)));
    let (traceparent, trace_id, parent_span_id, trace_flags) =
        propagated.as_ref().map_or((None, "", "", ""), |(value, parsed)| {
            (
                Some(value.clone()),
                parsed.trace_id.as_str(),
                parsed.parent_id.as_str(),
                parsed.flags.as_str(),
            )
        });
    let span = tracing::info_span!(
        "http.request",
        http.method = %method,
        http.route = %path,
        trace_id = %trace_id,
        parent_span_id = %parent_span_id,
        trace_flags = %trace_flags,
    );
    #[cfg(feature = "otel")]
    if let Some((_, parsed)) = propagated.as_ref() {
        if let Some(parent_context) = remote_parent_context(request.headers(), parsed) {
            if let Err(error) = span.set_parent(parent_context) {
                warn!(?error, "failed to attach remote OTel parent context");
            }
        }
    }
    let mut response = next.run(request).instrument(span).await;
    if let Some(value) = traceparent.and_then(|value| HeaderValue::from_str(&value).ok()) {
        response.headers_mut().insert(TRACEPARENT, value);
    }
    let is_error = response.status().is_client_error() || response.status().is_server_error();
    let elapsed = started.elapsed().as_micros().try_into().unwrap_or(u64::MAX);
    let route = normalize_http_route(&path);
    metrics.request_completed(route, is_error, elapsed);
    response
}

/// `GET /api/stream` — SSE; one event per newly-written `*.okf.json` path.
#[tracing::instrument(skip(state))]
async fn sse_stream(
    State(state): State<AppState>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    info!("SSE client subscribed");
    let rx = state.broadcast_tx.subscribe();
    let stream = BroadcastStream::new(rx).filter_map(|result| {
        result
            .ok()
            .map(|path| Ok(Event::default().event("bundle").data(path.display().to_string())))
    });

    Sse::new(stream).keep_alive(KeepAlive::default())
}

/// Query parameters accepted by `GET /api/search`.
///
/// All fields are optional; omitted fields mean "no constraint on that axis".
/// `tags` is a comma-separated string (e.g. `?tags=rust,ml`) that is split on
/// the server side before being handed to [`apply_filters`].
#[derive(Debug, Deserialize)]
pub(crate) struct SearchParams {
    /// ISO date lower bound, e.g. `2024-01-01`.
    pub since: Option<String>,
    /// ISO date upper bound, e.g. `2024-12-31`.
    pub until: Option<String>,
    /// Case-insensitive model substring, e.g. `claude`.
    pub model: Option<String>,
    /// Minimum token count.
    pub min_tokens: Option<u64>,
    /// Comma-separated tags; ALL must be present (AND logic).
    pub tags: Option<String>,
    /// Maximum results (default 50).
    #[serde(default = "default_limit")]
    pub limit: usize,
}

fn default_limit() -> usize {
    50
}

impl Default for SearchParams {
    fn default() -> Self {
        Self {
            since: None,
            until: None,
            model: None,
            min_tokens: None,
            tags: None,
            limit: default_limit(),
        }
    }
}

/// Build a [`FilterSpec`] from HTTP query parameters.
///
/// This is a pure function so it can be unit-tested without a running server.
pub(crate) fn params_to_spec(p: &SearchParams) -> FilterSpec {
    let tags: Vec<String> = p
        .tags
        .as_deref()
        .unwrap_or("")
        .split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
        .collect();

    FilterSpec {
        since: p.since.clone(),
        until: p.until.clone(),
        model: p.model.clone(),
        min_tokens: p.min_tokens,
        tags,
        limit: p.limit,
    }
}

/// `GET /api/search` — filter bundles by date, model, tokens, and tags.
///
/// Returns a JSON array of [`BundleMeta`] objects matching the query.
#[tracing::instrument(skip(state, params), fields(out_dir = %state.out_dir.display(), limit = params.limit))]
async fn search_bundles(
    headers: HeaderMap,
    State(state): State<AppState>,
    Query(params): Query<SearchParams>,
) -> Response {
    let spec = params_to_spec(&params);
    let matched = match read_matching_bundle_metas(&state.out_dir, &spec) {
        Ok(v) => v,
        Err(e) => {
            error!(error = %e, "failed to read bundles for search");
            return api_error(
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                "bundle_read_failed",
                format!("failed to read bundles: {e}"),
                request_id_from_headers(&headers),
            );
        }
    };

    info!(matched = matched.len(), limit = spec.limit, "search_bundles");

    Json(matched).into_response()
}

/// `POST /api/ingest` — validate an OKF bundle payload before accepting it.
///
/// Returns `200 OK` with the [`crate::validation::ValidationResult`] JSON when the
/// bundle passes all structural checks. Returns `422 Unprocessable Entity` with
/// the same JSON body when one or more validation errors are found. This allows
/// clients to distinguish a transport-level failure (4xx/5xx from the proxy or
/// server) from a business-logic rejection (422 with actionable error details).
#[tracing::instrument(skip(state, request))]
async fn ingest_bundle(State(state): State<AppState>, request: Request) -> Response {
    let request_id = request_id_from_headers(request.headers());
    let idempotency_key = idempotency_key_from_headers(request.headers());
    if !state.api_key_auth.allows(request.headers()) {
        audit_event(&state.audit_sink, "ingest", "rejected", "unauthorized", &request_id);
        return api_error(
            axum::http::StatusCode::UNAUTHORIZED,
            "unauthorized",
            "missing or invalid API key",
            &request_id,
        );
    }
    let Ok(_permit) = state.ingest_admission.semaphore.clone().try_acquire_owned() else {
        audit_event(&state.audit_sink, "ingest", "rejected", "concurrency_limit", &request_id);
        return api_error(
            axum::http::StatusCode::TOO_MANY_REQUESTS,
            "ingest_busy",
            "too many concurrent ingest requests",
            &request_id,
        );
    };
    let bytes = match to_bytes(request.into_body(), state.ingest_admission.max_body_bytes).await {
        Ok(bytes) => bytes,
        Err(_) => {
            audit_event(&state.audit_sink, "ingest", "rejected", "body_too_large", &request_id);
            return api_error(
                axum::http::StatusCode::PAYLOAD_TOO_LARGE,
                "payload_too_large",
                format!("ingest payload exceeds {} bytes", state.ingest_admission.max_body_bytes),
                &request_id,
            );
        }
    };
    let body_hash = hash_body(&bytes);
    if let Some(key) = idempotency_key.as_deref() {
        if let Some(previous) = state.idempotency_cache.get(key) {
            if previous.body_hash == body_hash {
                audit_event(
                    &state.audit_sink,
                    "ingest",
                    "accepted",
                    "idempotent_replay",
                    &request_id,
                );
                return Json(previous.response).into_response();
            }
            audit_event(
                &state.audit_sink,
                "ingest",
                "rejected",
                "idempotency_conflict",
                &request_id,
            );
            return api_error(
                axum::http::StatusCode::CONFLICT,
                "idempotency_conflict",
                "Idempotency-Key was already used with a different request body",
                &request_id,
            );
        }
    }
    let payload: PostBundle = match serde_json::from_slice(&bytes) {
        Ok(payload) => payload,
        Err(error) => {
            audit_event(&state.audit_sink, "ingest", "rejected", "invalid_json", &request_id);
            return api_error(
                axum::http::StatusCode::BAD_REQUEST,
                "invalid_json",
                format!("invalid JSON payload: {error}"),
                &request_id,
            );
        }
    };
    let result = validate_okf_bundle(&payload);
    if result.valid {
        audit_event(&state.audit_sink, "ingest", "accepted", "validation", &request_id);
        if let Some(key) = idempotency_key {
            let result = match state.idempotency_cache.record_success(key, body_hash, result) {
                Ok(result) => result,
                Err(()) => {
                    audit_event(
                        &state.audit_sink,
                        "ingest",
                        "rejected",
                        "idempotency_conflict",
                        &request_id,
                    );
                    return api_error(
                        axum::http::StatusCode::CONFLICT,
                        "idempotency_conflict",
                        "Idempotency-Key was already used with a different request body",
                        &request_id,
                    );
                }
            };
            return Json(result).into_response();
        }
        Json(&result).into_response()
    } else {
        audit_event(&state.audit_sink, "ingest", "rejected", "validation", &request_id);
        (axum::http::StatusCode::UNPROCESSABLE_ENTITY, Json(&result)).into_response()
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Read every `*.okf.json` file in `out_dir` and parse each as
/// [`serde_json::Value`].  Files that fail to parse are silently skipped so
/// a single corrupt file does not poison the entire listing.
fn read_all_bundles(out_dir: &Path, limit: Option<usize>) -> std::io::Result<Vec<Value>> {
    let mut results = Vec::new();
    if limit == Some(0) {
        return Ok(results);
    }

    let rd = match std::fs::read_dir(out_dir) {
        Ok(rd) => rd,
        // If the directory doesn't exist yet, return an empty list.
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(vec![]),
        Err(e) => return Err(e),
    };

    for entry in rd {
        let entry = entry?;
        let path = entry.path();
        let is_okf =
            path.file_name().and_then(|n| n.to_str()).is_some_and(|n| n.ends_with(".okf.json"));
        if !is_okf {
            continue;
        }
        if let Ok(contents) = std::fs::read_to_string(&path) {
            if let Ok(value) = serde_json::from_str::<Value>(&contents) {
                results.push(value);
                if limit.is_some_and(|limit| results.len() >= limit) {
                    break;
                }
            }
        }
    }

    Ok(results)
}

/// Read bundle metadata one file at a time, filtering before retaining it.
///
/// Search must not materialize every OKF payload (which may contain large
/// entity/message arrays) before applying a small result limit. As with
/// [`read_all_bundles`], malformed JSON is ignored so one corrupt export does
/// not poison the search response.
fn read_matching_bundle_metas(
    out_dir: &Path,
    spec: &FilterSpec,
) -> std::io::Result<Vec<BundleMeta>> {
    let mut results = Vec::with_capacity(spec.limit.min(50));
    if spec.limit == 0 {
        return Ok(results);
    }

    let rd = match std::fs::read_dir(out_dir) {
        Ok(rd) => rd,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(results),
        Err(e) => return Err(e),
    };

    for entry in rd {
        let entry = entry?;
        let path = entry.path();
        let is_okf =
            path.file_name().and_then(|n| n.to_str()).is_some_and(|n| n.ends_with(".okf.json"));
        if !is_okf {
            continue;
        }
        let Ok(contents) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Ok(value) = serde_json::from_str::<Value>(&contents) else {
            continue;
        };
        let meta = BundleMeta::from_value(&value);
        if !apply_filters(std::slice::from_ref(&meta), spec).is_empty() {
            results.push(meta);
            if results.len() == spec.limit {
                break;
            }
        }
    }

    Ok(results)
}

fn bearer_token_matches(headers: &HeaderMap, expected: &str) -> bool {
    headers
        .get(AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .is_some_and(|token| token.trim() == expected)
}

fn x_api_key_matches(headers: &HeaderMap, expected: &str) -> bool {
    headers
        .get(X_API_KEY)
        .and_then(|value| value.to_str().ok())
        .is_some_and(|value| value.trim() == expected)
}

#[derive(Serialize)]
struct ApiErrorEnvelope {
    request_id: String,
    error: ApiError,
}

#[derive(Serialize)]
struct ApiError {
    #[serde(rename = "type")]
    error_type: &'static str,
    code: &'static str,
    message: String,
}

fn api_error(
    status: axum::http::StatusCode,
    code: &'static str,
    message: impl Into<String>,
    request_id: impl Into<String>,
) -> Response {
    (
        status,
        Json(ApiErrorEnvelope {
            request_id: request_id.into(),
            error: ApiError {
                error_type: "sessionledger.http_error",
                code,
                message: message.into(),
            },
        }),
    )
        .into_response()
}

async fn not_found(headers: HeaderMap) -> Response {
    api_error(
        axum::http::StatusCode::NOT_FOUND,
        "not_found",
        "route not found",
        request_id_from_headers(&headers),
    )
}

fn audit_event(
    sink: &AuditSink,
    action: &'static str,
    outcome: &'static str,
    reason: &'static str,
    request_id: &str,
) {
    info!(
        target: "sl_daemon::audit",
        event_kind = "audit",
        actor = audit::LOCAL_ACTOR,
        action,
        outcome,
        request_id,
        reason,
        "local operation"
    );
    let event = audit::AuditEvent {
        timestamp: audit::timestamp_unix_ms(),
        actor: audit::LOCAL_ACTOR,
        action,
        outcome,
        request_id,
        reason: Some(reason),
        resource: None,
    };
    if let Err(error) = sink.append(&event) {
        warn!(error = %error, path = %sink.path().display(), "failed to append audit event");
    }
}

// ---------------------------------------------------------------------------
// replay
// ---------------------------------------------------------------------------

/// Query parameters for `GET /api/replay/:bundle_id`.
#[derive(Debug, Deserialize)]
pub(crate) struct ReplayParams {
    /// Playback speed multiplier (default 1.0).  `speed=2.0` replays at 2×
    /// real-time by halving the inter-event delay.
    #[serde(default = "default_speed")]
    pub speed: f64,
}

fn default_speed() -> f64 {
    1.0
}

/// Base inter-event delay in milliseconds at speed = 1.0.
const BASE_DELAY_MS: f64 = 200.0;

/// Calculate the inter-event delay for a given speed multiplier.
///
/// Returns at least 1 ms so we never produce a zero-duration sleep.
pub(crate) fn delay_ms_for_speed(speed: f64) -> u64 {
    let speed = if speed <= 0.0 { 1.0 } else { speed };
    let ms = (BASE_DELAY_MS / speed).round() as u64;
    ms.max(1)
}

/// `GET /api/replay/:bundle_id` — SSE stream of OKF entities in order.
///
/// Opens `<out_dir>/<bundle_id>.okf.json`, reads all entities, and streams
/// each one as an SSE event with the following shape:
///
/// ```text
/// data: {"entity_index":0,"total_entities":5,"entity":{...}}\n\n
/// ```
///
/// After the last entity it sends:
/// ```text
/// event: done\ndata: {}\n\n
/// ```
///
/// The optional `?speed=<f>` query parameter (default 1.0) controls how
/// quickly entities are emitted: `speed=2.0` halves the inter-event delay.
#[tracing::instrument(skip(state, params), fields(bundle_id = %bundle_id, speed = params.speed, out_dir = %state.out_dir.display()))]
async fn replay_bundle(
    headers: HeaderMap,
    AxumPath(bundle_id): AxumPath<String>,
    Query(params): Query<ReplayParams>,
    State(state): State<AppState>,
) -> Response {
    // Sanitise the bundle_id: reject any path traversal.
    if bundle_id.contains('/') || bundle_id.contains('\\') || bundle_id.contains("..") {
        warn!(%bundle_id, "invalid bundle_id");
        return api_error(
            axum::http::StatusCode::BAD_REQUEST,
            "invalid_bundle_id",
            "invalid bundle_id",
            request_id_from_headers(&headers),
        );
    }

    let filename = if bundle_id.ends_with(".okf.json") {
        bundle_id.clone()
    } else {
        format!("{bundle_id}.okf.json")
    };

    let path = state.out_dir.join(&filename);
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return api_error(
                axum::http::StatusCode::NOT_FOUND,
                "bundle_not_found",
                format!("bundle {bundle_id:?} not found"),
                request_id_from_headers(&headers),
            );
        }
        Err(e) => {
            return api_error(
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                "bundle_read_failed",
                format!("failed to read bundle: {e}"),
                request_id_from_headers(&headers),
            );
        }
    };

    let doc: serde_json::Value = match serde_json::from_str(&contents) {
        Ok(v) => v,
        Err(e) => {
            return api_error(
                axum::http::StatusCode::UNPROCESSABLE_ENTITY,
                "invalid_bundle_json",
                format!("invalid OKF JSON: {e}"),
                request_id_from_headers(&headers),
            );
        }
    };

    // Extract the entities array; fall back to empty if absent.
    let entities: Vec<serde_json::Value> =
        doc.get("entities").and_then(|v| v.as_array()).cloned().unwrap_or_default();

    let delay = delay_ms_for_speed(params.speed);
    let total = entities.len();
    info!(entities = total, delay_ms = delay, "replay starting");

    let stream = async_stream::stream! {
        for (idx, entity) in entities.into_iter().enumerate() {
            if idx > 0 {
                tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
            }
            let payload = serde_json::json!({
                "event_index": idx,
                "total_events": total,
                "entity": entity,
            });
            let data = payload.to_string();
            yield Ok::<Event, Infallible>(Event::default().event("entity").data(data));
        }
        // Final done sentinel.
        yield Ok(Event::default().event("done").data("{}"));
    };

    Sse::new(stream).keep_alive(KeepAlive::default()).into_response()
}

// ---------------------------------------------------------------------------
// Unit tests for params_to_spec
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use tracing_test::traced_test;

    fn test_state(out_dir: &Path) -> AppState {
        let (broadcast_tx, _) = broadcast::channel(1);
        AppState {
            resolver: Resolver::default(),
            out_dir: Arc::new(out_dir.to_owned()),
            broadcast_tx,
            http_metrics: Arc::new(HttpMetrics::default()),
            ingest_admission: IngestAdmission::from_values(None, None).unwrap(),
            api_rate_limit: ApiRateLimit::disabled(),
            api_circuit_breaker: ApiCircuitBreaker::disabled(),
            api_key_auth: ApiKeyAuth::default(),
            audit_sink: Arc::new(AuditSink::open(out_dir).expect("audit sink")),
            idempotency_cache: IngestIdempotencyCache::default(),
            #[cfg(feature = "sqlite")]
            memory_store: None,
        }
    }

    fn test_state_with_api_key(out_dir: &Path, api_key: &str) -> AppState {
        let mut state = test_state(out_dir);
        state.api_key_auth = ApiKeyAuth::from_value(Some(api_key.to_owned()));
        state
    }

    fn test_state_with_protect_all_api(out_dir: &Path, api_key: &str) -> AppState {
        let mut state = test_state_with_api_key(out_dir, api_key);
        state.api_key_auth = state.api_key_auth.with_protect_all_api(true);
        state
    }

    fn valid_ingest_body() -> &'static str {
        r#"{
            "bundle_id": "bundle-auth-test",
            "created_at": "2026-07-13T21:40:00Z",
            "messages": [{"role": "user", "content": "hello"}],
            "token_count": 1
        }"#
    }

    async fn start_test_server(state: AppState) -> (SocketAddr, tokio::task::JoinHandle<()>) {
        start_test_server_with_pprof(state, false).await
    }

    async fn start_test_server_with_pprof(
        state: AppState,
        pprof_enabled: bool,
    ) -> (SocketAddr, tokio::task::JoinHandle<()>) {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            axum::serve(listener, router_with_pprof(state, pprof_enabled)).await.unwrap();
        });
        (addr, server)
    }

    /// Prove the complete local-session path at the HTTP boundary:
    /// JSONL ingestion -> durable distillation -> OKF export -> replay SSE.
    #[cfg(feature = "sqlite")]
    #[tokio::test]
    async fn local_jsonl_distill_okf_replay_sse_round_trip() {
        use session_ledger::domain::session::Corpus;
        use session_ledger::ports::MemoryStore;
        use session_ledger::{compile_and_store, export_to_okf, Message, Role, Session};

        let tmp = tempfile::tempdir().expect("tempdir");
        let input = tmp.path().join("local-session.jsonl");
        let output = tmp.path().join("okf");
        std::fs::create_dir_all(&output).expect("create output");

        let mut session = Session::new("e2e-local-session", Corpus::Codex);
        session.cwd = Some("/Users/test/SessionLedger".into());
        session.title = Some("prove durable replay".into());
        session.messages = vec![
            Message::new(Role::User, "Implement durable replay for this session"),
            Message::new(Role::Assistant, "Distilling the session into the memory ledger"),
            Message::new(Role::User, "Looks good, replay it"),
        ];
        std::fs::write(&input, format!("{}\n", serde_json::to_string(&session).unwrap()))
            .expect("write JSONL fixture");

        // Ingest the same on-disk JSONL shape used by the daemon worker.
        let sessions = session_ledger::read_jsonl_sessions(&input).expect("ingest JSONL");
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, "e2e-local-session");

        // Distill into a durable SQLite memory ledger before exporting OKF.
        let memory = session_ledger::SqliteMemoryStore::open(tmp.path().join("memory.db"))
            .expect("open durable memory store");
        let distilled = compile_and_store(&sessions[0], &memory).expect("distill and store");
        assert!(distilled.bundle.is_injectable());
        assert_eq!(distilled.memories.len(), 3);
        assert!(!memory.recall("durable replay", 10).expect("recall memory").is_empty());

        let document = export_to_okf(&distilled.bundle, sessions[0].corpus.as_str());
        assert!(!document.entities.is_empty(), "OKF export must contain entities");
        let bundle_id = document.source_id.clone();
        std::fs::write(
            output.join(format!("{bundle_id}.okf.json")),
            serde_json::to_vec_pretty(&document).expect("serialize OKF"),
        )
        .expect("write OKF export");

        let mut state = test_state(&output);
        state.memory_store = Some(std::sync::Arc::new(memory));
        let (addr, server) = start_test_server(state).await;
        let response = reqwest::get(format!("http://{addr}/api/replay/{bundle_id}?speed=1000"))
            .await
            .expect("replay request");
        assert!(response.status().is_success());
        let body = response.text().await.expect("read replay SSE");
        assert!(body.contains("event: entity"), "replay must emit entity events: {body}");
        assert!(body.contains("event: done"), "replay must emit done sentinel: {body}");
        assert_eq!(
            body.matches("event: entity").count(),
            document.entities.len(),
            "replay must emit every exported graph entity"
        );
        server.abort();
    }

    fn openapi_path_from_manifest() -> std::path::PathBuf {
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/api/openapi.yaml")
    }

    fn parse_openapi_route_surface(yaml: &str) -> std::collections::BTreeSet<(String, String)> {
        use std::collections::BTreeSet;

        let mut routes = BTreeSet::new();
        let mut in_paths = false;
        let mut current_path: Option<String> = None;

        for line in yaml.lines() {
            if line.trim() == "paths:" {
                in_paths = true;
                current_path = None;
                continue;
            }
            if !in_paths {
                continue;
            }
            if !line.is_empty() && !line.starts_with(' ') && line.trim_end().ends_with(':') {
                break;
            }
            if let Some(path) = line.strip_prefix("  ").and_then(|rest| rest.strip_suffix(':')) {
                if path.starts_with('/') {
                    current_path = Some(path.to_owned());
                    continue;
                }
            }
            if let Some(path) = &current_path {
                let trimmed = line.trim();
                if let Some(method) = trimmed.strip_suffix(':') {
                    match method {
                        "get" | "post" | "put" | "patch" | "delete" | "head" | "options" => {
                            routes.insert((method.to_ascii_uppercase(), path.clone()));
                        }
                        _ => {}
                    }
                }
            }
        }

        routes
    }

    fn stable_router_routes_from_source() -> std::collections::BTreeSet<(String, String)> {
        use std::collections::BTreeSet;

        let src = include_str!("http.rs");
        let start =
            src.find("let router = Router::new()").expect("stable router block marker missing");
        let end = start
            + src[start..]
                .find("let router = if pprof_enabled")
                .expect("pprof router split marker missing");
        let block = &src[start..end];
        let mut routes = BTreeSet::new();

        for line in block.lines() {
            let trimmed = line.trim();
            let Some(route_start) = trimmed.find(".route(\"") else {
                continue;
            };
            let rest = &trimmed[route_start + ".route(\"".len()..];
            let Some((path, remainder)) = rest.split_once('"') else {
                continue;
            };
            let method = if remainder.contains("get(") {
                "GET"
            } else if remainder.contains("post(") {
                "POST"
            } else if remainder.contains("put(") {
                "PUT"
            } else if remainder.contains("patch(") {
                "PATCH"
            } else if remainder.contains("delete(") {
                "DELETE"
            } else {
                continue;
            };
            routes.insert((method.to_owned(), path.to_owned()));
        }

        routes
    }

    fn expected_openapi_route_surface() -> std::collections::BTreeSet<(String, String)> {
        OPENAPI_ROUTE_SURFACE
            .iter()
            .map(|&(method, path)| (method.to_owned(), path.to_owned()))
            .collect()
    }

    #[test]
    fn openapi_route_surface_matches_yaml_contract() {
        let openapi_path = openapi_path_from_manifest();
        let yaml = std::fs::read_to_string(&openapi_path)
            .unwrap_or_else(|err| panic!("failed to read {}: {err}", openapi_path.display()));
        let spec_routes = parse_openapi_route_surface(&yaml);
        let expected = expected_openapi_route_surface();

        let missing_from_spec: Vec<_> = expected.difference(&spec_routes).collect();
        let extra_in_spec: Vec<_> = spec_routes.difference(&expected).collect();
        assert!(
            missing_from_spec.is_empty() && extra_in_spec.is_empty(),
            "OpenAPI drift detected in {}.\n\
             missing from openapi.yaml: {missing_from_spec:?}\n\
             extra in openapi.yaml: {extra_in_spec:?}",
            openapi_path.display()
        );
    }

    #[test]
    fn openapi_route_surface_matches_axum_router() {
        let router_routes = stable_router_routes_from_source();
        let expected = expected_openapi_route_surface();

        let missing_from_router: Vec<_> = expected.difference(&router_routes).collect();
        let extra_in_router: Vec<_> = router_routes.difference(&expected).collect();
        assert!(
            missing_from_router.is_empty() && extra_in_router.is_empty(),
            "axum router drift detected in http.rs stable routes.\n\
             missing from router: {missing_from_router:?}\n\
             extra in router: {extra_in_router:?}"
        );
    }

    #[test]
    fn default_params_produce_default_spec() {
        let p = SearchParams::default();
        let spec = params_to_spec(&p);
        assert!(spec.since.is_none());
        assert!(spec.until.is_none());
        assert!(spec.model.is_none());
        assert!(spec.min_tokens.is_none());
        assert!(spec.tags.is_empty());
        assert_eq!(spec.limit, 50);
    }

    #[test]
    fn since_until_model_min_tokens_propagate() {
        let p = SearchParams {
            since: Some("2024-01-01".into()),
            until: Some("2024-12-31".into()),
            model: Some("claude".into()),
            min_tokens: Some(1000),
            tags: None,
            limit: 10,
        };
        let spec = params_to_spec(&p);
        assert_eq!(spec.since.as_deref(), Some("2024-01-01"));
        assert_eq!(spec.until.as_deref(), Some("2024-12-31"));
        assert_eq!(spec.model.as_deref(), Some("claude"));
        assert_eq!(spec.min_tokens, Some(1000));
        assert_eq!(spec.limit, 10);
    }

    #[test]
    fn tags_comma_separated_parsed_correctly() {
        let p = SearchParams { tags: Some("rust, ml, perf".into()), ..SearchParams::default() };
        let spec = params_to_spec(&p);
        assert_eq!(spec.tags, vec!["rust", "ml", "perf"]);
    }

    #[test]
    fn empty_tags_string_yields_empty_vec() {
        let p = SearchParams { tags: Some(String::new()), ..SearchParams::default() };
        let spec = params_to_spec(&p);
        assert!(spec.tags.is_empty());
    }

    #[test]
    fn single_tag_no_trailing_comma() {
        let p = SearchParams { tags: Some("rust".into()), ..SearchParams::default() };
        let spec = params_to_spec(&p);
        assert_eq!(spec.tags, vec!["rust"]);
    }

    // --- replay helpers ---

    #[test]
    fn delay_speed_1_is_base() {
        assert_eq!(delay_ms_for_speed(1.0), 200);
    }

    #[test]
    fn delay_speed_2_is_half_base() {
        assert_eq!(delay_ms_for_speed(2.0), 100);
    }

    #[test]
    fn delay_speed_10_is_clamped_to_1ms_min() {
        // BASE_DELAY_MS(200) / 10 = 20ms — still above minimum.
        assert_eq!(delay_ms_for_speed(10.0), 20);
    }

    #[test]
    fn delay_zero_or_negative_defaults_to_base() {
        // Non-positive speed treated as 1.0.
        assert_eq!(delay_ms_for_speed(0.0), 200);
        assert_eq!(delay_ms_for_speed(-5.0), 200);
    }

    #[test]
    fn delay_very_high_speed_at_least_1ms() {
        // 200 / 1000 = 0.2 → rounds to 0 → clamped to 1.
        assert!(delay_ms_for_speed(1000.0) >= 1);
    }

    #[cfg(feature = "otel")]
    #[test]
    fn builds_remote_otel_parent_context_from_trace_context_headers() {
        use opentelemetry::trace::TraceContextExt as _;

        let traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";
        let parsed = parse_traceparent(traceparent).unwrap();
        let mut headers = HeaderMap::new();
        headers.insert(TRACEPARENT, HeaderValue::from_static(traceparent));
        headers.insert(TRACESTATE, HeaderValue::from_static("rojo=00f067aa0ba902b7"));

        let context = remote_parent_context(&headers, &parsed).unwrap();
        let span_context = context.span().span_context().clone();

        assert!(span_context.is_remote());
        assert_eq!(span_context.trace_id().to_string(), parsed.trace_id);
        assert_eq!(span_context.span_id().to_string(), parsed.parent_id);
        assert!(span_context.is_sampled());
        assert_eq!(span_context.trace_state().header(), "rojo=00f067aa0ba902b7");
    }

    #[test]
    fn ingest_admission_defaults_and_rejects_invalid_values() {
        let defaults = IngestAdmission::from_values(None, None).unwrap();
        assert_eq!(defaults.max_body_bytes, DEFAULT_INGEST_MAX_BODY_BYTES);
        assert_eq!(defaults.semaphore.available_permits(), DEFAULT_INGEST_MAX_CONCURRENCY);
        assert!(IngestAdmission::from_values(Some("0".into()), None).is_err());
        assert!(IngestAdmission::from_values(None, Some("many".into())).is_err());
    }

    #[test]
    fn api_rate_limit_defaults_and_parses_env_values() {
        let loopback_dx = ApiRateLimit::from_values(false, None, None).unwrap();
        assert!(!loopback_dx.is_enabled());

        let shared_key_default = ApiRateLimit::from_values(true, None, None).unwrap();
        assert!(shared_key_default.is_enabled());
        assert_eq!(shared_key_default.limit, DEFAULT_API_RATE_LIMIT);
        assert_eq!(shared_key_default.window, DEFAULT_API_RATE_WINDOW);

        let disabled = ApiRateLimit::from_values(true, Some("off".into()), None).unwrap();
        assert!(!disabled.is_enabled());
        let zero = ApiRateLimit::from_values(true, Some("0".into()), None).unwrap();
        assert!(!zero.is_enabled());

        let custom =
            ApiRateLimit::from_values(false, Some("3".into()), Some("250".into())).unwrap();
        assert!(custom.is_enabled());
        assert_eq!(custom.limit, 3);
        assert_eq!(custom.window, Duration::from_millis(250));

        assert!(ApiRateLimit::from_values(true, Some("nope".into()), None).is_err());
        assert!(ApiRateLimit::from_values(true, Some("5".into()), Some("0".into())).is_err());
    }

    #[test]
    fn api_rate_limit_try_acquire_enforces_fixed_window() {
        let limit = ApiRateLimit::enabled(2, Duration::from_secs(60));
        assert!(limit.try_acquire());
        assert!(limit.try_acquire());
        assert!(!limit.try_acquire());
    }

    #[tokio::test]
    async fn api_circuit_breaker_returns_503_after_consecutive_5xx_keeps_healthz_open() {
        use crate::resilience::BreakerState;

        let out_dir = tempfile::TempDir::new().unwrap();
        let mut state = test_state(out_dir.path());
        // Trip after a single synthetic 5xx recorded against the shared breaker.
        state.api_circuit_breaker = ApiCircuitBreaker::enabled(1, Duration::from_secs(60));
        state.api_circuit_breaker.record_failure();
        assert_eq!(state.api_circuit_breaker.state(), BreakerState::Open);

        let (addr, server) = start_test_server(state).await;
        let client = reqwest::Client::new();

        let blocked = client.get(format!("http://{addr}/api/bundles")).send().await.unwrap();
        assert_eq!(blocked.status(), axum::http::StatusCode::SERVICE_UNAVAILABLE);
        assert!(blocked.headers().get(axum::http::header::RETRY_AFTER).is_some());
        let body: Value = blocked.json().await.unwrap();
        assert_eq!(body["error"]["code"], "circuit_open");

        let health = client.get(format!("http://{addr}/healthz")).send().await.unwrap();
        assert_eq!(health.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[tokio::test]
    async fn api_circuit_breaker_disabled_allows_traffic() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let state = test_state(out_dir.path());
        assert!(!state.api_circuit_breaker.is_enabled());
        let (addr, server) = start_test_server(state).await;
        let response =
            reqwest::Client::new().get(format!("http://{addr}/api/bundles")).send().await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[tokio::test]
    async fn bundle_listing_honors_an_optional_limit() {
        let out_dir = tempfile::TempDir::new().unwrap();
        for name in ["first", "second"] {
            std::fs::write(
                out_dir.path().join(format!("{name}.okf.json")),
                format!(
                    r#"{{"okf":"1.0","source_id":"{name}","entities":[],"relations":[],"provenance":{{"corpus":"forge","source_id":"{name}"}}}}"#
                ),
            )
            .unwrap();
        }

        let (addr, server) = start_test_server(test_state(out_dir.path())).await;
        let listed: Vec<Value> = reqwest::Client::new()
            .get(format!("http://{addr}/api/bundles?limit=1"))
            .send()
            .await
            .unwrap()
            .json()
            .await
            .unwrap();

        assert_eq!(listed.len(), 1);
        server.abort();
    }

    #[test]
    fn api_key_auth_ignores_unset_or_empty_env_values() {
        assert!(ApiKeyAuth::from_value(None).allows(&HeaderMap::new()));
        assert!(ApiKeyAuth::from_value(Some("  ".into())).allows(&HeaderMap::new()));
        assert!(!ApiKeyAuth::from_value(None).is_configured());
        assert!(ApiKeyAuth::from_value(Some("secret".into())).is_configured());
    }

    #[tokio::test]
    async fn protect_all_api_requires_key_on_read_routes_but_healthz_stays_open() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) =
            start_test_server(test_state_with_protect_all_api(out_dir.path(), "secret-token"))
                .await;
        let client = reqwest::Client::new();

        let health = client.get(format!("http://{addr}/healthz")).send().await.unwrap();
        assert_eq!(health.status(), axum::http::StatusCode::OK);

        let denied = client.get(format!("http://{addr}/api/bundles")).send().await.unwrap();
        assert_eq!(denied.status(), axum::http::StatusCode::UNAUTHORIZED);
        let body: Value = denied.json().await.unwrap();
        assert_eq!(body["error"]["code"], "unauthorized");

        let allowed = client
            .get(format!("http://{addr}/api/bundles"))
            .header(AUTHORIZATION, "Bearer secret-token")
            .send()
            .await
            .unwrap();
        assert_eq!(allowed.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[tokio::test]
    async fn loopback_api_key_keeps_read_routes_open_without_credentials() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) =
            start_test_server(test_state_with_api_key(out_dir.path(), "secret-token")).await;

        let response =
            reqwest::Client::new().get(format!("http://{addr}/api/bundles")).send().await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[test]
    #[traced_test]
    fn audit_event_contains_actor_action_and_outcome() {
        let dir = tempfile::TempDir::new().unwrap();
        let sink = AuditSink::open(dir.path()).unwrap();
        audit_event(&sink, "ingest", "accepted", "validation", "req-test");
        assert!(logs_contain("actor=\"local\"") || logs_contain("actor=local"));
        assert!(logs_contain("action=\"ingest\""));
        assert!(logs_contain("outcome=\"accepted\""));

        let contents = std::fs::read_to_string(sink.path()).unwrap();
        let line: serde_json::Value =
            serde_json::from_str(contents.lines().next().unwrap()).unwrap();
        assert_eq!(line["actor"], "local");
        assert_eq!(line["action"], "ingest");
        assert_eq!(line["outcome"], "accepted");
        assert_eq!(line["request_id"], "req-test");
    }

    #[tokio::test]
    async fn ingest_appends_durable_audit_record() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server(test_state(out_dir.path())).await;

        let response = reqwest::Client::new()
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);
        server.abort();

        let audit_path = out_dir.path().join(crate::audit::AUDIT_JSONL_RELATIVE_PATH);
        let contents = std::fs::read_to_string(audit_path).unwrap();
        let last: serde_json::Value =
            serde_json::from_str(contents.lines().last().unwrap()).unwrap();
        assert_eq!(last["actor"], "local");
        assert_eq!(last["action"], "ingest");
        assert_eq!(last["outcome"], "accepted");
        assert_eq!(last["reason"], "validation");
    }

    #[tokio::test]
    async fn ingest_without_api_key_keeps_loopback_trust_model() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server(test_state(out_dir.path())).await;

        let response = reqwest::Client::new()
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);
        let body: Value = response.json().await.unwrap();
        assert_eq!(body["valid"], true);
        server.abort();
    }

    #[tokio::test]
    async fn ingest_idempotency_key_replays_prior_success_for_same_body() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server(test_state(out_dir.path())).await;
        let client = reqwest::Client::new();
        let url = format!("http://{addr}/api/ingest");

        let first = client
            .post(&url)
            .header(CONTENT_TYPE, "application/json")
            .header(IDEMPOTENCY_KEY, "same-body-key")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(first.status(), axum::http::StatusCode::OK);
        let first_body: Value = first.json().await.unwrap();

        let replay = client
            .post(&url)
            .header(CONTENT_TYPE, "application/json")
            .header(IDEMPOTENCY_KEY, "same-body-key")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(replay.status(), axum::http::StatusCode::OK);
        let replay_body: Value = replay.json().await.unwrap();
        assert_eq!(replay_body, first_body);
        server.abort();
    }

    #[tokio::test]
    async fn ingest_idempotency_key_conflicts_for_different_body() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server(test_state(out_dir.path())).await;
        let client = reqwest::Client::new();
        let url = format!("http://{addr}/api/ingest");
        let changed_body = r#"{
            "bundle_id": "bundle-auth-test",
            "created_at": "2026-07-13T21:40:00Z",
            "messages": [{"role": "user", "content": "changed"}],
            "token_count": 2
        }"#;

        let first = client
            .post(&url)
            .header(CONTENT_TYPE, "application/json")
            .header(IDEMPOTENCY_KEY, "conflict-key")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(first.status(), axum::http::StatusCode::OK);

        let conflict = client
            .post(&url)
            .header(CONTENT_TYPE, "application/json")
            .header(IDEMPOTENCY_KEY, "conflict-key")
            .body(changed_body)
            .send()
            .await
            .unwrap();
        assert_eq!(conflict.status(), axum::http::StatusCode::CONFLICT);
        let body: Value = conflict.json().await.unwrap();
        assert_eq!(body["error"]["code"], "idempotency_conflict");
        assert_eq!(
            body["error"]["message"],
            "Idempotency-Key was already used with a different request body"
        );
        server.abort();
    }

    #[tokio::test]
    async fn configured_api_key_allows_bearer_and_x_api_key_headers() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) =
            start_test_server(test_state_with_api_key(out_dir.path(), "secret-token")).await;
        let client = reqwest::Client::new();

        let bearer = client
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .header(AUTHORIZATION, "Bearer secret-token")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(bearer.status(), axum::http::StatusCode::OK);

        let x_api_key = client
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .header(X_API_KEY, "secret-token")
            .body(valid_ingest_body())
            .send()
            .await
            .unwrap();
        assert_eq!(x_api_key.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[tokio::test]
    async fn configured_api_key_denies_missing_or_invalid_credentials() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) =
            start_test_server(test_state_with_api_key(out_dir.path(), "secret-token")).await;
        let client = reqwest::Client::new();

        for request in [
            client
                .post(format!("http://{addr}/api/ingest"))
                .header(CONTENT_TYPE, "application/json")
                .body(valid_ingest_body()),
            client
                .post(format!("http://{addr}/api/ingest"))
                .header(CONTENT_TYPE, "application/json")
                .header(AUTHORIZATION, "Bearer wrong-token")
                .body(valid_ingest_body()),
        ] {
            let response = request.send().await.unwrap();
            assert_eq!(response.status(), axum::http::StatusCode::UNAUTHORIZED);
            let body: Value = response.json().await.unwrap();
            assert_eq!(body["error"]["code"], "unauthorized");
            assert_eq!(body["error"]["message"], "missing or invalid API key");
        }
        server.abort();
    }

    #[tokio::test]
    async fn oversized_ingest_returns_json_error_envelope() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let mut state = test_state(out_dir.path());
        state.ingest_admission = IngestAdmission::from_values(Some("16".into()), None).unwrap();
        let (addr, server) = start_test_server(state).await;

        let response = reqwest::Client::new()
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .header(X_REQUEST_ID, "req-oversized")
            .body(r#"{"payload":"this is larger than sixteen bytes"}"#)
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::PAYLOAD_TOO_LARGE);
        let body: Value = response.json().await.unwrap();
        assert_eq!(body["request_id"], "req-oversized");
        assert_eq!(body["error"]["type"], "sessionledger.http_error");
        assert_eq!(body["error"]["code"], "payload_too_large");
        assert!(body["error"]["message"].as_str().unwrap().contains("16 bytes"));
        server.abort();
    }

    #[tokio::test]
    async fn saturated_ingest_returns_json_too_many_requests() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let mut state = test_state(out_dir.path());
        state.ingest_admission = IngestAdmission {
            max_body_bytes: DEFAULT_INGEST_MAX_BODY_BYTES,
            semaphore: Arc::new(Semaphore::new(0)),
        };
        let (addr, server) = start_test_server(state).await;

        let response = reqwest::Client::new()
            .post(format!("http://{addr}/api/ingest"))
            .header(CONTENT_TYPE, "application/json")
            .body("{}")
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::TOO_MANY_REQUESTS);
        let body: Value = response.json().await.unwrap();
        assert_eq!(body["error"]["code"], "ingest_busy");
        server.abort();
    }

    #[tokio::test]
    async fn api_rate_limit_returns_429_on_api_routes_but_keeps_healthz_open() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let mut state = test_state(out_dir.path());
        state.api_rate_limit = ApiRateLimit::enabled(2, Duration::from_secs(60));
        let (addr, server) = start_test_server(state).await;
        let client = reqwest::Client::new();

        for _ in 0..2 {
            let ok = client.get(format!("http://{addr}/api/bundles")).send().await.unwrap();
            assert_eq!(ok.status(), axum::http::StatusCode::OK);
        }

        let limited = client.get(format!("http://{addr}/api/bundles")).send().await.unwrap();
        assert_eq!(limited.status(), axum::http::StatusCode::TOO_MANY_REQUESTS);
        let body: Value = limited.json().await.unwrap();
        assert_eq!(body["error"]["code"], "rate_limited");
        assert!(body["error"]["message"].as_str().unwrap().contains("2 requests"));

        let health = client.get(format!("http://{addr}/healthz")).send().await.unwrap();
        assert_eq!(health.status(), axum::http::StatusCode::OK);
        server.abort();
    }

    #[tokio::test]
    async fn api_rate_limit_disabled_allows_burst_on_loopback_dx() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let state = test_state(out_dir.path());
        assert!(!state.api_rate_limit.is_enabled());
        let (addr, server) = start_test_server(state).await;
        let client = reqwest::Client::new();

        for _ in 0..8 {
            let response = client.get(format!("http://{addr}/api/bundles")).send().await.unwrap();
            assert_eq!(response.status(), axum::http::StatusCode::OK);
        }
        server.abort();
    }

    #[tokio::test]
    async fn http_observability_middleware_propagates_and_counts() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let state = test_state(out_dir.path());
        let (addr, server) = start_test_server(state).await;
        let base_url = format!("http://{addr}");
        let traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";
        let client = reqwest::Client::new();

        let health = client
            .get(format!("{base_url}/healthz"))
            .header(TRACEPARENT, traceparent)
            .send()
            .await
            .unwrap();
        assert_eq!(health.headers().get(TRACEPARENT).unwrap(), traceparent);

        let metrics =
            client.get(format!("{base_url}/metrics")).send().await.unwrap().text().await.unwrap();
        assert!(metrics.contains("sl_http_requests_total 2"));
        assert!(metrics.contains("sl_http_errors_total 0"));
        server.abort();
    }

    #[tokio::test]
    async fn pprof_routes_are_absent_by_default() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server(test_state(out_dir.path())).await;

        let response = reqwest::Client::new()
            .get(format!("http://{addr}/debug/pprof/profile"))
            .send()
            .await
            .unwrap();

        assert_eq!(response.status(), axum::http::StatusCode::NOT_FOUND);
        server.abort();
    }

    #[tokio::test]
    async fn pprof_routes_are_available_when_enabled() {
        let out_dir = tempfile::TempDir::new().unwrap();
        let (addr, server) = start_test_server_with_pprof(test_state(out_dir.path()), true).await;
        let client = reqwest::Client::new();

        let cmdline =
            client.get(format!("http://{addr}/debug/pprof/cmdline")).send().await.unwrap();
        assert_eq!(cmdline.status(), axum::http::StatusCode::OK);
        assert!(!cmdline.bytes().await.unwrap().is_empty());

        // Keep the sample window short; default is already 1s.
        let profile = client
            .get(format!("http://{addr}/debug/pprof/profile?seconds=1"))
            .timeout(Duration::from_secs(15))
            .send()
            .await
            .unwrap();
        #[cfg(unix)]
        {
            assert_eq!(profile.status(), axum::http::StatusCode::OK);
            assert!(!profile.bytes().await.unwrap().is_empty());
        }
        #[cfg(not(unix))]
        {
            assert_eq!(profile.status(), axum::http::StatusCode::NOT_IMPLEMENTED);
            assert!(profile.bytes().await.unwrap().len() > 16);
        }
        server.abort();
    }

    #[test]
    fn idempotency_cache_remains_bounded() {
        use super::{IngestIdempotencyCache, IDEMPOTENCY_CACHE_MAX_ENTRIES};

        let cache = IngestIdempotencyCache::default();
        for i in 0..(IDEMPOTENCY_CACHE_MAX_ENTRIES + 50) {
            let _ = cache.record_success(
                format!("key-{i}"),
                i as u64,
                crate::validation::ValidationResult { valid: true, errors: Vec::new() },
            );
        }
        // The cache must not retain every inserted key.
        let entries = cache.entries.lock().expect("poisoned");
        assert!(
            entries.len() <= IDEMPOTENCY_CACHE_MAX_ENTRIES,
            "cache grew to {} entries; expected at most {}",
            entries.len(),
            IDEMPOTENCY_CACHE_MAX_ENTRIES
        );
    }
}
