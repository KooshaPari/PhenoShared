//! Docker orchestration module.
//!
//! Placeholder for Phase-2 extraction from KVirtualStage:
//! - orchestration.rs: process-compose + container lifecycle
//! - networking.rs: port mapping, bridge configuration
//! - resource_limits.rs: CPU, memory, disk quotas

/// Docker container orchestrator trait.
pub trait DockerOrchestrator {
    /// Create and start a container.
    fn start_container(&self, image: &str, config: ContainerConfig) -> Result<String, String>;

    /// Stop and remove a container.
    fn stop_container(&self, container_id: &str) -> Result<(), String>;

    /// Get container resource usage.
    fn get_resource_usage(&self, container_id: &str) -> Result<ResourceSnapshot, String>;
}

/// Container configuration for orchestration.
#[derive(Debug, Clone)]
pub struct ContainerConfig {
    pub cpu_limit: f64,
    pub memory_limit_mb: u64,
    pub disk_limit_mb: Option<u64>,
    pub ports: Vec<PortMapping>,
}

/// Port mapping for container networking.
#[derive(Debug, Clone)]
pub struct PortMapping {
    pub host_port: u16,
    pub container_port: u16,
}

/// Resource snapshot from container introspection.
#[derive(Debug, Clone)]
pub struct ResourceSnapshot {
    pub cpu_percent: f64,
    pub memory_mb: u64,
    pub disk_mb: Option<u64>,
}

/// Unimplemented stub returned by [`StubDockerOrchestrator`].
///
/// Phase-2 extraction from KVirtualStage is tracked in
/// `docs/EXTRACTION_PLAN.md` § Phase 2. Until that work lands, callers
/// that try to use Docker orchestration will receive this error rather
/// than silently receiving empty/zero values.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DockerUnimplemented(pub &'static str);

impl std::fmt::Display for DockerUnimplemented {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "DockerOrchestrator::{} is not yet implemented \
             (Phase-2 KVirtualStage extraction pending — see docs/EXTRACTION_PLAN.md)",
            self.0
        )
    }
}

impl std::error::Error for DockerUnimplemented {}

/// Stub orchestrator that fails loudly on every call.
///
/// Callers receive a [`DockerUnimplemented`] error that names the method
/// and points to the extraction plan, so accidental reliance on default
/// zero/empty values is surfaced immediately rather than silently
/// passing through.
pub struct StubDockerOrchestrator;

impl DockerOrchestrator for StubDockerOrchestrator {
    fn start_container(&self, _image: &str, _config: ContainerConfig) -> Result<String, String> {
        Err(DockerUnimplemented("start_container").to_string())
    }

    fn stop_container(&self, _container_id: &str) -> Result<(), String> {
        Err(DockerUnimplemented("stop_container").to_string())
    }

    fn get_resource_usage(&self, _container_id: &str) -> Result<ResourceSnapshot, String> {
        Err(DockerUnimplemented("get_resource_usage").to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stub_start_container_returns_unimplemented_error() {
        let orch = StubDockerOrchestrator;
        let err = orch
            .start_container(
                "ubuntu:latest",
                ContainerConfig {
                    cpu_limit: 1.0,
                    memory_limit_mb: 512,
                    disk_limit_mb: None,
                    ports: vec![],
                },
            )
            .unwrap_err();
        assert!(err.contains("start_container"), "err = {err}");
        assert!(err.contains("EXTRACTION_PLAN"), "err = {err}");
    }

    #[test]
    fn stub_stop_container_returns_unimplemented_error() {
        let orch = StubDockerOrchestrator;
        let err = orch.stop_container("abc123").unwrap_err();
        assert!(err.contains("stop_container"), "err = {err}");
    }

    #[test]
    fn stub_get_resource_usage_returns_unimplemented_error() {
        let orch = StubDockerOrchestrator;
        let err = orch.get_resource_usage("abc123").unwrap_err();
        assert!(err.contains("get_resource_usage"), "err = {err}");
    }

    #[test]
    fn docker_unimplemented_display_contains_method_name() {
        let e = DockerUnimplemented("test_method");
        assert!(e.to_string().contains("test_method"));
    }
}
