//! OKF bundle validation — structural integrity checks applied before ingest.
//!
//! ## Validated fields
//!
//! | Field              | Rule                                                   |
//! |--------------------|--------------------------------------------------------|
//! | `bundle_id`        | Non-empty string                                       |
//! | `created_at`       | Parseable RFC 3339 datetime string                     |
//! | `messages`         | Non-empty array                                        |
//! | `messages[].role`  | One of `"user"`, `"assistant"`, `"system"`, `"tool"`   |
//! | `messages[].content` | Non-empty string                                     |
//! | `token_count`      | Non-negative integer                                   |

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Ingest payload types
// ---------------------------------------------------------------------------

/// A single message in an ingested OKF bundle.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PostMessage {
    /// Message author role.
    pub role: String,
    /// Message text body (may be multi-paragraph).
    pub content: String,
}

/// The HTTP ingest payload for a single OKF bundle.
///
/// This is the body accepted by `POST /api/ingest`. Fields map onto the
/// daemon's internal `Session` type after validation passes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PostBundle {
    /// Unique bundle identifier. Becomes the on-disk filename stem.
    pub bundle_id: String,
    /// RFC 3339 creation timestamp, e.g. `"2024-06-01T12:00:00Z"`.
    pub created_at: String,
    /// Ordered list of messages in this session.
    pub messages: Vec<PostMessage>,
    /// Total token count for the bundle. Must be ≥ 0.
    pub token_count: i64,
}

// ---------------------------------------------------------------------------
// Validation result types
// ---------------------------------------------------------------------------

/// A single validation failure for a specific field path.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ValidationError {
    /// Dot-separated field path, e.g. `"bundle_id"` or `"messages[2].role"`.
    pub field: String,
    /// Short machine-readable error code, e.g. `"required"` or `"invalid_role"`.
    pub code: String,
    /// Human-readable explanation of the failure.
    pub message: String,
}

/// Aggregated result of validating one [`PostBundle`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ValidationResult {
    /// `true` iff `errors` is empty.
    pub valid: bool,
    /// All validation errors found; empty when `valid` is `true`.
    pub errors: Vec<ValidationError>,
}

impl ValidationResult {
    fn new(errors: Vec<ValidationError>) -> Self {
        Self { valid: errors.is_empty(), errors }
    }
}

// ---------------------------------------------------------------------------
// Validation logic
// ---------------------------------------------------------------------------

/// Valid message roles for an ingested bundle.
const VALID_ROLES: &[&str] = &["user", "assistant", "system", "tool"];

/// Validate a [`PostBundle`] and return a [`ValidationResult`].
///
/// This function is pure (no I/O) and collects *all* errors in a single pass
/// rather than failing on the first violation.
#[must_use]
pub fn validate_okf_bundle(bundle: &PostBundle) -> ValidationResult {
    let mut errors: Vec<ValidationError> = Vec::new();

    // 1. bundle_id — non-empty
    if bundle.bundle_id.trim().is_empty() {
        errors.push(ValidationError {
            field: "bundle_id".into(),
            code: "required".into(),
            message: "bundle_id must not be empty".into(),
        });
    }
    if bundle.bundle_id.contains("..") || bundle.bundle_id.contains(['/', '\\', ':']) {
        errors.push(ValidationError {
            field: "bundle_id".into(),
            code: "unsafe_path".into(),
            message: "bundle_id must not contain path traversal or path separators".into(),
        });
    }

    // 2. created_at — parseable RFC 3339
    if chrono::DateTime::parse_from_rfc3339(&bundle.created_at).is_err() {
        errors.push(ValidationError {
            field: "created_at".into(),
            code: "invalid_rfc3339".into(),
            message: format!("created_at {:?} is not a valid RFC 3339 datetime", bundle.created_at),
        });
    }

    // 3. messages — non-empty
    if bundle.messages.is_empty() {
        errors.push(ValidationError {
            field: "messages".into(),
            code: "required".into(),
            message: "messages must contain at least one entry".into(),
        });
    } else {
        // 4. per-message: role and content
        for (i, msg) in bundle.messages.iter().enumerate() {
            let role_field = format!("messages[{i}].role");
            let content_field = format!("messages[{i}].content");

            if !VALID_ROLES.contains(&msg.role.as_str()) {
                errors.push(ValidationError {
                    field: role_field,
                    code: "invalid_role".into(),
                    message: format!("role {:?} is not one of {:?}", msg.role, VALID_ROLES),
                });
            }

            if msg.content.trim().is_empty() {
                errors.push(ValidationError {
                    field: content_field,
                    code: "required".into(),
                    message: "content must not be empty".into(),
                });
            }
        }
    }

    // 5. token_count — non-negative
    if bundle.token_count < 0 {
        errors.push(ValidationError {
            field: "token_count".into(),
            code: "negative".into(),
            message: format!("token_count {} must be >= 0", bundle.token_count),
        });
    }

    ValidationResult::new(errors)
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    // Traceability: these validation cases are acceptance evidence for FR-002,
    // including the rules enforced by POST /api/ingest.
    use super::*;

    /// Build a minimal valid bundle for property-style testing.
    fn valid_bundle() -> PostBundle {
        PostBundle {
            bundle_id: "sess-001".into(),
            created_at: "2024-06-01T12:00:00Z".into(),
            messages: vec![PostMessage { role: "user".into(), content: "hello".into() }],
            token_count: 10,
        }
    }

    #[test]
    fn fr002_valid_bundle_passes() {
        let result = validate_okf_bundle(&valid_bundle());
        assert!(result.valid, "unexpected errors: {:?}", result.errors);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn empty_bundle_id_is_rejected() {
        let b = PostBundle { bundle_id: "".into(), ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "bundle_id" && e.code == "required"));
    }

    #[test]
    fn whitespace_only_bundle_id_is_rejected() {
        let b = PostBundle { bundle_id: "   ".into(), ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(r.errors.iter().any(|e| e.field == "bundle_id"));
    }

    #[test]
    fn invalid_created_at_is_rejected() {
        let b = PostBundle { created_at: "not-a-date".into(), ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "created_at" && e.code == "invalid_rfc3339"));
    }

    #[test]
    fn valid_rfc3339_offset_passes() {
        // +05:30 offset should also parse correctly
        let b = PostBundle { created_at: "2024-06-01T17:30:00+05:30".into(), ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(r.valid, "unexpected errors: {:?}", r.errors);
    }

    #[test]
    fn empty_messages_is_rejected() {
        let b = PostBundle { messages: vec![], ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "messages" && e.code == "required"));
    }

    #[test]
    fn invalid_role_is_rejected() {
        let b = PostBundle {
            messages: vec![PostMessage { role: "bot".into(), content: "hi".into() }],
            ..valid_bundle()
        };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "messages[0].role" && e.code == "invalid_role"));
    }

    #[test]
    fn all_valid_roles_accepted() {
        for role in ["user", "assistant", "system", "tool"] {
            let b = PostBundle {
                messages: vec![PostMessage { role: role.into(), content: "x".into() }],
                ..valid_bundle()
            };
            let r = validate_okf_bundle(&b);
            assert!(r.valid, "role {role:?} should be valid");
        }
    }

    #[test]
    fn empty_content_is_rejected() {
        let b = PostBundle {
            messages: vec![PostMessage { role: "user".into(), content: "".into() }],
            ..valid_bundle()
        };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "messages[0].content" && e.code == "required"));
    }

    #[test]
    fn negative_token_count_is_rejected() {
        let b = PostBundle { token_count: -1, ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        assert!(r.errors.iter().any(|e| e.field == "token_count" && e.code == "negative"));
    }

    #[test]
    fn zero_token_count_is_valid() {
        let b = PostBundle { token_count: 0, ..valid_bundle() };
        let r = validate_okf_bundle(&b);
        assert!(r.valid);
    }

    #[test]
    fn multiple_errors_are_collected() {
        let b = PostBundle {
            bundle_id: "".into(),
            created_at: "bad".into(),
            messages: vec![],
            token_count: -5,
        };
        let r = validate_okf_bundle(&b);
        assert!(!r.valid);
        // All four failure categories must be present
        assert!(r.errors.iter().any(|e| e.field == "bundle_id"));
        assert!(r.errors.iter().any(|e| e.field == "created_at"));
        assert!(r.errors.iter().any(|e| e.field == "messages"));
        assert!(r.errors.iter().any(|e| e.field == "token_count"));
        assert_eq!(r.errors.len(), 4);
    }

    #[test]
    fn error_in_second_message_uses_correct_field_path() {
        let b = PostBundle {
            messages: vec![
                PostMessage { role: "user".into(), content: "ok".into() },
                PostMessage { role: "unknown".into(), content: "".into() },
            ],
            ..valid_bundle()
        };
        let r = validate_okf_bundle(&b);
        assert!(r.errors.iter().any(|e| e.field == "messages[1].role"));
        assert!(r.errors.iter().any(|e| e.field == "messages[1].content"));
    }

    #[test]
    fn valid_result_has_valid_true_and_empty_errors() {
        let r = ValidationResult::new(vec![]);
        assert!(r.valid);
        assert!(r.errors.is_empty());
    }

    #[test]
    fn invalid_result_has_valid_false() {
        let r = ValidationResult::new(vec![ValidationError {
            field: "f".into(),
            code: "c".into(),
            message: "m".into(),
        }]);
        assert!(!r.valid);
        assert_eq!(r.errors.len(), 1);
    }
}
