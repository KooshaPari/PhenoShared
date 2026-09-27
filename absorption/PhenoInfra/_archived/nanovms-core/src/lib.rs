// SPDX-License-Identifier: MIT OR Apache-2.0
//! nanovms-core — NVMS 3-tier isolation static library
//!
//! This crate contains the Go source for NVMS (3-tier isolation:
//! WASM/gVisor/Firecracker), compiled via CGo into a static archive.
//!
//! The build.rs script orchestrates `go build -buildmode=c-archive` to
//! produce `libnvms_core_<os>_<arch>.a`, which is linked by nvms-ffi
//! and downstream crates.

pub const VERSION: &str = "0.1.0";
