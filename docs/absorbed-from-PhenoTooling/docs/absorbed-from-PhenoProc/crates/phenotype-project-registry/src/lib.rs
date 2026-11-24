//! Project registry for Phenotype
//!
//! Provides project metadata management and discovery.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Project metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub description: String,
    pub version: String,
    pub path: String,
    pub tags: Vec<String>,
    pub metadata: HashMap<String, String>,
}

impl Project {
    /// Create a new project
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            description: String::new(),
            version: "0.1.0".to_string(),
            path: String::new(),
            tags: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Set description
    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = desc.into();
        self
    }

    /// Set version
    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = version.into();
        self
    }

    /// Set path
    pub fn with_path(mut self, path: impl Into<String>) -> Self {
        self.path = path.into();
        self
    }

    /// Add a tag
    pub fn with_tag(mut self, tag: impl Into<String>) -> Self {
        self.tags.push(tag.into());
        self
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }
}

/// Registry of projects
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ProjectRegistry {
    projects: HashMap<String, Project>,
}

impl ProjectRegistry {
    /// Create a new empty registry
    pub fn new() -> Self {
        Self {
            projects: HashMap::new(),
        }
    }

    /// Register a project
    pub fn register(&mut self, project: Project) {
        self.projects.insert(project.id.clone(), project);
    }

    /// Get a project by ID
    pub fn get(&self, id: &str) -> Option<&Project> {
        self.projects.get(id)
    }

    /// Remove a project
    pub fn remove(&mut self, id: &str) -> Option<Project> {
        self.projects.remove(id)
    }

    /// List all projects
    pub fn list(&self) -> Vec<&Project> {
        self.projects.values().collect()
    }

    /// Find projects by tag
    pub fn find_by_tag(&self, tag: &str) -> Vec<&Project> {
        self.projects
            .values()
            .filter(|p| p.tags.contains(&tag.to_string()))
            .collect()
    }

    /// Search projects by name
    pub fn search(&self, query: &str) -> Vec<&Project> {
        let query = query.to_lowercase();
        self.projects
            .values()
            .filter(|p| {
                p.name.to_lowercase().contains(&query)
                    || p.description.to_lowercase().contains(&query)
            })
            .collect()
    }

    /// Get project count
    pub fn count(&self) -> usize {
        self.projects.len()
    }

    /// Load from JSON
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Save to JSON
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

/// Registry builder
#[derive(Debug, Default)]
pub struct RegistryBuilder {
    registry: ProjectRegistry,
}

impl RegistryBuilder {
    /// Create a new builder
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a project
    pub fn with_project(mut self, project: Project) -> Self {
        self.registry.register(project);
        self
    }

    /// Build the registry
    pub fn build(self) -> ProjectRegistry {
        self.registry
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_builder() {
        let project = Project::new("p1", "Test Project")
            .with_description("A test project")
            .with_version("1.0.0")
            .with_tag("test");

        assert_eq!(project.id, "p1");
        assert_eq!(project.name, "Test Project");
        assert!(project.tags.contains(&"test".to_string()));
    }

    #[test]
    fn test_registry() {
        let mut registry = ProjectRegistry::new();
        let project = Project::new("p1", "Test");

        registry.register(project);
        assert_eq!(registry.count(), 1);
        assert!(registry.get("p1").is_some());
    }

    #[test]
    fn test_search() {
        let registry = RegistryBuilder::new()
            .with_project(Project::new("p1", "Alpha"))
            .with_project(Project::new("p2", "Beta"))
            .build();

        let results = registry.search("alpha");
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn project_new_uses_id_and_name() {
        let p = Project::new("id1", "name1");
        assert_eq!(p.id, "id1");
        assert_eq!(p.name, "name1");
        assert_eq!(p.version, "0.1.0");
        assert!(p.description.is_empty());
        assert!(p.path.is_empty());
        assert!(p.tags.is_empty());
        assert!(p.metadata.is_empty());
    }

    #[test]
    fn project_with_description_and_version() {
        let p = Project::new("i", "n")
            .with_description("d")
            .with_version("2.0.0");
        assert_eq!(p.description, "d");
        assert_eq!(p.version, "2.0.0");
    }

    #[test]
    fn project_with_path() {
        let p = Project::new("i", "n").with_path("/tmp/x");
        assert_eq!(p.path, "/tmp/x");
    }

    #[test]
    fn project_with_multiple_tags() {
        let p = Project::new("i", "n")
            .with_tag("a")
            .with_tag("b")
            .with_tag("c");
        assert_eq!(p.tags, vec!["a", "b", "c"]);
    }

    #[test]
    fn project_with_metadata() {
        let p = Project::new("i", "n").with_metadata("k1", "v1").with_metadata("k2", "v2");
        assert_eq!(p.metadata.get("k1"), Some(&"v1".to_string()));
        assert_eq!(p.metadata.get("k2"), Some(&"v2".to_string()));
    }

    #[test]
    fn registry_default_is_empty() {
        let r: ProjectRegistry = ProjectRegistry::default();
        assert_eq!(r.count(), 0);
        assert!(r.list().is_empty());
    }

    #[test]
    fn registry_get_missing_returns_none() {
        let r = ProjectRegistry::new();
        assert!(r.get("missing").is_none());
    }

    #[test]
    fn registry_remove_existing_and_missing() {
        let mut r = ProjectRegistry::new();
        r.register(Project::new("p1", "n1"));
        let removed = r.remove("p1");
        assert!(removed.is_some());
        assert_eq!(r.count(), 0);
        // Removing again returns None.
        assert!(r.remove("p1").is_none());
    }

    #[test]
    fn registry_register_overwrites() {
        let mut r = ProjectRegistry::new();
        r.register(Project::new("p1", "first"));
        r.register(Project::new("p1", "second"));
        assert_eq!(r.count(), 1);
        assert_eq!(r.get("p1").unwrap().name, "second");
    }

    #[test]
    fn registry_list_returns_all() {
        let r = RegistryBuilder::new()
            .with_project(Project::new("p1", "a"))
            .with_project(Project::new("p2", "b"))
            .with_project(Project::new("p3", "c"))
            .build();
        assert_eq!(r.list().len(), 3);
    }

    #[test]
    fn registry_find_by_tag_filters() {
        let r = RegistryBuilder::new()
            .with_project(Project::new("p1", "a").with_tag("rust"))
            .with_project(Project::new("p2", "b").with_tag("python"))
            .with_project(Project::new("p3", "c").with_tag("rust"))
            .build();
        let rust_projects = r.find_by_tag("rust");
        assert_eq!(rust_projects.len(), 2);
        let python_projects = r.find_by_tag("python");
        assert_eq!(python_projects.len(), 1);
        assert!(r.find_by_tag("nonexistent").is_empty());
    }

    #[test]
    fn registry_search_matches_name_and_description() {
        let r = RegistryBuilder::new()
            .with_project(Project::new("p1", "Alpha").with_description("fast search"))
            .with_project(Project::new("p2", "Beta"))
            .build();
        let by_name = r.search("alpha");
        assert_eq!(by_name.len(), 1);
        let by_desc = r.search("search");
        assert_eq!(by_desc.len(), 1);
        let no_match = r.search("xyz");
        assert!(no_match.is_empty());
    }

    #[test]
    fn registry_search_is_case_insensitive() {
        let r = RegistryBuilder::new()
            .with_project(Project::new("p1", "AlphaProject"))
            .build();
        assert_eq!(r.search("alphaproject").len(), 1);
        assert_eq!(r.search("ALPHAPROJECT").len(), 1);
    }

    #[test]
    fn registry_serde_roundtrip() {
        let mut r = ProjectRegistry::new();
        r.register(Project::new("p1", "n").with_tag("t").with_metadata("k", "v"));
        let json = r.to_json().unwrap();
        let back = ProjectRegistry::from_json(&json).unwrap();
        assert_eq!(back.count(), 1);
        assert_eq!(back.get("p1").unwrap().tags, vec!["t".to_string()]);
        assert_eq!(
            back.get("p1").unwrap().metadata.get("k"),
            Some(&"v".to_string())
        );
    }

    #[test]
    fn registry_from_json_error() {
        let bad = "{ not valid json";
        let res: Result<ProjectRegistry, _> = ProjectRegistry::from_json(bad);
        assert!(res.is_err());
    }

    #[test]
    fn builder_new_is_empty() {
        let b: RegistryBuilder = RegistryBuilder::new();
        let r = b.build();
        assert_eq!(r.count(), 0);
    }
}
