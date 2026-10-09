//! Stub library for the fuzz harness crate.
//!
//! This file exists so `cargo metadata` succeeds on a manifest that
//! declares no `[[bin]]` / `[[test]]` / `[lib]` target. Real fuzz
//! targets are normally added under `fuzz_targets/`; this lib is
//! just a placeholder for the manifest's own metadata contract.
//!
//! Removing this file is safe if the crate gains a real `[[bin]]`
//! or `[lib]` declaration in `Cargo.toml`.
