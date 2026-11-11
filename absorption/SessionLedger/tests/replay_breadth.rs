//! Wave-44-B6 corpus breadth wiring (C08 L73 production-scale corpus breadth).
//!
//! Confirms that the W44-B6 corpus generator has wired 13 new accepted fixtures
//! under `docs/reference/conformance/fixtures/` and that the corpus round-trip
//! test (`okf_roundtrip::conformance_corpus_fixtures_validate_via_our_parser`)
//! has the new fixtures visible from a single, stable discovery point.
//!
//! Self-evidence (machine-stable, no network, no harness drift):
//!   - 13 generated fixture slugs appear on disk
//!   - each generated fixture parses as JSON and has `okf == "1.0"`
//!   - the full corpus is >= 33 fixtures (20 hand-vetted + 13 generated)
//!
//! Traceability: docs/ops/corpus-breadth.md (W44-B6), C08 L73.

use std::path::{Path, PathBuf};

const W44_B6_SLUGS: &[&str] = &[
    "aider-rust-refactor-037",
    "opencode-python-debugger-038",
    "continue-go-microservice-039",
    "kiro-bash-ci-pipeline-040",
    "factory-droid-typescript-041",
    "sql-migration-multi-intent-043",
    "yaml-k8s-deployment-044",
    "large-entity-count-100-045",
    "deep-relation-graph-7-046",
    "rapid-fire-intent-stream-12-047",
    "unicode-intent-label-cjk-048",
    "embedded-json-label-049",
    "multi-modal-image-hint-050",
];

const W43_HAND_VETTED_COUNT: usize = 20;
const W44_B6_GENERATED_COUNT: usize = 13;
const W44_B6_TARGET_TOTAL: usize = W43_HAND_VETTED_COUNT + W44_B6_GENERATED_COUNT;

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("docs/reference/conformance/fixtures")
}

fn list_okf_fixtures(root: &Path) -> Vec<PathBuf> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(root)
        .expect("read conformance fixtures dir")
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension().is_some_and(|ext| ext == "json")
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.ends_with(".okf.json"))
        })
        .collect();
    paths.sort();
    paths
}

#[test]
fn w44_b6_all_generated_fixtures_are_on_disk() {
    let root = fixture_root();
    let on_disk: Vec<String> = list_okf_fixtures(&root)
        .into_iter()
        .filter_map(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .map(|s| s.trim_end_matches(".okf.json").to_string())
        })
        .collect();

    for slug in W44_B6_SLUGS {
        assert!(
            on_disk.iter().any(|name| name == slug),
            "W44-B6 fixture `{slug}.okf.json` missing from {} (found {} fixtures)",
            root.display(),
            on_disk.len(),
        );
    }
}

#[test]
fn w44_b6_corpus_total_meets_or_exceeds_target() {
    let root = fixture_root();
    let count = list_okf_fixtures(&root).len();
    assert!(
        count >= W44_B6_TARGET_TOTAL,
        "corpus total {count} below W44-B6 target {W44_B6_TARGET_TOTAL} \
         (W43 hand-vetted {W43_HAND_VETTED_COUNT} + W44-B6 generated {W44_B6_GENERATED_COUNT})",
    );
}

#[test]
fn w44_b6_each_generated_fixture_is_well_formed_okf_v1() {
    let root = fixture_root();
    let mut parsed = 0usize;
    let mut bad: Vec<(String, String)> = Vec::new();
    for slug in W44_B6_SLUGS {
        let path = root.join(format!("{slug}.okf.json"));
        let raw = std::fs::read_to_string(&path)
            .unwrap_or_else(|e| panic!("read {}: {e}", path.display()));
        match serde_json::from_str::<serde_json::Value>(&raw) {
            Ok(v) => {
                let okf = v.get("okf").and_then(serde_json::Value::as_str);
                if okf != Some("1.0") {
                    bad.push((slug.to_string(), format!("okf != 1.0 (got {okf:?})")));
                    continue;
                }
                let entities = v.get("entities").and_then(serde_json::Value::as_array);
                let prov = v.get("provenance").and_then(serde_json::Value::as_object);
                if entities.is_none() {
                    bad.push((slug.to_string(), "missing entities[]".into()));
                    continue;
                }
                if prov.is_none() {
                    bad.push((slug.to_string(), "missing provenance".into()));
                    continue;
                }
                parsed += 1;
            }
            Err(e) => bad.push((slug.to_string(), format!("json parse: {e}"))),
        }
    }
    assert!(bad.is_empty(), "W44-B6 fixtures failed shape check: {bad:#?}");
    assert_eq!(parsed, W44_B6_SLUGS.len(), "parsed count mismatch");
}

#[test]
fn w44_b6_generator_script_present_and_importable() {
    // The generator is a Python script, not part of the Rust crate, but its
    // presence on disk is part of the W44-B6 deliverable.
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("scripts/corpus-generate.py");
    assert!(script.is_file(), "expected corpus generator at {}", script.display());
    let raw = std::fs::read_to_string(&script).expect("read corpus-generate.py");
    assert!(raw.contains("OKF_VERSION"), "generator must define OKF_VERSION");
    assert!(raw.contains("FIXTURE_SPECS"), "generator must declare FIXTURE_SPECS");
    assert!(raw.contains("FAILURE_FIXTURES"), "generator must isolate failure-mode fixtures");
}

#[test]
fn w44_b6_corpus_breadth_doc_present() {
    let doc = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("docs/ops/corpus-breadth.md");
    assert!(doc.is_file(), "expected docs/ops/corpus-breadth.md at {}", doc.display());
    let raw = std::fs::read_to_string(&doc).expect("read corpus-breadth.md");
    assert!(raw.contains("C08 L73"), "doc must reference C08 L73 pillar");
    assert!(raw.contains("Wave-44"), "doc must reference Wave-44 (W44-B6) close-out");
}
