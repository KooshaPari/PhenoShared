//! In-memory adapter for [`RegistryPort`].
//!
//! Thread-safe via `std::sync::RwLock`. Suitable for tests, single-process
//! service meshes, and as a reference implementation for new adapters.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use uuid::Uuid;

use crate::{HealthStatus, RegistryError, RegistryPort, ServiceRegistration};

/// In-memory registry — zero external dependencies, suitable for tests and
/// single-process deployments.
#[derive(Clone, Default)]
pub struct InMemoryRegistry {
    inner: Arc<RwLock<HashMap<Uuid, ServiceRegistration>>>,
}

impl RegistryPort for InMemoryRegistry {
    async fn register(&self, svc: ServiceRegistration) -> Result<(), RegistryError> {
        let mut map = self
            .inner
            .write()
            .map_err(|e| RegistryError::Internal(e.to_string()))?;
        if map.contains_key(&svc.instance_id) {
            return Err(RegistryError::AlreadyRegistered {
                id: svc.instance_id.to_string(),
            });
        }
        map.insert(svc.instance_id, svc);
        Ok(())
    }

    async fn deregister(&self, instance_id: Uuid) -> Result<(), RegistryError> {
        let mut map = self
            .inner
            .write()
            .map_err(|e| RegistryError::Internal(e.to_string()))?;
        map.remove(&instance_id)
            .map(|_| ())
            .ok_or_else(|| RegistryError::NotFound(instance_id.to_string()))
    }

    async fn discover(&self, name: &str) -> Result<Vec<ServiceRegistration>, RegistryError> {
        let map = self
            .inner
            .read()
            .map_err(|e| RegistryError::Internal(e.to_string()))?;
        let known: Vec<_> = map.values().filter(|s| s.name == name).collect();
        if known.is_empty() {
            return Err(RegistryError::NotFound(name.to_owned()));
        }
        let healthy: Vec<ServiceRegistration> = known
            .into_iter()
            .filter(|s| s.health == HealthStatus::Healthy)
            .cloned()
            .collect();
        Ok(healthy)
    }

    async fn set_health(
        &self,
        instance_id: Uuid,
        status: HealthStatus,
    ) -> Result<(), RegistryError> {
        let mut map = self
            .inner
            .write()
            .map_err(|e| RegistryError::Internal(e.to_string()))?;
        match map.get_mut(&instance_id) {
            Some(svc) => {
                svc.health = status;
                Ok(())
            }
            None => Err(RegistryError::NotFound(instance_id.to_string())),
        }
    }

    async fn list_all(&self) -> Result<Vec<ServiceRegistration>, RegistryError> {
        let map = self
            .inner
            .read()
            .map_err(|e| RegistryError::Internal(e.to_string()))?;
        Ok(map.values().cloned().collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::HealthStatus;

    fn reg(name: &str) -> ServiceRegistration {
        ServiceRegistration::new(name, "127.0.0.1", 8080)
    }

    // ── register ────────────────────────────────────────────────────────────

    #[tokio::test]
    async fn register_new_service_succeeds() {
        let r = InMemoryRegistry::default();
        assert!(r.register(reg("svc-a")).await.is_ok());
    }

    #[tokio::test]
    async fn register_duplicate_id_errors() {
        let r = InMemoryRegistry::default();
        let svc = reg("svc-a");
        r.register(svc.clone()).await.unwrap();
        let err = r.register(svc).await.unwrap_err();
        assert!(matches!(err, RegistryError::AlreadyRegistered { .. }));
    }

    // ── deregister ───────────────────────────────────────────────────────────

    #[tokio::test]
    async fn deregister_known_instance_succeeds() {
        let r = InMemoryRegistry::default();
        let svc = reg("svc-b");
        let id = svc.instance_id;
        r.register(svc).await.unwrap();
        assert!(r.deregister(id).await.is_ok());
    }

    #[tokio::test]
    async fn deregister_unknown_instance_errors() {
        let r = InMemoryRegistry::default();
        let id = Uuid::new_v4();
        let err = r.deregister(id).await.unwrap_err();
        assert!(matches!(err, RegistryError::NotFound(_)));
    }

    // ── discover ─────────────────────────────────────────────────────────────

    #[tokio::test]
    async fn discover_returns_healthy_instances_only() {
        let r = InMemoryRegistry::default();
        let healthy = reg("svc-c");
        let mut sick = reg("svc-c");
        sick.health = HealthStatus::Unhealthy;

        r.register(healthy.clone()).await.unwrap();
        r.register(sick).await.unwrap();

        let found = r.discover("svc-c").await.unwrap();
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].instance_id, healthy.instance_id);
    }

    #[tokio::test]
    async fn discover_unknown_service_errors() {
        let r = InMemoryRegistry::default();
        let err = r.discover("ghost").await.unwrap_err();
        assert!(matches!(err, RegistryError::NotFound(_)));
    }

    #[tokio::test]
    async fn discover_all_unhealthy_returns_empty_vec() {
        let r = InMemoryRegistry::default();
        let mut svc = reg("svc-d");
        svc.health = HealthStatus::Unhealthy;
        r.register(svc).await.unwrap();
        let found = r.discover("svc-d").await.unwrap();
        assert!(found.is_empty());
    }

    // ── set_health ───────────────────────────────────────────────────────────

    #[tokio::test]
    async fn set_health_updates_status() {
        let r = InMemoryRegistry::default();
        let svc = reg("svc-e");
        let id = svc.instance_id;
        r.register(svc).await.unwrap();
        r.set_health(id, HealthStatus::Unhealthy).await.unwrap();
        let all = r.list_all().await.unwrap();
        let updated = all.iter().find(|s| s.instance_id == id).unwrap();
        assert_eq!(updated.health, HealthStatus::Unhealthy);
    }

    #[tokio::test]
    async fn set_health_unknown_id_errors() {
        let r = InMemoryRegistry::default();
        let err = r
            .set_health(Uuid::new_v4(), HealthStatus::Healthy)
            .await
            .unwrap_err();
        assert!(matches!(err, RegistryError::NotFound(_)));
    }

    // ── list_all ─────────────────────────────────────────────────────────────

    #[tokio::test]
    async fn list_all_returns_all_instances() {
        let r = InMemoryRegistry::default();
        r.register(reg("svc-f")).await.unwrap();
        r.register(reg("svc-g")).await.unwrap();
        assert_eq!(r.list_all().await.unwrap().len(), 2);
    }

    // ── tags ─────────────────────────────────────────────────────────────────

    #[tokio::test]
    async fn service_registration_preserves_tags() {
        let r = InMemoryRegistry::default();
        let svc = reg("svc-h").with_tags(["v2", "us-east"]);
        r.register(svc.clone()).await.unwrap();
        let all = r.list_all().await.unwrap();
        let found = all
            .iter()
            .find(|s| s.instance_id == svc.instance_id)
            .unwrap();
        assert!(found.tags.contains(&"v2".to_string()));
    }
}
