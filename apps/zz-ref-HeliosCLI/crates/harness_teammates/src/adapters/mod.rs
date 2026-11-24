// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Adapters - Concrete implementations

use crate::domain::{DelegationRequest, DelegationResult, HealthStatus, Teammate};
use crate::ports::{DelegationPort, HealthCheckPort, TeammateRegistryPort};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use tracing::debug;
use uuid::Uuid;

/// In-memory teammate registry using std::sync::RwLock
pub struct InMemoryTeammateRegistry {
    teammates: Arc<RwLock<HashMap<String, Teammate>>>,
}

impl InMemoryTeammateRegistry {
    pub fn new() -> Self {
        Self { teammates: Arc::new(RwLock::new(HashMap::new())) }
    }
}

impl Default for InMemoryTeammateRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl TeammateRegistryPort for InMemoryTeammateRegistry {
    fn register(&self, teammate: Teammate) {
        debug!(id = %teammate.id, name = %teammate.name, "registering teammate");
        if let Ok(mut t) = self.teammates.write() {
            t.insert(teammate.id.clone(), teammate);
        }
    }

    fn get(&self, id: &str) -> Option<Teammate> {
        self.teammates.read().ok()?.get(id).cloned()
    }

    fn list(&self) -> Vec<Teammate> {
        self.teammates.read().ok().map(|t| t.values().cloned().collect()).unwrap_or_default()
    }

    fn find_by_role(&self, role: &str) -> Vec<Teammate> {
        self.teammates
            .read()
            .ok()
            .map(|t| t.values().filter(|tm| tm.role == role).cloned().collect())
            .unwrap_or_default()
    }

    fn unregister(&self, id: &str) -> bool {
        self.teammates.write().ok().map(|mut t| t.remove(id).is_some()).unwrap_or(false)
    }
}

/// Simple delegation adapter (stub implementation)
pub struct SimpleDelegationAdapter;

impl DelegationPort for SimpleDelegationAdapter {
    fn submit(&self, request: DelegationRequest) -> DelegationResult {
        debug!(teammate = %request.teammate_id, task = %request.task_description, "submitting delegation");
        DelegationResult {
            delegation_id: Uuid::new_v4().to_string(),
            teammate_id: request.teammate_id.clone(),
            status: crate::domain::DelegationStatus::Completed,
            result: Some(format!("Completed: {}", request.task_description)),
            error: None,
            duration_ms: 0,
            evidence: vec![],
        }
    }

    fn status(&self, _delegation_id: &str) -> Option<DelegationResult> {
        None
    }

    fn cancel(&self, _delegation_id: &str) -> bool {
        false
    }
}

/// Health check adapter
pub struct HealthCheckAdapter {
    registry: Arc<RwLock<HashMap<String, Teammate>>>,
}

impl HealthCheckAdapter {
    pub fn new(registry: Arc<RwLock<HashMap<String, Teammate>>>) -> Self {
        Self { registry }
    }
}

impl HealthCheckPort for HealthCheckAdapter {
    fn check_health(&self, _teammate_id: &str) -> HealthStatus {
        HealthStatus::Healthy
    }

    fn healthy_teammates(&self) -> Vec<Teammate> {
        self.registry.read().ok().map(|t| t.values().cloned().collect()).unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn in_memory_registry_roundtrip() {
        let registry = InMemoryTeammateRegistry::new();
        let teammate = Teammate::new("t1", "Coder", "code", "writes code");
        registry.register(teammate.clone());
        assert_eq!(registry.get("t1").unwrap().name, "Coder");
        assert_eq!(registry.find_by_role("code").len(), 1);
        assert!(registry.unregister("t1"));
    }

    #[test]
    fn simple_delegation_adapter_completes_request() {
        let adapter = SimpleDelegationAdapter;
        let result = adapter.submit(DelegationRequest::new("t1", "run tests"));
        assert_eq!(result.status, crate::domain::DelegationStatus::Completed);
        assert!(adapter.status("missing").is_none());
        assert!(!adapter.cancel("missing"));
    }

    #[test]
    fn health_check_adapter_lists_registry_teammates() {
        let registry = Arc::new(RwLock::new(HashMap::new()));
        registry
            .write()
            .unwrap()
            .insert("t1".to_string(), Teammate::new("t1", "Coder", "code", "writes code"));
        let adapter = HealthCheckAdapter::new(registry);
        assert_eq!(adapter.check_health("t1"), HealthStatus::Healthy);
        assert_eq!(adapter.healthy_teammates().len(), 1);
    }
}
