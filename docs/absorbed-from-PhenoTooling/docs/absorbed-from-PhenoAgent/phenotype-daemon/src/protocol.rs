//! Protocol definitions for phenotype-daemon RPC
//!
//! This tree is a documentation snapshot of the daemon, not a buildable crate
//! (it carries `src/` only and no manifest). It used to hold its own full copy of
//! the protocol, which drifted: this file declared the port as 8953 while this
//! snapshot's `main.rs` bound 9456, so a client that imported the constant could
//! never reach the server.
//!
//! Rather than keep two definitions in sync by hand, the canonical file is
//! `crates/pheno-agent/phenotype-daemon/src/protocol.rs` and this module
//! re-exports it, exactly as `agents/phenoagent/phenotype-daemon/src/protocol.rs`
//! does. Reading this snapshot therefore shows the same item names and the same
//! port the live daemon uses.

#[path = "../../../../../../crates/pheno-agent/phenotype-daemon/src/protocol.rs"]
mod canonical;

pub use canonical::*;
