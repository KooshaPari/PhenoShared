//! Core skill types and traits for phenotype-daemon.
//!
//! `phenotype-skills` is the canonical Rust implementation of the skill
//! domain model: `Skill`, `SkillManifest`, `SkillId`, `SkillRegistry`,
//! `DependencyResolver`, plus cycle detection over the dependency graph.
//! It is consumed by `phenotype-daemon` via a path dependency.
//!
//! In the broader architecture a Python `phenotype-skills` package may
//! exist for tooling, but this crate is the source of truth for the
//! daemon's runtime types and is not a stub.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// Errors that can occur in skill operations
#[derive(Error, Debug)]
pub enum SkillError {
    #[error("Skill not found: {0}")]
    NotFound(String),

    #[error("Skill already registered: {0}")]
    AlreadyExists(String),

    #[error("Dependency error: {0}")]
    DependencyError(String),

    #[error("Serialization error: {0}")]
    SerializationError(String),
}

impl serde::Serialize for SkillError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

/// Unique identifier for a skill
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SkillId(String);

impl SkillId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for SkillId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// A skill dependency specification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillDependency {
    /// Name of the dependency
    pub name: String,
    /// Optional version constraint (e.g., ">=1.0.0")
    pub version: Option<String>,
    /// Whether this is a required dependency
    pub required: bool,
}

impl SkillDependency {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: None,
            required: true,
        }
    }

    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }

    pub fn optional(mut self) -> Self {
        self.required = false;
        self
    }
}

/// Skill manifest containing metadata and configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillManifest {
    /// Human-readable name
    pub name: String,
    /// Skill version
    pub version: String,
    /// Optional description
    pub description: Option<String>,
    /// Runtime environment requirements
    pub environment: Option<HashMap<String, String>>,
    /// Skill dependencies
    pub dependencies: Vec<SkillDependency>,
    /// Configuration schema (JSON Schema)
    pub config_schema: Option<serde_json::Value>,
}

impl SkillManifest {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
            description: None,
            environment: None,
            dependencies: Vec::new(),
            config_schema: None,
        }
    }
}

/// Core Skill type used throughout the daemon
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    /// Unique skill identifier
    pub id: String,
    /// Skill manifest with metadata
    pub manifest: SkillManifest,
    /// Metadata about the skill instance
    pub metadata: SkillMetadata,
}

impl Skill {
    pub fn new(id: impl Into<String>, manifest: SkillManifest) -> Self {
        Self {
            id: id.into(),
            manifest,
            metadata: SkillMetadata::default(),
        }
    }
}

/// Metadata about a skill instance
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillMetadata {
    /// When the skill was registered
    pub registered_at: Option<String>,
    /// Who registered this skill
    pub registered_by: Option<String>,
    /// Current status
    pub status: SkillStatus,
    /// Custom labels/tags
    pub labels: HashMap<String, String>,
}

/// Skill status enum
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum SkillStatus {
    Active,
    Inactive,
    Loading,
    Error,
    #[default]
    Unknown,
}

/// Trait for skill registry operations
pub trait SkillRegistryTrait: Send + Sync {
    fn register(&mut self, skill: Skill) -> Result<(), SkillError>;
    fn unregister(&mut self, id: &SkillId) -> Result<(), SkillError>;
    fn get(&self, id: &SkillId) -> Option<&Skill>;
    fn list(&self) -> Vec<&Skill>;
    fn find_by_name(&self, name: &str) -> Vec<&Skill>;
}

/// Thread-safe skill registry
#[derive(Debug, Default)]
pub struct SkillRegistry {
    skills: dashmap::DashMap<String, Skill>,
}

impl SkillRegistry {
    pub fn new() -> Self {
        Self {
            skills: dashmap::DashMap::new(),
        }
    }

    pub fn register(&self, skill: Skill) -> Result<(), SkillError> {
        let id = skill.id.clone();
        if self.skills.contains_key(&id) {
            return Err(SkillError::AlreadyExists(id));
        }
        self.skills.insert(id, skill);
        Ok(())
    }

    pub fn unregister(&self, id: &SkillId) -> Result<(), SkillError> {
        self.skills
            .remove(id.as_str())
            .map(|_| ())
            .ok_or_else(|| SkillError::NotFound(id.to_string()))
    }

    pub fn get(&self, id: &SkillId) -> Option<Skill> {
        self.skills.get(id.as_str()).map(|v| v.clone())
    }

    pub fn list(&self) -> Vec<Skill> {
        self.skills.iter().map(|v| v.clone()).collect()
    }

    pub fn find_by_name(&self, name: &str) -> Vec<Skill> {
        self.skills
            .iter()
            .filter(|v| v.manifest.name == name)
            .map(|v| v.clone())
            .collect()
    }
}

/// Default LRU cache capacity for resolved dependency topologies.
///
/// Per `SPEC.md:444` ("DependencyResolver Cache — Cached topologies: Last
/// 100 queries — LRU eviction"). Exposed as a `const` so tests and
/// downstream consumers can reference the same number when sizing their
/// own state.
pub const DEFAULT_CACHE_CAPACITY: usize = 100;

/// Dependency resolver for skill graphs
pub struct DependencyResolver {
    /// LRU cache of resolved dependency topologies keyed by a stable
    /// representation of the input id set. Bounded by
    /// [`DEFAULT_CACHE_CAPACITY`] to bound memory under repeated
    /// resolve() calls.
    cache: std::sync::Mutex<lru::LruCache<String, Vec<String>>>,
}

impl std::fmt::Debug for DependencyResolver {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let len = self.cache.lock().map(|c| c.len()).unwrap_or(0);
        f.debug_struct("DependencyResolver")
            .field("cache_len", &len)
            .field("cache_cap", &DEFAULT_CACHE_CAPACITY)
            .finish()
    }
}

impl Default for DependencyResolver {
    fn default() -> Self {
        Self::new()
    }
}

impl DependencyResolver {
    pub fn new() -> Self {
        Self {
            cache: std::sync::Mutex::new(lru::LruCache::new(
                std::num::NonZeroUsize::new(DEFAULT_CACHE_CAPACITY)
                    .expect("DEFAULT_CACHE_CAPACITY must be > 0"),
            )),
        }
    }

    /// Construct a resolver with a custom cache capacity. Mainly useful
    /// for tests that want to exercise eviction with a small bound.
    pub fn with_cache_capacity(capacity: usize) -> Self {
        Self {
            cache: std::sync::Mutex::new(lru::LruCache::new(
                std::num::NonZeroUsize::new(capacity).expect("capacity must be > 0"),
            )),
        }
    }

    /// Current cache occupancy. Returns 0 if the lock is poisoned.
    pub fn cache_len(&self) -> usize {
        self.cache.lock().map(|c| c.len()).unwrap_or(0)
    }

    /// Look up a cached resolved topology by its stable key.
    pub fn cache_get(&self, key: &str) -> Option<Vec<String>> {
        self.cache.lock().ok().and_then(|mut c| c.get(key).cloned())
    }

    /// Insert (or update) a cached resolved topology. The LRU policy
    /// will evict the least-recently-used entry when the cache is full.
    pub fn cache_put(&self, key: String, value: Vec<String>) {
        if let Ok(mut c) = self.cache.lock() {
            c.put(key, value);
        }
    }

    /// Resolve all dependencies for a set of skills.
    ///
    /// The result is cached against a stable, sorted key derived from
    /// the input ids; subsequent calls with the same input set hit the
    /// cache instead of re-walking the graph. Eviction is LRU-bounded by
    /// [`DEFAULT_CACHE_CAPACITY`].
    pub fn resolve(&self, skill_ids: &[SkillId], registry: &SkillRegistry) -> Vec<SkillId> {
        let key = Self::cache_key(skill_ids);

        if let Some(cached) = self.cache_get(&key) {
            return cached.into_iter().map(SkillId::new).collect();
        }

        let mut resolved = Vec::new();
        let mut visited = std::collections::HashSet::new();

        for id in skill_ids {
            self.resolve_recursive(id, registry, &mut visited, &mut resolved);
        }

        let snapshot: Vec<String> = resolved.iter().map(|s| s.to_string()).collect();
        self.cache_put(key, snapshot);

        resolved
    }

    /// Stable cache key for a set of skill ids: sort, dedupe, join with
    /// a separator that cannot appear in a SkillId.
    fn cache_key(skill_ids: &[SkillId]) -> String {
        let mut sorted: Vec<&str> = skill_ids.iter().map(|s| s.as_str()).collect();
        sorted.sort_unstable();
        sorted.dedup();
        sorted.join("\x1f") // ASCII Unit Separator
    }

    fn resolve_recursive(
        &self,
        id: &SkillId,
        registry: &SkillRegistry,
        visited: &mut std::collections::HashSet<String>,
        resolved: &mut Vec<SkillId>,
    ) {
        if visited.contains(id.as_str()) {
            return;
        }

        visited.insert(id.to_string());

        if let Some(skill) = registry.get(id) {
            for dep in &skill.manifest.dependencies {
                let dep_id = SkillId::new(dep.name.clone());
                self.resolve_recursive(&dep_id, registry, visited, resolved);
                if !resolved.iter().any(|i| i == &dep_id) {
                    resolved.push(dep_id);
                }
            }
        }
    }

    /// Clear the resolution cache
    pub fn clear_cache(&self) {
        if let Ok(mut cache) = self.cache.lock() {
            cache.clear();
        }
    }

    /// Check for circular dependencies within a set of skills.
    ///
    /// Two skills `a` and `b` form a cycle if `a` declares a dependency
    /// on `b` and `b` (transitively) declares a dependency on `a`. The
    /// algorithm walks the dependency graph rooted at each skill in
    /// `skills` and returns `true` as soon as it revisits a node already
    /// on the current DFS stack.
    ///
    /// Only dependencies that resolve to a skill in the provided slice
    /// are followed. Deps that point outside the slice are treated as
    /// leaves and do not contribute to a cycle.
    pub fn has_circular_deps(&self, skills: &[&Skill]) -> bool {
        let mut visited: std::collections::HashSet<String> = std::collections::HashSet::new();
        let mut stack: Vec<String> = Vec::new();

        for skill in skills {
            if Self::detect_cycle(skill, skills, &mut visited, &mut stack) {
                return true;
            }
        }

        false
    }

    fn detect_cycle<'a>(
        skill: &'a Skill,
        skills: &'a [&'a Skill],
        visited: &mut std::collections::HashSet<String>,
        stack: &mut Vec<String>,
    ) -> bool {
        let id = &skill.id;

        if stack.iter().any(|s| s == id) {
            return true;
        }
        if visited.contains(id) {
            return false;
        }

        visited.insert(id.clone());
        stack.push(id.clone());

        for dep in &skill.manifest.dependencies {
            if Self::detect_cycle_dep(&dep.name, skills, visited, stack) {
                return true;
            }
        }

        stack.pop();
        false
    }

    fn detect_cycle_dep<'a>(
        dep_name: &str,
        skills: &'a [&'a Skill],
        visited: &mut std::collections::HashSet<String>,
        stack: &mut Vec<String>,
    ) -> bool {
        // Resolve the dep against the provided skill slice. A dep that
        // does not name any skill in the slice is treated as a leaf and
        // contributes nothing to a cycle.
        let Some(next) = skills.iter().find(|s| s.id == dep_name).copied() else {
            return false;
        };
        Self::detect_cycle(next, skills, visited, stack)
    }
}

// Re-export commonly used items
pub use SkillId as SkillIdentifier;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_skill_id() {
        let id = SkillId::new("test-skill");
        assert_eq!(id.as_str(), "test-skill");
        assert_eq!(id.to_string(), "test-skill");
    }

    #[test]
    fn test_skill_registry() {
        let registry = SkillRegistry::new();
        let skill = Skill::new(
            "test-1",
            SkillManifest::new("Test Skill", "1.0.0"),
        );

        assert!(registry.register(skill.clone()).is_ok());
        assert!(registry.get(&SkillId::new("test-1")).is_some());
        assert!(registry.unregister(&SkillId::new("test-1")).is_ok());
        assert!(registry.get(&SkillId::new("test-1")).is_none());
    }

    #[test]
    fn test_dependency_resolver() {
        let resolver = DependencyResolver::new();
        let registry = SkillRegistry::new();

        let mut skill = Skill::new(
            "parent",
            SkillManifest::new("Parent Skill", "1.0.0"),
        );
        skill.manifest.dependencies.push(SkillDependency::new("child"));
        registry.register(skill).unwrap();

        let child_skill = Skill::new(
            "child",
            SkillManifest::new("Child Skill", "1.0.0"),
        );
        registry.register(child_skill).unwrap();

        let resolved = resolver.resolve(&[SkillId::new("parent")], &registry);
        assert!(resolved.iter().any(|id| id.as_str() == "child"));
    }

    /// Helper: build a skill with the given id and a list of dep ids.
    fn skill_with_deps(id: &str, deps: &[&str]) -> Skill {
        let mut s = Skill::new(id, SkillManifest::new(id, "1.0.0"));
        for d in deps {
            s.manifest.dependencies.push(SkillDependency::new(*d));
        }
        s
    }

    #[test]
    fn test_has_circular_deps_no_cycle() {
        // a -> b -> c (b is a leaf from c's perspective; no cycle)
        let resolver = DependencyResolver::new();
        let a = skill_with_deps("a", &["b"]);
        let b = skill_with_deps("b", &["c"]);
        let c = skill_with_deps("c", &[]);
        assert!(!resolver.has_circular_deps(&[&a, &b, &c]));
    }

    #[test]
    fn test_has_circular_deps_direct_two_node() {
        // a -> b -> a  (two-node cycle, classic)
        let resolver = DependencyResolver::new();
        let a = skill_with_deps("a", &["b"]);
        let b = skill_with_deps("b", &["a"]);
        assert!(resolver.has_circular_deps(&[&a, &b]));
    }

    #[test]
    fn test_has_circular_deps_three_node() {
        // a -> b -> c -> a  (transitive cycle)
        let resolver = DependencyResolver::new();
        let a = skill_with_deps("a", &["b"]);
        let b = skill_with_deps("b", &["c"]);
        let c = skill_with_deps("c", &["a"]);
        assert!(resolver.has_circular_deps(&[&a, &b, &c]));
    }

    #[test]
    fn test_has_circular_deps_self_loop() {
        // a -> a  (self-dependency)
        let resolver = DependencyResolver::new();
        let a = skill_with_deps("a", &["a"]);
        assert!(resolver.has_circular_deps(&[&a]));
    }

    #[test]
    fn test_has_circular_deps_external_dep_ignored() {
        // a -> b -> external (a dep named "external" is not in the slice,
        // so it is treated as a leaf and does not contribute to a cycle)
        let resolver = DependencyResolver::new();
        let a = skill_with_deps("a", &["b"]);
        let b = skill_with_deps("b", &["external"]);
        assert!(!resolver.has_circular_deps(&[&a, &b]));
    }

    // ---- DependencyResolver LRU cache tests ----
    // These verify the SPEC.md:444 commitment: "Cached topologies: Last
    // 100 queries — LRU eviction".

    #[test]
    fn test_default_cache_capacity_matches_spec() {
        // SPEC.md:444 specifies "Last 100 queries". Pin the constant so
        // any future change is a deliberate, reviewable edit.
        assert_eq!(DEFAULT_CACHE_CAPACITY, 100);
    }

    #[test]
    fn test_resolve_populates_cache() {
        let resolver = DependencyResolver::new();
        let registry = SkillRegistry::new();
        registry
            .register(Skill::new(
                "p",
                SkillManifest::new("P", "1.0.0"),
            ))
            .unwrap();

        assert_eq!(resolver.cache_len(), 0);
        let _ = resolver.resolve(&[SkillId::new("p")], &registry);
        assert_eq!(resolver.cache_len(), 1);
    }

    #[test]
    fn test_resolve_cache_hit_is_stable() {
        // resolve(a) and resolve(b) where a and b are the same set in
        // different orders should hit the same cache entry.
        let resolver = DependencyResolver::new();
        let registry = SkillRegistry::new();
        registry
            .register(Skill::new("a", SkillManifest::new("A", "1.0.0")))
            .unwrap();
        registry
            .register(Skill::new("b", SkillManifest::new("B", "1.0.0")))
            .unwrap();

        let r1 = resolver.resolve(&[SkillId::new("a"), SkillId::new("b")], &registry);
        let r2 = resolver.resolve(&[SkillId::new("b"), SkillId::new("a")], &registry);
        let r3 = resolver.resolve(&[SkillId::new("a")], &registry);

        assert_eq!(r1, r2, "order-independent resolve must match");
        // a is a subset of {a,b}; LRU promotes the touched entry to most
        // recent. resolve([a]) inserts/promotes a separate key from
        // resolve([a,b]) so cache should hold both.
        assert!(resolver.cache_len() >= 2, "distinct keys should be cached");
        let _ = r3;
    }

    #[test]
    fn test_resolve_lru_eviction() {
        // Capacity-2 cache: inserting 3 distinct keys must evict the
        // least-recently-used (the first one inserted).
        let resolver = DependencyResolver::with_cache_capacity(2);
        let registry = SkillRegistry::new();
        for id in ["a", "b", "c"] {
            registry
                .register(Skill::new(id, SkillManifest::new(id, "1.0.0")))
                .unwrap();
        }

        let _ = resolver.resolve(&[SkillId::new("a")], &registry);
        let _ = resolver.resolve(&[SkillId::new("b")], &registry);
        assert_eq!(resolver.cache_len(), 2);

        // Touch "a" so it becomes most-recently-used; then insert "c"
        // which should evict "b" (now LRU), not "a".
        let _ = resolver.resolve(&[SkillId::new("a")], &registry);
        let _ = resolver.resolve(&[SkillId::new("c")], &registry);
        assert_eq!(resolver.cache_len(), 2);

        // Verify the surviving keys: "a" was promoted; "b" was evicted.
        // For a single-element input, cache_key returns the id itself
        // (sort + dedup of a 1-element vec is just the one element).
        // We probe via cache_get to confirm the LRU policy.
        assert!(resolver.cache_get("a").is_some(), "a should still be cached");
        assert!(resolver.cache_get("c").is_some(), "c should be cached");
        assert!(resolver.cache_get("b").is_none(), "b should have been evicted");
    }

    #[test]
    fn test_clear_cache_empties() {
        let resolver = DependencyResolver::with_cache_capacity(2);
        let registry = SkillRegistry::new();
        registry
            .register(Skill::new("a", SkillManifest::new("A", "1.0.0")))
            .unwrap();
        let _ = resolver.resolve(&[SkillId::new("a")], &registry);
        assert_eq!(resolver.cache_len(), 1);
        resolver.clear_cache();
        assert_eq!(resolver.cache_len(), 0);
    }
}
