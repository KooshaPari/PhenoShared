// SPDX-License-Identifier: MIT OR Apache-2.0
//! `phenotype-port-interfaces` — shared port interface trait definitions
//! for the Phenotype formal-verification backend family.
//!
//! This crate is the Rust twin of the TypeScript `ContractVerifier`
//! port in `ports/contract_verifier.ts`. It exists so that all backend
//! adapters (Kani, Prusti, Coq) implement the same trait shape and so
//! that the dependency surface of the toolchain can be audited with
//! `cargo deny`.
#![deny(unsafe_code)]
#![warn(missing_docs)]

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Supported formal-verification backends.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Backend {
    /// The Kani model checker.
    Kani,
    /// The Prusti deductive verifier.
    Prusti,
    /// The Coq proof assistant.
    Coq,
}

impl Backend {
    /// String tag used in proofs and the `Backend` field of the
    /// matching TypeScript port.
    pub const fn as_str(self) -> &'static str {
        match self {
            Backend::Kani => "kani",
            Backend::Prusti => "prusti",
            Backend::Coq => "coq",
        }
    }
}

/// A verification request: a named contract + the backend that should run it.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct VerifyRequest {
    /// Backend that should service the request.
    pub backend: Backend,
    /// Contract being verified.
    pub contract_name: String,
}

/// A verification result returned by a backend.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VerifyResponse {
    /// Whether the contract held.
    pub ok: bool,
    /// Optional human-readable proof.
    pub proof: Option<String>,
    /// Optional counterexample string.
    pub counterexample: Option<String>,
    /// Wall-clock duration in milliseconds.
    pub duration_ms: u64,
}

/// Errors surfaced by backend adapters.
#[derive(Debug, Error)]
pub enum PortError {
    /// The backend could not be initialized (toolchain missing, etc).
    #[error("backend init failed: {0}")]
    Init(String),
    /// The backend was given a contract it could not parse.
    #[error("invalid contract: {0}")]
    InvalidContract(String),
    /// A timeout occurred while the backend was running.
    #[error("backend timeout after {0}ms")]
    Timeout(u64),
    /// Catch-all for unexpected internal errors.
    #[error("internal error: {0}")]
    Internal(String),
}

/// Hexagonal port trait implemented by every backend adapter.
#[async_trait]
pub trait Port: Send + Sync {
    /// The backend that this port services.
    fn backend(&self) -> Backend;

    /// Verify a contract on behalf of the port.
    async fn verify(&self, request: VerifyRequest) -> Result<VerifyResponse, PortError>;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backend_str_round_trip_matches_typescript_port() {
        assert_eq!(Backend::Kani.as_str(), "kani");
        assert_eq!(Backend::Prusti.as_str(), "prusti");
        assert_eq!(Backend::Coq.as_str(), "coq");
    }

    #[test]
    fn request_serde_round_trip() {
        let r = VerifyRequest {
            backend: Backend::Coq,
            contract_name: "no_overflow".to_string(),
        };
        let j = serde_json::to_string(&r).unwrap();
        let back: VerifyRequest = serde_json::from_str(&j).unwrap();
        assert_eq!(r, back);
    }
}
