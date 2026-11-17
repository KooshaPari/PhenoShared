//! `Diagnostic` value type — the unified LSP-style diagnostic shape
//! every provider produces and every consumer (agent REPL, audit
//! pipeline, future editor surfaces) consumes.

use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DiagnosticSeverity {
    Error,
    Warning,
    Information,
    Hint,
}

impl DiagnosticSeverity {
    /// String form for audit/tooling (e.g. `"error"`).
    pub fn as_str(&self) -> &'static str {
        match self {
            DiagnosticSeverity::Error => "error",
            DiagnosticSeverity::Warning => "warning",
            DiagnosticSeverity::Information => "information",
            DiagnosticSeverity::Hint => "hint",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub file: PathBuf,
    pub severity: DiagnosticSeverity,
    /// 1-based line number.
    pub line: u32,
    pub message: String,
    /// Source identifier (provider name) — e.g. `"rustc"`, `"tsc"`.
    pub source: Option<String>,
}

impl Diagnostic {
    pub fn new(
        file: PathBuf,
        severity: DiagnosticSeverity,
        line: u32,
        message: impl Into<String>,
    ) -> Self {
        Self { file, severity, line, message: message.into(), source: None }
    }

    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = Some(source.into());
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn diagnostic_severity_as_str() {
        assert_eq!(DiagnosticSeverity::Error.as_str(), "error");
        assert_eq!(DiagnosticSeverity::Warning.as_str(), "warning");
        assert_eq!(DiagnosticSeverity::Information.as_str(), "information");
        assert_eq!(DiagnosticSeverity::Hint.as_str(), "hint");
    }

    #[test]
    fn diagnostic_new_sets_fields() {
        let d = Diagnostic::new(
            PathBuf::from("foo.rs"),
            DiagnosticSeverity::Error,
            42,
            "bad",
        );
        assert_eq!(d.file, PathBuf::from("foo.rs"));
        assert_eq!(d.severity, DiagnosticSeverity::Error);
        assert_eq!(d.line, 42);
        assert_eq!(d.message, "bad");
        assert!(d.source.is_none());
    }

    #[test]
    fn diagnostic_with_source_overrides_default() {
        let d = Diagnostic::new(PathBuf::from("x.ts"), DiagnosticSeverity::Warning, 1, "msg")
            .with_source("tsc");
        assert_eq!(d.source.as_deref(), Some("tsc"));
    }

    #[test]
    fn diagnostic_message_accepts_string_and_str() {
        let from_str = Diagnostic::new(
            PathBuf::from("a.rs"),
            DiagnosticSeverity::Hint,
            1,
            "from &str",
        );
        let from_string = Diagnostic::new(
            PathBuf::from("a.rs"),
            DiagnosticSeverity::Hint,
            1,
            String::from("from String"),
        );
        assert_eq!(from_str.message, "from &str");
        assert_eq!(from_string.message, "from String");
    }
}
