//! PhenoTesting - Testing Utilities

use anyhow::Result;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

/// Mock HTTP server for testing
pub struct MockHttpServer {
    server: MockServer,
}

impl MockHttpServer {
    pub async fn start() -> Result<Self> {
        let server = MockServer::start().await;
        Ok(Self { server })
    }

    pub fn uri(&self) -> String {
        self.server.uri()
    }

    pub async fn mock_get(&self, url_path: &str, body: &str) {
        Mock::given(method("GET"))
            .and(path(url_path))
            .respond_with(ResponseTemplate::new(200).set_body_string(body))
            .mount(&self.server)
            .await;
    }

    pub async fn mock_post(&self, url_path: &str, response: &str, status: u16) {
        Mock::given(method("POST"))
            .and(path(url_path))
            .respond_with(ResponseTemplate::new(status).set_body_string(response))
            .mount(&self.server)
            .await;
    }
}

/// Generate random test data
pub fn random_string(len: usize) -> String {
    use rand::distr::{Alphanumeric, SampleString};

    Alphanumeric.sample_string(&mut rand::rng(), len)
}

/// Temp directory for tests
pub fn temp_dir() -> tempfile::TempDir {
    tempfile::tempdir().expect("Failed to create temp dir")
}
