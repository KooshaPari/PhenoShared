//! Traceability enforcement.
//!
//! The acceptance contract must actually reference every traceability id that
//! the canonical matrices declare. This test enumerates the ids from the JSON
//! registry, requires that each one maps to a real evidence artifact via
//! `traceability/evidence-families.json`, requires that the owning spec
//! directory exists, and requires that the id is also present in the markdown
//! matrix. It fails loudly on any id that has no artifact.
//!
//! Before this test existed, nothing referenced a single `PF-CT-*` or
//! `PF-AT-*` id, so the traceability contract was aspirational only.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

const TRACEABILITY_JSON: &str = "verification/requirements-traceability.json";
const TRACEABILITY_MD: &str = "verification/requirements-traceability-matrix.md";
const FAMILIES_JSON: &str = "crates/acceptance-contract/traceability/evidence-families.json";

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("acceptance-contract must live two levels below the repo root")
        .to_path_buf()
}

#[derive(serde::Deserialize)]
struct Record {
    fr: String,
    requirement: String,
    spec: String,
    verification: String,
    acceptance: String,
}

#[derive(serde::Deserialize)]
struct Families {
    schema_version: u32,
    verification_families: BTreeMap<String, String>,
    acceptance_families: BTreeMap<String, String>,
}

/// `PF-AT-ABLETON-037` -> `AT-ABLETON`.
fn family(id: &str) -> String {
    let parts: Vec<&str> = id.split('-').collect();
    assert!(parts.len() >= 4, "malformed traceability id: {id}");
    assert_eq!(parts[0], "PF", "traceability ids must be PF-prefixed: {id}");
    format!("{}-{}", parts[1], parts[2])
}

fn load_records(root: &Path) -> Vec<Record> {
    let raw = std::fs::read_to_string(root.join(TRACEABILITY_JSON))
        .expect("read verification/requirements-traceability.json");
    serde_json::from_str(&raw).expect("parse requirements-traceability.json")
}

fn load_families(root: &Path) -> Families {
    let raw = std::fs::read_to_string(root.join(FAMILIES_JSON))
        .expect("read crates/acceptance-contract/traceability/evidence-families.json");
    let families: Families = serde_json::from_str(&raw).expect("parse evidence-families.json");
    assert_eq!(families.schema_version, 1, "unexpected registry schema");
    families
}

#[test]
fn every_matrix_id_has_an_artifact() {
    let root = repo_root();
    let records = load_records(&root);
    let families = load_families(&root);
    let matrix_md = std::fs::read_to_string(root.join(TRACEABILITY_MD))
        .expect("read verification/requirements-traceability-matrix.md");

    assert!(!records.is_empty(), "traceability matrix is empty");

    let mut frs = BTreeSet::new();
    let mut verification = BTreeSet::new();
    let mut acceptance = BTreeSet::new();
    let mut unmapped_verification = Vec::new();
    let mut unmapped_acceptance = Vec::new();
    let mut missing_artifacts = BTreeSet::new();
    let mut missing_specs = BTreeSet::new();
    let mut absent_from_markdown = Vec::new();

    for record in &records {
        assert!(frs.insert(record.fr.clone()), "duplicate FR {}", record.fr);
        assert!(
            !record.requirement.trim().is_empty(),
            "{} has an empty requirement statement",
            record.fr
        );
        assert!(
            verification.insert(record.verification.clone()),
            "verification id {} is reused",
            record.verification
        );
        assert!(
            acceptance.insert(record.acceptance.clone()),
            "acceptance id {} is reused",
            record.acceptance
        );

        for id in [&record.verification, &record.acceptance] {
            if !matrix_md.contains(id.as_str()) {
                absent_from_markdown.push(id.clone());
            }
        }

        let v_family = family(&record.verification);
        match families.verification_families.get(&v_family) {
            Some(artifact) => {
                if !root.join(artifact).is_file() {
                    missing_artifacts.insert(artifact.clone());
                }
            },
            None => unmapped_verification.push(format!("{} ({})", record.verification, v_family)),
        }

        let a_family = family(&record.acceptance);
        match families.acceptance_families.get(&a_family) {
            Some(artifact) => {
                if !root.join(artifact).is_file() {
                    missing_artifacts.insert(artifact.clone());
                }
            },
            None => unmapped_acceptance.push(format!("{} ({})", record.acceptance, a_family)),
        }

        // The `spec` field is a semicolon-separated list of owning spec dirs.
        for spec in record
            .spec
            .split(';')
            .map(str::trim)
            .filter(|s| !s.is_empty())
        {
            if !root.join("specs").join(spec).is_dir() {
                missing_specs.insert(spec.to_string());
            }
        }
    }

    assert!(
        unmapped_verification.is_empty(),
        "{} verification ids have no evidence family/artifact: {unmapped_verification:?}",
        unmapped_verification.len()
    );
    assert!(
        unmapped_acceptance.is_empty(),
        "{} acceptance ids have no evidence family/artifact: {unmapped_acceptance:?}",
        unmapped_acceptance.len()
    );
    assert!(
        missing_artifacts.is_empty(),
        "mapped evidence artifacts do not exist: {missing_artifacts:?}"
    );
    assert!(
        missing_specs.is_empty(),
        "owning spec directories do not exist: {missing_specs:?}"
    );
    assert!(
        absent_from_markdown.is_empty(),
        "ids present in JSON but absent from the markdown matrix: {absent_from_markdown:?}"
    );

    // Registry must not drift ahead of the matrices either.
    let used_verification: BTreeSet<String> = verification.iter().map(|id| family(id)).collect();
    let used_acceptance: BTreeSet<String> = acceptance.iter().map(|id| family(id)).collect();
    let stale: Vec<String> = families
        .verification_families
        .keys()
        .filter(|k| !used_verification.contains(*k))
        .chain(
            families
                .acceptance_families
                .keys()
                .filter(|k| !used_acceptance.contains(*k)),
        )
        .cloned()
        .collect();
    assert!(
        stale.is_empty(),
        "evidence-families.json lists id families no matrix id uses: {stale:?}"
    );

    println!(
        "traceability: {} records, {} verification ids, {} acceptance ids, {} verification families, {} acceptance families, all artifacts present",
        records.len(),
        verification.len(),
        acceptance.len(),
        used_verification.len(),
        used_acceptance.len()
    );
}
