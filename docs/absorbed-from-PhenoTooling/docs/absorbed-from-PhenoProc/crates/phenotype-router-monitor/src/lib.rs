use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use url::Url;

pub mod api;
pub mod monitor;

#[derive(Error, Debug)]
pub enum MonitorError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("URL parse error: {0}")]
    Url(#[from] url::ParseError),
    #[error("API error: {status} - {message}")]
    Api { status: u16, message: String },
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

pub type MonitorResult<T> = Result<T, MonitorError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterMetrics {
    pub router_id: String,
    pub uptime_seconds: u64,
    pub requests_total: u64,
    pub requests_per_second: f64,
    pub avg_latency_ms: f64,
    pub error_rate: f64,
    pub active_connections: u32,
    pub memory_usage_bytes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterStatus {
    pub router_id: String,
    pub healthy: bool,
    pub last_check: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub routers: Vec<RouterStatus>,
}

pub struct RouterMonitorClient {
    client: Client,
    base_url: Url,
}

impl RouterMonitorClient {
    pub fn new(base_url: &str) -> MonitorResult<Self> {
        Ok(Self {
            client: Client::new(),
            base_url: Url::parse(base_url)?,
        })
    }

    pub async fn get_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics> {
        let url = self
            .base_url
            .join(&format!("/api/v1/routers/{}/metrics", router_id))?;
        let response = self.client.get(url).send().await?;

        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>> {
        let url = self.base_url.join("/api/v1/routers/metrics")?;
        let response = self.client.get(url).send().await?;

        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_status(&self, router_id: &str) -> MonitorResult<RouterStatus> {
        let url = self
            .base_url
            .join(&format!("/api/v1/routers/{}/status", router_id))?;
        let response = self.client.get(url).send().await?;

        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }

    pub async fn get_health(&self) -> MonitorResult<HealthResponse> {
        let url = self.base_url.join("/api/v1/health")?;
        let response = self.client.get(url).send().await?;

        if response.status().is_success() {
            Ok(response.json().await?)
        } else {
            let status = response.status().as_u16();
            let message = response.text().await.unwrap_or_default();
            Err(MonitorError::Api { status, message })
        }
    }
}

#[async_trait]
pub trait RouterMetricsProvider: Send + Sync {
    async fn fetch_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics>;
    async fn fetch_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>>;
    async fn check_health(&self) -> MonitorResult<HealthResponse>;
}

#[async_trait]
impl RouterMetricsProvider for RouterMonitorClient {
    async fn fetch_metrics(&self, router_id: &str) -> MonitorResult<RouterMetrics> {
        self.get_metrics(router_id).await
    }

    async fn fetch_all_metrics(&self) -> MonitorResult<Vec<RouterMetrics>> {
        self.get_all_metrics().await
    }

    async fn check_health(&self) -> MonitorResult<HealthResponse> {
        self.get_health().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    #[test]
    fn test_router_metrics_serialization() {
        let json = r#"{
            "router_id": "router-1",
            "uptime_seconds": 3600,
            "requests_total": 10000,
            "requests_per_second": 2.78,
            "avg_latency_ms": 15.5,
            "error_rate": 0.01,
            "active_connections": 42,
            "memory_usage_bytes": 1073741824
        }"#;
        let metrics: RouterMetrics = serde_json::from_str(json).unwrap();
        assert_eq!(metrics.router_id, "router-1");
        assert_eq!(metrics.requests_total, 10000);
    }

    #[test]
    fn test_router_status_serialization() {
        let json = r#"{
            "router_id": "router-1",
            "healthy": true,
            "last_check": "2026-03-30T12:00:00Z",
            "version": "1.0.0"
        }"#;
        let status: RouterStatus = serde_json::from_str(json).unwrap();
        assert!(status.healthy);
        assert_eq!(status.version, "1.0.0");
    }

    #[test]
    fn test_client_creation() {
        let client = RouterMonitorClient::new("http://localhost:8080").unwrap();
        assert_eq!(client.base_url.as_str(), "http://localhost:8080/");
    }

    #[test]
    fn test_invalid_url() {
        let result = RouterMonitorClient::new("not-a-valid-url");
        assert!(result.is_err());
    }

    #[test]
    fn test_router_metrics_serde_roundtrip() {
        let m = RouterMetrics {
            router_id: "r1".into(),
            uptime_seconds: 60,
            requests_total: 5,
            requests_per_second: 0.1,
            avg_latency_ms: 1.0,
            error_rate: 0.0,
            active_connections: 1,
            memory_usage_bytes: 1024,
        };
        let s = serde_json::to_string(&m).unwrap();
        let m2: RouterMetrics = serde_json::from_str(&s).unwrap();
        assert_eq!(m.router_id, m2.router_id);
        assert_eq!(m.uptime_seconds, m2.uptime_seconds);
    }

    #[test]
    fn test_router_status_serde_roundtrip() {
        let s = RouterStatus {
            router_id: "r1".into(),
            healthy: true,
            last_check: "2026-01-01T00:00:00Z".into(),
            version: "0.1.0".into(),
        };
        let j = serde_json::to_string(&s).unwrap();
        let s2: RouterStatus = serde_json::from_str(&j).unwrap();
        assert_eq!(s.router_id, s2.router_id);
        assert_eq!(s.version, s2.version);
    }

    #[test]
    fn test_health_response_serde_roundtrip() {
        let h = HealthResponse {
            status: "ok".into(),
            routers: vec![RouterStatus {
                router_id: "r1".into(),
                healthy: true,
                last_check: "now".into(),
                version: "1".into(),
            }],
        };
        let j = serde_json::to_string(&h).unwrap();
        let h2: HealthResponse = serde_json::from_str(&j).unwrap();
        assert_eq!(h2.status, "ok");
        assert_eq!(h2.routers.len(), 1);
        assert!(h2.routers[0].healthy);
    }

    #[test]
    fn test_monitor_error_display() {
        let url_err: MonitorError = url::ParseError::EmptyHost.into();
        assert!(format!("{}", url_err).contains("URL parse"));

        let ser_err: MonitorError = serde_json::from_str::<i32>("not a number").unwrap_err().into();
        assert!(format!("{}", ser_err).contains("Serialization"));

        let api_err = MonitorError::Api { status: 500, message: "boom".into() };
        let text = format!("{}", api_err);
        assert!(text.contains("500"));
        assert!(text.contains("boom"));
    }

    #[tokio::test]
    async fn test_get_metrics_ok() {
        let server = MockServer::start().await;
        let body = serde_json::json!({
            "router_id": "router-1",
            "uptime_seconds": 120,
            "requests_total": 7,
            "requests_per_second": 0.5,
            "avg_latency_ms": 2.0,
            "error_rate": 0.0,
            "active_connections": 0,
            "memory_usage_bytes": 256
        });
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/router-1/metrics"))
            .respond_with(ResponseTemplate::new(200).set_body_json(body))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let m = client.get_metrics("router-1").await.unwrap();
        assert_eq!(m.router_id, "router-1");
        assert_eq!(m.requests_total, 7);
    }

    #[tokio::test]
    async fn test_get_metrics_api_error() {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/missing/metrics"))
            .respond_with(ResponseTemplate::new(404).set_body_string("not found"))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let res = client.get_metrics("missing").await;
        match res {
            Err(MonitorError::Api { status, message }) => {
                assert_eq!(status, 404);
                assert!(message.contains("not found"));
            }
            other => panic!("expected Api error, got {:?}", other),
        }
    }

    #[tokio::test]
    async fn test_get_all_metrics_ok() {
        let server = MockServer::start().await;
        let body = serde_json::json!([
            {"router_id":"r1","uptime_seconds":1,"requests_total":1,"requests_per_second":0.0,"avg_latency_ms":0.0,"error_rate":0.0,"active_connections":0,"memory_usage_bytes":0},
            {"router_id":"r2","uptime_seconds":2,"requests_total":2,"requests_per_second":0.0,"avg_latency_ms":0.0,"error_rate":0.0,"active_connections":0,"memory_usage_bytes":0}
        ]);
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/metrics"))
            .respond_with(ResponseTemplate::new(200).set_body_json(body))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let all = client.get_all_metrics().await.unwrap();
        assert_eq!(all.len(), 2);
    }

    #[tokio::test]
    async fn test_get_all_metrics_api_error() {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/metrics"))
            .respond_with(ResponseTemplate::new(502).set_body_string("bad gateway"))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let res = client.get_all_metrics().await;
        match res {
            Err(MonitorError::Api { status, message }) => {
                assert_eq!(status, 502);
                assert!(message.contains("bad gateway"));
            }
            other => panic!("expected Api error, got {:?}", other),
        }
    }

    #[tokio::test]
    async fn test_get_status_ok_and_err() {
        let server = MockServer::start().await;
        let body = serde_json::json!({
            "router_id": "r1",
            "healthy": true,
            "last_check": "now",
            "version": "1.0"
        });
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/r1/status"))
            .respond_with(ResponseTemplate::new(200).set_body_json(body))
            .mount(&server)
            .await;
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/r2/status"))
            .respond_with(ResponseTemplate::new(503))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let ok = client.get_status("r1").await.unwrap();
        assert!(ok.healthy);

        let err = client.get_status("r2").await;
        assert!(matches!(err, Err(MonitorError::Api { status: 503, .. })));
    }

    #[tokio::test]
    async fn test_get_health_ok_and_err() {
        let server = MockServer::start().await;
        let body = serde_json::json!({"status":"ok","routers":[]});
        Mock::given(method("GET"))
            .and(path("/api/v1/health"))
            .respond_with(ResponseTemplate::new(200).set_body_json(body))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let h = client.get_health().await.unwrap();
        assert_eq!(h.status, "ok");
        assert!(h.routers.is_empty());

        // Now test the error path.
        let server2 = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/api/v1/health"))
            .respond_with(ResponseTemplate::new(500).set_body_string("oops"))
            .mount(&server2)
            .await;
        let client2 = RouterMonitorClient::new(&server2.uri()).unwrap();
        let err = client2.get_health().await;
        assert!(matches!(err, Err(MonitorError::Api { status: 500, .. })));
    }

    #[tokio::test]
    async fn test_trait_provider_delegates() {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/r1/metrics"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "router_id":"r1","uptime_seconds":1,"requests_total":1,"requests_per_second":0.0,
                "avg_latency_ms":0.0,"error_rate":0.0,"active_connections":0,"memory_usage_bytes":0
            })))
            .mount(&server)
            .await;
        Mock::given(method("GET"))
            .and(path("/api/v1/routers/metrics"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!([])))
            .mount(&server)
            .await;
        Mock::given(method("GET"))
            .and(path("/api/v1/health"))
            .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({"status":"ok","routers":[]})))
            .mount(&server)
            .await;

        let client = RouterMonitorClient::new(&server.uri()).unwrap();
        let provider: &dyn RouterMetricsProvider = &client;

        let m = provider.fetch_metrics("r1").await.unwrap();
        assert_eq!(m.router_id, "r1");

        let all = provider.fetch_all_metrics().await.unwrap();
        assert!(all.is_empty());

        let h = provider.check_health().await.unwrap();
        assert_eq!(h.status, "ok");
    }
}
