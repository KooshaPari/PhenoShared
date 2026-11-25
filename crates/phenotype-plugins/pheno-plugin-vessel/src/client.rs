//! # phenotype-vessel
//!
//! Container client for managing containers.

use super::container::{Container, ContainerStatus};
use super::image::Image;
use super::{ContainerRuntime, VesselError};
use crate::runtime::{ContainerCreateConfig, ContainerInfo};

/// Unified container client for all runtimes
#[derive(Debug)]
pub struct ContainerClient<R: ContainerRuntime> {
    runtime: R,
}

impl<R: ContainerRuntime> ContainerClient<R> {
    /// Create a new container client
    pub fn new(runtime: R) -> Self {
        Self { runtime }
    }

    /// Get the runtime name
    pub fn runtime_name(&self) -> &str {
        self.runtime.name()
    }

    /// Check if the runtime is available
    pub async fn is_available(&self) -> bool {
        self.runtime.is_available().await
    }

    /// List all containers
    pub async fn list_containers(&self) -> Result<Vec<ContainerInfo>, VesselError> {
        self.runtime.list_containers().await.map_err(VesselError::Runtime)
    }

    /// Pull an image
    pub async fn pull_image(&self, image: &str) -> Result<Image, VesselError> {
        self.runtime.pull_image(image).await.map_err(VesselError::Runtime)?;

        Ok(Image {
            id: image.to_string(),
            name: image.to_string(),
            tag: "latest".to_string(),
            size: 0,
        })
    }

    /// Remove an image
    pub async fn remove_image(&self, image: &str) -> Result<(), VesselError> {
        self.runtime.remove_image(image).await.map_err(VesselError::Runtime)
    }

    /// Create and start a container
    pub async fn run(&self, image: &str, name: &str) -> Result<Container, VesselError> {
        let config = ContainerCreateConfig {
            image: image.to_string(),
            name: Some(name.to_string()),
            env: Default::default(),
            ports: vec![],
            volumes: vec![],
        };

        let container_id =
            self.runtime.create_container(&config).await.map_err(VesselError::Runtime)?;

        self.runtime.start_container(&container_id).await.map_err(VesselError::Runtime)?;

        Ok(Container {
            id: container_id,
            name: name.to_string(),
            image: image.to_string(),
            status: ContainerStatus::Running,
        })
    }

    /// Create a container without starting it
    pub async fn create(&self, image: &str, name: &str) -> Result<Container, VesselError> {
        let config = ContainerCreateConfig {
            image: image.to_string(),
            name: Some(name.to_string()),
            env: Default::default(),
            ports: vec![],
            volumes: vec![],
        };

        let container_id =
            self.runtime.create_container(&config).await.map_err(VesselError::Runtime)?;

        Ok(Container {
            id: container_id,
            name: name.to_string(),
            image: image.to_string(),
            status: ContainerStatus::Created,
        })
    }

    /// Start a container
    pub async fn start(&self, id: &str) -> Result<(), VesselError> {
        self.runtime.start_container(id).await.map_err(VesselError::Runtime)
    }

    /// Stop a container
    pub async fn stop(&self, id: &str) -> Result<(), VesselError> {
        self.runtime.stop_container(id).await.map_err(VesselError::Runtime)
    }

    /// Remove a container
    pub async fn rm(&self, id: &str) -> Result<(), VesselError> {
        self.runtime.remove_container(id).await.map_err(VesselError::Runtime)
    }

    /// Get container logs
    pub async fn logs(&self, id: &str) -> Result<String, VesselError> {
        self.runtime.logs(id).await.map_err(VesselError::Runtime)
    }
}

/// Container operation errors
#[derive(Debug, thiserror::Error)]
pub enum ContainerError {
    #[error("Container not found: {0}")]
    NotFound(String),

    #[error("Container already exists: {0}")]
    AlreadyExists(String),

    #[error("Operation failed: {0}")]
    OperationFailed(String),
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::{ContainerCreateConfig, ContainerInfo, DockerRuntime};
    use async_trait::async_trait;
    use std::collections::HashMap;
    use std::sync::Mutex;

    /// MockRuntime: a configurable test double for `ContainerRuntime`.
    ///
    /// Each method returns a pre-configured `Result`. Defaults are
    /// happy-path (`Ok`). Tests override individual fields via the
    /// `with_*` builder methods to inject failures. This lets us
    /// exercise `ContainerClient`'s error mapping and return-value
    /// construction without spawning docker/podman subprocesses.
    struct MockRuntime {
        name: String,
        list_result: Result<Vec<ContainerInfo>, String>,
        pull_result: Result<(), String>,
        remove_image_result: Result<(), String>,
        create_result: Result<String, String>,
        start_result: Result<(), String>,
        stop_result: Result<(), String>,
        remove_container_result: Result<(), String>,
        logs_result: Result<String, String>,
        available: bool,
        removed_images: Mutex<Vec<String>>,
    }

    impl MockRuntime {
        /// Build a `MockRuntime` with the given name. `list_result` is
        /// supplied directly; all other methods default to a happy-path
        /// `Ok`. Use the `with_*` builder methods to override specific
        /// fields.
        fn new(name: &str, list_result: Result<Vec<ContainerInfo>, String>) -> Self {
            Self {
                name: name.to_string(),
                list_result,
                pull_result: Ok(()),
                remove_image_result: Ok(()),
                create_result: Ok("mock-container-id".to_string()),
                start_result: Ok(()),
                stop_result: Ok(()),
                remove_container_result: Ok(()),
                logs_result: Ok("mock log output".to_string()),
                available: true,
            removed_images: Mutex::new(Vec::new()),
            }
        }

        fn with_pull_result(mut self, r: Result<(), String>) -> Self {
            self.pull_result = r;
            self
        }

        fn with_remove_image_result(mut self, r: Result<(), String>) -> Self {
            self.remove_image_result = r;
            self
        }

        fn with_create_result(mut self, r: Result<String, String>) -> Self {
            self.create_result = r;
            self
        }

        fn with_start_result(mut self, r: Result<(), String>) -> Self {
            self.start_result = r;
            self
        }

        fn with_stop_result(mut self, r: Result<(), String>) -> Self {
            self.stop_result = r;
            self
        }

        fn with_remove_container_result(mut self, r: Result<(), String>) -> Self {
            self.remove_container_result = r;
            self
        }

        fn with_logs_result(mut self, r: Result<String, String>) -> Self {
            self.logs_result = r;
            self
        }

        fn with_available(mut self, b: bool) -> Self {
            self.available = b;
            self
        }

        /// Returns a snapshot of the image names that have been passed
        /// to `remove_image` on this runtime. Used by tests to verify
        /// the client propagated the call.
        fn list_removed_images(&self) -> Vec<String> {
            self.removed_images.lock().expect("removed_images mutex poisoned").clone()
        }
    }

    #[async_trait]
    impl ContainerRuntime for MockRuntime {
        fn name(&self) -> &str {
            &self.name
        }

        async fn is_available(&self) -> bool {
            self.available
        }

        async fn list_containers(&self) -> Result<Vec<ContainerInfo>, String> {
            self.list_result.clone()
        }

        async fn pull_image(&self, _image: &str) -> Result<(), String> {
            self.pull_result.clone()
        }

        async fn remove_image(&self, image: &str) -> Result<(), String> {
            self.removed_images
                .lock()
                .expect("removed_images mutex poisoned")
                .push(image.to_string());
            self.remove_image_result.clone()
        }

        async fn create_container(
            &self,
            _config: &ContainerCreateConfig,
        ) -> Result<String, String> {
            self.create_result.clone()
        }

        async fn start_container(&self, _id: &str) -> Result<(), String> {
            self.start_result.clone()
        }

        async fn stop_container(&self, _id: &str) -> Result<(), String> {
            self.stop_result.clone()
        }

        async fn remove_container(&self, _id: &str) -> Result<(), String> {
            self.remove_container_result.clone()
        }

        async fn logs(&self, _id: &str) -> Result<String, String> {
            self.logs_result.clone()
        }
    }

    #[test]
    fn test_container_client_new() {
        let client = ContainerClient::new(DockerRuntime::new());
        assert_eq!(client.runtime_name(), "docker");
    }

    #[test]
    fn test_container_client_runtime_name() {
        let client = ContainerClient::new(DockerRuntime::new());
        assert_eq!(client.runtime_name(), "docker");
        assert!(!client.runtime_name().is_empty());
    }

    #[test]
    fn test_container_error_display() {
        let not_found = ContainerError::NotFound("my-container".to_string());
        let not_found_str = format!("{}", not_found);
        assert!(not_found_str.contains("not found"));
        assert!(not_found_str.contains("my-container"));

        let already_exists = ContainerError::AlreadyExists("my-container".to_string());
        let already_exists_str = format!("{}", already_exists);
        assert!(already_exists_str.contains("already exists"));
        assert!(already_exists_str.contains("my-container"));

        let operation_failed = ContainerError::OperationFailed("something broke".to_string());
        let operation_failed_str = format!("{}", operation_failed);
        assert!(operation_failed_str.contains("failed"));
        assert!(operation_failed_str.contains("something broke"));
    }

    #[test]
    fn test_container_error_from() {
        let container_err = ContainerError::NotFound("abc".to_string());
        let v: VesselError = container_err.into();
        match v {
            VesselError::Container(ContainerError::NotFound(s)) => {
                assert_eq!(s, "abc");
            }
            other => panic!("Expected VesselError::Container(NotFound), got {:?}", other),
        }
    }

    #[test]
    fn test_container_client_default_runtime() {
        let client = ContainerClient::new(DockerRuntime);
        assert_eq!(client.runtime_name(), "docker");
    }

    #[tokio::test]
    async fn test_container_client_is_available_returns_bool() {
        let client = ContainerClient::new(DockerRuntime);
        let _: bool = client.is_available().await;
    }

    // -----------------------------------------------------------------
    // MockRuntime-backed tests: exercise ContainerClient behavior
    // (error mapping, return-value construction) without requiring
    // docker/podman subprocesses to exist on the test host.
    // -----------------------------------------------------------------

    #[tokio::test]
    async fn test_mock_runtime_construction() {
        let mock = MockRuntime::new("test", Ok(vec![]));
        assert_eq!(mock.name(), "test");
        assert!(mock.is_available().await);
    }

    #[tokio::test]
    async fn test_client_list_containers_success() {
        let info = ContainerInfo {
            id: "abc".to_string(),
            name: "web".to_string(),
            image: "nginx:1.25".to_string(),
            status: "running".to_string(),
            created: "2024-01-01".to_string(),
        };
        let mock = MockRuntime::new("test", Ok(vec![info]));
        let client = ContainerClient::new(mock);

        let result = client
            .list_containers()
            .await
            .expect("list_containers should succeed");

        assert_eq!(result.len(), 1);
        assert_eq!(result[0].id, "abc");
        assert_eq!(result[0].name, "web");
        assert_eq!(result[0].image, "nginx:1.25");
        assert_eq!(result[0].status, "running");
        assert_eq!(result[0].created, "2024-01-01");
    }

    #[tokio::test]
    async fn test_client_list_containers_runtime_error() {
        let mock = MockRuntime::new("test", Err("daemon down".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.list_containers().await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "daemon down"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_pull_image_success() {
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let image = client
            .pull_image("nginx:1.25")
            .await
            .expect("pull_image should succeed");

        // Verifies the client's Image construction (client.rs:38-47):
        // the requested ref is used for both id and name, the tag is
        // hard-coded to "latest", and the size is 0.
        assert_eq!(image.id, "nginx:1.25");
        assert_eq!(image.name, "nginx:1.25");
        assert_eq!(image.tag, "latest");
        assert_eq!(image.size, 0);
    }

    #[tokio::test]
    async fn test_client_pull_image_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_pull_result(Err("pull failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.pull_image("nginx:1.25").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "pull failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_run_creates_running_container() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Ok("id123".to_string()));
        let client = ContainerClient::new(mock);

        let container = client
            .run("nginx:1.25", "web")
            .await
            .expect("run should succeed");

        // run() should call create_container (returning the id from the
        // mock) and start_container (Ok), then build a Container with
        // ContainerStatus::Running.
        assert_eq!(container.id, "id123");
        assert_eq!(container.name, "web");
        assert_eq!(container.image, "nginx:1.25");
        assert_eq!(container.status, ContainerStatus::Running);
    }

    #[tokio::test]
    async fn test_client_run_create_failure() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Err("create failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.run("nginx:1.25", "web").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "create failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_create_returns_created_status() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Ok("id456".to_string()));
        let client = ContainerClient::new(mock);

        let container = client
            .create("nginx:1.25", "web")
            .await
            .expect("create should succeed");

        // create() does NOT call start_container, so the returned
        // Container must be ContainerStatus::Created, not Running.
        assert_eq!(container.id, "id456");
        assert_eq!(container.name, "web");
        assert_eq!(container.image, "nginx:1.25");
        assert_eq!(container.status, ContainerStatus::Created);
        assert_ne!(container.status, ContainerStatus::Running);
    }

    #[tokio::test]
    async fn test_client_remove_container_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_remove_container_result(Err("rm failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.rm("abc").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "rm failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_logs_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_logs_result(Err("log fetch failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.logs("abc").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "log fetch failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_remove_image_success() {
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let result = client
            .remove_image("nginx:1.25")
            .await
            .expect("remove_image should succeed");

        // The success variant carries no payload; just confirm we got Ok.
        let _: () = result;
    }

    #[tokio::test]
    async fn test_client_remove_image_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_remove_image_result(Err("image in use".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.remove_image("nginx:1.25").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "image in use"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_start_container_success() {
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let result = client
            .start("abc123")
            .await
            .expect("start should succeed");

        // The success variant carries no payload; just confirm we got Ok.
        let _: () = result;
    }

    #[tokio::test]
    async fn test_client_start_container_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_start_result(Err("container not found".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.start("abc123").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "container not found"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_stop_container_success() {
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let result = client
            .stop("abc123")
            .await
            .expect("stop should succeed");

        // The success variant carries no payload; just confirm we got Ok.
        let _: () = result;
    }

    #[tokio::test]
    async fn test_client_stop_container_runtime_error() {
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_stop_result(Err("container already stopped".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.stop("abc123").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "container already stopped"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_create_with_config_success() {
        // Build a `ContainerCreateConfig` (as the task requests) and pass
        // its image/name through to the existing `create(image, name)`
        // entry point, which internally constructs the same config and
        // delegates to the runtime's `create_container`.
        let config = ContainerCreateConfig {
            image: "nginx:1.25".to_string(),
            name: Some("web".to_string()),
            env: HashMap::new(),
            ports: vec![],
            volumes: vec![],
        };
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Ok("id-xyz".to_string()));
        let client = ContainerClient::new(mock);

        let container = client
            .create(&config.image, config.name.as_deref().unwrap())
            .await
            .expect("create should succeed");

        // Verifies the client's Container construction (client.rs:78-96):
        // the id comes from the runtime's create_container, name + image
        // come from the args, and the status is Created (not Running,
        // since `create` does NOT call start_container).
        assert_eq!(container.id, "id-xyz");
        assert_eq!(container.name, "web");
        assert_eq!(container.image, "nginx:1.25");
        assert_eq!(container.status, ContainerStatus::Created);
    }

    #[tokio::test]
    async fn test_client_create_with_config_runtime_error() {
        let config = ContainerCreateConfig {
            image: "nginx:1.25".to_string(),
            name: Some("web".to_string()),
            env: HashMap::new(),
            ports: vec![],
            volumes: vec![],
        };
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Err("create failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client
            .create(&config.image, config.name.as_deref().unwrap())
            .await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "create failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_is_available_returns_false() {
        // Build a mock whose runtime reports itself as unavailable.
        let mock = MockRuntime::new("test", Ok(vec![])).with_available(false);
        let client = ContainerClient::new(mock);

        let available = client.is_available().await;
        assert!(
            !available,
            "is_available should propagate the runtime's `false` to the client"
        );
    }

    #[tokio::test]
    async fn test_client_list_containers_empty() {
        // MockRuntime::list_containers returns Ok(vec![]); the client
        // must surface that as Ok(empty Vec) without mutation.
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let result = client
            .list_containers()
            .await
            .expect("list_containers should succeed");

        assert!(
            result.is_empty(),
            "expected empty container list, got {:?}",
            result
        );
        assert_eq!(result.len(), 0);
    }

    #[tokio::test]
    async fn test_client_pull_image_with_complex_name() {
        // The image name "docker.io/library/nginx:1.25-alpine" carries a
        // registry prefix, a library path, and a versioned tag. The
        // client's pull_image must preserve the entire string as the
        // Image id (it is just echoed back from the input ref).
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let image = client
            .pull_image("docker.io/library/nginx:1.25-alpine")
            .await
            .expect("pull_image should succeed");

        assert_eq!(image.id, "docker.io/library/nginx:1.25-alpine");
        assert_eq!(image.name, "docker.io/library/nginx:1.25-alpine");
    }

    #[tokio::test]
    async fn test_client_run_start_failure() {
        // Create succeeds with "id-ok", but start fails. The error from
        // start_container must propagate as VesselError::Runtime, not
        // be swallowed by the successful create step.
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Ok("id-ok".to_string()))
            .with_start_result(Err("start failed".to_string()));
        let client = ContainerClient::new(mock);

        let result = client.run("nginx:1.25", "web").await;
        match result {
            Err(VesselError::Runtime(s)) => assert_eq!(s, "start failed"),
            Err(other) => panic!("expected VesselError::Runtime, got {:?}", other),
            Ok(_) => panic!("expected error from start_container, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_client_create_uses_image_id_as_container_id_when_create_returns_id() {
        // The client's `create` method should set the resulting
        // Container's id to whatever the runtime's create_container
        // returns (i.e., the runtime's id, not the image name).
        let mock = MockRuntime::new("test", Ok(vec![]))
            .with_create_result(Ok("rt-generated-id".to_string()));
        let client = ContainerClient::new(mock);

        let container = client
            .create("nginx:1.25", "web")
            .await
            .expect("create should succeed");

        assert_eq!(container.id, "rt-generated-id");
        assert_eq!(container.name, "web");
        assert_eq!(container.image, "nginx:1.25");
        assert_eq!(container.status, ContainerStatus::Created);
    }

    #[tokio::test]
    async fn test_mock_runtime_can_be_built_for_each_method_independently() {
        // Build a MockRuntime with a unique per-method result, then
        // exercise every trait method and verify each one returns its
        // own configured value (and not, e.g., a default from some
        // other method). Covers all 10 trait methods: name, is_available,
        // list_containers, pull_image, remove_image, create_container,
        // start_container, stop_container, remove_container, logs.
        let mock = MockRuntime::new(
            "custom-name",
            Ok(vec![ContainerInfo {
                id: "default-list-id".to_string(),
                name: "default-list-name".to_string(),
                image: "default-list-img".to_string(),
                status: "default-list-status".to_string(),
                created: "default-list-created".to_string(),
            }]),
        )
        .with_pull_result(Ok(()))
        .with_remove_image_result(Ok(()))
        .with_create_result(Ok("custom-create-id".to_string()))
        .with_start_result(Ok(()))
        .with_stop_result(Ok(()))
        .with_remove_container_result(Ok(()))
        .with_logs_result(Ok("custom-log-output".to_string()))
        .with_available(false);

        let client = ContainerClient::new(mock);

        // name() — sync method on the trait.
        assert_eq!(client.runtime_name(), "custom-name");

        // is_available — async method returning bool.
        assert!(
            !client.is_available().await,
            "is_available should be the configured false"
        );

        // list_containers — must return the configured ContainerInfo.
        let list = client
            .list_containers()
            .await
            .expect("list should succeed");
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].id, "default-list-id");
        assert_eq!(list[0].name, "default-list-name");
        assert_eq!(list[0].image, "default-list-img");
        assert_eq!(list[0].status, "default-list-status");
        assert_eq!(list[0].created, "default-list-created");

        // pull_image — the returned Image id/name come from the input ref.
        let image = client
            .pull_image("custom-img:1.0")
            .await
            .expect("pull should succeed");
        assert_eq!(image.id, "custom-img:1.0");
        assert_eq!(image.name, "custom-img:1.0");
        assert_eq!(image.tag, "latest");

        // remove_image — the runtime should record the call.
        client
            .remove_image("custom-img:1.0")
            .await
            .expect("remove_image should succeed");
        let removed = client.runtime.list_removed_images();
        assert!(
            removed.contains(&"custom-img:1.0".to_string()),
            "expected runtime to record removal of 'custom-img:1.0', got {:?}",
            removed
        );

        // run() exercises create_container + start_container; verify
        // the runtime-generated id propagates into the Container.
        let container = client
            .run("custom-img:1.0", "custom-name")
            .await
            .expect("run should succeed");
        assert_eq!(container.id, "custom-create-id");
        assert_eq!(container.name, "custom-name");
        assert_eq!(container.image, "custom-img:1.0");
        assert_eq!(container.status, ContainerStatus::Running);

        // start/stop/rm/logs — verify each returns its configured value.
        client
            .start("custom-create-id")
            .await
            .expect("start should succeed");
        client
            .stop("custom-create-id")
            .await
            .expect("stop should succeed");
        client
            .rm("custom-create-id")
            .await
            .expect("rm should succeed");
        let logs = client
            .logs("custom-create-id")
            .await
            .expect("logs should succeed");
        assert_eq!(logs, "custom-log-output");
    }

    #[tokio::test]
    async fn test_client_pull_image_preserves_image_id_field() {
        // The image id field on the returned Image must be exactly the
        // string the user requested pulled.
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        let image = client
            .pull_image("myimage:1.0")
            .await
            .expect("pull_image should succeed");

        assert_eq!(image.id, "myimage:1.0");
    }

    #[tokio::test]
    async fn test_client_remove_image_with_image_name() {
        // remove_image should pass the requested image name to the
        // runtime, and the runtime should record that it was called
        // with that exact name.
        let mock = MockRuntime::new("test", Ok(vec![]));
        let client = ContainerClient::new(mock);

        client
            .remove_image("nginx:1.25")
            .await
            .expect("remove_image should succeed");

        // The runtime's recorded list of removed image names should
        // contain the name we just passed in.
        let removed = client.runtime.list_removed_images();
        assert!(
            removed.contains(&"nginx:1.25".to_string()),
            "expected runtime to record removal of 'nginx:1.25', got {:?}",
            removed
        );
    }
}
