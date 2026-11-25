//! Mock implementations of phenotype-contracts port traits.
//!
//! Provides test doubles for hexagonal architecture ports.
//!
//! # FR Traceability
//! - FR-TEST-003: Mock port implementations

use phenotype_contracts::outbound::{CachePort, EventBus, Repository};
use phenotype_error_core::DomainError;
use std::collections::HashMap;
use std::fmt::Debug;
use std::sync::{Arc, Mutex, RwLock};

/// Mock repository with configurable behavior and call tracking.
///
/// # FR Traceability
/// - FR-TEST-003-001: Mock Repository implementation
pub struct MockRepository<Entity, Id> {
    data: Arc<RwLock<HashMap<Id, Entity>>>,
    call_log: Arc<Mutex<Vec<RepoCall<Id>>>>,
    fail_next: Arc<RwLock<Option<DomainError>>>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
enum RepoCall<Id> {
    Save { id: Id },
    Get { id: Id },
    Delete { id: Id },
    List,
}

impl<
        Entity: Clone + Send + Sync + Debug,
        Id: Clone + Eq + std::hash::Hash + Send + Sync + Debug,
    > MockRepository<Entity, Id>
{
    /// Create a new empty mock repository.
    ///
    /// # FR Traceability
    /// - FR-TEST-003-002: Mock constructor
    pub fn new() -> Self {
        Self {
            data: Arc::new(RwLock::new(HashMap::new())),
            call_log: Arc::new(Mutex::new(Vec::new())),
            fail_next: Arc::new(RwLock::new(None)),
        }
    }

    /// Pre-populate with data.
    pub fn with_data(data: HashMap<Id, Entity>) -> Self {
        Self {
            data: Arc::new(RwLock::new(data)),
            call_log: Arc::new(Mutex::new(Vec::new())),
            fail_next: Arc::new(RwLock::new(None)),
        }
    }

    /// Configure the next call to fail with the given error.
    ///
    /// # FR Traceability
    /// - FR-TEST-003-003: Failure simulation
    pub fn fail_next(&self, error: DomainError) {
        *self.fail_next.write().unwrap() = Some(error);
    }

    /// Get the call log for verification.
    ///
    /// # FR Traceability
    /// - FR-TEST-003-004: Call verification
    pub fn calls(&self) -> Vec<String> {
        self.call_log
            .lock()
            .unwrap()
            .iter()
            .map(|c| format!("{:?}", c))
            .collect()
    }

    /// Get call count.
    pub fn call_count(&self) -> usize {
        self.call_log.lock().unwrap().len()
    }

    /// Check if save was called.
    pub fn was_saved(&self, id: &Id) -> bool
    where
        Id: std::fmt::Debug,
    {
        self.call_log
            .lock()
            .unwrap()
            .iter()
            .any(|c| matches!(c, RepoCall::Save { id: saved_id } if format!("{:?}", saved_id) == format!("{:?}", id)))
    }

    /// Clear all data and call history.
    pub fn clear(&self) {
        self.data.write().unwrap().clear();
        self.call_log.lock().unwrap().clear();
        *self.fail_next.write().unwrap() = None;
    }

    fn check_failure(&self) -> Result<(), DomainError> {
        if let Some(err) = self.fail_next.write().unwrap().take() {
            return Err(err);
        }
        Ok(())
    }
}

impl<
        Entity: Clone + Send + Sync + Debug,
        Id: Clone + Eq + std::hash::Hash + std::fmt::Debug + Send + Sync,
    > Default for MockRepository<Entity, Id>
{
    fn default() -> Self {
        Self::new()
    }
}

impl<
        Entity: Clone + Send + Sync + Debug,
        Id: Clone + Eq + std::hash::Hash + std::fmt::Debug + Send + Sync,
    > Repository for MockRepository<Entity, Id>
{
    type Entity = Entity;
    type Id = Id;

    fn save(&self, id: Self::Id, entity: Self::Entity) -> Result<(), DomainError> {
        self.check_failure()?;
        self.call_log
            .lock()
            .unwrap()
            .push(RepoCall::Save { id: id.clone() });
        self.data.write().unwrap().insert(id, entity);
        Ok(())
    }

    fn get(&self, id: &Self::Id) -> Result<Self::Entity, DomainError> {
        self.check_failure()?;
        self.call_log
            .lock()
            .unwrap()
            .push(RepoCall::Get { id: id.clone() });
        self.data
            .read()
            .unwrap()
            .get(id)
            .cloned()
            .ok_or_else(|| DomainError::NotFound {
                entity: "Entity".to_string(),
                id: format!("{:?}", id),
            })
    }

    fn delete(&self, id: &Self::Id) -> Result<(), DomainError> {
        self.check_failure()?;
        self.call_log
            .lock()
            .unwrap()
            .push(RepoCall::Delete { id: id.clone() });
        self.data.write().unwrap().remove(id);
        Ok(())
    }

    fn list(&self) -> Result<Vec<Self::Entity>, DomainError> {
        self.check_failure()?;
        self.call_log.lock().unwrap().push(RepoCall::List);
        Ok(self.data.read().unwrap().values().cloned().collect())
    }
}

/// Mock cache with configurable behavior and hit/miss tracking.
///
/// # FR Traceability
/// - FR-TEST-003-005: Mock CachePort implementation
pub struct MockCache<Key: Debug, Value> {
    store: Arc<RwLock<HashMap<Key, Value>>>,
    hit_count: Arc<RwLock<usize>>,
    miss_count: Arc<RwLock<usize>>,
    call_log: Arc<Mutex<Vec<CacheCall<Key>>>>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
enum CacheCall<Key: Debug> {
    Get { key: Key },
    Set { key: Key },
    Invalidate { key: Key },
}

impl<Key: Clone + Eq + std::hash::Hash + Debug, Value: Clone> MockCache<Key, Value> {
    /// Create a new empty mock cache.
    ///
    /// # FR Traceability
    /// - FR-TEST-003-006: Cache mock constructor
    pub fn new() -> Self {
        Self {
            store: Arc::new(RwLock::new(HashMap::new())),
            hit_count: Arc::new(RwLock::new(0)),
            miss_count: Arc::new(RwLock::new(0)),
            call_log: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Get hit count for cache hit ratio analysis.
    ///
    /// # FR Traceability
    /// - FR-TEST-003-007: Cache metrics
    pub fn hit_count(&self) -> usize {
        *self.hit_count.read().unwrap()
    }

    /// Get miss count.
    pub fn miss_count(&self) -> usize {
        *self.miss_count.read().unwrap()
    }

    /// Calculate hit ratio (0.0 to 1.0).
    pub fn hit_ratio(&self) -> f64 {
        let hits = self.hit_count();
        let misses = self.miss_count();
        let total = hits + misses;
        if total == 0 {
            0.0
        } else {
            hits as f64 / total as f64
        }
    }

    /// Get call log.
    pub fn calls(&self) -> Vec<String> {
        self.call_log
            .lock()
            .unwrap()
            .iter()
            .map(|c| format!("{:?}", c))
            .collect()
    }

    /// Clear all data and metrics.
    pub fn clear(&self) {
        self.store.write().unwrap().clear();
        *self.hit_count.write().unwrap() = 0;
        *self.miss_count.write().unwrap() = 0;
        self.call_log.lock().unwrap().clear();
    }
}

impl<Key: Clone + Eq + std::hash::Hash + Debug, Value: Clone> Default for MockCache<Key, Value> {
    fn default() -> Self {
        Self::new()
    }
}

impl<Key: Clone + Eq + std::hash::Hash + Debug + Send + Sync, Value: Clone + Send + Sync> CachePort
    for MockCache<Key, Value>
{
    type Key = Key;
    type Value = Value;

    fn get(&self, key: &Self::Key) -> Result<Option<Self::Value>, DomainError> {
        self.call_log
            .lock()
            .unwrap()
            .push(CacheCall::Get { key: key.clone() });
        let result = self.store.read().unwrap().get(key).cloned();
        if result.is_some() {
            *self.hit_count.write().unwrap() += 1;
        } else {
            *self.miss_count.write().unwrap() += 1;
        }
        Ok(result)
    }

    fn set(&self, key: Self::Key, value: Self::Value) -> Result<(), DomainError> {
        self.call_log
            .lock()
            .unwrap()
            .push(CacheCall::Set { key: key.clone() });
        self.store.write().unwrap().insert(key, value);
        Ok(())
    }

    fn invalidate(&self, key: &Self::Key) -> Result<(), DomainError> {
        self.call_log
            .lock()
            .unwrap()
            .push(CacheCall::Invalidate { key: key.clone() });
        self.store.write().unwrap().remove(key);
        Ok(())
    }
}

/// Mock event bus with event capture and verification.
///
/// # FR Traceability
/// - FR-TEST-003-008: Mock EventBus implementation
pub struct MockEventBus<Event> {
    events: Arc<RwLock<Vec<Event>>>,
}

impl<E: Clone + Send + Sync + Debug + 'static> MockEventBus<E> {
    /// Creates a new mock event bus
    ///
    /// # FR Traceability
    /// - FR-TEST-003-009: EventBus mock constructor
    pub fn new() -> Self {
        Self {
            events: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Get all captured events.
    pub fn events(&self) -> Vec<E> {
        self.events.read().unwrap().clone()
    }

    /// Get event count.
    pub fn event_count(&self) -> usize {
        self.events.read().unwrap().len()
    }

    /// Check if specific event was published (requires PartialEq).
    pub fn was_event_published(&self, event: &E) -> bool
    where
        E: PartialEq,
    {
        self.events.read().unwrap().contains(event)
    }

    /// Get events matching a predicate.
    pub fn find_events<F>(&self, predicate: F) -> Vec<E>
    where
        F: Fn(&E) -> bool,
    {
        self.events
            .read()
            .unwrap()
            .iter()
            .filter(|e| predicate(e))
            .cloned()
            .collect()
    }

    /// Clear all events.
    pub fn clear(&self) {
        self.events.write().unwrap().clear();
    }
}

impl<Event: Clone + Send + Sync> Default for MockEventBus<Event> {
    fn default() -> Self {
        Self {
            events: Arc::new(RwLock::new(Vec::new())),
        }
    }
}

impl<Event: Clone + Send + Sync + Debug + 'static> EventBus for MockEventBus<Event> {
    type Event = Event;

    fn publish(&self, event: Self::Event) -> Result<(), DomainError> {
        self.events.write().unwrap().push(event);
        Ok(())
    }

    fn publish_batch(&self, events: Vec<Self::Event>) -> Result<(), DomainError> {
        let mut stored = self.events.write().unwrap();
        for event in events {
            stored.push(event);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-TEST-003-001
    #[test]
    fn mock_repository_save_and_get() {
        let repo = MockRepository::<String, String>::new();
        repo.save("id1".to_string(), "value1".to_string()).unwrap();

        let value = repo.get(&"id1".to_string()).unwrap();
        assert_eq!(value, "value1");
    }

    // Traces to: FR-TEST-003-003
    #[test]
    fn mock_repository_failure_simulation() {
        let repo = MockRepository::<String, String>::new();
        repo.fail_next(DomainError::Other("simulated error".to_string()));

        let result = repo.save("id".to_string(), "value".to_string());
        assert!(result.is_err());
    }

    // Traces to: FR-TEST-003-004
    #[test]
    fn mock_repository_call_tracking() {
        let repo = MockRepository::<String, String>::new();
        repo.save("id1".to_string(), "value1".to_string()).unwrap();
        repo.get(&"id1".to_string()).unwrap();

        assert_eq!(repo.call_count(), 2);
        assert!(repo.was_saved(&"id1".to_string()));
    }

    // Traces to: FR-TEST-003-005
    #[test]
    fn mock_cache_hit_tracking() {
        let cache = MockCache::<String, String>::new();
        cache.set("key1".to_string(), "value1".to_string()).unwrap();

        // First access - hit
        let _ = cache.get(&"key1".to_string()).unwrap();
        assert_eq!(cache.hit_count(), 1);
        assert_eq!(cache.miss_count(), 0);

        // Second access - miss
        let _ = cache.get(&"nonexistent".to_string()).unwrap();
        assert_eq!(cache.miss_count(), 1);

        assert_eq!(cache.hit_ratio(), 0.5);
    }

    // Traces to: FR-TEST-003-008
    #[test]
    fn mock_event_bus_captures_events() {
        let bus = MockEventBus::<String>::new();
        bus.publish("event1".to_string()).unwrap();
        bus.publish("event2".to_string()).unwrap();

        assert_eq!(bus.event_count(), 2);
        let events = bus.events();
        assert!(events.contains(&"event1".to_string()));
    }

    // Traces to: FR-TEST-003-008
    #[test]
    fn mock_event_bus_batch_publish() {
        let bus = MockEventBus::<String>::new();
        bus.publish_batch(vec!["e1".to_string(), "e2".to_string(), "e3".to_string()])
            .unwrap();

        assert_eq!(bus.event_count(), 3);
    }
}
