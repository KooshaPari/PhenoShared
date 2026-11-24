//! # phenotype-vessel
//!
//! Docker Compose file parsing and orchestration.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Docker Compose file representation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComposeFile {
    /// Compose file version
    pub version: Option<String>,
    /// Services defined
    pub services: HashMap<String, ComposeService>,
    /// Networks defined
    pub networks: Option<HashMap<String, NetworkConfig>>,
    /// Volumes defined
    pub volumes: Option<HashMap<String, VolumeConfig>>,
}

/// Configuration for a compose service
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ComposeService {
    /// Image to use
    pub image: Option<String>,
    /// Build configuration
    pub build: Option<BuildConfig>,
    /// Container name
    pub container_name: Option<String>,
    /// Environment variables
    pub environment: Option<HashMap<String, String>>,
    /// Port mappings
    pub ports: Option<Vec<String>>,
    /// Volume mounts
    pub volumes: Option<Vec<String>>,
    /// Dependencies (depends_on)
    pub depends_on: Option<Vec<String>>,
    /// Restart policy
    pub restart: Option<String>,
    /// Command to run
    pub command: Option<String>,
    /// Working directory
    pub working_dir: Option<String>,
}

/// Build configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildConfig {
    /// Build context
    pub context: Option<String>,
    /// Dockerfile path
    pub dockerfile: Option<String>,
    /// Build args
    pub args: Option<HashMap<String, String>>,
}

/// Network configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkConfig {
    pub driver: Option<String>,
    pub external: Option<bool>,
}

/// Volume configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolumeConfig {
    pub driver: Option<String>,
    pub external: Option<bool>,
}

impl ComposeFile {
    /// Parse a compose file from YAML
    pub fn from_yaml(yaml: &str) -> Result<Self, serde_yaml::Error> {
        serde_yaml::from_str(yaml)
    }

    /// Serialize to YAML
    pub fn to_yaml(&self) -> Result<String, serde_yaml::Error> {
        serde_yaml::to_string(self)
    }

    /// Get all service names
    pub fn service_names(&self) -> Vec<&String> {
        self.services.keys().collect()
    }

    /// Get service in dependency order
    pub fn ordered_services(&self) -> Vec<&ComposeService> {
        let mut ordered = Vec::new();
        let mut visited = std::collections::HashSet::new();

        fn visit<'a>(
            service_name: &'a str,
            services: &'a HashMap<String, ComposeService>,
            ordered: &mut Vec<&'a ComposeService>,
            visited: &mut std::collections::HashSet<&'a str>,
        ) {
            if visited.contains(service_name) {
                return;
            }
            visited.insert(service_name);

            if let Some(service) = services.get(service_name) {
                if let Some(deps) = &service.depends_on {
                    for dep in deps {
                        visit(dep, services, ordered, visited);
                    }
                }
                if let Some(svc) = services.get(service_name) {
                    ordered.push(svc);
                }
            }
        }

        for name in self.services.keys() {
            visit(name.as_str(), &self.services, &mut ordered, &mut visited);
        }

        ordered
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_compose_file() {
        let yaml = r#"
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
"#;
        let compose = ComposeFile::from_yaml(yaml).unwrap();
        assert_eq!(compose.services.len(), 2);
        assert!(compose.services.contains_key("web"));
        assert!(compose.services.contains_key("db"));
    }

    #[test]
    fn test_service_dependencies() {
        let mut services = HashMap::new();

        let mut web = ComposeService::default();
        web.image = Some("nginx".to_string());
        web.depends_on = Some(vec!["db".to_string()]);

        let mut db = ComposeService::default();
        db.image = Some("postgres".to_string());

        services.insert("web".to_string(), web);
        services.insert("db".to_string(), db);

        let compose = ComposeFile {
            version: Some("3.8".to_string()),
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        // db should come before web due to dependency
        let db_idx = ordered.iter().position(|s| s.image.as_ref().unwrap() == "postgres");
        let web_idx = ordered.iter().position(|s| s.image.as_ref().unwrap() == "nginx");

        assert!(db_idx.is_some() && web_idx.is_some());
    }

    #[test]
    fn test_compose_from_yaml_invalid() {
        let result = ComposeFile::from_yaml(":invalid: yaml: :::");
        assert!(result.is_err());
    }

    #[test]
    fn test_compose_to_yaml_roundtrip() {
        let mut services = HashMap::new();

        let mut web = ComposeService::default();
        web.image = Some("nginx:latest".to_string());
        services.insert("web".to_string(), web);

        let mut db = ComposeService::default();
        db.image = Some("postgres:15".to_string());
        services.insert("db".to_string(), db);

        let compose = ComposeFile {
            version: Some("3.8".to_string()),
            services,
            networks: None,
            volumes: None,
        };

        let yaml = compose.to_yaml().unwrap();
        let parsed = ComposeFile::from_yaml(&yaml).unwrap();

        assert_eq!(parsed.services.len(), compose.services.len());
        assert_eq!(parsed.version, compose.version);
        assert_eq!(parsed.services["web"].image, compose.services["web"].image);
        assert_eq!(parsed.services["db"].image, compose.services["db"].image);
    }

    #[test]
    fn test_compose_service_names() {
        use std::collections::HashSet;

        let mut services = HashMap::new();
        services.insert("db".to_string(), ComposeService::default());
        services.insert("api".to_string(), ComposeService::default());
        services.insert("web".to_string(), ComposeService::default());

        let compose = ComposeFile { version: None, services, networks: None, volumes: None };

        let names: HashSet<&str> = compose.service_names().iter().map(|s| s.as_str()).collect();
        assert_eq!(names.len(), 3);
        assert!(names.contains("db"));
        assert!(names.contains("api"));
        assert!(names.contains("web"));
    }

    #[test]
    fn test_compose_service_default() {
        let service = ComposeService::default();
        assert!(service.image.is_none());
        assert!(service.command.is_none());
        assert!(service.depends_on.is_none());
        assert!(service.environment.is_none());
        assert!(service.ports.is_none());
        assert!(service.volumes.is_none());
    }

    #[test]
    fn test_ordered_services_empty() {
        let compose =
            ComposeFile { version: None, services: HashMap::new(), networks: None, volumes: None };

        let ordered = compose.ordered_services();
        assert!(ordered.is_empty());
    }

    #[test]
    fn test_compose_service_field_access() {
        let mut env = HashMap::new();
        env.insert("POSTGRES_DB".to_string(), "test".to_string());

        let service = ComposeService {
            image: Some("postgres:15".to_string()),
            build: None,
            container_name: None,
            environment: Some(env),
            ports: Some(vec!["5432:5432".to_string()]),
            volumes: None,
            depends_on: None,
            restart: None,
            command: None,
            working_dir: None,
        };

        assert_eq!(service.image.as_ref().unwrap(), "postgres:15");
        assert_eq!(service.environment.as_ref().unwrap().get("POSTGRES_DB").unwrap(), "test");
        assert_eq!(service.ports.as_ref().unwrap(), &vec!["5432:5432".to_string()]);
    }

    #[test]
    fn test_compose_dependencies_count() {
        let mut services = HashMap::new();

        let mut web = ComposeService::default();
        web.depends_on = Some(vec!["db".to_string(), "api".to_string()]);
        services.insert("web".to_string(), web);

        services.insert("db".to_string(), ComposeService::default());
        services.insert("api".to_string(), ComposeService::default());

        let compose = ComposeFile { version: None, services, networks: None, volumes: None };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 3);
        assert_eq!(compose.services["web"].depends_on.as_ref().unwrap().len(), 2);
    }

    #[test]
    fn test_build_config_construction() {
        let mut args = HashMap::new();
        args.insert("VERSION".to_string(), "1.0".to_string());

        let build = BuildConfig {
            context: Some(".".to_string()),
            dockerfile: Some("Dockerfile".to_string()),
            args: Some(args),
        };

        assert_eq!(build.context.as_deref(), Some("."));
        assert_eq!(build.dockerfile.as_deref(), Some("Dockerfile"));

        let args_ref = build.args.as_ref().unwrap();
        assert_eq!(args_ref.len(), 1);
        assert_eq!(args_ref.get("VERSION").map(|s| s.as_str()), Some("1.0"));
    }

    #[test]
    fn test_build_config_serde() {
        let mut args = HashMap::new();
        args.insert("VERSION".to_string(), "1.0".to_string());

        let original = BuildConfig {
            context: Some(".".to_string()),
            dockerfile: Some("Dockerfile".to_string()),
            args: Some(args),
        };

        let yaml = serde_yaml::to_string(&original).unwrap();
        let parsed: BuildConfig = serde_yaml::from_str(&yaml).unwrap();

        assert_eq!(parsed.context, original.context);
        assert_eq!(parsed.dockerfile, original.dockerfile);
        assert_eq!(parsed.args, original.args);
    }

    #[test]
    fn test_network_config_construction() {
        let net = NetworkConfig {
            driver: Some("bridge".to_string()),
            external: Some(false),
        };

        assert_eq!(net.driver.as_deref(), Some("bridge"));
        assert_eq!(net.external, Some(false));
    }

    #[test]
    fn test_network_config_serde() {
        let original = NetworkConfig {
            driver: Some("bridge".to_string()),
            external: Some(false),
        };

        let yaml = serde_yaml::to_string(&original).unwrap();
        let parsed: NetworkConfig = serde_yaml::from_str(&yaml).unwrap();

        assert_eq!(parsed.driver, original.driver);
        assert_eq!(parsed.external, original.external);
    }

    #[test]
    fn test_volume_config_construction() {
        let vol = VolumeConfig {
            driver: Some("local".to_string()),
            external: Some(true),
        };

        assert_eq!(vol.driver.as_deref(), Some("local"));
        assert_eq!(vol.external, Some(true));
    }

    #[test]
    fn test_volume_config_serde() {
        let original = VolumeConfig {
            driver: Some("local".to_string()),
            external: Some(true),
        };

        let yaml = serde_yaml::to_string(&original).unwrap();
        let parsed: VolumeConfig = serde_yaml::from_str(&yaml).unwrap();

        assert_eq!(parsed.driver, original.driver);
        assert_eq!(parsed.external, original.external);
    }

    #[test]
    fn test_ordered_services_with_missing_dependency() {
        let mut services = HashMap::new();

        let mut web = ComposeService::default();
        web.image = Some("nginx".to_string());
        web.depends_on = Some(vec!["nonexistent".to_string()]);
        services.insert("web".to_string(), web);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 1);
        assert_eq!(ordered[0].image.as_deref(), Some("nginx"));
        assert_eq!(
            ordered[0].depends_on.as_deref(),
            Some(&vec!["nonexistent".to_string()][..])
        );
    }

    #[test]
    fn test_ordered_services_three_level_chain() {
        let mut services = HashMap::new();

        let mut cache = ComposeService::default();
        cache.container_name = Some("cache".to_string());
        services.insert("cache".to_string(), cache);

        let mut db = ComposeService::default();
        db.container_name = Some("db".to_string());
        db.depends_on = Some(vec!["cache".to_string()]);
        services.insert("db".to_string(), db);

        let mut web = ComposeService::default();
        web.container_name = Some("web".to_string());
        web.depends_on = Some(vec!["db".to_string()]);
        services.insert("web".to_string(), web);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 3);

        let names: Vec<&str> = ordered
            .iter()
            .map(|s| s.container_name.as_deref().unwrap())
            .collect();
        let cache_idx = names.iter().position(|n| *n == "cache").unwrap();
        let db_idx = names.iter().position(|n| *n == "db").unwrap();
        let web_idx = names.iter().position(|n| *n == "web").unwrap();

        assert!(cache_idx < db_idx, "cache should come before db");
        assert!(db_idx < web_idx, "db should come before web");
    }

    #[test]
    fn test_compose_with_networks_and_volumes() {
        let mut networks = HashMap::new();
        networks.insert(
            "net1".to_string(),
            NetworkConfig {
                driver: Some("bridge".to_string()),
                external: Some(false),
            },
        );

        let mut volumes = HashMap::new();
        volumes.insert(
            "vol1".to_string(),
            VolumeConfig {
                driver: Some("local".to_string()),
                external: Some(true),
            },
        );

        let compose = ComposeFile {
            version: Some("3.8".to_string()),
            services: HashMap::new(),
            networks: Some(networks),
            volumes: Some(volumes),
        };

        assert!(compose.networks.is_some());
        assert_eq!(compose.networks.as_ref().unwrap().len(), 1);
        assert!(compose.networks.as_ref().unwrap().contains_key("net1"));

        assert!(compose.volumes.is_some());
        assert_eq!(compose.volumes.as_ref().unwrap().len(), 1);
        assert!(compose.volumes.as_ref().unwrap().contains_key("vol1"));
    }

    #[test]
    fn test_compose_service_build_field() {
        let service = ComposeService {
            image: None,
            build: Some(BuildConfig {
                context: Some("./app".to_string()),
                dockerfile: None,
                args: None,
            }),
            container_name: None,
            environment: None,
            ports: None,
            volumes: None,
            depends_on: None,
            restart: None,
            command: None,
            working_dir: None,
        };

        assert_eq!(
            service.build.as_ref().unwrap().context.as_deref(),
            Some("./app")
        );
        assert!(service.build.as_ref().unwrap().dockerfile.is_none());
        assert!(service.build.as_ref().unwrap().args.is_none());
    }

    #[test]
    fn test_compose_default() {
        // ComposeFile does not derive Default, so construct the equivalent
        // "empty" value explicitly: empty services map and None for the
        // optional fields — exactly what Default::default() would yield.
        let c = ComposeFile {
            version: None,
            services: HashMap::new(),
            networks: None,
            volumes: None,
        };
        assert!(c.services.is_empty());
        assert!(c.networks.is_none());
        assert!(c.volumes.is_none());
        assert!(c.version.is_none());
    }

    #[test]
    fn test_compose_services_accessor() {
        let mut services = HashMap::new();

        let mut web = ComposeService::default();
        web.image = Some("nginx:latest".to_string());
        services.insert("web".to_string(), web);

        let mut db = ComposeService::default();
        db.image = Some("postgres:15".to_string());
        services.insert("db".to_string(), db);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let services_ref: &HashMap<String, ComposeService> = &compose.services;
        assert_eq!(services_ref.len(), 2);
        assert!(services_ref.contains_key("web"));
        assert!(services_ref.contains_key("db"));
        assert_eq!(
            services_ref.get("web").unwrap().image.as_deref(),
            Some("nginx:latest")
        );
        assert_eq!(
            services_ref.get("db").unwrap().image.as_deref(),
            Some("postgres:15")
        );
    }

    #[test]
    fn test_compose_debug_format() {
        let mut services = HashMap::new();
        let mut web = ComposeService::default();
        web.image = Some("nginx:latest".to_string());
        services.insert("web".to_string(), web);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let debug = format!("{:?}", compose);
        assert!(debug.contains("ComposeFile"), "debug should contain struct name: {}", debug);
        assert!(debug.contains("services"), "debug should contain field name: {}", debug);
        assert!(debug.contains("web"), "debug should contain service name: {}", debug);
    }

    #[test]
    fn test_build_config_default() {
        // BuildConfig does not derive Default, so construct the equivalent
        // all-None value explicitly.
        let b = BuildConfig { context: None, dockerfile: None, args: None };
        assert!(b.context.is_none());
        assert!(b.dockerfile.is_none());
        assert!(b.args.is_none());
    }

    #[test]
    fn test_network_config_default() {
        let n = NetworkConfig { driver: None, external: None };
        assert!(n.driver.is_none());
        assert!(n.external.is_none());
    }

    #[test]
    fn test_volume_config_default() {
        let v = VolumeConfig { driver: None, external: None };
        assert!(v.driver.is_none());
        assert!(v.external.is_none());
    }

    #[test]
    fn test_build_config_debug() {
        let b = BuildConfig {
            context: Some(".".to_string()),
            dockerfile: Some("Dockerfile".to_string()),
            args: None,
        };
        let debug = format!("{:?}", b);
        assert!(debug.contains("BuildConfig"), "debug should contain struct name: {}", debug);
        assert!(debug.contains("Dockerfile"), "debug should contain dockerfile value: {}", debug);
        assert!(debug.contains("."), "debug should contain context value: {}", debug);
    }

    #[test]
    fn test_network_config_debug() {
        let n = NetworkConfig {
            driver: Some("bridge".to_string()),
            external: Some(false),
        };
        let debug = format!("{:?}", n);
        assert!(debug.contains("NetworkConfig"), "debug should contain struct name: {}", debug);
        assert!(debug.contains("bridge"), "debug should contain driver value: {}", debug);
    }

    #[test]
    fn test_volume_config_debug() {
        let v = VolumeConfig {
            driver: Some("local".to_string()),
            external: Some(true),
        };
        let debug = format!("{:?}", v);
        assert!(debug.contains("VolumeConfig"), "debug should contain struct name: {}", debug);
        assert!(debug.contains("local"), "debug should contain driver value: {}", debug);
    }

    #[test]
    fn test_ordered_services_with_circular_dep() {
        // A depends on B, and B depends on A. The implementation guards
        // against infinite recursion via a `visited` set, so both services
        // should still appear in the result (in some order, without panicking).
        let mut services = HashMap::new();

        let mut a = ComposeService::default();
        a.image = Some("a".to_string());
        a.depends_on = Some(vec!["b".to_string()]);
        services.insert("a".to_string(), a);

        let mut b = ComposeService::default();
        b.image = Some("b".to_string());
        b.depends_on = Some(vec!["a".to_string()]);
        services.insert("b".to_string(), b);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 2);
        let images: Vec<&str> =
            ordered.iter().map(|s| s.image.as_deref().unwrap()).collect();
        assert!(images.contains(&"a"));
        assert!(images.contains(&"b"));
    }

    #[test]
    fn test_ordered_services_with_self_referential() {
        // A depends on itself. The `visited` set should prevent infinite
        // recursion, so A appears exactly once in the result.
        let mut services = HashMap::new();

        let mut a = ComposeService::default();
        a.image = Some("a".to_string());
        a.depends_on = Some(vec!["a".to_string()]);
        services.insert("a".to_string(), a);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 1);
        assert_eq!(ordered[0].image.as_deref(), Some("a"));
    }

    #[test]
    fn test_compose_to_yaml_does_not_panic_with_special_chars() {
        let mut services = HashMap::new();
        let mut svc = ComposeService::default();
        svc.image = Some("nginx:latest".to_string());
        services.insert("service-with-dashes_and_underscores".to_string(), svc);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        // Round-trip should not panic and should preserve the name verbatim.
        let yaml = compose.to_yaml().unwrap();
        let parsed = ComposeFile::from_yaml(&yaml).unwrap();

        assert!(parsed.services.contains_key("service-with-dashes_and_underscores"));
        assert_eq!(
            parsed.services["service-with-dashes_and_underscores"].image.as_deref(),
            Some("nginx:latest")
        );
    }

    #[test]
    fn test_compose_clone() {
        // Build a ComposeFile with services, networks, and volumes populated.
        // Clone it and verify every field is preserved.
        let mut services = HashMap::new();
        let mut web = ComposeService::default();
        web.image = Some("nginx:latest".to_string());
        services.insert("web".to_string(), web);

        let mut networks = HashMap::new();
        networks.insert(
            "net1".to_string(),
            NetworkConfig {
                driver: Some("bridge".to_string()),
                external: Some(false),
            },
        );

        let mut volumes = HashMap::new();
        volumes.insert(
            "vol1".to_string(),
            VolumeConfig {
                driver: Some("local".to_string()),
                external: Some(true),
            },
        );

        let original = ComposeFile {
            version: Some("3.8".to_string()),
            services,
            networks: Some(networks),
            volumes: Some(volumes),
        };

        let cloned = original.clone();

        assert_eq!(cloned.version, original.version);
        assert_eq!(cloned.services.len(), original.services.len());
        assert_eq!(cloned.services["web"].image, original.services["web"].image);

        assert!(cloned.networks.is_some());
        assert_eq!(
            cloned.networks.as_ref().unwrap().len(),
            original.networks.as_ref().unwrap().len()
        );
        assert_eq!(
            cloned.networks.as_ref().unwrap()["net1"].driver,
            original.networks.as_ref().unwrap()["net1"].driver
        );
        assert_eq!(
            cloned.networks.as_ref().unwrap()["net1"].external,
            original.networks.as_ref().unwrap()["net1"].external
        );

        assert!(cloned.volumes.is_some());
        assert_eq!(
            cloned.volumes.as_ref().unwrap().len(),
            original.volumes.as_ref().unwrap().len()
        );
        assert_eq!(
            cloned.volumes.as_ref().unwrap()["vol1"].driver,
            original.volumes.as_ref().unwrap()["vol1"].driver
        );
        assert_eq!(
            cloned.volumes.as_ref().unwrap()["vol1"].external,
            original.volumes.as_ref().unwrap()["vol1"].external
        );
    }

    #[test]
    fn test_service_clone() {
        // Build a ComposeService with every field populated, clone it, and
        // verify the clone is an exact copy.
        let mut env = HashMap::new();
        env.insert("KEY".to_string(), "value".to_string());

        let service = ComposeService {
            image: Some("nginx:latest".to_string()),
            build: Some(BuildConfig {
                context: Some(".".to_string()),
                dockerfile: Some("Dockerfile".to_string()),
                args: Some(env.clone()),
            }),
            container_name: Some("mycontainer".to_string()),
            environment: Some(env),
            ports: Some(vec!["80:80".to_string()]),
            volumes: Some(vec!["./data:/data".to_string()]),
            depends_on: Some(vec!["db".to_string()]),
            restart: Some("always".to_string()),
            command: Some("nginx -g 'daemon off;'".to_string()),
            working_dir: Some("/app".to_string()),
        };

        let cloned = service.clone();

        assert_eq!(cloned.image, service.image);
        assert_eq!(
            cloned.build.as_ref().unwrap().context,
            service.build.as_ref().unwrap().context
        );
        assert_eq!(
            cloned.build.as_ref().unwrap().dockerfile,
            service.build.as_ref().unwrap().dockerfile
        );
        assert_eq!(
            cloned.build.as_ref().unwrap().args,
            service.build.as_ref().unwrap().args
        );
        assert_eq!(cloned.container_name, service.container_name);
        assert_eq!(cloned.environment, service.environment);
        assert_eq!(cloned.ports, service.ports);
        assert_eq!(cloned.volumes, service.volumes);
        assert_eq!(cloned.depends_on, service.depends_on);
        assert_eq!(cloned.restart, service.restart);
        assert_eq!(cloned.command, service.command);
        assert_eq!(cloned.working_dir, service.working_dir);
    }

    #[test]
    fn test_build_config_with_all_fields() {
        // BuildConfig has three fields: context, dockerfile, args. Populate
        // them all and assert each is preserved verbatim.
        let build = BuildConfig {
            context: Some(".".to_string()),
            dockerfile: Some("Dockerfile".to_string()),
            args: Some(HashMap::from([("KEY".to_string(), "val".to_string())])),
        };

        assert_eq!(build.context.as_deref(), Some("."));
        assert_eq!(build.dockerfile.as_deref(), Some("Dockerfile"));

        let args_ref = build.args.as_ref().unwrap();
        assert_eq!(args_ref.len(), 1);
        assert_eq!(args_ref.get("KEY").map(|s| s.as_str()), Some("val"));
    }

    #[test]
    fn test_network_config_with_all_fields() {
        // NetworkConfig currently exposes `driver` and `external` only;
        // populate both and assert they are preserved.
        let net = NetworkConfig {
            driver: Some("bridge".to_string()),
            external: Some(true),
        };

        assert_eq!(net.driver.as_deref(), Some("bridge"));
        assert_eq!(net.external, Some(true));
    }

    #[test]
    fn test_volume_config_with_all_fields() {
        // VolumeConfig currently exposes `driver` and `external` only;
        // populate both and assert they are preserved.
        let vol = VolumeConfig {
            driver: Some("local".to_string()),
            external: Some(false),
        };

        assert_eq!(vol.driver.as_deref(), Some("local"));
        assert_eq!(vol.external, Some(false));
    }

    #[test]
    fn test_service_with_all_fields() {
        // Build a ComposeService with image, build, ports, volumes,
        // environment, depends_on, and command all populated.
        let mut env = HashMap::new();
        env.insert("KEY".to_string(), "value".to_string());

        let service = ComposeService {
            image: Some("nginx:latest".to_string()),
            build: Some(BuildConfig {
                context: Some(".".to_string()),
                dockerfile: Some("Dockerfile".to_string()),
                args: None,
            }),
            container_name: None,
            environment: Some(env),
            ports: Some(vec!["80:80".to_string(), "443:443".to_string()]),
            volumes: Some(vec!["./data:/data".to_string()]),
            depends_on: Some(vec!["db".to_string()]),
            restart: None,
            command: Some("nginx -g 'daemon off;'".to_string()),
            working_dir: None,
        };

        assert_eq!(service.image.as_deref(), Some("nginx:latest"));
        assert_eq!(
            service.build.as_ref().unwrap().context.as_deref(),
            Some(".")
        );
        assert_eq!(
            service
                .environment
                .as_ref()
                .unwrap()
                .get("KEY")
                .map(|s| s.as_str()),
            Some("value")
        );
        assert_eq!(service.ports.as_ref().unwrap().len(), 2);
        assert_eq!(
            service.ports.as_ref().unwrap(),
            &vec!["80:80".to_string(), "443:443".to_string()]
        );
        assert_eq!(
            service.volumes.as_ref().unwrap(),
            &vec!["./data:/data".to_string()]
        );
        assert_eq!(
            service.depends_on.as_ref().unwrap(),
            &vec!["db".to_string()]
        );
        assert_eq!(
            service.command.as_deref(),
            Some("nginx -g 'daemon off;'")
        );
    }

    #[test]
    fn test_ordered_services_deep_chain() {
        // D -> C -> B -> A. The implementation pushes a service only after
        // visiting its dependencies recursively, so the topological order is
        // guaranteed to be [A, B, C, D] regardless of HashMap iteration order.
        let mut services = HashMap::new();

        let mut a = ComposeService::default();
        a.image = Some("a".to_string());
        services.insert("a".to_string(), a);

        let mut b = ComposeService::default();
        b.image = Some("b".to_string());
        b.depends_on = Some(vec!["a".to_string()]);
        services.insert("b".to_string(), b);

        let mut c = ComposeService::default();
        c.image = Some("c".to_string());
        c.depends_on = Some(vec!["b".to_string()]);
        services.insert("c".to_string(), c);

        let mut d = ComposeService::default();
        d.image = Some("d".to_string());
        d.depends_on = Some(vec!["c".to_string()]);
        services.insert("d".to_string(), d);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 4);

        let images: Vec<&str> = ordered
            .iter()
            .map(|s| s.image.as_deref().unwrap())
            .collect();
        assert_eq!(images, vec!["a", "b", "c", "d"]);
    }

    #[test]
    fn test_ordered_services_no_deps_returns_input_order() {
        // Three services with no depends_on. The implementation iterates
        // self.services.keys() in arbitrary order, so the resulting order
        // is not guaranteed. Assert all 3 are present.
        let mut services = HashMap::new();

        let mut a = ComposeService::default();
        a.image = Some("a".to_string());
        services.insert("a".to_string(), a);

        let mut b = ComposeService::default();
        b.image = Some("b".to_string());
        services.insert("b".to_string(), b);

        let mut c = ComposeService::default();
        c.image = Some("c".to_string());
        services.insert("c".to_string(), c);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let ordered = compose.ordered_services();
        assert_eq!(ordered.len(), 3);

        let images: std::collections::HashSet<&str> = ordered
            .iter()
            .map(|s| s.image.as_deref().unwrap())
            .collect();
        assert!(images.contains("a"));
        assert!(images.contains("b"));
        assert!(images.contains("c"));
    }

    #[test]
    fn test_from_yaml_with_version_3_8() {
        // Single-service compose file with version "3.8". Verify the version
        // is captured and the service is parsed with the expected image.
        let yaml = r#"version: "3.8"
services:
  web:
    image: nginx
"#;
        let compose = ComposeFile::from_yaml(yaml).unwrap();
        assert_eq!(compose.version.as_deref(), Some("3.8"));
        assert_eq!(compose.services.len(), 1);
        assert!(compose.services.contains_key("web"));
        assert_eq!(
            compose.services["web"].image.as_deref(),
            Some("nginx")
        );
    }

    #[test]
    fn test_compose_to_yaml_preserves_special_chars_in_env_values() {
        // Environment values that contain spaces and colons must survive a
        // YAML roundtrip intact. serde_yaml quotes such values automatically.
        let mut env = HashMap::new();
        env.insert(
            "KEY".to_string(),
            "value with spaces and: colons".to_string(),
        );

        let mut svc = ComposeService::default();
        svc.image = Some("nginx".to_string());
        svc.environment = Some(env);

        let mut services = HashMap::new();
        services.insert("web".to_string(), svc);

        let compose = ComposeFile {
            version: None,
            services,
            networks: None,
            volumes: None,
        };

        let yaml = compose.to_yaml().unwrap();
        let parsed = ComposeFile::from_yaml(&yaml).unwrap();

        assert_eq!(
            parsed.services["web"]
                .environment
                .as_ref()
                .unwrap()
                .get("KEY")
                .map(|s| s.as_str()),
            Some("value with spaces and: colons")
        );
    }
}
