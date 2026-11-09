//! Prometheus Adapter

use std::net::SocketAddr;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request, Response, header::CONTENT_TYPE};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;
use http_body_util::Full;
use bytes::Bytes;

use crate::application::{PrometheusExporter, exporter::MetricExporter};
use crate::domain::Registry;

/// Start Prometheus metrics endpoint
pub async fn start_prometheus_server(
    addr: SocketAddr,
    registry: Registry,
) -> Result<(), Box<dyn std::error::Error>> {
    let _exporter = PrometheusExporter::new();
    let registry = std::sync::Arc::new(registry);

    let listener = TcpListener::bind(addr).await?;
    println!("Prometheus server listening on {}", addr);

    loop {
        let (stream, _) = listener.accept().await?;
        let io = TokioIo::new(stream);
        let registry = registry.clone();
        let exporter = PrometheusExporter::new();

        tokio::spawn(async move {
            let svc = service_fn(move |_req: Request<hyper::body::Incoming>| {
                let registry = registry.clone();
                let exporter = exporter.clone();
                async move {
                    let metrics = exporter.export(&registry).unwrap_or_default();
                    Ok::<_, std::convert::Infallible>(Response::builder()
                        .header(CONTENT_TYPE, "text/plain; version=0.0.4")
                        .body(Full::new(Bytes::from(metrics)))
                        .unwrap())
                }
            });

            if let Err(e) = http1::Builder::new()
                .serve_connection(io, svc)
                .await
            {
                eprintln!("Error serving connection: {}", e);
            }
        });
    }
}
