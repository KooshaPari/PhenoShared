//! `phenotype-service-registry` — service registration, discovery, and health.
//!
//! Migrated from KooshaPari/Servion (archived skeleton, `nexus` crate intent).
//!
//! # Architecture (Hexagonal)
//!
//! * **Port**: [`RegistryPort`] trait — the only surface consumers depend on.
//! * **Adapters**: [`InMemoryRegistry`] (default, sync-safe); further adapters
//!   (Consul, etcd) can be added without changing the port.
//!
//! # Quick start
//!
//! ```rust,no_run
//! use phenotype_service_registry::{InMemoryRegistry, RegistryPort, ServiceRegistration};
//!
//! #[tokio::main]
//! async fn main() {
//!     let registry = InMemoryRegistry::default();
//!     let svc = ServiceRegistration::new("user-svc", "127.0.0.1", 8080);
//!     registry.register(svc.clone()).await.unwrap();
//!     let found = registry.discover("user-svc").await.unwrap();
//!     assert!(!found.is_empty());
//! }
//! ```

pub mod error;
pub mod memory;
pub mod model;
pub mod port;

pub use error::RegistryError;
pub use memory::InMemoryRegistry;
pub use model::{HealthStatus, ServiceRegistration};
pub use port::RegistryPort;
