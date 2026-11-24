//! Contract tests for verifying adapter compliance.
//!
//! ## xDD Methodology: CDD (Contract-Driven Development)
//!
//! These tests verify that adapters correctly implement ports
//! by testing against the contract specification.

use std::collections::HashMap;

use phenotype_xdd_lib::contract::{Contract, ContractVerifier};

// ============================================================================
// Example Contract: Key-Value Storage Port
// ============================================================================

/// Storage port trait - defines what a storage adapter must implement.
trait StoragePort {
    fn get(&self, key: &str) -> Option<String>;
    fn set(&mut self, key: &str, value: &str) -> bool;
    fn delete(&mut self, key: &str) -> bool;
    fn keys(&self) -> Vec<String>;
}

/// Contract for StoragePort.
#[allow(dead_code)]
struct StorageContract;

impl Contract for StorageContract {
    fn name() -> &'static str {
        "StoragePort"
    }

    fn verify() -> Result<(), phenotype_xdd_lib::domain::XddError> {
        let mut store = MemoryStorage::default();

        // Test 1: Set and get
        store.set("key1", "value1");
        assert_eq!(store.get("key1"), Some("value1".to_string()));

        // Test 2: Overwrite
        store.set("key1", "value2");
        assert_eq!(store.get("key1"), Some("value2".to_string()));

        // Test 3: Delete
        store.delete("key1");
        assert_eq!(store.get("key1"), None);

        // Test 4: Keys
        store.set("key1", "value1");
        store.set("key2", "value2");
        let keys = store.keys();
        assert!(keys.contains(&"key1".to_string()));
        assert!(keys.contains(&"key2".to_string()));

        Ok(())
    }
}

// ============================================================================
// Memory Storage Adapter (Implements the port)
// ============================================================================

#[derive(Default)]
struct MemoryStorage {
    data: HashMap<String, String>,
}

impl StoragePort for MemoryStorage {
    fn get(&self, key: &str) -> Option<String> {
        self.data.get(key).cloned()
    }

    fn set(&mut self, key: &str, value: &str) -> bool {
        self.data.insert(key.to_string(), value.to_string());
        true
    }

    fn delete(&mut self, key: &str) -> bool {
        self.data.remove(key).is_some()
    }

    fn keys(&self) -> Vec<String> {
        self.data.keys().cloned().collect()
    }
}

// ============================================================================
// Contract Verification Tests
// ============================================================================

#[test]
fn test_memory_storage_contract() {
    // This test verifies that MemoryStorage implements StoragePort correctly
    let mut store = MemoryStorage::default();

    // Set and get
    store.set("test", "value");
    assert_eq!(store.get("test"), Some("value".to_string()));

    // Delete
    store.delete("test");
    assert_eq!(store.get("test"), None);

    // Multiple keys
    store.set("a", "1");
    store.set("b", "2");
    store.set("c", "3");
    let keys = store.keys();
    assert_eq!(keys.len(), 3);
}

#[test]
fn test_contract_verifier() {
    let mut verifier = ContractVerifier::new();
    verifier.assert_eq(1 + 1, 2, "basic arithmetic");
    verifier.assert_eq("hello".len(), 5, "string length");
    let result = verifier.result("test_contract");
    assert!(result.passed);
}

#[test]
fn test_contract_result_failure() {
    use phenotype_xdd_lib::contract::{ContractFailure, ContractResult};

    let failures = vec![ContractFailure {
        expectation: "value > 0".to_string(),
        actual: "value = 0".to_string(),
        location: Some("src/lib.rs:42".to_string()),
    }];

    let result = ContractResult::failure("test", 1, failures);
    assert!(!result.passed);
    assert_eq!(result.failures.len(), 1);
}
