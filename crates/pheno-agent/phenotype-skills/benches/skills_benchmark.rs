use criterion::{black_box, criterion_group, criterion_main, Criterion};
use phenotype_skills::*;

fn registry_register_1000(c: &mut Criterion) {
    c.bench_function("registry_register_1000", |b| {
        b.iter(|| {
            let registry = SkillRegistry::new();
            for i in 0..1000 {
                let skill = Skill::new(
                    format!("skill-{i}"),
                    SkillManifest::new(format!("Skill {i}"), "1.0.0"),
                );
                registry.register(skill).unwrap();
            }
            black_box(registry.list().len());
        });
    });
}

fn registry_find_by_name_1000(c: &mut Criterion) {
    let registry = SkillRegistry::new();
    for i in 0..1000 {
        let skill = Skill::new(
            format!("skill-{i}"),
            SkillManifest::new(format!("Skill {}", i % 50), "1.0.0"),
        );
        registry.register(skill).unwrap();
    }
    c.bench_function("registry_find_by_name_1000", |b| {
        b.iter(|| {
            for i in 0..50 {
                black_box(registry.find_by_name(&format!("Skill {i}")));
            }
        });
    });
}

fn resolver_50_skills(c: &mut Criterion) {
    let registry = SkillRegistry::new();
    for i in 0..50 {
        let mut skill = Skill::new(
            format!("skill-{i}"),
            SkillManifest::new(format!("Skill {i}"), "1.0.0"),
        );
        if i > 0 {
            skill
                .manifest
                .dependencies
                .push(SkillDependency::new(format!("skill-{}", i - 1)));
        }
        registry.register(skill).unwrap();
    }
    let resolver = DependencyResolver::new();
    let ids: Vec<SkillId> = (0..50)
        .map(|i| SkillId::new(format!("skill-{i}")))
        .collect();
    c.bench_function("resolver_50_skills", |b| {
        b.iter(|| {
            black_box(resolver.resolve(black_box(&ids), &registry));
        });
    });
}

fn skill_json_serde(c: &mut Criterion) {
    let mut manifest = SkillManifest::new("bench-skill", "3.2.1");
    manifest.description = Some("A skill for benchmarking".into());
    manifest
        .dependencies
        .push(SkillDependency::new("dep-a").with_version(">=1.0"));
    manifest
        .dependencies
        .push(SkillDependency::new("dep-b").optional());
    let skill = Skill::new("bench-001", manifest);

    c.bench_function("skill_json_serialize", |b| {
        b.iter(|| black_box(serde_json::to_string(black_box(&skill)).unwrap()));
    });

    let json = serde_json::to_string(&skill).unwrap();
    c.bench_function("skill_json_deserialize", |b| {
        b.iter(|| black_box(serde_json::from_str::<Skill>(black_box(&json)).unwrap()));
    });
}

criterion_group!(
    benches,
    registry_register_1000,
    registry_find_by_name_1000,
    resolver_50_skills,
    skill_json_serde,
);
criterion_main!(benches);
