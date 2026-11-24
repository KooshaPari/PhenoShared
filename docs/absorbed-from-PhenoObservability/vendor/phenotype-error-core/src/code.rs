use serde::{Deserialize, Serialize};

/// Stable wire error codes shared across Rust and TypeScript interfaces.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    InternalError,
    InvalidArgument,
    NotFound,
    AlreadyExists,
    PermissionDenied,
    Unauthenticated,
    ResourceExhausted,
    Cancelled,
    Unavailable,
    NotImplemented,
    Timeout,
    ValidationError,
    MethodNotSupported,
    MissingCorrelationId,
    TerminalNotFound,
    LaneNotFound,
    SessionNotFound,
    SessionNotAttached,
    TerminalBindingInvalid,
}

/// Contract-ordered string values for cross-language parity checks.
pub const ERROR_CODES: &[&str] = &[
    "INTERNAL_ERROR",
    "INVALID_ARGUMENT",
    "NOT_FOUND",
    "ALREADY_EXISTS",
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
    "RESOURCE_EXHAUSTED",
    "CANCELLED",
    "UNAVAILABLE",
    "NOT_IMPLEMENTED",
    "TIMEOUT",
    "VALIDATION_ERROR",
    "METHOD_NOT_SUPPORTED",
    "MISSING_CORRELATION_ID",
    "TERMINAL_NOT_FOUND",
    "LANE_NOT_FOUND",
    "SESSION_NOT_FOUND",
    "SESSION_NOT_ATTACHED",
    "TERMINAL_BINDING_INVALID",
];

impl ErrorCode {
    /// Return the stable string representation used on the wire.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InternalError => "INTERNAL_ERROR",
            Self::InvalidArgument => "INVALID_ARGUMENT",
            Self::NotFound => "NOT_FOUND",
            Self::AlreadyExists => "ALREADY_EXISTS",
            Self::PermissionDenied => "PERMISSION_DENIED",
            Self::Unauthenticated => "UNAUTHENTICATED",
            Self::ResourceExhausted => "RESOURCE_EXHAUSTED",
            Self::Cancelled => "CANCELLED",
            Self::Unavailable => "UNAVAILABLE",
            Self::NotImplemented => "NOT_IMPLEMENTED",
            Self::Timeout => "TIMEOUT",
            Self::ValidationError => "VALIDATION_ERROR",
            Self::MethodNotSupported => "METHOD_NOT_SUPPORTED",
            Self::MissingCorrelationId => "MISSING_CORRELATION_ID",
            Self::TerminalNotFound => "TERMINAL_NOT_FOUND",
            Self::LaneNotFound => "LANE_NOT_FOUND",
            Self::SessionNotFound => "SESSION_NOT_FOUND",
            Self::SessionNotAttached => "SESSION_NOT_ATTACHED",
            Self::TerminalBindingInvalid => "TERMINAL_BINDING_INVALID",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn error_code_serializes_to_contract_value() {
        let json = serde_json::to_string(&ErrorCode::InvalidArgument).unwrap();
        assert_eq!(json, "\"INVALID_ARGUMENT\"");
    }

    #[test]
    fn error_codes_match_contract_fixture_order() {
        let contract = include_str!("../../../contracts/errors/error-codes.json");
        let values: Vec<String> = serde_json::from_str(contract).unwrap();
        assert_eq!(values, ERROR_CODES);
    }
}
