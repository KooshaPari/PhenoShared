//! Integration tests for phenotype-vessel container client.
//!
//! These tests use mock runtimes to validate the ContainerClient API
//! without requiring actual Docker/Podman runtime.
//!
//! Traces to: FR-VESSEL-INTEGRATION-001

use async_trait::async_trait;
use phenotype_vessel::client::ContainerClient;
use phenotype_vessel::runtime::{
    ContainerCreateConfig, ContainerInfo, ContainerRuntime, DockerRuntime, PodmanRuntime,
    PortMapping, Protocol, VolumeMapping,
};
use phenotype_vessel::{Container, ContainerStatus, Image, VesselError};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// ============================================================================
// Mock Runtime for Testing
// ============================================================================

/// Mock runtime for integration testing
#[derive(Debug, Default)]
struct MockRuntime {
    containers: Arc<Mutex<Vec<ContainerInfo>>>,
    images: Arc<Mutex<Vec<String>>>,
    available: bool,
}

impl MockRuntime {
    fn new() -> Self {
        Self {
            containers: Arc::new(Mutex::new(Vec::new())),
            images: Arc::new(Mutex::new(vec!["nginx:latest".to_string()])),
            available: true,
        }
    }

    fn with_containers(containers: Vec<ContainerInfo>) -> Self {
        Self {
            containers: Arc::new(Mutex::new(containers)),
            images: Arc::new(Mutex::new(Vec::new())),
            available: true,
        }
    }

    fn unavailable() -> Self {
        Self {
            containers: Arc::new(Mutex::new(Vec::new())),
            images: Arc::new(Mutex::new(Vec::new())),
            available: false,
        }
    }
}

#[async_trait]
impl ContainerRuntime for MockRuntime {
    fn name(&self) -> &str {
        "mock"
    }

    async fn is_available(&self) -> bool {
        self.available
    }

    async fn list_containers(&self) -> Result<Vec<ContainerInfo>, String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        Ok(self.containers.lock().unwrap().clone())
    }

    async fn pull_image(&self, image: &str) -> Result<(), String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        self.images.lock().unwrap().push(image.to_string());
        Ok(())
    }

    async fn remove_image(&self, image: &str) -> Result<(), String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        self.images.lock().unwrap().retain(|i| i != image);
        Ok(())
    }

    async fn create_container(&self, config: &ContainerCreateConfig) -> Result<String, String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        let id = format!("mock-{}", rand_id());
        let container = ContainerInfo {
            id: id.clone(),
            name: config.name.clone().unwrap_or_default(),
            image: config.image.clone(),
            status: "created".to_string(),
            created: "2024-01-01".to_string(),
        };
        self.containers.lock().unwrap().push(container);
        Ok(id)
    }

    async fn start_container(&self, id: &str) -> Result<(), String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        if let Some(c) = self.containers.lock().unwrap().iter_mut().find(|c| c.id == id) {
            c.status = "running".to_string();
            Ok(())
        } else {
            Err(format!("Container {} not found", id))
        }
    }

    async fn stop_container(&self, id: &str) -> Result<(), String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        if let Some(c) = self.containers.lock().unwrap().iter_mut().find(|c| c.id == id) {
            c.status = "exited".to_string();
            Ok(())
        } else {
            Err(format!("Container {} not found", id))
        }
    }

    async fn remove_container(&self, id: &str) -> Result<(), String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        self.containers.lock().unwrap().retain(|c| c.id != id);
        Ok(())
    }

    async fn logs(&self, id: &str) -> Result<String, String> {
        if !self.available {
            return Err("Runtime unavailable".to_string());
        }
        if self.containers.lock().unwrap().iter().any(|c| c.id == id) {
            Ok(format!("Logs for container {}", id))
        } else {
            Err(format!("Container {} not found", id))
        }
    }
}

fn rand_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let duration = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
    format!("{:x}", duration.as_nanos())
}

// ============================================================================
// Integration Tests - Client Lifecycle
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-002
#[tokio::test]
async fn test_container_client_creation() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    assert_eq!(client.runtime_name(), "mock");
}

// Traces to: FR-VESSEL-INTEGRATION-003
#[tokio::test]
async fn test_container_client_availability() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    assert!(client.is_available().await);
}

// Traces to: FR-VESSEL-INTEGRATION-004
#[tokio::test]
async fn test_container_client_unavailable_runtime() {
    let runtime = MockRuntime::unavailable();
    let client = ContainerClient::new(runtime);

    assert!(!client.is_available().await);
}

// Traces to: FR-VESSEL-INTEGRATION-005
#[tokio::test]
async fn test_list_containers_empty() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let containers = client.list_containers().await.unwrap();
    assert!(containers.is_empty());
}

// Traces to: FR-VESSEL-INTEGRATION-006
#[tokio::test]
async fn test_list_containers_with_data() {
    let containers = vec![
        ContainerInfo {
            id: "abc123".to_string(),
            name: "web".to_string(),
            image: "nginx:latest".to_string(),
            status: "running".to_string(),
            created: "2024-01-01".to_string(),
        },
        ContainerInfo {
            id: "def456".to_string(),
            name: "db".to_string(),
            image: "postgres:15".to_string(),
            status: "running".to_string(),
            created: "2024-01-02".to_string(),
        },
    ];
    let runtime = MockRuntime::with_containers(containers);
    let client = ContainerClient::new(runtime);

    let result = client.list_containers().await.unwrap();
    assert_eq!(result.len(), 2);
    assert_eq!(result[0].name, "web");
    assert_eq!(result[1].name, "db");
}

// Traces to: FR-VESSEL-INTEGRATION-007
#[tokio::test]
async fn test_pull_image() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let image = client.pull_image("redis:alpine").await.unwrap();
    assert_eq!(image.name, "redis:alpine");
    assert_eq!(image.tag, "latest");
}

// Traces to: FR-VESSEL-INTEGRATION-008
#[tokio::test]
async fn test_remove_image() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    // Pull first
    client.pull_image("nginx:latest").await.unwrap();

    // Then remove
    let result = client.remove_image("nginx:latest").await;
    assert!(result.is_ok());
}

// Traces to: FR-VESSEL-INTEGRATION-009
#[tokio::test]
async fn test_run_container() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.run("nginx:latest", "test-container").await.unwrap();

    assert_eq!(container.name, "test-container");
    assert_eq!(container.image, "nginx:latest");
    assert_eq!(container.status, ContainerStatus::Running);
    assert!(!container.id.is_empty());
}

// Traces to: FR-VESSEL-INTEGRATION-010
#[tokio::test]
async fn test_create_container_only() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("postgres:15", "test-db").await.unwrap();

    assert_eq!(container.name, "test-db");
    assert_eq!(container.image, "postgres:15");
    // Note: create doesn't start, so status depends on runtime
}

// ============================================================================
// Integration Tests - Error Handling
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-011
#[tokio::test]
async fn test_unavailable_runtime_error() {
    let runtime = MockRuntime::unavailable();
    let client = ContainerClient::new(runtime);

    let result = client.list_containers().await;
    assert!(result.is_err());
}

// Traces to: FR-VESSEL-INTEGRATION-012
#[tokio::test]
async fn test_vessel_error_types() {
    let error = VesselError::ImagePullFailed("test".to_string());
    let display = format!("{}", error);
    // The #[error(...)] attribute uses "Image error" not "ImagePullFailed"
    assert!(display.contains("Image error"));

    let io_error = VesselError::Io(std::io::Error::new(std::io::ErrorKind::NotFound, "test error"));
    let display = format!("{}", io_error);
    assert!(display.contains("IO error"));
}

// ============================================================================
// Integration Tests - Port and Volume Mappings
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-013
#[test]
fn test_port_mapping_creation() {
    let mapping = PortMapping { host_port: 8080, container_port: 80, protocol: Protocol::Tcp };

    assert_eq!(mapping.host_port, 8080);
    assert_eq!(mapping.container_port, 80);
    assert!(matches!(mapping.protocol, Protocol::Tcp));
}

// Traces to: FR-VESSEL-INTEGRATION-014
#[test]
fn test_volume_mapping_creation() {
    let mapping = VolumeMapping {
        host_path: "/data".to_string(),
        container_path: "/app/data".to_string(),
        read_only: true,
    };

    assert_eq!(mapping.host_path, "/data");
    assert_eq!(mapping.container_path, "/app/data");
    assert!(mapping.read_only);
}

// Traces to: FR-VESSEL-INTEGRATION-015
#[test]
fn test_protocol_variants() {
    assert!(matches!(Protocol::Tcp, Protocol::Tcp));
    assert!(matches!(Protocol::Udp, Protocol::Udp));
}

// ============================================================================
// Integration Tests - Image Handling
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-016
#[test]
fn test_image_struct() {
    let image = Image {
        id: "sha256:abc123".to_string(),
        name: "nginx".to_string(),
        tag: "1.25".to_string(),
        size: 142_000_000,
    };

    assert_eq!(image.name, "nginx");
    assert_eq!(image.tag, "1.25");
    assert!(image.size > 0);
}

// Traces to: FR-VESSEL-INTEGRATION-017
#[test]
fn test_container_status_from_string() {
    let running = ContainerStatus::Running;
    let exited = ContainerStatus::Exited;

    assert_eq!(running.to_string(), "running");
    assert_eq!(exited.to_string(), "exited");
}

// ============================================================================
// Integration Tests - Docker and Podman Runtimes
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-018
#[test]
fn test_docker_runtime_name() {
    let runtime = DockerRuntime::new();
    assert_eq!(runtime.name(), "docker");
}

// Traces to: FR-VESSEL-INTEGRATION-019
#[test]
fn test_podman_runtime_name() {
    let runtime = PodmanRuntime::new();
    assert_eq!(runtime.name(), "podman");
}

// Traces to: FR-VESSEL-INTEGRATION-020
#[test]
fn test_docker_runtime_debug() {
    let runtime = DockerRuntime::new();
    let debug = format!("{:?}", runtime);
    assert!(debug.contains("DockerRuntime"));
}

// Traces to: FR-VESSEL-INTEGRATION-021
#[test]
fn test_container_struct() {
    let container = Container {
        id: "test-id-123".to_string(),
        name: "my-container".to_string(),
        image: "nginx:latest".to_string(),
        status: ContainerStatus::Running,
    };

    assert_eq!(container.id, "test-id-123");
    assert_eq!(container.name, "my-container");
    assert!(container.is_running());
    assert!(!container.is_stopped());
}

// Traces to: FR-VESSEL-INTEGRATION-022
#[test]
fn test_container_short_id() {
    let container = Container {
        id: "abcdef123456789".to_string(),
        name: "test".to_string(),
        image: "nginx".to_string(),
        status: ContainerStatus::Running,
    };

    // short_id returns the full ID if < 12 chars, or first 12 chars
    assert_eq!(container.short_id(), "abcdef123456"); // First 12 chars
}

// Traces to: FR-VESSEL-INTEGRATION-023
#[test]
fn test_container_exited_status() {
    let container = Container {
        id: "123".to_string(),
        name: "exited-container".to_string(),
        image: "alpine".to_string(),
        status: ContainerStatus::Exited,
    };

    assert!(!container.is_running());
    assert!(container.is_stopped());
}

// Traces to: FR-VESSEL-INTEGRATION-024
#[test]
fn test_container_info_clone() {
    let info = ContainerInfo {
        id: "id-123".to_string(),
        name: "test".to_string(),
        image: "nginx".to_string(),
        status: "running".to_string(),
        created: "2024-01-01".to_string(),
    };

    let cloned = info.clone();
    assert_eq!(cloned.id, info.id);
    assert_eq!(cloned.name, info.name);
}

// Traces to: FR-VESSEL-INTEGRATION-025
#[test]
fn test_container_create_config_with_env() {
    let mut env = HashMap::new();
    env.insert("DATABASE_URL".to_string(), "postgres://localhost/test".to_string());
    env.insert("RUST_LOG".to_string(), "debug".to_string());

    let config = ContainerCreateConfig {
        image: "postgres:15".to_string(),
        name: Some("test-db".to_string()),
        env,
        ports: vec![PortMapping { host_port: 5432, container_port: 5432, protocol: Protocol::Tcp }],
        volumes: vec![VolumeMapping {
            host_path: "/tmp/data".to_string(),
            container_path: "/var/lib/postgresql/data".to_string(),
            read_only: false,
        }],
    };

    assert_eq!(config.env.len(), 2);
    assert!(config.env.contains_key("DATABASE_URL"));
    assert_eq!(config.ports.len(), 1);
    assert_eq!(config.volumes.len(), 1);
}

// ============================================================================
// Integration Tests - Data Type Coverage
// ============================================================================

// Traces to: FR-VESSEL-INTEGRATION-031
//
// Note: phenotype-vessel depends on `serde_yaml` (not `serde_json`) for serde
// format round-trips (see crates/pheno-plugin-vessel/Cargo.toml). The in-crate
// unit test at src/container.rs::test_container_status_serde_roundtrip uses
// serde_yaml for the same purpose. We mirror that here so the integration test
// compiles against the crate's actual dependency graph.
#[test]
fn test_container_status_all_variants_serde() {
    // ContainerStatus derives Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize
    // (with #[serde(rename_all = "lowercase")]) per src/container.rs.
    // Verify every variant round-trips through a real Serialize/Deserialize call.
    let variants = [
        ContainerStatus::Created,
        ContainerStatus::Running,
        ContainerStatus::Paused,
        ContainerStatus::Restarting,
        ContainerStatus::Removing,
        ContainerStatus::Exited,
        ContainerStatus::Dead,
    ];
    for v in variants {
        let serialized = serde_yaml::to_string(&v).expect("serialize ContainerStatus");
        let back: ContainerStatus =
            serde_yaml::from_str(&serialized).expect("deserialize ContainerStatus");
        assert_eq!(back, v, "serde roundtrip failed for variant");
    }
}

// Traces to: FR-VESSEL-INTEGRATION-032
#[test]
fn test_container_info_fields() {
    let info = ContainerInfo {
        id: "abc".to_string(),
        name: "x".to_string(),
        image: "nginx".to_string(),
        status: "running".to_string(),
        created: "2024-01-01".to_string(),
    };

    assert_eq!(info.id, "abc");
    assert_eq!(info.name, "x");
    assert_eq!(info.image, "nginx");
    assert_eq!(info.status, "running");
    assert_eq!(info.created, "2024-01-01");
}

// Traces to: FR-VESSEL-INTEGRATION-033
//
// Renamed from `test_container_info_clone` to `test_container_info_clone_all_fields`
// to avoid colliding with the existing test at line 439 (which only verifies
// 2 of 5 fields). This new test exercises a full field-by-field comparison so
// the Clone impl's coverage of every field is checked at the integration level.
#[test]
fn test_container_info_clone_all_fields() {
    let info = ContainerInfo {
        id: "id-123".to_string(),
        name: "test".to_string(),
        image: "nginx".to_string(),
        status: "running".to_string(),
        created: "2024-01-01".to_string(),
    };

    let cloned = info.clone();
    assert_eq!(cloned.id, info.id);
    assert_eq!(cloned.name, info.name);
    assert_eq!(cloned.image, info.image);
    assert_eq!(cloned.status, info.status);
    assert_eq!(cloned.created, info.created);
}

// Traces to: FR-VESSEL-INTEGRATION-034
#[test]
fn test_volume_mapping_creation_full() {
    let ro = VolumeMapping {
        host_path: "/srv".to_string(),
        container_path: "/data".to_string(),
        read_only: true,
    };

    assert_eq!(ro.host_path, "/srv");
    assert_eq!(ro.container_path, "/data");
    assert!(ro.read_only);

    let rw = VolumeMapping {
        host_path: "/srv".to_string(),
        container_path: "/data".to_string(),
        read_only: false,
    };

    assert_eq!(rw.host_path, "/srv");
    assert_eq!(rw.container_path, "/data");
    assert!(!rw.read_only);
}

// Traces to: FR-VESSEL-INTEGRATION-035
#[test]
fn test_image_struct_full() {
    let image = Image {
        id: "nginx:1.25".to_string(),
        name: "nginx".to_string(),
        tag: "1.25".to_string(),
        size: 100,
    };

    assert_eq!(image.id, "nginx:1.25");
    assert_eq!(image.name, "nginx");
    assert_eq!(image.tag, "1.25");
    assert_eq!(image.size, 100);

    // Display impl returns "name:tag" (see src/image.rs::impl Display for Image).
    assert_eq!(format!("{}", image), "nginx:1.25");

    // reference() method returns "name:tag" (see src/image.rs::Image::reference).
    assert_eq!(image.reference(), "nginx:1.25");
}

// Traces to: FR-VESSEL-INTEGRATION-026
#[tokio::test]
async fn test_client_start() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("nginx:latest", "test-start").await.unwrap();
    let result = client.start(&container.id).await;
    assert!(result.is_ok());
}

// Traces to: FR-VESSEL-INTEGRATION-027
#[tokio::test]
async fn test_client_stop() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("nginx:latest", "test-stop").await.unwrap();
    client.start(&container.id).await.unwrap();
    let result = client.stop(&container.id).await;
    assert!(result.is_ok());
}

// Traces to: FR-VESSEL-INTEGRATION-028
#[tokio::test]
async fn test_client_rm() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("nginx:latest", "test-rm").await.unwrap();
    let result = client.rm(&container.id).await;
    assert!(result.is_ok());
}

// Traces to: FR-VESSEL-INTEGRATION-029
#[tokio::test]
async fn test_client_logs() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("nginx:latest", "test-logs").await.unwrap();
    let logs: String = client.logs(&container.id).await.unwrap();
    assert!(!logs.is_empty());
}

// Traces to: FR-VESSEL-INTEGRATION-030
#[tokio::test]
async fn test_client_full_lifecycle() {
    let runtime = MockRuntime::new();
    let client = ContainerClient::new(runtime);

    let container = client.create("nginx:latest", "test-lifecycle").await.unwrap();
    assert!(client.start(&container.id).await.is_ok());
    assert!(client.stop(&container.id).await.is_ok());
    assert!(client.logs(&container.id).await.is_ok());
    assert!(client.rm(&container.id).await.is_ok());
}
