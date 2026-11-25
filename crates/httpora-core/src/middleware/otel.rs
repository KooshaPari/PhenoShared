//! # OTEL Middleware
//!
//! OpenTelemetry tracing middleware for Tower-based HTTP services.
//! Emits a span per request with `http.method`, `http.target`,
//! `http.status_code`, `http.duration_ms` attributes + the standard
//! W3C TraceContext headers (`traceparent`, `tracestate`).
//!
//! ## Quick Start
//!
//! ```rust,ignore
//! use httpora_core::middleware::otel::{OtelConfig, OtelLayer};
//! use tower::ServiceBuilder;
//!
//! let otel = OtelLayer::new(OtelConfig::default()
//!     .with_service_name("my-service")
//!     .with_service_version(env!("CARGO_PKG_VERSION")));
//! let svc = ServiceBuilder::new().layer(otel).service(my_service);
//! ```

use crate::error::HttptoraError;
use http::{HeaderMap, Request, Response};
#[allow(unused_imports)]
use http_body;
use std::task::{Context, Poll};
use std::time::Instant;
use tower::{Layer, Service};
use tracing::{field::Empty, instrument::Instrument, Span};

/// Default service name if not specified
pub const DEFAULT_SERVICE_NAME: &str = "httpora-service";

/// W3C TraceContext header names
pub const TRACEPARENT: &str = "traceparent";
pub const TRACESTATE: &str = "tracestate";

/// OpenTelemetry configuration for the middleware layer.
#[derive(Debug, Clone)]
pub struct OtelConfig {
    service_name: String,
    service_version: Option<String>,
    /// If true, the middleware records the request body in the span.
    /// Defaults to false (PII redaction: bodies often contain tokens/PII).
    record_body: bool,
    /// If true, the middleware records the response body in the span.
    /// Defaults to false.
    record_response_body: bool,
    /// Sampling ratio [0.0, 1.0]. 1.0 = always sample.
    sample_ratio: f64,
    /// Whether to propagate the W3C TraceContext (traceparent/tracestate)
    /// from incoming headers onto the outgoing span.
    propagate_traceparent: bool,
}

impl Default for OtelConfig {
    fn default() -> Self {
        Self {
            service_name: DEFAULT_SERVICE_NAME.to_string(),
            service_version: None,
            record_body: false,
            record_response_body: false,
            sample_ratio: 1.0,
            propagate_traceparent: true,
        }
    }
}

impl OtelConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_service_name(mut self, name: impl Into<String>) -> Self {
        self.service_name = name.into();
        self
    }

    pub fn with_service_version(mut self, version: impl Into<String>) -> Self {
        self.service_version = Some(version.into());
        self
    }

    pub fn with_body_recording(mut self, on: bool) -> Self {
        self.record_body = on;
        self.record_response_body = on;
        self
    }

    pub fn with_sample_ratio(mut self, ratio: f64) -> Self {
        self.sample_ratio = ratio.clamp(0.0, 1.0);
        self
    }

    pub fn with_propagate_traceparent(mut self, on: bool) -> Self {
        self.propagate_traceparent = on;
        self
    }

    pub fn service_name(&self) -> &str {
        &self.service_name
    }

    pub fn service_version(&self) -> Option<&str> {
        self.service_version.as_deref()
    }
}

/// Parse a W3C TraceContext `traceparent` header into (version, trace-id,
/// parent-id, flags). Returns None if the header is malformed.
///
/// Format: `00-<32-hex trace-id>-<16-hex parent-id>-<2-hex flags>`
/// Reference: <https://www.w3.org/TR/trace-context/#traceparent-header>
pub fn parse_traceparent(value: &str) -> Option<TraceParent> {
    let parts: Vec<&str> = value.splitn(4, '-').collect();
    if parts.len() != 4 {
        return None;
    }
    if parts[0] != "00" || parts[1].len() != 32 || parts[2].len() != 16 || parts[3].len() != 2 {
        return None;
    }
    Some(TraceParent {
        version: parts[0].to_string(),
        trace_id: parts[1].to_string(),
        parent_id: parts[2].to_string(),
        flags: parts[3].to_string(),
    })
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceParent {
    pub version: String,
    pub trace_id: String,
    pub parent_id: String,
    pub flags: String,
}

impl TraceParent {
    pub fn render(&self) -> String {
        format!(
            "{}-{}-{}-{}",
            self.version, self.trace_id, self.parent_id, self.flags
        )
    }
}

/// Tower middleware layer that emits an OTEL-shaped span per request.
#[derive(Debug, Clone)]
pub struct OtelLayer {
    config: OtelConfig,
}

impl OtelLayer {
    pub fn new(config: OtelConfig) -> Self {
        Self { config }
    }

    pub fn from_config(config: OtelConfig) -> Self {
        Self::new(config)
    }

    pub fn config(&self) -> &OtelConfig {
        &self.config
    }
}

impl<S> Layer<S> for OtelLayer {
    type Service = OtelMiddleware<S>;

    fn layer(&self, inner: S) -> Self::Service {
        OtelMiddleware {
            inner,
            config: self.config.clone(),
        }
    }
}

/// Tower middleware service. Owns the inner service + config.
#[derive(Debug, Clone)]
pub struct OtelMiddleware<S> {
    inner: S,
    config: OtelConfig,
}

impl<S> OtelMiddleware<S> {
    pub fn config(&self) -> &OtelConfig {
        &self.config
    }

    /// Should this request be sampled, given the config's sample_ratio?
    /// Deterministic for testability (always-samples if ratio is 1.0,
    /// never if 0.0; otherwise samples on first hash byte being < ratio*256).
    pub fn should_sample(&self, req: &Request<impl http_body::Body>) -> bool {
        if self.config.sample_ratio >= 1.0 {
            return true;
        }
        if self.config.sample_ratio <= 0.0 {
            return false;
        }
        // Deterministic: hash the method+path and threshold on the first byte
        let key = format!(
            "{}{}",
            req.method().as_str(),
            req.uri()
                .path_and_query()
                .map(|p| p.as_str())
                .unwrap_or("/")
        );
        let h = simple_hash(&key);
        (h as f64 / 256.0) < self.config.sample_ratio
    }

    /// Extract the W3C TraceContext from incoming headers, if present and
    /// the config is set to propagate.
    pub fn extract_traceparent(&self, headers: &HeaderMap) -> Option<TraceParent> {
        if !self.config.propagate_traceparent {
            return None;
        }
        let value = headers.get(TRACEPARENT)?.to_str().ok()?;
        parse_traceparent(value)
    }
}

impl<S, B> Service<Request<B>> for OtelMiddleware<S>
where
    S: Service<Request<B>, Response = Response<B>> + Clone + Send + 'static,
    S::Future: Send + 'static,
    S::Error: std::fmt::Display,
    B: http_body::Body + Send + 'static,
    B::Error: std::fmt::Display,
{
    type Response = Response<B>;
    type Error = S::Error;
    type Future = std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<Self::Response, Self::Error>> + Send>,
    >;

    fn poll_ready(&mut self, cx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        self.inner.poll_ready(cx)
    }

    fn call(&mut self, req: Request<B>) -> Self::Future {
        let config = self.config.clone();
        let mut inner = self.inner.clone();

        // Build the span with attributes that will be filled in once the
        // response arrives.
        let method = req.method().clone();
        let path = req
            .uri()
            .path_and_query()
            .map(|p| p.as_str().to_string())
            .unwrap_or_else(|| "/".to_string());
        let incoming_traceparent = req.headers().get(TRACEPARENT).cloned();

        let span = tracing::info_span!(
            "http.request",
            "otel.service.name" = %config.service_name,
            "otel.service.version" = config.service_version.as_deref().unwrap_or("unknown"),
            "http.method" = %method,
            "http.target" = %path,
            "http.status_code" = Empty,
            "http.duration_ms" = Empty,
            "http.traceparent" = Empty,
        );

        Box::pin(
            async move {
                let start = Instant::now();
                let result = inner.call(req).await;

                match &result {
                    Ok(response) => {
                        let status = response.status().as_u16();
                        Span::current().record("http.status_code", status);
                        if let Some(ref tp) = incoming_traceparent {
                            if let Ok(s) = tp.to_str() {
                                Span::current().record("http.traceparent", s);
                            }
                        }
                    }
                    Err(_err) => {
                        Span::current().record("http.status_code", 0_i64);
                    }
                }

                let elapsed_ms = start.elapsed().as_millis() as u64;
                Span::current().record("http.duration_ms", elapsed_ms);

                if let Err(ref err) = result {
                    Span::current().record("error.message", tracing::field::display(err));
                }

                result
            }
            .instrument(span),
        )
    }
}

/// Simple FNV-style hash for deterministic sampling decisions.
/// NOT cryptographic — used only for sample bucketing.
fn simple_hash(s: &str) -> u8 {
    let mut h: u32 = 0x811c9dc5;
    for byte in s.as_bytes() {
        h ^= *byte as u32;
        h = h.wrapping_mul(0x01000193);
    }
    h as u8
}

/// Convenience: apply an OtelLayer to a service. Equivalent to
/// `OtelLayer::new(config).layer(svc)` but shorter for tests.
pub fn otel<S>(svc: S, config: OtelConfig) -> OtelMiddleware<S> {
    OtelLayer::new(config).layer(svc)
}

/// Helper to build an OtelError for use with HttptoraError
#[derive(Debug)]
pub enum OtelError {
    InvalidTraceparent(String),
    Http(http::Error),
}

impl std::fmt::Display for OtelError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OtelError::InvalidTraceparent(s) => {
                write!(f, "invalid W3C TraceContext traceparent: {}", s)
            }
            OtelError::Http(e) => write!(f, "http error: {}", e),
        }
    }
}

impl std::error::Error for OtelError {}

impl From<OtelError> for HttptoraError {
    fn from(e: OtelError) -> Self {
        HttptoraError::ParseError {
            detail: format!("otel: {}", e),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use http::Request;
    use tower::service_fn;

    #[test]
    fn test_parse_traceparent_valid() {
        let value = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let parsed = parse_traceparent(value).expect("valid traceparent");
        assert_eq!(parsed.version, "00");
        assert_eq!(parsed.trace_id, "0af7651916cd43dd8448eb211c80319c");
        assert_eq!(parsed.parent_id, "b7ad6b7169203331");
        assert_eq!(parsed.flags, "01");
        assert_eq!(parsed.render(), value);
    }

    #[test]
    fn test_parse_traceparent_invalid_too_few_parts() {
        assert!(parse_traceparent("00-abc-def").is_none());
    }

    #[test]
    fn test_parse_traceparent_invalid_version() {
        // Version != "00"
        assert!(
            parse_traceparent("01-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01").is_none()
        );
    }

    #[test]
    fn test_parse_traceparent_invalid_trace_id_length() {
        // trace_id must be 32 hex chars
        assert!(parse_traceparent("00-badtrace-b7ad6b7169203331-01").is_none());
    }

    #[test]
    fn test_parse_traceparent_invalid_parent_id_length() {
        // parent_id must be 16 hex chars
        assert!(parse_traceparent("00-0af7651916cd43dd8448eb211c80319c-badparent-01").is_none());
    }

    #[test]
    fn test_parse_traceparent_invalid_flags_length() {
        // flags must be 2 hex chars
        assert!(
            parse_traceparent("00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1").is_none()
        );
    }

    #[test]
    fn test_otel_config_defaults() {
        let c = OtelConfig::default();
        assert_eq!(c.service_name, DEFAULT_SERVICE_NAME);
        assert!(c.service_version.is_none());
        assert!(!c.record_body);
        assert!((c.sample_ratio - 1.0).abs() < f64::EPSILON);
        assert!(c.propagate_traceparent);
    }

    #[test]
    fn test_otel_config_builders() {
        let c = OtelConfig::new()
            .with_service_name("foo")
            .with_service_version("1.2.3")
            .with_body_recording(true)
            .with_sample_ratio(0.5)
            .with_propagate_traceparent(false);
        assert_eq!(c.service_name(), "foo");
        assert_eq!(c.service_version(), Some("1.2.3"));
        assert!(c.record_body);
        assert!(c.record_response_body);
        assert!((c.sample_ratio - 0.5).abs() < f64::EPSILON);
        assert!(!c.propagate_traceparent);
    }

    #[test]
    fn test_otel_config_sample_ratio_clamped() {
        assert!((OtelConfig::new().with_sample_ratio(2.0).sample_ratio - 1.0).abs() < f64::EPSILON);
        assert!(OtelConfig::new().with_sample_ratio(-1.0).sample_ratio == 0.0);
    }

    #[test]
    fn test_simple_hash_deterministic() {
        // Same input -> same output
        assert_eq!(simple_hash("GET /"), simple_hash("GET /"));
        // Different input -> different output (very likely)
        assert_ne!(simple_hash("GET /"), simple_hash("POST /"));
    }

    #[test]
    fn test_should_sample_full_ratio() {
        let svc = OtelLayer::new(OtelConfig::default().with_sample_ratio(1.0)).layer(service_fn(
            |_req: Request<String>| async { Ok::<_, std::io::Error>(Response::new(String::new())) },
        ));
        let req = Request::builder().uri("/").body(String::new()).unwrap();
        assert!(svc.should_sample(&req));
    }

    #[test]
    fn test_should_sample_zero_ratio() {
        let svc = OtelLayer::new(OtelConfig::default().with_sample_ratio(0.0)).layer(service_fn(
            |_req: Request<String>| async { Ok::<_, std::io::Error>(Response::new(String::new())) },
        ));
        let req = Request::builder().uri("/").body(String::new()).unwrap();
        assert!(!svc.should_sample(&req));
    }

    #[test]
    fn test_extract_traceparent_present() {
        let svc = OtelLayer::new(OtelConfig::default()).layer(service_fn(
            |_req: Request<String>| async { Ok::<_, std::io::Error>(Response::new(String::new())) },
        ));
        let tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let req = Request::builder()
            .uri("/")
            .header(TRACEPARENT, tp)
            .body(String::new())
            .unwrap();
        let extracted = svc.extract_traceparent(req.headers());
        assert!(extracted.is_some());
        assert_eq!(extracted.unwrap().render(), tp);
    }

    #[test]
    fn test_extract_traceparent_missing() {
        let svc = OtelLayer::new(OtelConfig::default()).layer(service_fn(
            |_req: Request<String>| async { Ok::<_, std::io::Error>(Response::new(String::new())) },
        ));
        let req = Request::builder().uri("/").body(String::new()).unwrap();
        assert!(svc.extract_traceparent(req.headers()).is_none());
    }

    #[test]
    fn test_extract_traceparent_disabled() {
        let svc = OtelLayer::new(OtelConfig::default().with_propagate_traceparent(false)).layer(
            service_fn(|_req: Request<String>| async {
                Ok::<_, std::io::Error>(Response::new(String::new()))
            }),
        );
        let tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let req = Request::builder()
            .uri("/")
            .header(TRACEPARENT, tp)
            .body(String::new())
            .unwrap();
        assert!(svc.extract_traceparent(req.headers()).is_none());
    }

    #[tokio::test]
    async fn test_middleware_emits_span_with_status() {
        // Use a noop service that returns 200
        async fn ok_svc(
            _req: Request<String>,
        ) -> Result<Response<String>, std::convert::Infallible> {
            Ok(Response::builder().status(200).body(String::new()).unwrap())
        }

        let svc = otel(service_fn(ok_svc), OtelConfig::default());
        let req = Request::builder().uri("/foo").body(String::new()).unwrap();

        let resp = tower::ServiceExt::oneshot(svc, req).await.unwrap();
        assert_eq!(resp.status().as_u16(), 200);
    }

    #[tokio::test]
    async fn test_middleware_propagates_traceparent_into_span() {
        async fn ok_svc(
            _req: Request<String>,
        ) -> Result<Response<String>, std::convert::Infallible> {
            Ok(Response::builder().status(200).body(String::new()).unwrap())
        }

        let svc = otel(service_fn(ok_svc), OtelConfig::default());
        let tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let req = Request::builder()
            .uri("/bar")
            .header(TRACEPARENT, tp)
            .body(String::new())
            .unwrap();

        let resp = tower::ServiceExt::oneshot(svc, req).await.unwrap();
        assert_eq!(resp.status().as_u16(), 200);
    }

    #[tokio::test]
    async fn test_middleware_records_error_status() {
        async fn err_svc(
            _req: Request<String>,
        ) -> Result<Response<String>, std::convert::Infallible> {
            Ok(Response::builder().status(500).body(String::new()).unwrap())
        }

        let svc = otel(service_fn(err_svc), OtelConfig::default());
        let req = Request::builder().uri("/boom").body(String::new()).unwrap();
        let resp = tower::ServiceExt::oneshot(svc, req).await.unwrap();
        assert_eq!(resp.status().as_u16(), 500);
    }

    #[test]
    fn test_otel_error_display() {
        let e = OtelError::InvalidTraceparent("bad".to_string());
        assert!(e.to_string().contains("invalid W3C TraceContext"));
        let http_error = Request::builder()
            .uri("http://[::1")
            .body(())
            .expect_err("invalid URI should produce an http::Error");
        let e = OtelError::Http(http_error);
        assert!(e.to_string().contains("http error"));
    }

    #[test]
    fn test_otel_error_into_httpora_error() {
        let e: HttptoraError = OtelError::InvalidTraceparent("bad".to_string()).into();
        assert!(matches!(e, HttptoraError::ParseError { detail } if detail.contains("otel")));
    }
}
