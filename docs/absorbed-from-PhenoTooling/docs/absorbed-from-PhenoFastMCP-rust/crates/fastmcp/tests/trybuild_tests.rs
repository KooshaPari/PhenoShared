//! Compile-fail tests for procedural macros using trybuild.
//!
//! These tests verify that macros produce clear compile errors
//! for invalid usage patterns.

#[test]
fn compile_fail_tests() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/trybuild/*.rs");
}
