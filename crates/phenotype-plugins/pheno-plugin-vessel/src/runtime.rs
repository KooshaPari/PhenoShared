//! # phenotype-vessel
//!
//! Container runtime trait and implementations.

use async_trait::async_trait;
use std::collections::HashMap;

/// Trait for container runtime implementations
#[async_trait]
pub trait ContainerRuntime: Send + Sync {
    /// Get the runtime name
    fn name(&self) -> &str;

    /// Check if the runtime is available
    async fn is_available(&self) -> bool;

    /// List all containers
    async fn list_containers(&self) -> Result<Vec<ContainerInfo>, String>;

    /// Pull an image
    async fn pull_image(&self, image: &str) -> Result<(), String>;

    /// Remove an image
    async fn remove_image(&self, image: &str) -> Result<(), String>;

    /// Create a container
    async fn create_container(&self, config: &ContainerCreateConfig) -> Result<String, String>;

    /// Start a container
    async fn start_container(&self, id: &str) -> Result<(), String>;

    /// Stop a container
    async fn stop_container(&self, id: &str) -> Result<(), String>;

    /// Remove a container
    async fn remove_container(&self, id: &str) -> Result<(), String>;

    /// Get container logs
    async fn logs(&self, id: &str) -> Result<String, String>;
}

/// Container information from list_containers
#[derive(Debug, Clone)]
pub struct ContainerInfo {
    pub id: String,
    pub name: String,
    pub image: String,
    pub status: String,
    pub created: String,
}

/// Configuration for creating a container
#[derive(Debug, Clone)]
pub struct ContainerCreateConfig {
    pub image: String,
    pub name: Option<String>,
    pub env: HashMap<String, String>,
    pub ports: Vec<PortMapping>,
    pub volumes: Vec<VolumeMapping>,
}

/// Port mapping for container networking
#[derive(Debug, Clone)]
pub struct PortMapping {
    pub host_port: u16,
    pub container_port: u16,
    pub protocol: Protocol,
}

/// Volume mapping for persistent storage
#[derive(Debug, Clone)]
pub struct VolumeMapping {
    pub host_path: String,
    pub container_path: String,
    pub read_only: bool,
}

/// Network protocol
#[derive(Debug, Clone, Copy)]
pub enum Protocol {
    Tcp,
    Udp,
}

/// Docker runtime implementation
#[derive(Debug, Clone, Default)]
pub struct DockerRuntime;

impl DockerRuntime {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl ContainerRuntime for DockerRuntime {
    fn name(&self) -> &str {
        "docker"
    }

    async fn is_available(&self) -> bool {
        tokio::process::Command::new("docker")
            .arg("--version")
            .output()
            .await
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    async fn list_containers(&self) -> Result<Vec<ContainerInfo>, String> {
        let output = tokio::process::Command::new("docker")
            .args([
                "ps",
                "-a",
                "--format",
                "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.CreatedAt}}",
            ])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).to_string());
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let containers = stdout
            .lines()
            .filter_map(|line| {
                let parts: Vec<&str> = line.split('|').collect();
                if parts.len() >= 5 {
                    Some(ContainerInfo {
                        id: parts[0].to_string(),
                        name: parts[1].to_string(),
                        image: parts[2].to_string(),
                        status: parts[3].to_string(),
                        created: parts[4].to_string(),
                    })
                } else {
                    None
                }
            })
            .collect();

        Ok(containers)
    }

    async fn pull_image(&self, image: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("docker")
            .args(["pull", image])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn remove_image(&self, image: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("docker")
            .args(["rmi", image])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn create_container(&self, config: &ContainerCreateConfig) -> Result<String, String> {
        let mut args: Vec<String> = vec!["create".to_string()];

        if let Some(name) = &config.name {
            args.push("--name".to_string());
            args.push(name.clone());
        }

        for env in &config.env {
            args.push("-e".to_string());
            args.push(format!("{}={}", env.0, env.1));
        }

        for port in &config.ports {
            args.push("-p".to_string());
            args.push(format!("{}:{}", port.host_port, port.container_port));
        }

        for volume in &config.volumes {
            let mode = if volume.read_only { ":ro" } else { "" };
            args.push("-v".to_string());
            args.push(format!("{}:{}{}", volume.host_path, volume.container_path, mode));
        }

        args.push(config.image.clone());

        let output = tokio::process::Command::new("docker")
            .args(&args)
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn start_container(&self, id: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("docker")
            .args(["start", id])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn stop_container(&self, id: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("docker")
            .args(["stop", id])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn remove_container(&self, id: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("docker")
            .args(["rm", "-f", id])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn logs(&self, id: &str) -> Result<String, String> {
        let output = tokio::process::Command::new("docker")
            .args(["logs", id])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() || output.status.code() == Some(0) {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }
}

/// Podman runtime implementation
#[derive(Debug, Clone, Default)]
pub struct PodmanRuntime;

impl PodmanRuntime {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl ContainerRuntime for PodmanRuntime {
    fn name(&self) -> &str {
        "podman"
    }

    async fn is_available(&self) -> bool {
        tokio::process::Command::new("podman")
            .arg("--version")
            .output()
            .await
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    async fn list_containers(&self) -> Result<Vec<ContainerInfo>, String> {
        // Similar to Docker but using podman commands
        let output = tokio::process::Command::new("podman")
            .args(["ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).to_string());
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let containers = stdout
            .lines()
            .filter_map(|line| {
                let parts: Vec<&str> = line.split('|').collect();
                if parts.len() >= 4 {
                    Some(ContainerInfo {
                        id: parts[0].to_string(),
                        name: parts[1].to_string(),
                        image: parts[2].to_string(),
                        status: parts[3].to_string(),
                        created: String::new(),
                    })
                } else {
                    None
                }
            })
            .collect();

        Ok(containers)
    }

    async fn pull_image(&self, image: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("podman")
            .args(["pull", image])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn remove_image(&self, image: &str) -> Result<(), String> {
        let output = tokio::process::Command::new("podman")
            .args(["rmi", image])
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn create_container(&self, config: &ContainerCreateConfig) -> Result<String, String> {
        let mut args: Vec<String> = vec!["create".to_string()];

        if let Some(name) = &config.name {
            args.push("--name".to_string());
            args.push(name.clone());
        }

        for env in &config.env {
            args.push("-e".to_string());
            args.push(format!("{}={}", env.0, env.1));
        }

        args.push(config.image.clone());

        let output = tokio::process::Command::new("podman")
            .args(&args)
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    async fn start_container(&self, id: &str) -> Result<(), String> {
        tokio::process::Command::new("podman")
            .args(["start", id])
            .output()
            .await
            .map_err(|e| e.to_string())
            .and_then(|o| {
                if o.status.success() {
                    Ok(())
                } else {
                    Err(String::from_utf8_lossy(&o.stderr).to_string())
                }
            })
    }

    async fn stop_container(&self, id: &str) -> Result<(), String> {
        tokio::process::Command::new("podman")
            .args(["stop", id])
            .output()
            .await
            .map_err(|e| e.to_string())
            .and_then(|o| {
                if o.status.success() {
                    Ok(())
                } else {
                    Err(String::from_utf8_lossy(&o.stderr).to_string())
                }
            })
    }

    async fn remove_container(&self, id: &str) -> Result<(), String> {
        tokio::process::Command::new("podman")
            .args(["rm", "-f", id])
            .output()
            .await
            .map_err(|e| e.to_string())
            .and_then(|o| {
                if o.status.success() {
                    Ok(())
                } else {
                    Err(String::from_utf8_lossy(&o.stderr).to_string())
                }
            })
    }

    async fn logs(&self, id: &str) -> Result<String, String> {
        tokio::process::Command::new("podman")
            .args(["logs", id])
            .output()
            .await
            .map_err(|e| e.to_string())
            .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_docker_runtime_name() {
        let runtime = DockerRuntime::new();
        assert_eq!(runtime.name(), "docker");
    }

    #[test]
    fn test_podman_runtime_name() {
        let runtime = PodmanRuntime::new();
        assert_eq!(runtime.name(), "podman");
    }

    #[test]
    fn test_container_create_config() {
        let mut env = HashMap::new();
        env.insert("FOO".to_string(), "bar".to_string());

        let config = ContainerCreateConfig {
            image: "nginx:latest".to_string(),
            name: Some("test".to_string()),
            env,
            ports: vec![],
            volumes: vec![],
        };

        assert_eq!(config.image, "nginx:latest");
        assert_eq!(config.name, Some("test".to_string()));
    }

    #[test]
    fn test_port_mapping_creation() {
        let mapping = PortMapping { host_port: 8080, container_port: 80, protocol: Protocol::Tcp };

        assert_eq!(mapping.host_port, 8080);
        assert_eq!(mapping.container_port, 80);
        assert!(matches!(mapping.protocol, Protocol::Tcp));
    }

    #[test]
    fn test_port_mapping_udp_protocol() {
        let mapping = PortMapping { host_port: 53, container_port: 53, protocol: Protocol::Udp };

        assert_eq!(mapping.host_port, 53);
        assert_eq!(mapping.container_port, 53);
        assert!(matches!(mapping.protocol, Protocol::Udp));
    }

    #[test]
    fn test_volume_mapping_creation() {
        let ro = VolumeMapping {
            host_path: "/host".to_string(),
            container_path: "/container".to_string(),
            read_only: true,
        };
        assert_eq!(ro.host_path, "/host");
        assert_eq!(ro.container_path, "/container");
        assert!(ro.read_only);

        let rw = VolumeMapping {
            host_path: "/data".to_string(),
            container_path: "/app/data".to_string(),
            read_only: false,
        };
        assert_eq!(rw.host_path, "/data");
        assert_eq!(rw.container_path, "/app/data");
        assert!(!rw.read_only);
    }

    #[test]
    fn test_protocol_debug_and_copy() {
        let tcp = Protocol::Tcp;
        assert_eq!(format!("{:?}", tcp), "Tcp");
        let udp = Protocol::Udp;
        assert_eq!(format!("{:?}", udp), "Udp");

        let moved = tcp;
        assert!(matches!(tcp, Protocol::Tcp));
        assert!(matches!(moved, Protocol::Tcp));
    }

    #[test]
    fn test_docker_runtime_default_trait() {
        let runtime: DockerRuntime = Default::default();
        assert_eq!(runtime.name(), "docker");
    }

    #[test]
    fn test_container_info_construction() {
        let info = ContainerInfo {
            id: "abc123".to_string(),
            name: "web".to_string(),
            image: "nginx:latest".to_string(),
            status: "running".to_string(),
            created: "2024-01-01".to_string(),
        };
        assert_eq!(info.id, "abc123");
        assert_eq!(info.name, "web");
        assert_eq!(info.image, "nginx:latest");
        assert_eq!(info.status, "running");
        assert_eq!(info.created, "2024-01-01");
    }

    #[test]
    fn test_container_info_clone() {
        let info = ContainerInfo {
            id: "id1".to_string(),
            name: "n1".to_string(),
            image: "img1".to_string(),
            status: "up".to_string(),
            created: "c1".to_string(),
        };
        let cloned = info.clone();
        assert_eq!(cloned.id, info.id);
        assert_eq!(cloned.name, info.name);
        assert_eq!(cloned.image, info.image);
        assert_eq!(cloned.status, info.status);
        assert_eq!(cloned.created, info.created);
    }

    #[test]
    fn test_container_create_config_with_all_fields() {
        let mut env = HashMap::new();
        env.insert("A".to_string(), "1".to_string());
        env.insert("B".to_string(), "2".to_string());

        let config = ContainerCreateConfig {
            image: "redis:7".to_string(),
            name: Some("cache".to_string()),
            env,
            ports: vec![PortMapping {
                host_port: 6379,
                container_port: 6379,
                protocol: Protocol::Tcp,
            }],
            volumes: vec![VolumeMapping {
                host_path: "/h".to_string(),
                container_path: "/c".to_string(),
                read_only: false,
            }],
        };

        assert_eq!(config.image, "redis:7");
        assert_eq!(config.name, Some("cache".to_string()));
        assert_eq!(config.env.len(), 2);
        assert_eq!(config.env.get("A"), Some(&"1".to_string()));
        assert_eq!(config.env.get("B"), Some(&"2".to_string()));
        assert_eq!(config.ports.len(), 1);
        assert_eq!(config.ports[0].host_port, 6379);
        assert_eq!(config.ports[0].container_port, 6379);
        assert!(matches!(config.ports[0].protocol, Protocol::Tcp));
        assert_eq!(config.volumes.len(), 1);
        assert_eq!(config.volumes[0].host_path, "/h");
        assert_eq!(config.volumes[0].container_path, "/c");
        assert!(!config.volumes[0].read_only);
    }

    #[test]
    fn test_container_create_config_default_values() {
        let config = ContainerCreateConfig {
            image: "x".to_string(),
            name: None,
            env: HashMap::new(),
            ports: vec![],
            volumes: vec![],
        };
        assert!(config.env.is_empty());
        assert!(config.ports.is_empty());
        assert!(config.volumes.is_empty());
        assert!(config.name.is_none());
    }

    #[test]
    fn test_podman_runtime_default_trait() {
        let p: PodmanRuntime = Default::default();
        assert_eq!(p.name(), "podman");
    }

    #[test]
    fn test_podman_runtime_clone() {
        let p1 = PodmanRuntime::new();
        let p2 = p1.clone();
        assert_eq!(p1.name(), p2.name());
    }

    #[test]
    fn test_protocol_inequality() {
        assert_ne!(format!("{:?}", Protocol::Tcp), format!("{:?}", Protocol::Udp));
    }

    #[test]
    fn test_docker_runtime_clone() {
        let d1 = DockerRuntime::new();
        let d2 = d1.clone();
        assert_eq!(d1.name(), d2.name());
    }

    #[test]
    fn test_docker_runtime_debug() {
        assert_eq!(format!("{:?}", DockerRuntime::new()), "DockerRuntime");
    }

    #[test]
    fn test_podman_runtime_debug() {
        assert_eq!(format!("{:?}", PodmanRuntime::new()), "PodmanRuntime");
    }

    #[test]
    fn test_container_info_debug() {
        let info = ContainerInfo {
            id: "x".to_string(),
            name: "n".to_string(),
            image: "i".to_string(),
            status: "s".to_string(),
            created: "c".to_string(),
        };
        let dbg = format!("{:?}", info);
        assert!(dbg.contains("ContainerInfo"));
        assert!(dbg.contains("x"));
    }

    #[test]
    fn test_port_mapping_clone() {
        let p = PortMapping {
            host_port: 80,
            container_port: 80,
            protocol: Protocol::Tcp,
        };
        let p2 = p.clone();
        assert_eq!(p.host_port, p2.host_port);
        assert_eq!(p.container_port, p2.container_port);
        assert!(matches!(p2.protocol, Protocol::Tcp));
    }

    #[test]
    fn test_volume_mapping_clone() {
        let v = VolumeMapping {
            host_path: "/h".to_string(),
            container_path: "/c".to_string(),
            read_only: true,
        };
        let v2 = v.clone();
        assert_eq!(v.host_path, v2.host_path);
        assert_eq!(v.container_path, v2.container_path);
        assert!(v2.read_only);
    }

    #[test]
    fn test_container_create_config_clone() {
        let mut env = HashMap::new();
        env.insert("K".to_string(), "V".to_string());

        let config = ContainerCreateConfig {
            image: "alpine:latest".to_string(),
            name: Some("cloned".to_string()),
            env,
            ports: vec![PortMapping {
                host_port: 443,
                container_port: 443,
                protocol: Protocol::Tcp,
            }],
            volumes: vec![VolumeMapping {
                host_path: "/host".to_string(),
                container_path: "/container".to_string(),
                read_only: false,
            }],
        };

        let cloned = config.clone();
        assert_eq!(config.image, cloned.image);
        assert_eq!(config.name, cloned.name);
        assert_eq!(config.env.get("K"), cloned.env.get("K"));
        assert_eq!(config.ports.len(), cloned.ports.len());
        assert_eq!(config.ports[0].host_port, cloned.ports[0].host_port);
        assert_eq!(config.ports[0].container_port, cloned.ports[0].container_port);
        assert!(matches!(cloned.ports[0].protocol, Protocol::Tcp));
        assert_eq!(config.volumes.len(), cloned.volumes.len());
        assert_eq!(config.volumes[0].host_path, cloned.volumes[0].host_path);
        assert_eq!(config.volumes[0].container_path, cloned.volumes[0].container_path);
        assert_eq!(config.volumes[0].read_only, cloned.volumes[0].read_only);
    }

    #[test]
    fn test_container_create_config_with_multiple_ports() {
        let config = ContainerCreateConfig {
            image: "nginx:latest".to_string(),
            name: Some("multi-port".to_string()),
            env: HashMap::new(),
            ports: vec![
                PortMapping {
                    host_port: 8080,
                    container_port: 80,
                    protocol: Protocol::Tcp,
                },
                PortMapping {
                    host_port: 8443,
                    container_port: 443,
                    protocol: Protocol::Tcp,
                },
                PortMapping {
                    host_port: 53,
                    container_port: 53,
                    protocol: Protocol::Udp,
                },
            ],
            volumes: vec![],
        };

        assert_eq!(config.ports.len(), 3);
        assert_eq!(config.ports[0].host_port, 8080);
        assert_eq!(config.ports[0].container_port, 80);
        assert!(matches!(config.ports[0].protocol, Protocol::Tcp));
        assert_eq!(config.ports[1].host_port, 8443);
        assert_eq!(config.ports[1].container_port, 443);
        assert!(matches!(config.ports[1].protocol, Protocol::Tcp));
        assert_eq!(config.ports[2].host_port, 53);
        assert_eq!(config.ports[2].container_port, 53);
        assert!(matches!(config.ports[2].protocol, Protocol::Udp));
    }

    #[test]
    fn test_container_create_config_with_multiple_volumes() {
        let config = ContainerCreateConfig {
            image: "postgres:15".to_string(),
            name: Some("db".to_string()),
            env: HashMap::new(),
            ports: vec![],
            volumes: vec![
                VolumeMapping {
                    host_path: "/data".to_string(),
                    container_path: "/var/lib/postgresql/data".to_string(),
                    read_only: false,
                },
                VolumeMapping {
                    host_path: "/etc/config".to_string(),
                    container_path: "/etc/app".to_string(),
                    read_only: true,
                },
            ],
        };

        assert_eq!(config.volumes.len(), 2);
        assert_eq!(config.volumes[0].host_path, "/data");
        assert_eq!(config.volumes[0].container_path, "/var/lib/postgresql/data");
        assert!(!config.volumes[0].read_only);
        assert_eq!(config.volumes[1].host_path, "/etc/config");
        assert_eq!(config.volumes[1].container_path, "/etc/app");
        assert!(config.volumes[1].read_only);
    }

    #[test]
    fn test_protocol_two_vars_remain_equal() {
        let a = Protocol::Tcp;
        let b = a;
        assert!(matches!(a, Protocol::Tcp));
        assert!(matches!(b, Protocol::Tcp));

        let c = Protocol::Udp;
        let d = c;
        assert!(matches!(c, Protocol::Udp));
        assert!(matches!(d, Protocol::Udp));
    }

    #[test]
    fn test_port_mapping_docker_port_range() {
        let mapping = PortMapping {
            host_port: 0,
            container_port: 65535,
            protocol: Protocol::Udp,
        };
        assert_eq!(mapping.host_port, 0);
        assert_eq!(mapping.container_port, 65535);
        assert!(matches!(mapping.protocol, Protocol::Udp));
    }

    #[test]
    fn test_volume_mapping_with_empty_paths() {
        let v = VolumeMapping {
            host_path: "".to_string(),
            container_path: "".to_string(),
            read_only: false,
        };
        assert_eq!(v.host_path, "");
        assert_eq!(v.container_path, "");
        assert!(!v.read_only);
    }

    #[test]
    fn test_port_mapping_eq_with_same_fields() {
        // PortMapping does not derive PartialEq, so compare field-by-field.
        let a = PortMapping {
            host_port: 8080,
            container_port: 80,
            protocol: Protocol::Tcp,
        };
        let b = PortMapping {
            host_port: 8080,
            container_port: 80,
            protocol: Protocol::Tcp,
        };
        assert_eq!(a.host_port, b.host_port);
        assert_eq!(a.container_port, b.container_port);
        assert!(matches!(a.protocol, Protocol::Tcp));
        assert!(matches!(b.protocol, Protocol::Tcp));
    }

    #[test]
    #[allow(unused_assignments)]
    fn test_port_mapping_clone_then_mutate_original() {
        let mut original = PortMapping {
            host_port: 8080,
            container_port: 80,
            protocol: Protocol::Tcp,
        };
        let clone = original.clone();

        // Mutate the original; the clone must be unaffected.
        original.host_port = 9999;
        original.container_port = 1234;

        assert_eq!(clone.host_port, 8080);
        assert_eq!(clone.container_port, 80);
        assert!(matches!(clone.protocol, Protocol::Tcp));
    }

    #[test]
    fn test_port_mapping_in_hashmap() {
        let mut map: HashMap<String, PortMapping> = HashMap::new();

        let http = PortMapping {
            host_port: 8080,
            container_port: 80,
            protocol: Protocol::Tcp,
        };
        let dns = PortMapping {
            host_port: 53,
            container_port: 53,
            protocol: Protocol::Udp,
        };

        map.insert("http".to_string(), http);
        map.insert("dns".to_string(), dns);

        assert_eq!(map.len(), 2);
        let retrieved_http = map.get("http").expect("http mapping present");
        assert_eq!(retrieved_http.host_port, 8080);
        assert_eq!(retrieved_http.container_port, 80);
        assert!(matches!(retrieved_http.protocol, Protocol::Tcp));

        let retrieved_dns = map.get("dns").expect("dns mapping present");
        assert_eq!(retrieved_dns.host_port, 53);
        assert_eq!(retrieved_dns.container_port, 53);
        assert!(matches!(retrieved_dns.protocol, Protocol::Udp));
    }

    #[test]
    fn test_port_mapping_with_max_ports() {
        let mapping = PortMapping {
            host_port: 65535,
            container_port: 65535,
            protocol: Protocol::Tcp,
        };
        assert_eq!(mapping.host_port, u16::MAX);
        assert_eq!(mapping.container_port, u16::MAX);
        assert!(matches!(mapping.protocol, Protocol::Tcp));
    }

    #[test]
    fn test_port_mapping_with_min_ports() {
        let mapping = PortMapping {
            host_port: 0,
            container_port: 0,
            protocol: Protocol::Udp,
        };
        assert_eq!(mapping.host_port, 0);
        assert_eq!(mapping.container_port, 0);
        assert!(matches!(mapping.protocol, Protocol::Udp));
    }

    #[test]
    fn test_volume_mapping_eq_with_same_fields() {
        // VolumeMapping does not derive PartialEq, so compare field-by-field.
        let a = VolumeMapping {
            host_path: "/data".to_string(),
            container_path: "/var/data".to_string(),
            read_only: true,
        };
        let b = VolumeMapping {
            host_path: "/data".to_string(),
            container_path: "/var/data".to_string(),
            read_only: true,
        };
        assert_eq!(a.host_path, b.host_path);
        assert_eq!(a.container_path, b.container_path);
        assert_eq!(a.read_only, b.read_only);
    }

    #[test]
    #[allow(unused_assignments)]
    fn test_volume_mapping_clone_then_mutate_original() {
        let mut original = VolumeMapping {
            host_path: "/data".to_string(),
            container_path: "/var/data".to_string(),
            read_only: true,
        };
        let clone = original.clone();

        // Mutate the original's read_only flag; the clone must be unaffected.
        original.read_only = false;
        original.host_path = "/other".to_string();
        original.container_path = "/var/other".to_string();

        assert!(clone.read_only);
        assert_eq!(clone.host_path, "/data");
        assert_eq!(clone.container_path, "/var/data");
    }

    #[test]
    fn test_container_create_config_with_empty_collections() {
        let config = ContainerCreateConfig {
            image: "scratch".to_string(),
            name: None,
            env: HashMap::new(),
            ports: vec![],
            volumes: vec![],
        };
        assert!(config.env.is_empty());
        assert!(config.ports.is_empty());
        assert!(config.volumes.is_empty());
        assert_eq!(config.env.len(), 0);
        assert_eq!(config.ports.len(), 0);
        assert_eq!(config.volumes.len(), 0);
        assert_eq!(config.image, "scratch");
        assert!(config.name.is_none());
    }

    #[test]
    fn test_container_create_config_clone_preserves_nested_collections() {
        let mut env = HashMap::new();
        env.insert("ORIGINAL".to_string(), "yes".to_string());

        let mut config = ContainerCreateConfig {
            image: "alpine:3".to_string(),
            name: Some("nested-clone".to_string()),
            env,
            ports: vec![PortMapping {
                host_port: 8000,
                container_port: 8000,
                protocol: Protocol::Tcp,
            }],
            volumes: vec![VolumeMapping {
                host_path: "/h".to_string(),
                container_path: "/c".to_string(),
                read_only: false,
            }],
        };

        let cloned = config.clone();

        // Mutate the original's nested collections; the clone's must be unchanged.
        config.env.insert("INJECTED".to_string(), "no".to_string());
        config.ports.push(PortMapping {
            host_port: 9000,
            container_port: 9000,
            protocol: Protocol::Udp,
        });
        config.volumes.push(VolumeMapping {
            host_path: "/h2".to_string(),
            container_path: "/c2".to_string(),
            read_only: true,
        });

        // Original has the new state.
        assert_eq!(config.env.len(), 2);
        assert!(config.env.contains_key("INJECTED"));
        assert_eq!(config.ports.len(), 2);
        assert_eq!(config.volumes.len(), 2);

        // Clone retains the original snapshot.
        assert_eq!(cloned.env.len(), 1);
        assert!(!cloned.env.contains_key("INJECTED"));
        assert_eq!(cloned.env.get("ORIGINAL"), Some(&"yes".to_string()));
        assert_eq!(cloned.ports.len(), 1);
        assert_eq!(cloned.ports[0].host_port, 8000);
        assert_eq!(cloned.ports[0].container_port, 8000);
        assert!(matches!(cloned.ports[0].protocol, Protocol::Tcp));
        assert_eq!(cloned.volumes.len(), 1);
        assert_eq!(cloned.volumes[0].host_path, "/h");
        assert_eq!(cloned.volumes[0].container_path, "/c");
        assert!(!cloned.volumes[0].read_only);
    }

    #[test]
    fn test_container_info_with_special_chars() {
        let info = ContainerInfo {
            id: "abc/def:ghi-jkl_mno.pqr".to_string(),
            name: "weird.name_with-chars".to_string(),
            image: "registry.example.com:5000/team/service:1.2.3-rc.4".to_string(),
            status: "Up 2 hours".to_string(),
            created: "2024-06-12T10:00:00Z".to_string(),
        };
        assert_eq!(info.id, "abc/def:ghi-jkl_mno.pqr");
        assert_eq!(info.name, "weird.name_with-chars");
        assert_eq!(
            info.image,
            "registry.example.com:5000/team/service:1.2.3-rc.4"
        );
        assert_eq!(info.status, "Up 2 hours");
        assert_eq!(info.created, "2024-06-12T10:00:00Z");

        // Round-trip the special chars through Clone and Debug formatting.
        let cloned = info.clone();
        assert_eq!(cloned.id, "abc/def:ghi-jkl_mno.pqr");

        let dbg = format!("{:?}", info);
        assert!(dbg.contains("abc/def:ghi-jkl_mno.pqr"));
    }
}
