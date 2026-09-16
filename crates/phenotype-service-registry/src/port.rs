use crate::{HealthStatus, RegistryError, ServiceRegistration};
use uuid::Uuid;

/// Hexagonal **port** — the only trait consumers depend on.
///
/// All adapters (in-memory, Consul, etcd …) implement this trait.
/// Consumers should accept `impl RegistryPort` or `Arc<dyn RegistryPort>`.
#[allow(async_fn_in_trait)] // stable since 1.75; no Send bound needed for in-process adapters
pub trait RegistryPort {
    /// Register a new service instance.
    ///
    /// Returns `Err(AlreadyRegistered)` if the `instance_id` is already present.
    async fn register(&self, svc: ServiceRegistration) -> Result<(), RegistryError>;

    /// Deregister a service instance by its unique ID.
    ///
    /// Returns `Err(NotFound)` if the ID is unknown.
    async fn deregister(&self, instance_id: Uuid) -> Result<(), RegistryError>;

    /// Discover all **healthy** instances of a named service.
    ///
    /// Returns an empty `Vec` (not an error) when the service is known but has
    /// no healthy instances.  Returns `Err(NotFound)` when the service name has
    /// never been registered.
    async fn discover(&self, name: &str) -> Result<Vec<ServiceRegistration>, RegistryError>;

    /// Update the health status of a specific instance.
    ///
    /// Returns `Err(NotFound)` if the ID is unknown.
    async fn set_health(
        &self,
        instance_id: Uuid,
        status: HealthStatus,
    ) -> Result<(), RegistryError>;

    /// Return every registered instance regardless of health.
    async fn list_all(&self) -> Result<Vec<ServiceRegistration>, RegistryError>;
}
