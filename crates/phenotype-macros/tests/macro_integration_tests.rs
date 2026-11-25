//! Integration tests for the current phenotype-macros crate surface.
//! Traces to: FR-MACRO-001, FR-MACRO-002, FR-MACRO-003

use std::fs;
use std::path::PathBuf;

fn crate_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn read_source(path: &str) -> String {
    fs::read_to_string(crate_root().join(path)).unwrap()
}

#[test]
fn async_trait_wrapper_reexports_async_trait() {
    let source = read_source("src/async_trait_wrapper.rs");
    assert!(source.contains("pub use async_trait::async_trait;"));
    assert!(source.contains("pub type AsyncFn<T>"));
}

#[test]
fn error_derive_reexports_thiserror_and_marker_trait() {
    let source = read_source("src/error_derive.rs");
    assert!(source.contains("pub use thiserror::Error;"));
    assert!(source.contains("pub trait CrossCrateError"));
    assert!(source
        .contains("impl<T: std::error::Error + Send + Sync + 'static> CrossCrateError for T {}"));
}

#[test]
fn macros_crate_source_layout_matches_expected_modules() {
    let mut modules: Vec<String> = fs::read_dir(crate_root().join("src"))
        .unwrap()
        .map(|entry| entry.unwrap().file_name().into_string().unwrap())
        .collect();
    modules.sort();

    assert_eq!(
        modules,
        vec![
            "async_trait_wrapper.rs".to_string(),
            "error_derive.rs".to_string(),
            "lib.rs".to_string(),
        ]
    );
}

#[test]
fn tests_document_current_macro_surface() {
    let doc = read_source("tests/macro_integration_tests.rs");
    assert!(doc.contains("current phenotype-macros crate surface"));
    assert!(doc.contains("CrossCrateError"));
    assert!(doc.contains("async_trait_wrapper_reexports_async_trait"));
}
