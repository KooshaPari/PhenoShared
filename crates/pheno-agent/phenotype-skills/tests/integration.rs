use phenotype_skills::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

// ── SkillId ─────────────────────────────────────────────────────────────────

#[test]
fn skill_id_creation_and_display() {
    let id = SkillId::new("my-skill");
    assert_eq!(id.as_str(), "my-skill");
    assert_eq!(id.to_string(), "my-skill");
    assert_eq!(format!("{id}"), "my-skill");
}

#[test]
fn skill_id_equality() {
    let a = SkillId::new("alpha");
    let b = SkillId::new("alpha");
    let c = SkillId::new("beta");
    assert_eq!(a, b);
    assert_ne!(a, c);
}

#[test]
fn skill_id_hash_consistency() {
    let a = SkillId::new("alpha");
    let b = SkillId::new("alpha");
    let mut h1 = DefaultHasher::new();
    let mut h2 = DefaultHasher::new();
    a.hash(&mut h1);
    b.hash(&mut h2);
    assert_eq!(h1.finish(), h2.finish());
}

// ── SkillDependency ─────────────────────────────────────────────────────────

#[test]
fn skill_dependency_builder_chain() {
    let dep = SkillDependency::new("core")
        .with_version(">=1.0.0")
        .optional();
    assert_eq!(dep.name, "core");
    assert_eq!(dep.version.as_deref(), Some(">=1.0.0"));
    assert!(!dep.required);
}

#[test]
fn skill_dependency_defaults() {
    let dep = SkillDependency::new("base");
    assert!(dep.required);
    assert!(dep.version.is_none());
}

// ── SkillManifest ───────────────────────────────────────────────────────────

#[test]
fn skill_manifest_construction() {
    let mut env = std::collections::HashMap::new();
    env.insert("python".into(), ">=3.10".into());
    let schema = serde_json::json!({"type": "object"});
    let manifest = SkillManifest {
        name: "web-search".into(),
        version: "2.1.0".into(),
        description: Some("Searches the web".into()),
        environment: Some(env),
        dependencies: vec![SkillDependency::new("http-client")],
        config_schema: Some(schema),
    };
    assert_eq!(manifest.name, "web-search");
    assert_eq!(manifest.version, "2.1.0");
    assert_eq!(manifest.description.as_deref(), Some("Searches the web"));
    assert!(manifest.dependencies.len() == 1);
    assert!(manifest.config_schema.is_some());
}

// ── Skill / SkillMetadata / SkillStatus ─────────────────────────────────────

#[test]
fn skill_status_default_is_unknown() {
    let status = SkillStatus::default();
    let json = serde_json::to_string(&status).unwrap();
    assert_eq!(json, "\"unknown\"");
}

#[test]
fn skill_metadata_defaults() {
    let meta = SkillMetadata::default();
    assert!(meta.registered_at.is_none());
    assert!(meta.registered_by.is_none());
    assert!(matches!(meta.status, SkillStatus::Unknown));
    assert!(meta.labels.is_empty());
}

#[test]
fn skill_construction() {
    let manifest = SkillManifest::new("demo", "0.1.0");
    let skill = Skill::new("demo-001", manifest);
    assert_eq!(skill.id, "demo-001");
    assert_eq!(skill.manifest.name, "demo");
    assert!(matches!(skill.metadata.status, SkillStatus::Unknown));
}

// ── SkillRegistry ───────────────────────────────────────────────────────────

#[test]
fn registry_register_and_get() {
    let registry = SkillRegistry::new();
    let skill = Skill::new("s1", SkillManifest::new("Alpha", "1.0.0"));
    registry.register(skill).unwrap();
    let fetched = registry.get(&SkillId::new("s1")).unwrap();
    assert_eq!(fetched.manifest.name, "Alpha");
}

#[test]
fn registry_list() {
    let registry = SkillRegistry::new();
    registry
        .register(Skill::new("a", SkillManifest::new("A", "1.0.0")))
        .unwrap();
    registry
        .register(Skill::new("b", SkillManifest::new("B", "1.0.0")))
        .unwrap();
    assert_eq!(registry.list().len(), 2);
}

#[test]
fn registry_find_by_name() {
    let registry = SkillRegistry::new();
    registry
        .register(Skill::new("x1", SkillManifest::new("X", "1.0.0")))
        .unwrap();
    registry
        .register(Skill::new("x2", SkillManifest::new("X", "2.0.0")))
        .unwrap();
    registry
        .register(Skill::new("y1", SkillManifest::new("Y", "1.0.0")))
        .unwrap();
    let xs = registry.find_by_name("X");
    assert_eq!(xs.len(), 2);
}

#[test]
fn registry_unregister() {
    let registry = SkillRegistry::new();
    registry
        .register(Skill::new("tmp", SkillManifest::new("Temp", "1.0.0")))
        .unwrap();
    registry.unregister(&SkillId::new("tmp")).unwrap();
    assert!(registry.get(&SkillId::new("tmp")).is_none());
}

#[test]
fn registry_duplicate_registration_error() {
    let registry = SkillRegistry::new();
    registry
        .register(Skill::new("dup", SkillManifest::new("Dup", "1.0.0")))
        .unwrap();
    let err = registry
        .register(Skill::new("dup", SkillManifest::new("Dup", "2.0.0")))
        .unwrap_err();
    assert!(matches!(err, SkillError::AlreadyExists(_)));
}

#[test]
fn registry_unregister_nonexistent_error() {
    let registry = SkillRegistry::new();
    let err = registry.unregister(&SkillId::new("ghost")).unwrap_err();
    assert!(matches!(err, SkillError::NotFound(_)));
}

// ── DependencyResolver ───────────────────────────────────────────────────────

#[test]
fn resolver_simple_linear_chain() {
    let registry = SkillRegistry::new();
    // a -> b -> c
    let mut a = Skill::new("a", SkillManifest::new("A", "1.0.0"));
    a.manifest.dependencies.push(SkillDependency::new("b"));
    let mut b = Skill::new("b", SkillManifest::new("B", "1.0.0"));
    b.manifest.dependencies.push(SkillDependency::new("c"));
    let c = Skill::new("c", SkillManifest::new("C", "1.0.0"));
    registry.register(a).unwrap();
    registry.register(b).unwrap();
    registry.register(c).unwrap();

    let resolver = DependencyResolver::new();
    let resolved = resolver.resolve(&[SkillId::new("a")], &registry);
    // c should come before b, b before a (depth-first)
    assert!(resolved.iter().any(|id| id.as_str() == "c"));
    assert!(resolved.iter().any(|id| id.as_str() == "b"));
}

#[test]
fn resolver_diamond_dependency_graph() {
    let registry = SkillRegistry::new();
    //   root
    //  /    \
    // left  right
    //  \    /
    //   base
    let mut root = Skill::new("root", SkillManifest::new("Root", "1.0.0"));
    root.manifest
        .dependencies
        .push(SkillDependency::new("left"));
    root.manifest
        .dependencies
        .push(SkillDependency::new("right"));
    let mut left = Skill::new("left", SkillManifest::new("Left", "1.0.0"));
    left.manifest
        .dependencies
        .push(SkillDependency::new("base"));
    let mut right = Skill::new("right", SkillManifest::new("Right", "1.0.0"));
    right
        .manifest
        .dependencies
        .push(SkillDependency::new("base"));
    let base = Skill::new("base", SkillManifest::new("Base", "1.0.0"));

    for s in [root, left, right, base] {
        registry.register(s).unwrap();
    }

    let resolver = DependencyResolver::new();
    let resolved = resolver.resolve(&[SkillId::new("root")], &registry);
    // base must appear only once
    assert_eq!(
        resolved.iter().filter(|id| id.as_str() == "base").count(),
        1
    );
    assert!(resolved.iter().any(|id| id.as_str() == "left"));
    assert!(resolved.iter().any(|id| id.as_str() == "right"));
}

#[test]
fn resolver_cycle_detection_via_visited_set() {
    let registry = SkillRegistry::new();
    // a -> b -> a  (cycle)
    let mut a = Skill::new("a", SkillManifest::new("A", "1.0.0"));
    a.manifest.dependencies.push(SkillDependency::new("b"));
    let mut b = Skill::new("b", SkillManifest::new("B", "1.0.0"));
    b.manifest.dependencies.push(SkillDependency::new("a"));
    registry.register(a).unwrap();
    registry.register(b).unwrap();

    let resolver = DependencyResolver::new();
    // Should not hang; visited set breaks the cycle
    let resolved = resolver.resolve(&[SkillId::new("a")], &registry);
    // Both a and b should be in the resolved set
    assert!(resolved.iter().any(|id| id.as_str() == "a"));
    assert!(resolved.iter().any(|id| id.as_str() == "b"));
}

// ── Skill serialization roundtrip ───────────────────────────────────────────

#[test]
fn skill_json_roundtrip() {
    let mut manifest = SkillManifest::new("roundtrip", "0.5.0");
    manifest.description = Some("test roundtrip".into());
    manifest
        .dependencies
        .push(SkillDependency::new("dep1").with_version("^1.0"));
    let skill = Skill::new("rt-1", manifest);

    let json = serde_json::to_string(&skill).unwrap();
    let back: Skill = serde_json::from_str(&json).unwrap();
    assert_eq!(back.id, skill.id);
    assert_eq!(back.manifest.name, skill.manifest.name);
    assert_eq!(back.manifest.version, skill.manifest.version);
    assert_eq!(back.manifest.dependencies.len(), 1);
}

// ── SkillError display ──────────────────────────────────────────────────────

#[test]
fn skill_error_display() {
    let e = SkillError::NotFound("x".into());
    assert!(e.to_string().contains("x"));
    let e = SkillError::AlreadyExists("y".into());
    assert!(e.to_string().contains("y"));
    let e = SkillError::DependencyError("z".into());
    assert!(e.to_string().contains("z"));
    let e = SkillError::SerializationError("bad".into());
    assert!(e.to_string().contains("bad"));
}

#[test]
fn skill_error_serialization() {
    let e = SkillError::NotFound("gone".into());
    let json = serde_json::to_string(&e).unwrap();
    assert!(json.contains("gone"));
}
