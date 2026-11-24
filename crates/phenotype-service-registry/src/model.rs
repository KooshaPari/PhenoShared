use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Liveness state of a registered service instance.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum HealthStatus {
    Healthy,
    Unhealthy,
    #[default]
    Unknown,
}

/// A single service instance entry in the registry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceRegistration {
    /// Stable unique ID for this instance (auto-generated if not supplied).
    pub instance_id: Uuid,
    /// Logical service name (e.g. `"user-svc"`).
    pub name: String,
    /// Reachable host/IP.
    pub host: String,
    /// Port the service listens on.
    pub port: u16,
    /// Optional free-form tags for filtering during discovery.
    pub tags: Vec<String>,
    /// Current health state (updated by health checks).
    pub health: HealthStatus,
    /// Wall-clock time the instance was first registered.
    pub registered_at: DateTime<Utc>,
}

impl ServiceRegistration {
    /// Create a minimal registration with an auto-generated instance ID.
    pub fn new(name: impl Into<String>, host: impl Into<String>, port: u16) -> Self {
        Self {
            instance_id: Uuid::new_v4(),
            name: name.into(),
            host: host.into(),
            port,
            tags: vec![],
            health: HealthStatus::Healthy,
            registered_at: Utc::now(),
        }
    }

    /// Builder-style tag attachment.
    pub fn with_tags(mut self, tags: impl IntoIterator<Item = impl Into<String>>) -> Self {
        self.tags = tags.into_iter().map(Into::into).collect();
        self
    }

    /// Convenience: the `host:port` address string.
    pub fn address(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }
}
