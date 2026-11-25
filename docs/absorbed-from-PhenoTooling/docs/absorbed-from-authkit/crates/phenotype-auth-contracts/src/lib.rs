//! Auth and policy contract traits for the Phenotype ecosystem.
//!
//! Terminal owner: **Authvault** (P4 contracts decompose slice 2).
//! Generic cross-cutting contracts (`Contract`, `Event`, `MetricsHook`) remain on
//! phenoShared interim per [ADR-ECO-014](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/adrs/ADR-ECO-014-phenoshared-decompose.md).

#![warn(missing_docs)]
#![warn(clippy::all)]

pub mod auth;
pub mod policy;

pub use auth::{
    AuditAction, AuditEvent, AuditOutcome, AuditSink, DataKey, KmsError, KeyManagementService,
    PasswordHasher, RefreshTokenStore, RevocationStore,
};
pub use policy::{
    AuthorizationContext, AuthorizationDecision, PolicyEffect, PolicyEvaluator,
};
