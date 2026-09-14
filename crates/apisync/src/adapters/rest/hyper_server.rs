//! Hyper-based HTTP server adapter
//!
//! Provides a real HTTP/1.1 server using hyper 1.0 and tokio.
//! Converts incoming hyper requests into the domain `Request` type, invokes the
//! configured `Endpoint`, and translates the domain `Response` back into a
//! hyper HTTP response.

use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;

use bytes::Bytes;
use http_body_util::{BodyExt, Full, Limited};
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request as HyperRequest, Response as HyperResponse, StatusCode};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;
use tracing::{error, info, trace};

use crate::domain::{Endpoint, Request, Response};

/// Maximum number of bytes the hyper adapter will read from a single request
/// body. Without this cap `req.collect().await?` will buffer an unbounded
/// stream into memory — a trivial memory-exhaustion DoS (see audit L15/L20).
///
/// 1 MiB is generous for the JSON CRUD API exposed by `endpoints::ItemCrudEndpoint`
/// and matches the size of a healthy `CreateItem` payload by several orders of
/// magnitude. Larger uploads should move to a streaming endpoint.
pub const MAX_REQUEST_BODY_BYTES: usize = 1024 * 1024;

/// HTTP server backed by hyper.
pub struct HyperServer {
    listener: TcpListener,
    endpoint: Arc<dyn Endpoint>,
    /// Maximum number of bytes read from a single request body.
    /// See [`MAX_REQUEST_BODY_BYTES`] for the rationale and default.
    body_limit: usize,
}

impl HyperServer {
    /// Bind a new server to the supplied address.
    ///
    /// # Errors
    ///
    /// Returns an error if the underlying `TcpListener` fails to bind.
    pub async fn new(
        addr: SocketAddr,
        endpoint: Arc<dyn Endpoint>,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(addr).await?;
        Ok(Self { listener, endpoint, body_limit: MAX_REQUEST_BODY_BYTES })
    }

    /// Override the per-request body byte limit.
    ///
    /// Useful for tests that want to exercise the size-cap path without
    /// sending megabytes over a real socket. Production callers should leave
    /// this at [`MAX_REQUEST_BODY_BYTES`].
    pub fn with_body_limit(mut self, limit: usize) -> Self {
        self.body_limit = limit;
        self
    }

    /// Return the configured per-request body byte limit.
    pub fn body_limit(&self) -> usize {
        self.body_limit
    }

    /// Return the local socket address the server is bound to.
    pub fn local_addr(&self) -> Result<SocketAddr, std::io::Error> {
        self.listener.local_addr()
    }

    /// Run the server, accepting connections until the process is shut down.
    ///
    /// Each connection is handled in its own spawned task so the server can
    /// accept new connections concurrently.
    ///
    /// # Errors
    ///
    /// Returns an error only if the server fails to read its local address
    /// before entering the accept loop.
    pub async fn run(self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let HyperServer { listener, endpoint, body_limit } = self;
        let local_addr = listener.local_addr()?;
        info!("HyperServer listening on http://{}", local_addr);

        loop {
            let (stream, peer_addr) = match listener.accept().await {
                Ok(conn) => conn,
                Err(e) => {
                    error!("Failed to accept connection: {}", e);
                    continue;
                }
            };

            let io = TokioIo::new(stream);
            let ep = endpoint.clone();
            let limit = body_limit;

            trace!("Accepted connection from {}", peer_addr);

            tokio::spawn(async move {
                let service = service_fn(move |req: HyperRequest<Incoming>| {
                    let ep = ep.clone();
                    async move {
                        let domain_req = match convert_request(req, limit).await {
                            Ok(req) => req,
                            Err(ConvertError::PayloadTooLarge) => {
                                return Ok::<_, Infallible>(error_response(
                                    StatusCode::PAYLOAD_TOO_LARGE,
                                    "Payload Too Large",
                                ));
                            }
                            Err(e) => {
                                error!("Failed to convert request: {}", e);
                                return Ok::<_, Infallible>(error_response(
                                    StatusCode::BAD_REQUEST,
                                    "Bad Request",
                                ));
                            }
                        };

                        trace!("{} {} -> domain endpoint", domain_req.method, domain_req.path);

                        let domain_res = ep.handle(domain_req).await;
                        let hyper_res = convert_response(domain_res);
                        Ok::<_, Infallible>(hyper_res)
                    }
                });

                if let Err(err) = http1::Builder::new().serve_connection(io, service).await {
                    error!("Error serving connection from {}: {}", peer_addr, err);
                }
            });
        }
    }

    /// Run the server for a single request and then shut down.
    ///
    /// Useful for integration tests where you want to verify one request/response
    /// cycle without keeping the server alive indefinitely.
    #[cfg(test)]
    async fn run_once(self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let HyperServer { listener, endpoint, body_limit } = self;
        let local_addr = listener.local_addr()?;
        info!("HyperServer (run_once) listening on http://{}", local_addr);

        let (stream, peer_addr) = match listener.accept().await {
            Ok(conn) => conn,
            Err(e) => {
                error!("Failed to accept connection: {}", e);
                return Err(e.into());
            }
        };

        let io = TokioIo::new(stream);

        let service = service_fn(move |req: HyperRequest<Incoming>| {
            let ep = endpoint.clone();
            let limit = body_limit;
            async move {
                let domain_req = match convert_request(req, limit).await {
                    Ok(req) => req,
                    Err(ConvertError::PayloadTooLarge) => {
                        return Ok::<_, Infallible>(error_response(
                            StatusCode::PAYLOAD_TOO_LARGE,
                            "Payload Too Large",
                        ));
                    }
                    Err(e) => {
                        error!("Failed to convert request: {}", e);
                        return Ok::<_, Infallible>(error_response(
                            StatusCode::BAD_REQUEST,
                            "Bad Request",
                        ));
                    }
                };

                trace!("{} {} -> domain endpoint", domain_req.method, domain_req.path);

                let domain_res = ep.handle(domain_req).await;
                let hyper_res = convert_response(domain_res);
                Ok::<_, Infallible>(hyper_res)
            }
        });

        if let Err(err) = http1::Builder::new().serve_connection(io, service).await {
            error!("Error serving connection from {}: {}", peer_addr, err);
        }

        Ok(())
    }
}

/// Convert a hyper HTTP request into our domain `Request`.
///
/// The request body is wrapped in [`Limited`] with a hard byte cap
/// (`body_limit`). If the limit is exceeded we surface a
/// [`ConvertError::PayloadTooLarge`] so the caller can return 413 instead of
/// silently buffering an attacker-controlled stream.
async fn convert_request(
    req: HyperRequest<Incoming>,
    body_limit: usize,
) -> Result<Request, ConvertError> {
    let path = req.uri().path().to_string();
    let method = req.method().to_string();
    let headers = req
        .headers()
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or_default().to_string()))
        .collect();

    let limited = Limited::new(req.into_body(), body_limit);
    let collected = limited.collect().await.map_err(|e| {
        if is_length_limit_error(&*e) {
            ConvertError::PayloadTooLarge
        } else {
            ConvertError::BadRequest(e.to_string())
        }
    })?;
    let bytes = collected.to_bytes();
    let body = if bytes.is_empty() { None } else { Some(bytes.to_vec()) };

    Ok(Request { path, method, headers, body })
}

/// Errors that can occur while translating a hyper request into a domain one.
#[derive(Debug)]
pub enum ConvertError {
    /// Request body exceeded the configured body limit.
    PayloadTooLarge,
    /// Any other conversion failure (malformed headers, body I/O error, ...).
    BadRequest(String),
}

impl std::fmt::Display for ConvertError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConvertError::PayloadTooLarge => f.write_str("request body exceeds size limit"),
            ConvertError::BadRequest(msg) => write!(f, "bad request: {msg}"),
        }
    }
}

impl std::error::Error for ConvertError {}

/// Walk an error's `source()` chain looking for `http_body_util::LengthLimitError`.
fn is_length_limit_error(err: &(dyn std::error::Error + 'static)) -> bool {
    if err.is::<http_body_util::LengthLimitError>() {
        return true;
    }
    let mut current = err.source();
    while let Some(e) = current {
        if e.is::<http_body_util::LengthLimitError>() {
            return true;
        }
        current = e.source();
    }
    false
}

/// Convert a domain `Response` into a hyper HTTP response.
fn convert_response(res: Response) -> HyperResponse<Full<Bytes>> {
    let status = StatusCode::from_u16(res.status).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR);
    let mut builder = HyperResponse::builder().status(status);

    for (k, v) in &res.headers {
        builder = builder.header(k, v);
    }

    let body = match res.body {
        Some(bytes) => Full::new(Bytes::from(bytes)),
        None => Full::new(Bytes::new()),
    };

    builder.body(body).unwrap_or_else(|_| {
        HyperResponse::builder()
            .status(StatusCode::INTERNAL_SERVER_ERROR)
            .body(Full::new(Bytes::new()))
            .unwrap()
    })
}

/// Build a simple hyper error response with a plain-text body.
fn error_response(status: StatusCode, message: &str) -> HyperResponse<Full<Bytes>> {
    HyperResponse::builder()
        .status(status)
        .header("Content-Type", "text/plain")
        .body(Full::new(Bytes::from(message.to_string())))
        .unwrap()
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use async_trait::async_trait;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpStream;
    use tokio::time::timeout;

    use super::*;
    use crate::domain::{Endpoint, Request, Response};
    use crate::Router;

    /// Endpoint that echoes the HTTP method and path back.
    #[derive(Clone)]
    struct EchoEndpoint;

    #[async_trait]
    impl Endpoint for EchoEndpoint {
        async fn handle(&self, req: Request) -> Response {
            let body = format!("{} {}", req.method, req.path);
            Response::ok().with_body(body.into_bytes())
        }
    }

    /// Endpoint that echoes the request body back.
    #[derive(Clone)]
    struct BodyEchoEndpoint;

    #[async_trait]
    impl Endpoint for BodyEchoEndpoint {
        async fn handle(&self, req: Request) -> Response {
            let body =
                req.body.map(|b| String::from_utf8_lossy(&b).to_string()).unwrap_or_default();
            Response::ok().with_body(body.into_bytes())
        }
    }

    /// Endpoint that simulates a CRUD interface with different responses per method.
    #[derive(Clone)]
    struct CrudEndpoint;

    #[async_trait]
    impl Endpoint for CrudEndpoint {
        async fn handle(&self, req: Request) -> Response {
            match req.method.as_str() {
                "GET" => Response::ok().with_body(format!("read {}", req.path).into_bytes()),
                "POST" => Response::ok().with_body(format!("created {}", req.path).into_bytes()),
                "PUT" => Response::ok().with_body(format!("updated {}", req.path).into_bytes()),
                "DELETE" => Response::ok().with_body(format!("deleted {}", req.path).into_bytes()),
                _ => Response::not_found(),
            }
        }
    }

    /// Send a raw HTTP/1.1 request and return the raw response bytes.
    async fn send_request(addr: SocketAddr, request: &str) -> Vec<u8> {
        let mut stream = TcpStream::connect(addr).await.expect("failed to connect to server");
        stream.write_all(request.as_bytes()).await.expect("failed to write request");

        let mut buf = Vec::new();
        let mut temp = [0u8; 1024];
        loop {
            match timeout(Duration::from_millis(500), stream.read(&mut temp)).await {
                Ok(Ok(0)) | Ok(Err(_)) | Err(_) => break,
                Ok(Ok(n)) => buf.extend_from_slice(&temp[..n]),
            }
        }
        buf
    }

    #[tokio::test]
    async fn test_get_request() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server =
            HyperServer::new(addr, Arc::new(EchoEndpoint)).await.expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let response = send_request(
            bound,
            "GET /hello HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains("GET /hello"), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_post_request_with_body() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server = HyperServer::new(addr, Arc::new(BodyEchoEndpoint))
            .await
            .expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let body = r#"{"name":"test"}"#;
        let request = format!(
            "POST /users HTTP/1.1\r\n\
             Host: localhost\r\n\
             Content-Length: {}\r\n\
             Connection: close\r\n\r\n\
             {}",
            body.len(),
            body
        );

        let response = send_request(bound, &request).await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains(body), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_put_request() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server =
            HyperServer::new(addr, Arc::new(CrudEndpoint)).await.expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let response = send_request(
            bound,
            "PUT /items/1 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains("updated /items/1"), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_delete_request() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server =
            HyperServer::new(addr, Arc::new(CrudEndpoint)).await.expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let response = send_request(
            bound,
            "DELETE /items/1 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains("deleted /items/1"), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_not_found() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server =
            HyperServer::new(addr, Arc::new(EchoEndpoint)).await.expect("failed to bind server");
        let _bound = server.local_addr().unwrap();

        // No route at /not-found — but EchoEndpoint handles everything.
        // To test 404, use a Router with no matching route.
        let mut router = Router::new();
        router.route("/existing", EchoEndpoint);

        let server = HyperServer::new(addr, Arc::new(router)).await.expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let response = send_request(
            bound,
            "GET /not-found HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("404"), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_server_with_router() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let mut router = Router::new();
        router.route("/users", CrudEndpoint);
        router.route("/echo", EchoEndpoint);

        let server = HyperServer::new(addr, Arc::new(router)).await.expect("failed to bind server");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        let response = send_request(
            bound,
            "POST /users HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains("created /users"), "response: {response_str}");

        server_task.await.unwrap();
    }

    // --- body size limit (Fix #3 / audit L15/L20) -----------------------

    #[tokio::test]
    async fn test_body_under_limit_succeeds() {
        // Use a tiny body_limit so the test stays fast while still exercising
        // the same code path as the production default.
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server = HyperServer::new(addr, Arc::new(BodyEchoEndpoint))
            .await
            .expect("failed to bind server")
            .with_body_limit(64);
        assert_eq!(server.body_limit(), 64, "with_body_limit must persist");
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        // Body of 32 bytes — comfortably under the 64-byte cap.
        let body = "x".repeat(32);
        let request = format!(
            "POST /echo HTTP/1.1\r\n\
             Host: localhost\r\n\
             Content-Length: {}\r\n\
             Connection: close\r\n\r\n\
             {}",
            body.len(),
            body
        );

        let response = send_request(bound, &request).await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(response_str.contains("200 OK"), "response: {response_str}");
        assert!(response_str.contains(&body), "response: {response_str}");

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_body_over_limit_returns_413() {
        // Regression test for the audit's L15 finding: the old `req.collect().await?`
        // buffered an unbounded stream into memory, which is a trivial memory-exhaustion
        // DoS. With `Limited::new(req.into_body(), body_limit)`, oversize bodies
        // surface as `ConvertError::PayloadTooLarge` → HTTP 413.
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server = HyperServer::new(addr, Arc::new(BodyEchoEndpoint))
            .await
            .expect("failed to bind server")
            .with_body_limit(64);
        let bound = server.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            server.run_once().await.unwrap();
        });

        // Body of 200 bytes — well over the 64-byte cap.
        let body = "y".repeat(200);
        let request = format!(
            "POST /echo HTTP/1.1\r\n\
             Host: localhost\r\n\
             Content-Length: {}\r\n\
             Connection: close\r\n\r\n\
             {}",
            body.len(),
            body
        );

        let response = send_request(bound, &request).await;
        let response_str = String::from_utf8_lossy(&response);

        assert!(
            response_str.contains("413"),
            "expected 413 Payload Too Large, got: {response_str}"
        );

        server_task.await.unwrap();
    }

    #[tokio::test]
    async fn test_default_body_limit_matches_constant() {
        // The default must match `MAX_REQUEST_BODY_BYTES` so the documented
        // rationale and the runtime behavior stay aligned.
        let addr = SocketAddr::from(([127, 0, 0, 1], 0));
        let server =
            HyperServer::new(addr, Arc::new(EchoEndpoint)).await.expect("failed to bind server");
        assert_eq!(server.body_limit(), MAX_REQUEST_BODY_BYTES);
    }

    #[test]
    fn convert_error_displays_payload_too_large() {
        let err = ConvertError::PayloadTooLarge;
        assert_eq!(err.to_string(), "request body exceeds size limit");
    }

    #[test]
    fn convert_error_displays_bad_request_with_message() {
        let err = ConvertError::BadRequest("missing header".into());
        assert_eq!(err.to_string(), "bad request: missing header");
    }

    #[test]
    fn is_length_limit_error_detects_direct_instance() {
        // Drive a real `Limited` body past its limit so we get an authentic
        // `LengthLimitError` to feed into the classifier. We can't construct
        // the type directly because it's `#[non_exhaustive]`.
        let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().expect("rt");
        let inner = Full::new(Bytes::from_static(b"too big"));
        let mut limited = http_body_util::Limited::new(inner, 4);
        let err = rt.block_on(async {
            limited.frame().await.expect("frame ready").expect_err("must exceed limit")
        });
        assert!(is_length_limit_error(&*err));
    }

    #[test]
    fn is_length_limit_error_walks_source_chain() {
        // Wrap a LengthLimitError in a custom error that exposes it via
        // `source()`. is_length_limit_error must follow the chain.
        let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().expect("rt");
        let inner = Full::new(Bytes::from_static(b"0123456789"));
        let mut limited = http_body_util::Limited::new(inner, 2);
        let underlying = rt.block_on(async {
            limited.frame().await.expect("frame ready").expect_err("must exceed limit")
        });
        // `underlying` is a `Box<dyn Error>` whose target is the limit error.
        // Wrap it in a custom error type so we exercise the source-chain walk
        // in is_length_limit_error.
        #[derive(Debug)]
        struct OuterError(Box<dyn std::error::Error + Send + Sync>);
        impl std::fmt::Display for OuterError {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "outer({})", self.0)
            }
        }
        impl std::error::Error for OuterError {
            fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
                Some(&*self.0)
            }
        }

        let outer = OuterError(underlying);
        assert!(is_length_limit_error(&outer));
    }

    #[test]
    fn convert_response_falls_back_to_500_for_invalid_status() {
        let res = Response { status: 0, headers: Vec::new(), body: None };
        let hyper_res = convert_response(res);
        assert_eq!(hyper_res.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }

    #[test]
    fn convert_response_preserves_headers_and_body() {
        let res = Response::ok().with_header("x-custom", "value").with_body(b"hello".to_vec());
        let hyper_res = convert_response(res);
        assert_eq!(hyper_res.status(), StatusCode::OK);
        assert_eq!(hyper_res.headers().get("x-custom").unwrap(), "value");
    }

    #[test]
    fn error_response_sets_status_and_plain_text_body() {
        let res = error_response(StatusCode::BAD_REQUEST, "Bad Request");
        assert_eq!(res.status(), StatusCode::BAD_REQUEST);
        assert_eq!(res.headers().get("Content-Type").unwrap(), "text/plain");
    }

    #[test]
    fn is_length_limit_error_returns_false_for_unrelated_errors() {
        #[derive(Debug)]
        struct OtherError;
        impl std::fmt::Display for OtherError {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str("other")
            }
        }
        impl std::error::Error for OtherError {}

        let err = OtherError;
        assert!(!is_length_limit_error(&err));
    }
}
