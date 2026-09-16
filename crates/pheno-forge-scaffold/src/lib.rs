//! # pheno-forge-scaffold
//!
//! Documented scaffold-only task-runner shape, ported from
//! [`KooshaPari/phenoForge`](https://github.com/KooshaPari/phenoForge) on
//! 2026-09-10. The original phenoForge repo's bounded target (Recovery hold
//! / G2 sentinel + negative invocation) was satisfied by explicit
//! classification of the unimplemented state, not by re-implementation;
//! this crate is the artifact of that classification.
//!
//! See `PROVENANCE.md` at the workspace root for the full migration trail
//! and `cargo test -p pheno-forge-scaffold` for the 9 negative-oracle tests
//! + 1 `#[ignore]` sentinel that lock the truthful state.
//!
//! This crate is intentionally minimal: the binary `pheno-forge-scaffold`
//! just prints `Running task: <name>`, the same 12-line `clap` stub that
//! phenoForge had at HEAD `2fccbc27`. It exists as an exemplar so other
//! workspace members that find themselves as scaffolds can be modelled on
//! it rather than fabricating fictional features.
