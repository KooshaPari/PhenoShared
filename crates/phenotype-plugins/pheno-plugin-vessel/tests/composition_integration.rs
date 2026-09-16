//! Integration tests for phenotype-vessel ComposeFile public API.
//!
//! These tests exercise `ComposeFile` end-to-end as an orchestration spec —
//! how YAML, services, networks, volumes, and dependency ordering compose
//! together through the public surface.
//!
//! Traces to: FR-VESSEL-COMPOSE-001

use phenotype_vessel::compose::{
    BuildConfig, ComposeFile, ComposeService, NetworkConfig, VolumeConfig,
};
use std::collections::{HashMap, HashSet};

// ============================================================================
// YAML Roundtrip
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-002
///
/// Parse a multi-service YAML spec, serialize it back to YAML, and re-parse.
/// The services present in the round-tripped spec must match the original —
/// this guards against the most common operational hazard (lossy serialization).
#[test]
fn test_compose_yaml_roundtrip() {
    let yaml = r#"
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
  api:
    image: myorg/api:1.2.3
    environment:
      RUST_LOG: info
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
"#;

    let original = ComposeFile::from_yaml(yaml).expect("initial parse must succeed");
    assert_eq!(original.services.len(), 3, "expected 3 services in source YAML");

    let serialized = original.to_yaml().expect("serialize must succeed");
    let reparsed = ComposeFile::from_yaml(&serialized).expect("re-parse must succeed");

    assert_eq!(
        reparsed.services.len(),
        original.services.len(),
        "service count must survive roundtrip"
    );
    assert_eq!(reparsed.version, original.version, "version must survive roundtrip");

    // Each named service from the original must be present after the roundtrip
    // and its `image` must match exactly.
    for (name, svc) in &original.services {
        let reparsed_svc = reparsed
            .services
            .get(name)
            .unwrap_or_else(|| panic!("service '{}' lost in roundtrip", name));
        assert_eq!(reparsed_svc.image, svc.image, "image for '{}' must survive roundtrip", name);
    }
}

// ============================================================================
// Top-level fields: services + networks + volumes
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-003
///
/// A `ComposeFile` carries three top-level collections: `services`,
/// `networks`, `volumes`. All three must survive a `from_yaml → to_yaml →
/// from_yaml` cycle. This catches bugs where, e.g., networks are silently
/// dropped on the way out.
#[test]
fn test_compose_with_networks_and_volumes() {
    let mut services = HashMap::new();
    let web = ComposeService { image: Some("nginx:latest".to_string()), ..Default::default() };
    services.insert("web".to_string(), web);
    let compose =
        ComposeFile { version: Some("3.8".to_string()), services, networks: None, volumes: None };

    // Re-build the full file with networks + volumes populated.
    let mut networks: HashMap<String, NetworkConfig> = HashMap::new();
    networks.insert(
        "frontend".to_string(),
        NetworkConfig { driver: Some("bridge".to_string()), external: Some(false) },
    );
    networks.insert(
        "backend".to_string(),
        NetworkConfig { driver: Some("overlay".to_string()), external: None },
    );

    let mut volumes: HashMap<String, VolumeConfig> = HashMap::new();
    volumes.insert(
        "pgdata".to_string(),
        VolumeConfig { driver: Some("local".to_string()), external: Some(false) },
    );
    volumes.insert("shared".to_string(), VolumeConfig { driver: None, external: Some(true) });

    let compose = ComposeFile {
        version: compose.version,
        services: compose.services,
        networks: Some(networks.clone()),
        volumes: Some(volumes.clone()),
    };

    // Roundtrip through YAML.
    let yaml = compose.to_yaml().expect("serialize must succeed");
    let reparsed = ComposeFile::from_yaml(&yaml).expect("re-parse must succeed");

    // Services preserved.
    assert_eq!(reparsed.services.len(), 1);
    assert!(reparsed.services.contains_key("web"));

    // Networks preserved (and field-by-field equality on each entry).
    let reparsed_networks = reparsed.networks.as_ref().expect("networks must survive roundtrip");
    assert_eq!(reparsed_networks.len(), networks.len());
    for (name, cfg) in &networks {
        let got = reparsed_networks
            .get(name)
            .unwrap_or_else(|| panic!("network '{}' lost in roundtrip", name));
        assert_eq!(got.driver, cfg.driver, "network '{}' driver", name);
        assert_eq!(got.external, cfg.external, "network '{}' external", name);
    }

    // Volumes preserved (and field-by-field equality on each entry).
    let reparsed_volumes = reparsed.volumes.as_ref().expect("volumes must survive roundtrip");
    assert_eq!(reparsed_volumes.len(), volumes.len());
    for (name, cfg) in &volumes {
        let got = reparsed_volumes
            .get(name)
            .unwrap_or_else(|| panic!("volume '{}' lost in roundtrip", name));
        assert_eq!(got.driver, cfg.driver, "volume '{}' driver", name);
        assert_eq!(got.external, cfg.external, "volume '{}' external", name);
    }
}

// ============================================================================
// Dependency ordering
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-004
///
/// A 3-service chain — `web → api → db` — exercises `ordered_services()`.
/// We don't pin to a single exact ordering (the implementation may use any
/// valid topological traversal), but we DO require that `db` appears before
/// `api`, and `api` before `web`, so that a runtime booting services in this
/// order would never see a "dependency not ready" condition.
#[test]
fn test_compose_dependency_chain() {
    let mut services = HashMap::new();
    let web = ComposeService {
        image: Some("nginx:latest".to_string()),
        depends_on: Some(vec!["api".to_string(), "db".to_string()]),
        ..Default::default()
    };
    services.insert("web".to_string(), web);

    let api = ComposeService {
        image: Some("myorg/api:1.0".to_string()),
        depends_on: Some(vec!["db".to_string()]),
        ..Default::default()
    };
    services.insert("api".to_string(), api);

    let db = ComposeService { image: Some("postgres:15".to_string()), ..Default::default() };
    services.insert("db".to_string(), db);

    let compose =
        ComposeFile { version: Some("3.8".to_string()), services, networks: None, volumes: None };

    let ordered = compose.ordered_services();
    assert_eq!(ordered.len(), 3, "all 3 services must be in the ordered output");

    // Find each service in the output by its `image` (a stable proxy for identity).
    let db_idx = ordered
        .iter()
        .position(|s| s.image.as_deref() == Some("postgres:15"))
        .expect("db must appear in ordered_services()");
    let api_idx = ordered
        .iter()
        .position(|s| s.image.as_deref() == Some("myorg/api:1.0"))
        .expect("api must appear in ordered_services()");
    let web_idx = ordered
        .iter()
        .position(|s| s.image.as_deref() == Some("nginx:latest"))
        .expect("web must appear in ordered_services()");

    assert!(
        db_idx < web_idx,
        "db (index {}) must come before web (index {}) — web depends on db",
        db_idx,
        web_idx
    );
    assert!(
        api_idx < web_idx,
        "api (index {}) must come before web (index {}) — web depends on api",
        api_idx,
        web_idx
    );
    assert!(
        db_idx < api_idx,
        "db (index {}) must come before api (index {}) — api depends on db",
        db_idx,
        api_idx
    );
}

// ============================================================================
// Full ComposeService field set
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-005
///
/// Build a `ComposeService` with every optional field populated and verify
/// each one is set and readable. This is the canary that catches accidental
/// field removal or accidental `Option<>` wrapping of fields that should be
/// inline.
#[test]
fn test_compose_service_with_full_config() {
    let mut env: HashMap<String, String> = HashMap::new();
    env.insert("POSTGRES_DB".to_string(), "test".to_string());
    env.insert("POSTGRES_USER".to_string(), "admin".to_string());

    let service = ComposeService {
        image: Some("postgres:15".to_string()),
        build: Some(BuildConfig {
            context: Some(".".to_string()),
            dockerfile: Some("Dockerfile.dev".to_string()),
            args: None,
        }),
        container_name: Some("my-postgres".to_string()),
        environment: Some(env),
        ports: Some(vec!["5432:5432".to_string()]),
        volumes: Some(vec!["./data:/var/lib/postgresql/data".to_string()]),
        depends_on: Some(vec!["db".to_string()]),
        restart: Some("unless-stopped".to_string()),
        command: Some("postgres -c log_statement=all".to_string()),
        working_dir: Some("/app".to_string()),
    };

    assert_eq!(service.image.as_deref(), Some("postgres:15"));
    assert_eq!(service.container_name.as_deref(), Some("my-postgres"));
    assert_eq!(service.restart.as_deref(), Some("unless-stopped"));
    assert_eq!(service.command.as_deref(), Some("postgres -c log_statement=all"));
    assert_eq!(service.working_dir.as_deref(), Some("/app"));

    let env = service.environment.as_ref().expect("environment must be set");
    assert_eq!(env.len(), 2);
    assert_eq!(env.get("POSTGRES_DB").map(String::as_str), Some("test"));
    assert_eq!(env.get("POSTGRES_USER").map(String::as_str), Some("admin"));

    let ports = service.ports.as_ref().expect("ports must be set");
    assert_eq!(ports, &vec!["5432:5432".to_string()]);

    let volumes = service.volumes.as_ref().expect("volumes must be set");
    assert_eq!(volumes.len(), 1);
    assert_eq!(volumes[0], "./data:/var/lib/postgresql/data");

    let deps = service.depends_on.as_ref().expect("depends_on must be set");
    assert_eq!(deps, &vec!["db".to_string()]);

    let build = service.build.as_ref().expect("build must be set");
    assert_eq!(build.context.as_deref(), Some("."));
    assert_eq!(build.dockerfile.as_deref(), Some("Dockerfile.dev"));
}

// ============================================================================
// Default state of ComposeService
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-006
///
/// `ComposeService::default()` must produce a fully-empty struct: every
/// optional field is `None`. This is the "no surprises" guarantee that lets
/// callers incrementally build a service from a bare default.
#[test]
fn test_compose_default_service_is_empty() {
    let service = ComposeService::default();

    assert!(service.image.is_none(), "image must default to None");
    assert!(service.build.is_none(), "build must default to None");
    assert!(service.container_name.is_none(), "container_name must default to None");
    assert!(service.environment.is_none(), "environment must default to None");
    assert!(service.ports.is_none(), "ports must default to None");
    assert!(service.volumes.is_none(), "volumes must default to None");
    assert!(service.depends_on.is_none(), "depends_on must default to None");
    assert!(service.restart.is_none(), "restart must default to None");
    assert!(service.command.is_none(), "command must default to None");
    assert!(service.working_dir.is_none(), "working_dir must default to None");
}

// ============================================================================
// service_names() coverage
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-007
///
/// `service_names()` must return every name in the services map. We insert
/// 5 services and assert all 5 are present in the returned list (order is
/// not guaranteed, so compare as a set).
#[test]
fn test_compose_service_names_returns_all() {
    let expected: HashSet<String> =
        ["web", "db", "api", "cache", "worker"].iter().map(|s| s.to_string()).collect();

    let mut services = HashMap::new();
    for name in &expected {
        services.insert(name.clone(), ComposeService::default());
    }

    let compose = ComposeFile { version: None, services, networks: None, volumes: None };

    let names: HashSet<String> = compose.service_names().into_iter().cloned().collect();

    assert_eq!(names.len(), 5, "expected 5 service names, got {:?}", names);
    assert_eq!(names, expected, "service_names() must return the full set");
}

// ============================================================================
// Empty services edge case
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-008
///
/// A `ComposeFile` with no services is a legal (if unusual) value. Both
/// `service_names()` and `ordered_services()` must return empty `Vec`s
/// rather than panicking or returning `None`.
#[test]
fn test_compose_empty_services() {
    let compose =
        ComposeFile { version: None, services: HashMap::new(), networks: None, volumes: None };

    assert!(compose.service_names().is_empty(), "service_names() on empty file must be empty");
    assert!(
        compose.ordered_services().is_empty(),
        "ordered_services() on empty file must be empty"
    );
}

// ============================================================================
// Invalid YAML rejection
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-009
///
/// Malformed YAML must be rejected with `Err`, not silently coerced into an
/// empty `ComposeFile` (which would mask upstream schema/parse failures).
#[test]
fn test_compose_invalid_yaml() {
    let result = ComposeFile::from_yaml("invalid: yaml: :::");
    assert!(result.is_err(), "malformed YAML must produce Err, got Ok({:?})", result.ok());
}

// ============================================================================
// Environment HashMap preservation
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-010
///
/// `environment` is a `HashMap<String, String>` — both keys and values must
/// survive the public surface intact. Insert two entries and verify each is
/// retrievable with the expected value.
#[test]
fn test_compose_with_environment_hashmap() {
    let mut env: HashMap<String, String> = HashMap::new();
    env.insert("POSTGRES_DB".to_string(), "test".to_string());
    env.insert("POSTGRES_USER".to_string(), "admin".to_string());

    let service = ComposeService {
        image: Some("postgres:15".to_string()),
        environment: Some(env),
        ..Default::default()
    };

    let stored_env = service.environment.as_ref().expect("environment must be set on the service");
    assert_eq!(stored_env.len(), 2, "both env entries must be preserved");
    assert_eq!(
        stored_env.get("POSTGRES_DB").map(String::as_str),
        Some("test"),
        "POSTGRES_DB value must be preserved"
    );
    assert_eq!(
        stored_env.get("POSTGRES_USER").map(String::as_str),
        Some("admin"),
        "POSTGRES_USER value must be preserved"
    );
}

// ============================================================================
// Serialization order independence
// ============================================================================

/// Traces to: FR-VESSEL-COMPOSE-011
///
/// Two `ComposeFile`s with the same set of services inserted in different
/// orders must be semantically equivalent. After serializing each to YAML
/// and re-parsing, the resulting `ComposeFile`s must agree field-by-field.
/// We compare by `HashSet` of service names and by per-service field equality
/// to side-step the fact that `HashMap` iteration order is not stable.
#[test]
fn test_compose_serialization_preserves_order_independence() {
    fn make_service_a() -> ComposeService {
        ComposeService {
            image: Some("nginx:latest".to_string()),
            ports: Some(vec!["80:80".to_string()]),
            restart: Some("always".to_string()),
            ..Default::default()
        }
    }
    fn make_service_b() -> ComposeService {
        ComposeService {
            image: Some("postgres:15".to_string()),
            environment: Some(
                [
                    ("POSTGRES_DB".to_string(), "test".to_string()),
                    ("POSTGRES_USER".to_string(), "admin".to_string()),
                ]
                .into_iter()
                .collect(),
            ),
            ..Default::default()
        }
    }
    fn make_service_c() -> ComposeService {
        ComposeService {
            image: Some("redis:7".to_string()),
            depends_on: Some(vec!["db".to_string()]),
            ..Default::default()
        }
    }

    // Insertion order #1: a, b, c
    let mut services_order_a: HashMap<String, ComposeService> = HashMap::new();
    services_order_a.insert("web".to_string(), make_service_a());
    services_order_a.insert("db".to_string(), make_service_b());
    services_order_a.insert("cache".to_string(), make_service_c());
    let compose_a = ComposeFile {
        version: Some("3.8".to_string()),
        services: services_order_a,
        networks: None,
        volumes: None,
    };

    // Insertion order #2: c, a, b (intentionally reversed for two of three)
    let mut services_order_b: HashMap<String, ComposeService> = HashMap::new();
    services_order_b.insert("cache".to_string(), make_service_c());
    services_order_b.insert("web".to_string(), make_service_a());
    services_order_b.insert("db".to_string(), make_service_b());
    let compose_b = ComposeFile {
        version: Some("3.8".to_string()),
        services: services_order_b,
        networks: None,
        volumes: None,
    };

    // Roundtrip both through YAML.
    let yaml_a = compose_a.to_yaml().expect("serialize a must succeed");
    let yaml_b = compose_b.to_yaml().expect("serialize b must succeed");
    let reparsed_a = ComposeFile::from_yaml(&yaml_a).expect("re-parse a must succeed");
    let reparsed_b = ComposeFile::from_yaml(&yaml_b).expect("re-parse b must succeed");

    // Same set of service names on both sides.
    let names_a: HashSet<&String> = reparsed_a.services.keys().collect();
    let names_b: HashSet<&String> = reparsed_b.services.keys().collect();
    assert_eq!(names_a, names_b, "service name sets must match across orders");
    assert_eq!(names_a.len(), 3, "must have 3 distinct services");

    // Field-by-field equality on each shared service.
    for name in names_a {
        let svc_a = &reparsed_a.services[name];
        let svc_b = &reparsed_b.services[name];

        assert_eq!(
            svc_a.image, svc_b.image,
            "image for '{}' must match across insertion orders",
            name
        );
        assert_eq!(
            svc_a.ports, svc_b.ports,
            "ports for '{}' must match across insertion orders",
            name
        );
        assert_eq!(
            svc_a.restart, svc_b.restart,
            "restart for '{}' must match across insertion orders",
            name
        );
        assert_eq!(
            svc_a.environment, svc_b.environment,
            "environment for '{}' must match across insertion orders",
            name
        );
        assert_eq!(
            svc_a.depends_on, svc_b.depends_on,
            "depends_on for '{}' must match across insertion orders",
            name
        );
    }

    // Version also preserved on both sides.
    assert_eq!(reparsed_a.version, reparsed_b.version);
    assert_eq!(reparsed_a.version.as_deref(), Some("3.8"));
}
