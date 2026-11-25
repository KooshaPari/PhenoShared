//! BDD test shim for pheno-plugin-vessel.
//!
//! The 224-line body that previously lived here has been extracted to
//! `phenoShared/crates/phenotype-test-support/src/bdd/steps.rs` as part
//! of the lib-merge across PhenoSchema/pheno-xdd-lib, PhenoSchema/pheno-xdd,
//! and PhenoPlugins/pheno-plugin-vessel. Re-export the shared body so
//! existing BDD entry points keep working.
#[path = "../../../../../phenoShared/crates/phenotype-test-support/src/bdd/steps.rs"]
mod _shared;
pub use _shared::*;
