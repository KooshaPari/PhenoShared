// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Discoverer module - Service discovery for heliosHarness
//! Find and register available services

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Service descriptor
#[derive(Debug, Clone)]
pub struct ServiceInfo {
    pub name: String,
    pub address: String,
    pub port: u16,
    pub metadata: HashMap<String, String>,
    pub healthy: bool,
}

/// Service registry
pub struct ServiceRegistry {
    services: Arc<RwLock<HashMap<String, ServiceInfo>>>,
}

impl ServiceRegistry {
    pub fn new() -> Self {
        Self { services: Arc::new(RwLock::new(HashMap::new())) }
    }

    /// Register a service
    pub async fn register(&self, info: ServiceInfo) {
        let mut services = self.services.write().await;
        services.insert(info.name.clone(), info);
    }

    /// Unregister a service
    pub async fn unregister(&self, name: &str) -> bool {
        let mut services = self.services.write().await;
        services.remove(name).is_some()
    }

    /// Get service by name
    pub async fn get(&self, name: &str) -> Option<ServiceInfo> {
        let services = self.services.read().await;
        services.get(name).cloned()
    }

    /// List all services
    pub async fn list(&self) -> Vec<ServiceInfo> {
        let services = self.services.read().await;
        services.values().cloned().collect()
    }

    /// Get healthy services
    pub async fn healthy(&self) -> Vec<ServiceInfo> {
        let services = self.services.read().await;
        services.values().filter(|s| s.healthy).cloned().collect()
    }

    /// Update service health
    pub async fn set_healthy(&self, name: &str, healthy: bool) -> bool {
        let mut services = self.services.write().await;
        if let Some(service) = services.get_mut(name) {
            service.healthy = healthy;
            true
        } else {
            false
        }
    }
}

impl Default for ServiceRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn svc(name: &str, healthy: bool) -> ServiceInfo {
        ServiceInfo {
            name: name.to_string(),
            address: "127.0.0.1".to_string(),
            port: 8080,
            metadata: HashMap::new(),
            healthy,
        }
    }

    // Traces to: FR-HELIOS-DISCO-001 (register + get)
    #[tokio::test]
    async fn register_then_get_returns_service() {
        let reg = ServiceRegistry::new();
        reg.register(svc("api", true)).await;
        let got = reg.get("api").await.expect("service present");
        assert_eq!(got.name, "api");
        assert_eq!(got.port, 8080);
        assert!(reg.get("missing").await.is_none());
    }

    // Traces to: FR-HELIOS-DISCO-002 (unregister)
    #[tokio::test]
    async fn unregister_reports_removal() {
        let reg = ServiceRegistry::new();
        reg.register(svc("api", true)).await;
        assert!(reg.unregister("api").await);
        assert!(!reg.unregister("api").await);
        assert!(reg.get("api").await.is_none());
    }

    // Traces to: FR-HELIOS-DISCO-003 (list + healthy filter)
    #[tokio::test]
    async fn list_and_healthy_filter() {
        let reg = ServiceRegistry::new();
        reg.register(svc("a", true)).await;
        reg.register(svc("b", false)).await;
        assert_eq!(reg.list().await.len(), 2);
        let healthy = reg.healthy().await;
        assert_eq!(healthy.len(), 1);
        assert_eq!(healthy[0].name, "a");
    }

    // Traces to: FR-HELIOS-DISCO-004 (health toggle)
    #[tokio::test]
    async fn set_healthy_updates_existing_only() {
        let reg = ServiceRegistry::new();
        reg.register(svc("a", true)).await;
        assert!(reg.set_healthy("a", false).await);
        assert!(!reg.get("a").await.unwrap().healthy);
        assert!(!reg.set_healthy("ghost", true).await);
    }

    // Traces to: FR-HELIOS-DISCO-005 (default constructor)
    #[tokio::test]
    async fn default_registry_starts_empty() {
        let reg = ServiceRegistry::default();
        assert!(reg.list().await.is_empty());
    }
}
