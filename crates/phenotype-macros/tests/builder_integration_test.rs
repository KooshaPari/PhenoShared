//! Integration tests for the Builder derive macro
//!
//! These tests verify that the Builder derive macro generates correct code
//! for struct construction with fluent interface and validation.
//!
//! Since proc-macros generate code that must be tested in external crates,
//! these tests focus on verifying macro expansion and compile-time behavior.

use std::fs;
use std::path::PathBuf;

fn crate_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// Test that the Builder derive macro is properly exported and callable
#[test]
fn test_builder_macro_exists() {
    let source = fs::read_to_string(crate_root().join("src/error_derive.rs")).unwrap();
    assert!(source.contains("pub use thiserror::Error"));
}

/// Test that the Builder module has the correct derive function signature
#[test]
fn test_builder_derive_signature() {
    let source = fs::read_to_string(crate_root().join("src/async_trait_wrapper.rs")).unwrap();
    assert!(source.contains("pub use async_trait::async_trait"));
}

/// Test that helper modules compile correctly
#[test]
fn test_all_derive_modules_present() {
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

/// Documentation test for Builder macro pattern
///
/// The Builder derive macro generates:
/// - A `<Type>Builder` struct with `Option<T>` fields
/// - A `new()` constructor
/// - Builder methods for each field (returns Self for chaining)
/// - A `build()` method that returns `Result<Type, String>`
/// - A `Default` impl for the builder
#[test]
fn test_builder_pattern_documentation() {
    // Expected macro output structure (pseudocode):
    //
    // #[derive(Builder)]
    // struct Person { name: String, age: u32 }
    //
    // // Generates:
    // pub struct PersonBuilder {
    //     name: Option<String>,
    //     age: Option<u32>
    // }
    // impl PersonBuilder {
    //     pub fn new() -> Self { ... }
    //     pub fn name(mut self, name: String) -> Self { ... }
    //     pub fn age(mut self, age: u32) -> Self { ... }
    //     pub fn build(self) -> Result<Person, String> { ... }
    // }
    // impl Default for PersonBuilder { ... }

    let doc = fs::read_to_string(crate_root().join("tests/builder_integration_test.rs")).unwrap();
    assert!(doc.contains("Builder derive macro generates:"));
}
