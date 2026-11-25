//! Health-check types for the event bus.
//!
//! Integrates with phenotype-health for unified health reporting.

use std::future::Future;
use std::pin::Pin;

pub use phenotype_health::{HealthChecker, HealthStatus};

/// Connection state of the event bus.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BusHealth {
    Connected,
    Disconnected,
}

impl From<BusHealth> for HealthStatus {
    fn from(bus: BusHealth) -> Self {
        match bus {
            BusHealth::Connected => HealthStatus::Healthy,
            BusHealth::Disconnected => HealthStatus::Unhealthy,
        }
    }
}

/// Health checker for NATS event bus connections.
pub struct NatsHealthChecker {
    name: String,
}

impl NatsHealthChecker {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

impl HealthChecker for NatsHealthChecker {
    fn name(&self) -> &str {
        &self.name
    }

    fn check(&self) -> Pin<Box<dyn Future<Output = HealthStatus> + Send + '_>> {
        // Actual check would query NATS connection state.
        // For now, returns Unknown - implementors should override.
        Box::pin(async move { HealthStatus::Unknown })
    }
}
