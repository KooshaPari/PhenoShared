//! Plugin error types.

use thiserror::Error;

/// Machine-readable error codes for programmatic handling by host adapters.
///
/// Every `PluginError` variant maps to exactly one `ErrorCode`. Host adapters
/// and test code can match on the code without parsing the human-readable
/// message string.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ErrorCode {
    /// PLUGIN_INIT_001 — adapter constructor or migration failed.
    Initialization,
    /// PLUGIN_REG_002 — named plugin not present in registry.
    NotFound,
    /// PLUGIN_REG_003 — name collision during registration.
    AlreadyRegistered,
    /// PLUGIN_STORE_004 — entity uniqueness constraint violated.
    AlreadyExists,
    /// PLUGIN_OPS_005 — generic runtime operation failure.
    Operation,
    /// PLUGIN_CFG_006 — adapter configuration schema violation.
    Config,
    /// PLUGIN_IO_007 — underlying I/O error.
    Io,
    /// PLUGIN_SER_008 — JSON serialization/deserialization failure.
    Serialization,
    /// PLUGIN_EXEC_009 — plugin execution-time error.
    Execution,
    /// PLUGIN_VAL_010 — input validation failure.
    Validation,
}

impl ErrorCode {
    /// Returns the stable string token used in logs and structured error
    /// payloads (e.g. `"PLUGIN_INIT_001"`).
    pub fn as_str(self) -> &'static str {
        match self {
            ErrorCode::Initialization => "PLUGIN_INIT_001",
            ErrorCode::NotFound => "PLUGIN_REG_002",
            ErrorCode::AlreadyRegistered => "PLUGIN_REG_003",
            ErrorCode::AlreadyExists => "PLUGIN_STORE_004",
            ErrorCode::Operation => "PLUGIN_OPS_005",
            ErrorCode::Config => "PLUGIN_CFG_006",
            ErrorCode::Io => "PLUGIN_IO_007",
            ErrorCode::Serialization => "PLUGIN_SER_008",
            ErrorCode::Execution => "PLUGIN_EXEC_009",
            ErrorCode::Validation => "PLUGIN_VAL_010",
        }
    }

    /// Returns a short human-readable recovery hint that host adapters may
    /// surface to operators. Callers SHOULD check the error message for
    /// additional context-specific detail.
    pub fn recovery_hint(self) -> &'static str {
        match self {
            ErrorCode::Initialization => {
                "Check adapter config, file permissions, and database path."
            }
            ErrorCode::NotFound => "Register the required plugin before calling lookup methods.",
            ErrorCode::AlreadyRegistered => {
                "Each plugin name must be unique; remove the duplicate registration."
            }
            ErrorCode::AlreadyExists => "Use an update operation or choose a different identifier.",
            ErrorCode::Operation => {
                "Inspect error detail; retry if transient, report if persistent."
            }
            ErrorCode::Config => "Verify adapter_config against the plugin's configuration schema.",
            ErrorCode::Io => "Check filesystem permissions, disk space, and file locks.",
            ErrorCode::Serialization => {
                "Ensure JSON payload matches the expected schema; check for encoding issues."
            }
            ErrorCode::Execution => "Inspect error detail; the adapter may need re-initialization.",
            ErrorCode::Validation => {
                "Correct the input data according to the field-level error message."
            }
        }
    }
}

impl std::fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Errors that can occur in plugin operations.
#[derive(Error, Debug)]
pub enum PluginError {
    #[error("Plugin initialization failed: {0}")]
    Initialization(String),

    #[error("Plugin `{0}` not found in registry")]
    NotFound(String),

    #[error("Plugin `{0}` already registered")]
    AlreadyRegistered(String),

    #[error("Entity already exists: {0}")]
    AlreadyExists(String),

    #[error("Operation failed: {0}")]
    Operation(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Plugin execution error: {0}")]
    Execution(String),

    #[error("Validation error: {0}")]
    Validation(String),
}

impl PluginError {
    /// Returns the machine-readable `ErrorCode` for this error variant.
    ///
    /// Use this in structured log events and programmatic error handling
    /// instead of matching on display strings.
    ///
    /// ```rust
    /// use pheno_plugin_core::error::{ErrorCode, PluginError};
    ///
    /// let e = PluginError::NotFound("git".into());
    /// assert_eq!(e.code(), ErrorCode::NotFound);
    /// assert_eq!(e.code().as_str(), "PLUGIN_REG_002");
    /// ```
    pub fn code(&self) -> ErrorCode {
        match self {
            PluginError::Initialization(_) => ErrorCode::Initialization,
            PluginError::NotFound(_) => ErrorCode::NotFound,
            PluginError::AlreadyRegistered(_) => ErrorCode::AlreadyRegistered,
            PluginError::AlreadyExists(_) => ErrorCode::AlreadyExists,
            PluginError::Operation(_) => ErrorCode::Operation,
            PluginError::Config(_) => ErrorCode::Config,
            PluginError::Io(_) => ErrorCode::Io,
            PluginError::Serialization(_) => ErrorCode::Serialization,
            PluginError::Execution(_) => ErrorCode::Execution,
            PluginError::Validation(_) => ErrorCode::Validation,
        }
    }

    /// Returns the recovery hint for this error's code.
    ///
    /// Convenience wrapper over `self.code().recovery_hint()`.
    pub fn recovery_hint(&self) -> &'static str {
        self.code().recovery_hint()
    }
}

/// Result type alias for plugin operations.
pub type PluginResult<T> = Result<T, PluginError>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error;

    #[test]
    fn test_plugin_error_display() {
        // String-bearing variants: each row is (variant, unique payload, recognizable keyword).
        let cases: Vec<(PluginError, &str, &str)> = vec![
            (
                PluginError::Initialization("init_payload".to_string()),
                "init_payload",
                "initialization",
            ),
            (
                PluginError::NotFound("notfound_payload".to_string()),
                "notfound_payload",
                "not found",
            ),
            (
                PluginError::AlreadyRegistered("reg_payload".to_string()),
                "reg_payload",
                "already registered",
            ),
            (
                PluginError::AlreadyExists("exists_payload".to_string()),
                "exists_payload",
                "already exists",
            ),
            (
                PluginError::Operation("op_payload".to_string()),
                "op_payload",
                "operation",
            ),
            (
                PluginError::Config("cfg_payload".to_string()),
                "cfg_payload",
                "configuration",
            ),
            (
                PluginError::Execution("exec_payload".to_string()),
                "exec_payload",
                "execution",
            ),
            (
                PluginError::Validation("val_payload".to_string()),
                "val_payload",
                "validation",
            ),
        ];

        for (err, payload, keyword) in cases {
            let displayed = format!("{}", err);
            let lower = displayed.to_lowercase();
            assert!(
                displayed.contains(payload),
                "Display for {:?} missing payload `{}`: `{}`",
                err,
                payload,
                displayed
            );
            assert!(
                lower.contains(keyword),
                "Display for {:?} missing keyword `{}`: `{}`",
                err,
                keyword,
                displayed
            );
        }

        // `#[from]` variants: build via the From conversion and verify Display is
        // non-empty and preserves the inner error's text.
        let io_err: PluginError =
            std::io::Error::new(std::io::ErrorKind::NotFound, "io_inner_text").into();
        let io_displayed = format!("{}", io_err);
        assert!(!io_displayed.is_empty(), "Io Display should not be empty");
        assert!(
            io_displayed.contains("io_inner_text"),
            "Io Display should contain inner text: `{}`",
            io_displayed
        );

        let bad_json: serde_json::Error =
            serde_json::from_str::<i32>("{ not valid json").unwrap_err();
        let inner_text = bad_json.to_string();
        let ser_err: PluginError = bad_json.into();
        let ser_displayed = format!("{}", ser_err);
        assert!(
            !ser_displayed.is_empty(),
            "Serialization Display should not be empty"
        );
        assert!(
            ser_displayed.contains(&inner_text),
            "Serialization Display should contain inner serde error text: `{}`",
            ser_displayed
        );
    }

    #[test]
    fn test_plugin_error_from_io() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "x");
        let err: PluginError = io_err.into();
        assert!(matches!(err, PluginError::Io(_)));
        assert!(std::error::Error::source(&err).is_some());
    }

    #[test]
    fn test_plugin_error_from_serde() {
        let bad: serde_json::Error = serde_json::from_str::<i32>("{ not valid json").unwrap_err();
        let err: PluginError = bad.into();
        assert!(matches!(err, PluginError::Serialization(_)));
        assert!(std::error::Error::source(&err).is_some());
    }

    #[test]
    fn test_plugin_result_alias() {
        let r: PluginResult<i64> = Ok(42);
        assert_eq!(r.unwrap(), 42);

        let r: PluginResult<()> = Err(PluginError::Validation("bad".into()));
        assert!(r.is_err());
    }

    #[test]
    fn test_plugin_error_debug_for_all_variants() {
        // Each row is (variant-constructor-call, expected-variant-tag-substring-in-Debug).
        // Debug output for an enum variant starts with the variant name, so each tag
        // must appear in the formatted `{:?}` output.
        let bad: serde_json::Error = serde_json::from_str::<i32>("bad").unwrap_err();
        let io = std::io::Error::new(std::io::ErrorKind::Other, "x");

        let cases: Vec<(PluginError, &str)> = vec![
            (PluginError::Initialization("x".into()), "Initialization"),
            (PluginError::NotFound("x".into()), "NotFound"),
            (
                PluginError::AlreadyRegistered("x".into()),
                "AlreadyRegistered",
            ),
            (PluginError::AlreadyExists("x".into()), "AlreadyExists"),
            (PluginError::Operation("x".into()), "Operation"),
            (PluginError::Config("x".into()), "Config"),
            (PluginError::Io(io), "Io"),
            (PluginError::Serialization(bad), "Serialization"),
            (PluginError::Execution("x".into()), "Execution"),
            (PluginError::Validation("x".into()), "Validation"),
        ];

        for (err, tag) in cases {
            let dbg = format!("{:?}", err);
            assert!(
                dbg.contains(tag),
                "Debug output `{}` should contain variant name `{}`",
                dbg,
                tag
            );
        }
    }

    #[test]
    fn test_plugin_error_source_chain_io() {
        // `#[from] std::io::Error` should yield a non-None source chain.
        let io = std::io::Error::new(std::io::ErrorKind::NotFound, "x");
        let e: PluginError = io.into();
        assert!(e.source().is_some());
    }

    #[test]
    fn test_plugin_error_source_chain_serde() {
        // `#[from] serde_json::Error` should yield a non-None source chain.
        let s: serde_json::Error = serde_json::from_str::<i32>("bad").unwrap_err();
        let e: PluginError = s.into();
        assert!(e.source().is_some());
    }

    #[test]
    fn test_plugin_error_source_for_custom_variant() {
        // Custom (non-`#[from]`) variants have no underlying source.
        let e = PluginError::Validation("x".into());
        assert!(e.source().is_none());
    }

    #[test]
    fn test_plugin_error_send_sync() {
        // Compile-time assertion: PluginError must be Send + Sync.
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<PluginError>();
    }

    #[test]
    fn test_plugin_error_display_all_variants_unique() {
        // Every variant should produce a distinct Display string. Each `#[error(...)]`
        // template starts with a unique prefix, so the rendered output must be unique.
        let bad: serde_json::Error = serde_json::from_str::<i32>("bad").unwrap_err();
        let io = std::io::Error::new(std::io::ErrorKind::Other, "io_unique_payload");

        let variants: Vec<PluginError> = vec![
            PluginError::Initialization("init_unique_payload".into()),
            PluginError::NotFound("notfound_unique_payload".into()),
            PluginError::AlreadyRegistered("reg_unique_payload".into()),
            PluginError::AlreadyExists("exists_unique_payload".into()),
            PluginError::Operation("op_unique_payload".into()),
            PluginError::Config("cfg_unique_payload".into()),
            PluginError::Io(io),
            PluginError::Serialization(bad),
            PluginError::Execution("exec_unique_payload".into()),
            PluginError::Validation("val_unique_payload".into()),
        ];

        let original: Vec<String> = variants.iter().map(|e| format!("{}", e)).collect();
        let mut sorted = original.clone();
        sorted.sort();
        sorted.dedup();
        assert_eq!(
            sorted.len(),
            original.len(),
            "Expected all {} variants to have distinct Display output, but found duplicates among: {:?}",
            original.len(),
            original
        );
    }

    #[test]
    fn test_plugin_result_alias_with_string() {
        // `PluginResult<T>` should work for any T, including owned `String`.
        let r: PluginResult<String> = Ok("hello".into());
        assert_eq!(r.unwrap(), "hello");
    }

    #[test]
    fn test_plugin_result_alias_with_vec() {
        // `PluginResult<T>` should work for any T, including heap-allocated `Vec<u8>`.
        let r: PluginResult<Vec<u8>> = Ok(vec![1, 2, 3]);
        assert_eq!(r.unwrap(), vec![1, 2, 3]);
    }

    #[test]
    fn test_plugin_error_io_preserves_error_kind() {
        // When converting via `#[from]`, the inner `std::io::Error` (and thus its
        // `ErrorKind`) must be preserved on the wrapped variant.
        let io = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "x");
        let e: PluginError = io.into();
        if let PluginError::Io(inner) = e {
            assert_eq!(inner.kind(), std::io::ErrorKind::PermissionDenied);
        } else {
            panic!("expected Io variant");
        }
    }

    #[test]
    fn test_plugin_error_via_map_err() {
        // `.map_err(|e| e.into())` should cleanly convert any `std::io::Error`
        // source into a `PluginError`.
        let r: Result<i32, std::io::Error> =
            Err(std::io::Error::new(std::io::ErrorKind::Other, "x"));
        let mapped: PluginResult<i32> = r.map_err(|e| e.into());
        assert!(mapped.is_err());
    }

    // -----------------------------------------------------------------------
    // ErrorCode tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_error_code_variants_all_unique_tokens() {
        // Every ErrorCode must produce a distinct stable string token.
        use std::collections::HashSet;
        let codes = [
            ErrorCode::Initialization,
            ErrorCode::NotFound,
            ErrorCode::AlreadyRegistered,
            ErrorCode::AlreadyExists,
            ErrorCode::Operation,
            ErrorCode::Config,
            ErrorCode::Io,
            ErrorCode::Serialization,
            ErrorCode::Execution,
            ErrorCode::Validation,
        ];
        let tokens: HashSet<&str> = codes.iter().map(|c| c.as_str()).collect();
        assert_eq!(
            tokens.len(),
            codes.len(),
            "every ErrorCode must have a unique as_str() token"
        );
    }

    #[test]
    fn test_error_code_display_equals_as_str() {
        let code = ErrorCode::NotFound;
        assert_eq!(format!("{}", code), code.as_str());
    }

    #[test]
    fn test_error_code_recovery_hints_non_empty() {
        let codes = [
            ErrorCode::Initialization,
            ErrorCode::NotFound,
            ErrorCode::AlreadyRegistered,
            ErrorCode::AlreadyExists,
            ErrorCode::Operation,
            ErrorCode::Config,
            ErrorCode::Io,
            ErrorCode::Serialization,
            ErrorCode::Execution,
            ErrorCode::Validation,
        ];
        for code in codes {
            let hint = code.recovery_hint();
            assert!(
                !hint.is_empty(),
                "recovery_hint for {:?} must not be empty",
                code
            );
        }
    }

    #[test]
    fn test_plugin_error_code_method_maps_all_variants() {
        let bad: serde_json::Error = serde_json::from_str::<i32>("bad").unwrap_err();
        let io = std::io::Error::new(std::io::ErrorKind::Other, "x");

        let cases: Vec<(PluginError, ErrorCode)> = vec![
            (
                PluginError::Initialization("x".into()),
                ErrorCode::Initialization,
            ),
            (PluginError::NotFound("x".into()), ErrorCode::NotFound),
            (
                PluginError::AlreadyRegistered("x".into()),
                ErrorCode::AlreadyRegistered,
            ),
            (
                PluginError::AlreadyExists("x".into()),
                ErrorCode::AlreadyExists,
            ),
            (PluginError::Operation("x".into()), ErrorCode::Operation),
            (PluginError::Config("x".into()), ErrorCode::Config),
            (PluginError::Io(io), ErrorCode::Io),
            (PluginError::Serialization(bad), ErrorCode::Serialization),
            (PluginError::Execution("x".into()), ErrorCode::Execution),
            (PluginError::Validation("x".into()), ErrorCode::Validation),
        ];
        for (err, expected_code) in cases {
            assert_eq!(err.code(), expected_code, "wrong code for {:?}", err);
        }
    }

    #[test]
    fn test_plugin_error_recovery_hint_non_empty_for_all_variants() {
        let bad: serde_json::Error = serde_json::from_str::<i32>("bad").unwrap_err();
        let io = std::io::Error::new(std::io::ErrorKind::Other, "x");

        let errors: Vec<PluginError> = vec![
            PluginError::Initialization("x".into()),
            PluginError::NotFound("x".into()),
            PluginError::AlreadyRegistered("x".into()),
            PluginError::AlreadyExists("x".into()),
            PluginError::Operation("x".into()),
            PluginError::Config("x".into()),
            PluginError::Io(io),
            PluginError::Serialization(bad),
            PluginError::Execution("x".into()),
            PluginError::Validation("x".into()),
        ];
        for err in errors {
            assert!(
                !err.recovery_hint().is_empty(),
                "recovery_hint must not be empty for {:?}",
                err
            );
        }
    }

    #[test]
    fn test_error_code_copy_clone() {
        // ErrorCode must be Copy+Clone so callers can store and compare it cheaply.
        let code = ErrorCode::Validation;
        let cloned = code;
        let copied = code;
        assert_eq!(cloned, copied);
        assert_eq!(code.as_str(), cloned.as_str());
    }
}
