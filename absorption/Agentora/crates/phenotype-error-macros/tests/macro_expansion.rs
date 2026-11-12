//! Integration tests for the PhenotypeError derive macro.
//!
//! The macro generates Display (via Debug) and std::error::Error impls.

use phenotype_error_macros::PhenotypeError;
use std::error::Error as StdError;

// ── Test types ──────────────────────────────────────────────────────────────

/// Simple enum with unit variants.
#[derive(Debug, PhenotypeError)]
#[allow(dead_code)]
enum SimpleError {
    NotFound,
    PermissionDenied,
    Timeout,
}

/// Enum with tuple-style variants carrying data.
#[derive(Debug, PhenotypeError)]
#[allow(dead_code)]
enum DataError {
    Io(std::io::ErrorKind),
    Custom(String),
    Nested { code: u32, detail: String },
}

/// Enum mixing unit and data-carrying variants.
#[derive(Debug, PhenotypeError)]
#[allow(dead_code)]
enum MixedError {
    Empty,
    WithMsg(String),
    WithCode(i32),
    Compound { source: String, line: u32 },
}

/// Struct (not enum) with derive.
#[derive(Debug, PhenotypeError)]
#[allow(dead_code)]
struct StructError {
    field: String,
}

/// Unit struct with derive.
#[derive(Debug, PhenotypeError)]
#[allow(dead_code)]
struct UnitError;

// ── Tests: compilation ──────────────────────────────────────────────────────

#[test]
fn derive_compiles_on_unit_variants() {
    let _ = SimpleError::NotFound;
}

#[test]
fn derive_compiles_on_data_variants() {
    let _ = DataError::Io(std::io::ErrorKind::NotFound);
    let _ = DataError::Custom("msg".into());
}

#[test]
fn derive_compiles_on_mixed_variants() {
    let _ = MixedError::Empty;
    let _ = MixedError::WithMsg("x".into());
    let _ = MixedError::WithCode(42);
    let _ = MixedError::Compound {
        source: "s".into(),
        line: 1,
    };
}

#[test]
fn derive_compiles_on_struct() {
    let _ = StructError { field: "f".into() };
}

#[test]
fn derive_compiles_on_unit_struct() {
    let _ = UnitError;
}

// ── Tests: Display generation ───────────────────────────────────────────────

#[test]
fn display_uses_debug_formatting() {
    let err = SimpleError::NotFound;
    let display = format!("{}", err);
    assert_eq!(display, "NotFound");
}

#[test]
fn display_with_data_variants() {
    let err = DataError::Custom("something broke".into());
    let display = format!("{}", err);
    assert!(display.contains("something broke"));
}

#[test]
fn display_with_nested_variant() {
    let err = DataError::Nested {
        code: 500,
        detail: "internal".into(),
    };
    let display = format!("{}", err);
    assert!(display.contains("500"));
    assert!(display.contains("internal"));
}

#[test]
fn display_struct_error() {
    let err = StructError {
        field: "test".into(),
    };
    let display = format!("{}", err);
    assert!(display.contains("test"));
}

#[test]
fn display_unit_struct_error() {
    let err = UnitError;
    let display = format!("{}", err);
    assert_eq!(display, "UnitError");
}

// ── Tests: std::error::Error implementation ─────────────────────────────────

#[test]
fn error_trait_implemented_for_simple() {
    fn assert_error<E: StdError>(_e: &E) {}
    assert_error(&SimpleError::NotFound);
}

#[test]
fn error_trait_implemented_for_data() {
    fn assert_error<E: StdError>(_e: &E) {}
    assert_error(&DataError::Custom("x".into()));
}

#[test]
fn error_trait_implemented_for_mixed() {
    fn assert_error<E: StdError>(_e: &E) {}
    assert_error(&MixedError::Empty);
}

#[test]
fn error_trait_implemented_for_struct() {
    fn assert_error<E: StdError>(_e: &E) {}
    assert_error(&StructError {
        field: String::new(),
    });
}

#[test]
fn error_trait_implemented_for_unit_struct() {
    fn assert_error<E: StdError>(_e: &E) {}
    assert_error(&UnitError);
}

#[test]
fn error_trait_description_matches_display() {
    let err = SimpleError::Timeout;
    assert_eq!(err.to_string(), format!("{:?}", err));
}

#[test]
fn error_trait_object_safe() {
    let err: Box<dyn StdError> = Box::new(SimpleError::PermissionDenied);
    let _ = err.to_string();
}
