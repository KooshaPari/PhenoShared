//! Policy and authorization contract traits.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Policy effect — allow or deny.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PolicyEffect {
    /// Grant access.
    Allow,
    /// Deny access.
    Deny,
}

/// Authorization decision returned by a policy evaluator.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthorizationDecision {
    /// Whether access is granted.
    pub allowed: bool,
    /// Optional human-readable explanation.
    pub reason: Option<String>,
}

impl AuthorizationDecision {
    /// Construct an allow decision.
    pub fn allow() -> Self {
        Self { allowed: true, reason: None }
    }

    /// Construct a deny decision with a reason.
    pub fn deny(reason: impl Into<String>) -> Self {
        Self {
            allowed: false,
            reason: Some(reason.into()),
        }
    }
}

/// Context supplied to a policy evaluation request.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AuthorizationContext {
    /// Subject identity (user or service principal).
    pub subject: Option<String>,
    /// Resource identifier being accessed.
    pub resource: String,
    /// Action being performed.
    pub action: String,
    /// Attribute bag for ABAC-style conditions.
    pub attributes: HashMap<String, Value>,
}

impl AuthorizationContext {
    /// Create a new authorization context.
    pub fn new(resource: impl Into<String>, action: impl Into<String>) -> Self {
        Self {
            subject: None,
            resource: resource.into(),
            action: action.into(),
            attributes: HashMap::new(),
        }
    }

    /// Attach a subject.
    pub fn with_subject(mut self, subject: impl Into<String>) -> Self {
        self.subject = Some(subject.into());
        self
    }

    /// Insert an attribute.
    pub fn with_attribute(mut self, key: impl Into<String>, value: Value) -> Self {
        self.attributes.insert(key.into(), value);
        self
    }
}

/// Contract for making authorization decisions.
pub trait PolicyEvaluator: Send + Sync {
    /// Evaluate whether the request is allowed.
    fn evaluate(&self, ctx: &AuthorizationContext) -> AuthorizationDecision;

    /// Optional explanation of the decision (for audit / debugging).
    fn explain(&self, ctx: &AuthorizationContext) -> Vec<String> {
        let decision = self.evaluate(ctx);
        if decision.allowed {
            vec!["ALLOW".to_string()]
        } else {
            vec![format!(
                "DENY: {}",
                decision.reason.as_deref().unwrap_or("unspecified")
            )]
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct AllowAll;

    impl PolicyEvaluator for AllowAll {
        fn evaluate(&self, _ctx: &AuthorizationContext) -> AuthorizationDecision {
            AuthorizationDecision::allow()
        }
    }

    struct DenyConfidential;

    impl PolicyEvaluator for DenyConfidential {
        fn evaluate(&self, ctx: &AuthorizationContext) -> AuthorizationDecision {
            if ctx
                .attributes
                .get("classification")
                .and_then(|v| v.as_str())
                == Some("confidential")
            {
                AuthorizationDecision::deny("confidential resource")
            } else {
                AuthorizationDecision::allow()
            }
        }
    }

    #[test]
    fn allow_all_grants_access() {
        let engine = AllowAll;
        let ctx = AuthorizationContext::new("documents:1", "read");
        assert!(engine.evaluate(&ctx).allowed);
    }

    #[test]
    fn deny_confidential_blocks_matching_attribute() {
        let engine = DenyConfidential;
        let ctx = AuthorizationContext::new("documents:1", "read")
            .with_attribute("classification", Value::String("confidential".into()));
        assert!(!engine.evaluate(&ctx).allowed);
    }

    #[test]
    fn explain_returns_deny_reason() {
        let engine = DenyConfidential;
        let ctx = AuthorizationContext::new("documents:1", "read")
            .with_attribute("classification", Value::String("confidential".into()));
        let lines = engine.explain(&ctx);
        assert!(lines[0].starts_with("DENY:"));
    }
}
