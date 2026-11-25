//! Test fixtures and builders for common test scenarios.
//!
//! # FR Traceability
//! - FR-TEST-001: Test fixture support for domain entities

use chrono::{DateTime, Utc};
use std::collections::HashMap;
use uuid::Uuid;

/// Builder pattern for constructing test fixtures with sensible defaults.
///
/// # FR Traceability
/// - FR-TEST-001-001: Builder pattern for test data construction
pub trait FixtureBuilder<T> {
    /// Build the fixture instance.
    fn build(self) -> T;
}

/// Standard test entity for demonstration and testing.
///
/// # FR Traceability
/// - FR-TEST-001-002: Standard test entity structure
#[derive(Debug, Clone, PartialEq)]
pub struct TestEntity {
    pub id: String,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}

impl Default for TestEntity {
    fn default() -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            name: "test-entity".to_string(),
            created_at: Utc::now(),
            metadata: HashMap::new(),
        }
    }
}

/// Builder for TestEntity with fluent API.
///
/// # FR Traceability
/// - FR-TEST-001-003: Entity builder fluent API
#[derive(Default)]
pub struct TestEntityBuilder {
    id: Option<String>,
    name: Option<String>,
    created_at: Option<DateTime<Utc>>,
    metadata: HashMap<String, String>,
}

impl TestEntityBuilder {
    /// Create a new builder with defaults.
    ///
    /// # FR Traceability
    /// - FR-TEST-001-004: Builder constructor
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the entity ID.
    pub fn id(mut self, id: impl Into<String>) -> Self {
        self.id = Some(id.into());
        self
    }

    /// Set the entity name.
    pub fn name(mut self, name: impl Into<String>) -> Self {
        self.name = Some(name.into());
        self
    }

    /// Set the creation timestamp.
    pub fn created_at(mut self, ts: DateTime<Utc>) -> Self {
        self.created_at = Some(ts);
        self
    }

    /// Add metadata key-value pair.
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Add multiple metadata entries.
    pub fn with_metadata_map(mut self, map: HashMap<String, String>) -> Self {
        self.metadata.extend(map);
        self
    }
}

impl FixtureBuilder<TestEntity> for TestEntityBuilder {
    fn build(self) -> TestEntity {
        TestEntity {
            id: self.id.unwrap_or_else(|| Uuid::new_v4().to_string()),
            name: self.name.unwrap_or_else(|| "test-entity".to_string()),
            created_at: self.created_at.unwrap_or_else(Utc::now),
            metadata: self.metadata,
        }
    }
}

/// Test fixture containing entities and context for test scenarios.
///
/// # FR Traceability
/// - FR-TEST-001-004: TestFixture container
#[derive(Default)]
pub struct TestFixture {
    pub entities: Vec<TestEntity>,
    pub context: HashMap<String, String>,
}

impl TestFixture {
    /// Create an empty fixture.
    ///
    /// # FR Traceability
    /// - FR-TEST-001-006: Empty fixture constructor
    pub fn new() -> Self {
        Self::default()
    }

    /// Add an entity to the fixture.
    pub fn with_entity(mut self, entity: TestEntity) -> Self {
        self.entities.push(entity);
        self
    }

    /// Add multiple entities to the fixture.
    pub fn with_entities(mut self, entities: Vec<TestEntity>) -> Self {
        self.entities.extend(entities);
        self
    }

    /// Set a context value.
    pub fn with_context(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.context.insert(key.into(), value.into());
        self
    }

    /// Get entity by ID.
    pub fn get_entity(&self, id: &str) -> Option<&TestEntity> {
        self.entities.iter().find(|e| e.id == id)
    }
}

/// Test scenario presets for common use cases.
///
/// # FR Traceability
/// - FR-TEST-001-007: Scenario presets
pub mod scenarios {
    use super::*;

    /// Create a single entity scenario.
    ///
    /// # FR Traceability
    /// - FR-TEST-001-008: Single entity scenario
    pub fn single_entity() -> TestFixture {
        TestFixture::new().with_entity(TestEntityBuilder::new().name("single-test").build())
    }

    /// Create a multi-entity scenario.
    ///
    /// # FR Traceability
    /// - FR-TEST-001-009: Multi-entity scenario
    pub fn multiple_entities(count: usize) -> TestFixture {
        let mut fixture = TestFixture::new();
        for i in 0..count {
            let entity = TestEntityBuilder::new()
                .id(format!("entity-{}", i))
                .name(format!("Entity {}", i))
                .build();
            fixture = fixture.with_entity(entity);
        }
        fixture
    }

    /// Create a scenario with metadata-rich entities.
    ///
    /// # FR Traceability
    /// - FR-TEST-001-010: Metadata-rich scenario
    pub fn metadata_rich() -> TestFixture {
        let metadata: HashMap<String, String> = [
            ("region", "us-east-1"),
            ("environment", "test"),
            ("version", "1.0.0"),
        ]
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();

        TestFixture::new().with_entity(
            TestEntityBuilder::new()
                .name("metadata-entity")
                .with_metadata_map(metadata)
                .build(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-TEST-001-003
    #[test]
    fn entity_builder_creates_entity() {
        let entity = TestEntityBuilder::new()
            .id("test-123")
            .name("Test Entity")
            .with_metadata("key", "value")
            .build();

        assert_eq!(entity.id, "test-123");
        assert_eq!(entity.name, "Test Entity");
        assert_eq!(entity.metadata.get("key"), Some(&"value".to_string()));
    }

    // Traces to: FR-TEST-001-003
    #[test]
    fn entity_builder_uses_defaults() {
        let entity = TestEntityBuilder::new().build();
        assert!(!entity.id.is_empty());
        assert_eq!(entity.name, "test-entity");
        assert!(entity.metadata.is_empty());
    }

    // Traces to: FR-TEST-001-009
    #[test]
    fn multiple_entities_scenario() {
        let fixture = scenarios::multiple_entities(5);
        assert_eq!(fixture.entities.len(), 5);
        assert_eq!(fixture.entities[0].id, "entity-0");
        assert_eq!(fixture.entities[4].id, "entity-4");
    }

    // Traces to: FR-TEST-001-010
    #[test]
    fn metadata_rich_scenario() {
        let fixture = scenarios::metadata_rich();
        assert_eq!(fixture.entities.len(), 1);
        let entity = &fixture.entities[0];
        assert_eq!(
            entity.metadata.get("region"),
            Some(&"us-east-1".to_string())
        );
        assert_eq!(
            entity.metadata.get("environment"),
            Some(&"test".to_string())
        );
    }
}
