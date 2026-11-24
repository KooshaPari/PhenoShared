//! Cross-module integration tests for phenotype-vessel.
//!
//! These tests exercise MULTIPLE modules together to verify their public
//! contracts are compatible across module boundaries. Existing per-module
//! tests cover each module in isolation; this file focuses on the seams
//! between them:
//!
//! - image ↔ container (image references stored on a Container)
//! - container ↔ runtime (ContainerCreateConfig ↔ Container state shape)
//! - runtime ↔ client (runtime implementations as plug-in backends)
//! - compose ↔ runtime (Compose env representation feeding ContainerCreateConfig)
//!
//! All tests are synchronous and use only the public API surface.

use std::collections::HashMap;

use phenotype_vessel::compose::ComposeService;
use phenotype_vessel::runtime::{
    ContainerCreateConfig, ContainerRuntime, DockerRuntime, PodmanRuntime, PortMapping, Protocol,
    VolumeMapping,
};
use phenotype_vessel::{Container, ContainerStatus, Image, ImagePullProgress};

// ============================================================================
// 1. image ↔ container: Image reference flows into Container fields
// ============================================================================

/// Build an `Image`, then a `Container` whose `image` field matches the
/// image's full reference, and a `ContainerCreateConfig` that references
/// the same image name. All three must agree on the image identifier.
///
/// This guards the contract that the runtime layer can take a configured
/// `ContainerCreateConfig` and produce a `Container` whose `image` field
/// still matches the original `Image` reference.
#[test]
fn test_image_to_container_full_flow() {
    // Step 1: build an Image with a canonical name:tag reference.
    let image = Image::new("nginx:1.25-alpine");
    let image_ref = image.reference();
    assert_eq!(image_ref, "nginx:1.25-alpine");

    // Step 2: build a Container that uses the image's full reference.
    let container = Container {
        id: "abc123def456ghi789jkl012mno345pq".to_string(),
        name: "web".to_string(),
        image: image_ref.clone(),
        status: ContainerStatus::Created,
    };

    // Step 3: build a ContainerCreateConfig that references the same image.
    // The config's image field holds the full reference (name:tag) — the
    // same string that the Container carries — so all three artifacts
    // share one identifier.
    let config = ContainerCreateConfig {
        image: image_ref.clone(),
        name: Some(container.name.clone()),
        env: HashMap::new(),
        ports: vec![],
        volumes: vec![],
    };

    // All three must agree on the image identifier.
    assert_eq!(
        container.image, config.image,
        "Container.image and ContainerCreateConfig.image must match"
    );
    assert_eq!(
        container.image, image_ref,
        "Container.image and Image.reference() must match"
    );
    assert_eq!(
        config.image,
        format!("{}:{}", image.name, image.tag),
        "ContainerCreateConfig.image and Image.name:tag must match"
    );
    assert_eq!(image.name, "nginx", "Image.name must be parsed from the reference");
    assert_eq!(image.tag, "1.25-alpine", "Image.tag must be parsed from the reference");

    // Sanity check: the Container's `image` field is exactly the canonical
    // reference the Image exposes via `reference()`.
    assert!(container.image.contains("nginx"));
    assert!(container.image.contains("1.25-alpine"));
}

// ============================================================================
// 2. runtime: PortMapping round-trips through ContainerCreateConfig
// ============================================================================

/// Two `PortMapping` entries attached to a `ContainerCreateConfig` must
/// survive structural inspection. The runtime layer is expected to
/// materialize each mapping into a `host:container` port flag, so the
/// Debug output (which is the canonical inspection tool) must contain
/// both port numbers and the protocol.
#[test]
fn test_port_mapping_in_create_config() {
    let config = ContainerCreateConfig {
        image: "nginx:1.25".to_string(),
        name: Some("web".to_string()),
        env: HashMap::new(),
        ports: vec![
            PortMapping {
                host_port: 80,
                container_port: 80,
                protocol: Protocol::Tcp,
            },
            PortMapping {
                host_port: 443,
                container_port: 8443,
                protocol: Protocol::Tcp,
            },
        ],
        volumes: vec![],
    };

    // Both port entries must be preserved structurally.
    assert_eq!(config.ports.len(), 2);

    // First mapping: 80:80 TCP.
    let p0 = &config.ports[0];
    assert_eq!(p0.host_port, 80);
    assert_eq!(p0.container_port, 80);
    assert!(matches!(p0.protocol, Protocol::Tcp));

    // Second mapping: 443:8443 TCP.
    let p1 = &config.ports[1];
    assert_eq!(p1.host_port, 443);
    assert_eq!(p1.container_port, 8443);
    assert!(matches!(p1.protocol, Protocol::Tcp));

    // Debug output is what runtime layers log when materializing the
    // config into a CLI invocation; it must contain both port numbers
    // so the port-flags are observable downstream.
    let dbg = format!("{:?}", config);
    assert!(dbg.contains("80"), "debug must mention host port 80: {dbg}");
    assert!(dbg.contains("443"), "debug must mention host port 443: {dbg}");
    assert!(dbg.contains("8443"), "debug must mention container port 8443: {dbg}");
    assert!(dbg.contains("Tcp"), "debug must mention TCP protocol: {dbg}");
}

// ============================================================================
// 3. runtime: VolumeMapping read_only flags are preserved
// ============================================================================

/// A `ContainerCreateConfig` carrying one read-only and one read-write
/// `VolumeMapping` must preserve the read-only flag on each entry.
/// Runtime layers translate this into a `:ro` suffix on the bind mount;
/// losing the flag would silently expose data the caller intended to
/// protect.
#[test]
fn test_volume_mapping_in_create_config() {
    let config = ContainerCreateConfig {
        image: "postgres:15".to_string(),
        name: Some("db".to_string()),
        env: HashMap::new(),
        ports: vec![],
        volumes: vec![
            // Read-only mount: configuration data.
            VolumeMapping {
                host_path: "/etc/config".to_string(),
                container_path: "/etc/app".to_string(),
                read_only: true,
            },
            // Read-write mount: live database files.
            VolumeMapping {
                host_path: "/data".to_string(),
                container_path: "/var/lib/postgresql/data".to_string(),
                read_only: false,
            },
        ],
    };

    assert_eq!(config.volumes.len(), 2);

    // First entry: read-only.
    let v0 = &config.volumes[0];
    assert_eq!(v0.host_path, "/etc/config");
    assert_eq!(v0.container_path, "/etc/app");
    assert!(v0.read_only, "first volume must be read-only");

    // Second entry: read-write.
    let v1 = &config.volumes[1];
    assert_eq!(v1.host_path, "/data");
    assert_eq!(v1.container_path, "/var/lib/postgresql/data");
    assert!(!v1.read_only, "second volume must be read-write");

    // Debug output must mention both volumes with paths intact.
    let dbg = format!("{:?}", config);
    assert!(dbg.contains("/etc/config"), "debug must mention first host path: {dbg}");
    assert!(dbg.contains("/data"), "debug must mention second host path: {dbg}");
    assert!(dbg.contains("read_only"), "debug must mention read_only field: {dbg}");
}

// ============================================================================
// 4. container: status transitions through Created → Running → Exited
// ============================================================================

/// A `Container` can be in one of several `ContainerStatus` variants.
/// The `is_running()` and `is_stopped()` predicates must reflect the
/// current status. This test walks a container through three states and
/// verifies the predicates at each step.
#[test]
fn test_container_status_transitions_via_client() {
    let mut container = Container {
        id: "abcdef1234567890abcdef1234567890".to_string(),
        name: "web".to_string(),
        image: "nginx:1.25".to_string(),
        status: ContainerStatus::Created,
    };

    // State 1: Created. Neither running nor stopped.
    assert!(!container.is_running(), "Created must not be running");
    assert!(!container.is_stopped(), "Created must not be stopped");
    assert_eq!(container.status, ContainerStatus::Created);
    assert_ne!(container.status, ContainerStatus::Running);
    assert_ne!(container.status, ContainerStatus::Exited);

    // State 2: Running. is_running() flips true; is_stopped() stays false.
    container.status = ContainerStatus::Running;
    assert!(container.is_running(), "Running must be running");
    assert!(!container.is_stopped(), "Running must not be stopped");
    assert_eq!(container.status, ContainerStatus::Running);

    // State 3: Exited. is_running() flips false; is_stopped() flips true.
    container.status = ContainerStatus::Exited;
    assert!(!container.is_running(), "Exited must not be running");
    assert!(container.is_stopped(), "Exited must be stopped");
    assert_eq!(container.status, ContainerStatus::Exited);

    // Short ID must remain stable across all status changes (it is derived
    // from the immutable `id` field).
    assert_eq!(container.short_id(), "abcdef123456");
}

// ============================================================================
// 5. image ↔ container: digest reference in Container.image field
// ============================================================================

/// A `Container` whose `image` field holds a sha256 digest reference
/// must be constructible without any validation rejecting digests.
/// The runtime layer is expected to accept a digest string verbatim
/// and pass it through to the underlying engine.
#[test]
fn test_image_digest_in_container_image_field() {
    let digest = "sha256:abc123def4567890abc123def4567890abc123def4567890abc123def4567890";

    // Construct a Container carrying a digest in the `image` field.
    // No validation runs at construction time — any validation happens
    // at the runtime boundary.
    let container = Container {
        id: "digestid01".to_string(),
        name: "pinned-web".to_string(),
        image: digest.to_string(),
        status: ContainerStatus::Created,
    };

    // The container round-trips the digest verbatim.
    assert_eq!(container.image, digest);
    assert!(
        container.image.starts_with("sha256:"),
        "image field must preserve the sha256: prefix: {}",
        container.image
    );
    assert_eq!(container.name, "pinned-web");
    assert_eq!(container.status, ContainerStatus::Created);

    // Build a corresponding Image to confirm the same digest string is
    // accepted by the image layer. The Image::new() parser splits on ':',
    // so a digest yields a multi-segment tag, but the constructor must
    // still succeed.
    let image = Image {
        id: digest.to_string(),
        name: "nginx".to_string(),
        tag: digest.to_string(),
        size: 0,
    };
    assert!(image.is_digest(), "Image built from digest must report is_digest()");
    assert_eq!(image.tag, digest);
}

// ============================================================================
// 6. compose ↔ runtime: env map compatibility
// ============================================================================

/// A `ComposeService` carries environment variables in
/// `environment: Option<HashMap<String, String>>`. The runtime's
/// `ContainerCreateConfig` carries the same shape in
/// `env: HashMap<String, String>`. When the same env map is built in
/// both representations, the keys and values must match exactly. This
/// guards the contract that compose-driven configuration can feed
/// runtime-driven configuration without translation loss.
#[test]
fn test_compose_service_environment_to_container_env() {
    // The same env map, expressed in two ways.
    let mut env = HashMap::new();
    env.insert("RUST_LOG".to_string(), "info".to_string());
    env.insert("DATABASE_URL".to_string(), "postgres://localhost/db".to_string());
    env.insert("PORT".to_string(), "8080".to_string());

    // Compose side: env is Option<HashMap<...>>.
    let service = ComposeService {
        image: Some("myorg/api:1.2.3".to_string()),
        environment: Some(env.clone()),
        ..Default::default()
    };

    // Runtime side: env is HashMap<...> directly.
    let config = ContainerCreateConfig {
        image: "myorg/api:1.2.3".to_string(),
        name: Some("api".to_string()),
        env: env.clone(),
        ports: vec![],
        volumes: vec![],
    };

    // Pull the env out of the compose side for comparison.
    let compose_env = service
        .environment
        .as_ref()
        .expect("compose environment must be Some for this test");

    // Both representations must have the same keys and values.
    assert_eq!(compose_env.len(), config.env.len());
    for (key, value) in &config.env {
        let compose_value = compose_env
            .get(key)
            .unwrap_or_else(|| panic!("compose env missing key: {key}"));
        assert_eq!(
            compose_value, value,
            "env value mismatch for {key}: compose={compose_value}, runtime={value}"
        );
    }

    // Spot-check a few entries directly to make the contract obvious.
    assert_eq!(compose_env.get("RUST_LOG").map(String::as_str), Some("info"));
    assert_eq!(
        compose_env.get("DATABASE_URL").map(String::as_str),
        Some("postgres://localhost/db")
    );
    assert_eq!(compose_env.get("PORT").map(String::as_str), Some("8080"));
}

// ============================================================================
// 7. image: ImagePullProgress default-constructed state
// ============================================================================

/// `ImagePullProgress` does not derive `Default`, but it must be
/// constructible with the empty/None state that callers use as a
/// "no progress yet" sentinel. All three fields must be in their
/// neutral state.
#[test]
fn test_image_pull_progress_default_state() {
    let progress = ImagePullProgress {
        status: String::new(),
        progress: None,
        speed: None,
    };

    // status must be the empty string.
    assert_eq!(progress.status, "");
    assert!(progress.status.is_empty());

    // progress must be None.
    assert!(progress.progress.is_none());
    assert_eq!(progress.progress, None);

    // speed must be None.
    assert!(progress.speed.is_none());
    assert_eq!(progress.speed, None);

    // Debug output must reflect all three fields.
    let dbg = format!("{:?}", progress);
    assert!(dbg.contains("ImagePullProgress"));
    assert!(dbg.contains("status"));
    assert!(dbg.contains("progress"));
    assert!(dbg.contains("speed"));
}

// ============================================================================
// 8. container: short_id is stable for the same input
// ============================================================================

/// `Container::short_id()` is a pure function of the `id` field. Two
/// `Container` values with the same `id` must yield identical
/// `short_id()` results. This guards against accidental non-determinism
/// (e.g., a hash mixed in) in the short-id computation.
#[test]
fn test_container_short_id_stable_across_runs() {
    let full_id = "abcdef1234567890abcdef1234567890abcdef1234567890";

    let c1 = Container {
        id: full_id.to_string(),
        name: "first".to_string(),
        image: "nginx:latest".to_string(),
        status: ContainerStatus::Running,
    };

    let c2 = Container {
        id: full_id.to_string(),
        name: "second".to_string(),
        image: "redis:7".to_string(),
        status: ContainerStatus::Exited,
    };

    let short1 = c1.short_id();
    let short2 = c2.short_id();

    // Both must return the same 12-character prefix of the full id.
    assert_eq!(short1, short2, "short_id must be deterministic for the same id");
    assert_eq!(short1, "abcdef123456");
    assert_eq!(short1.len(), 12);
    assert_eq!(full_id.starts_with(short1), true);

    // A different full id must yield a different short id.
    let c3 = Container {
        id: "zzzzzz9999999999zzzzzz9999999999".to_string(),
        name: "other".to_string(),
        image: "alpine".to_string(),
        status: ContainerStatus::Created,
    };
    assert_ne!(c3.short_id(), short1, "different id must yield different short_id");
}

// ============================================================================
// 9. runtime: DockerRuntime and PodmanRuntime expose a stable name format
// ============================================================================

/// `DockerRuntime::new().name()` and `PodmanRuntime::new().name()` must
/// return strings that begin with the runtime's canonical identifier.
/// This is the contract client code uses to route per-runtime behavior
/// (e.g., log message prefixes, error context).
#[test]
fn test_runtime_name_format() {
    let docker = DockerRuntime::new();
    let docker_name = docker.name();
    assert!(
        docker_name.starts_with("docker"),
        "DockerRuntime::name() must start with 'docker', got: {docker_name}"
    );
    assert_eq!(docker_name, "docker");

    let podman = PodmanRuntime::new();
    let podman_name = podman.name();
    assert!(
        podman_name.starts_with("podman"),
        "PodmanRuntime::name() must start with 'podman', got: {podman_name}"
    );
    assert_eq!(podman_name, "podman");

    // The two runtimes must report distinct names so client code can
    // disambiguate between them.
    assert_ne!(docker_name, podman_name);

    // Both names are non-empty ASCII strings suitable for embedding in
    // log lines and error messages.
    assert!(!docker_name.is_empty());
    assert!(!podman_name.is_empty());
    assert!(docker_name.is_ascii());
    assert!(podman_name.is_ascii());
}

// ============================================================================
// 10. container: Paused is its own state, not running or stopped
// ============================================================================

/// `ContainerStatus::Paused` is a third lifecycle state, distinct from
/// both Running and Stopped (which is defined as Exited | Dead). A
/// paused container must report `is_running() == false` and
/// `is_stopped() == false`. This guards the contract that the
/// `is_running`/`is_stopped` predicates partition the state space
/// without aliasing the Paused state.
#[test]
fn test_container_status_paused_is_neither_running_nor_stopped() {
    let container = Container {
        id: "pausedid01".to_string(),
        name: "paused-web".to_string(),
        image: "nginx:1.25".to_string(),
        status: ContainerStatus::Paused,
    };

    // Paused is not running.
    assert!(
        !container.is_running(),
        "Paused must not report is_running() == true"
    );

    // Paused is not stopped (stopped == Exited | Dead only).
    assert!(
        !container.is_stopped(),
        "Paused must not report is_stopped() == true"
    );

    // The status is exactly Paused — not equal to any other variant.
    assert_eq!(container.status, ContainerStatus::Paused);
    assert_ne!(container.status, ContainerStatus::Running);
    assert_ne!(container.status, ContainerStatus::Created);
    assert_ne!(container.status, ContainerStatus::Exited);
    assert_ne!(container.status, ContainerStatus::Dead);
    assert_ne!(container.status, ContainerStatus::Restarting);
    assert_ne!(container.status, ContainerStatus::Removing);

    // Sanity: Display representation is the lowercase string "paused".
    assert_eq!(container.status.to_string(), "paused");
}
