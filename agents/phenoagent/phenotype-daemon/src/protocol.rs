//! Protocol definitions for phenotype-daemon RPC
//!
//! This tree is a non-workspace snapshot of the daemon. It used to carry its own
//! full copy of the protocol, which drifted: this file declared a port
//! different from the one the copy's `main.rs` bound, so a client
//! that imported the constant could never reach the server.
//!
//! Rather than keep two definitions in sync by hand, the canonical file is
//! `crates/pheno-agent/phenotype-daemon/src/protocol.rs` and this module
//! re-exports it. Anything that builds this tree still gets the same item names.

#[path = "../../../../crates/pheno-agent/phenotype-daemon/src/protocol.rs"]
mod canonical;

pub use canonical::*;
