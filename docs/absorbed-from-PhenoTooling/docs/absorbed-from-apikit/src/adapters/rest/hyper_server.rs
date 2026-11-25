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
use http_body_util::{BodyExt, Full};
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request as HyperRequest, Response as HyperResponse, StatusCode};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;
use tracing::{error, info, trace};

use crate::domain::{Endpoint, Request, Response};

/// HTTP server backed by hyper.
pub struct HyperServer {
    listener: TcpListener,
    endpoint: Arc<dyn Endpoint>,
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
        Ok(Self { listener, endpoint })
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
        let HyperServer { listener, endpoint } = self;
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

            trace!("Accepted connection from {}", peer_addr);

            tokio::spawn(async move {
                let service = service_fn(move |req: HyperRequest<Incoming>| {
                    let ep = ep.clone();
                    async move {
                        let domain_req = match convert_request(req).await {
                            Ok(req) => req,
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
        let HyperServer { listener, endpoint } = self;
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
            async move {
                let domain_req = match convert_request(req).await {
                    Ok(req) => req,
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
async fn convert_request(
    req: HyperRequest<Incoming>,
) -> Result<Request, Box<dyn std::error::Error + Send + Sync>> {
    let path = req.uri().path().to_string();
    let method = req.method().to_string();
    let headers = req
        .headers()
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or_default().to_string()))
        .collect();

    let collected = req.collect().await?;
    let bytes = collected.to_bytes();
    let body = if bytes.is_empty() { None } else { Some(bytes.to_vec()) };

    Ok(Request { path, method, headers, body })
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
    use super::*;
    use crate::domain::{Endpoint, Request, Response};
    use crate::Router;
    use async_trait::async_trait;
    use std::time::Duration;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpStream;
    use tokio::time::timeout;

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

        assert!(response_str.contains("200 OK"), "response: {}", response_str);
        assert!(response_str.contains("GET /hello"), "response: {}", response_str);

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

        assert!(response_str.contains("200 OK"), "response: {}", response_str);
        assert!(response_str.contains(body), "response: {}", response_str);

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

        assert!(response_str.contains("200 OK"), "response: {}", response_str);
        assert!(response_str.contains("updated /items/1"), "response: {}", response_str);

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

        assert!(response_str.contains("200 OK"), "response: {}", response_str);
        assert!(response_str.contains("deleted /items/1"), "response: {}", response_str);

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

        assert!(response_str.contains("404"), "response: {}", response_str);

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

        assert!(response_str.contains("200 OK"), "response: {}", response_str);
        assert!(response_str.contains("created /users"), "response: {}", response_str);

        server_task.await.unwrap();
    }
}
