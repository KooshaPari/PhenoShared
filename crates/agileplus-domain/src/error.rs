//! Domain error types.

use phenotype_error_core::DomainError as CoreDomainError;

#[derive(Debug, thiserror::Error)]
pub enum DomainError {
    #[error("not implemented")]
    NotImplemented,
    #[error("invalid transition from {from} to {to}: {reason}")]
    InvalidTransition {
        from: String,
        to: String,
        reason: String,
    },
    #[error("no-op transition: already in state {0}")]
    NoOpTransition(String),
    #[error("entity not found: {0}")]
    NotFound(String),
    #[error("storage error: {0}")]
    Storage(String),
    #[error("vcs error: {0}")]
    Vcs(String),
    #[error("agent error: {0}")]
    Agent(String),
    #[error("review error: {0}")]
    Review(String),
    #[error("timeout after {0} seconds")]
    Timeout(u64),
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("{0}")]
    Other(String),
    // --- Module errors ---
    #[error("module not found: {0}")]
    ModuleNotFound(String),
    #[error("circular module reference: cannot set {child} as parent of {ancestor}")]
    CircularModuleRef { child: String, ancestor: String },
    #[error("module has dependents: {0}")]
    ModuleHasDependents(String),
    #[
        error(
            "feature not in module scope: feature {feature_slug} is not owned by or tagged to module {module_slug}"
        )
    ]
    FeatureNotInModuleScope {
        feature_slug: String,
        module_slug: String,
    },
    // --- Cycle errors ---
    #[error("cycle not found: {0}")]
    CycleNotFound(String),
    #[error("cycle gate not met: {0}")]
    CycleGateNotMet(String),
}

impl From<CoreDomainError> for DomainError {
    fn from(err: CoreDomainError) -> Self {
        match err {
            CoreDomainError::Validation(msg) => DomainError::Other(format!("validation: {msg}")),
            CoreDomainError::InvariantViolation(msg) => {
                DomainError::Other(format!("invariant: {msg}"))
            },
            CoreDomainError::NotFound { entity, id } => {
                DomainError::NotFound(format!("{entity} {id}"))
            },
            CoreDomainError::Duplicate { entity, id } => {
                DomainError::Conflict(format!("duplicate {entity} {id}"))
            },
            CoreDomainError::InvalidStateTransition { from, to } => {
                DomainError::InvalidTransition {
                    from,
                    to,
                    reason: "invalid state transition".to_string(),
                }
            },
            CoreDomainError::NotPermitted(msg) => {
                DomainError::Other(format!("not permitted: {msg}"))
            },
            CoreDomainError::PolicyEvaluation(msg) => DomainError::Other(format!("policy: {msg}")),
            CoreDomainError::Other(msg) => DomainError::Other(msg),
        }
    }
}

impl From<DomainError> for CoreDomainError {
    fn from(err: DomainError) -> Self {
        match err {
            DomainError::NotFound(msg) => {
                let parts: Vec<&str> = msg.splitn(2, ' ').collect();
                if parts.len() == 2 {
                    CoreDomainError::NotFound {
                        entity: parts[0].to_string(),
                        id: parts[1].to_string(),
                    }
                } else {
                    CoreDomainError::NotFound {
                        entity: "unknown".to_string(),
                        id: msg,
                    }
                }
            },
            DomainError::Conflict(msg) => CoreDomainError::Other(format!("conflict: {msg}")),
            DomainError::InvalidTransition { from, to, reason } => {
                if reason == "invalid state transition" {
                    CoreDomainError::InvalidStateTransition { from, to }
                } else {
                    CoreDomainError::Other(format!("transition {from} -> {to}: {reason}"))
                }
            },
            DomainError::Other(msg) => CoreDomainError::Other(msg),
            _ => CoreDomainError::Other(err.to_string()),
        }
    }
}
