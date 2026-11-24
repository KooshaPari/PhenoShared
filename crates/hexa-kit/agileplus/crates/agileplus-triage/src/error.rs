//! Triage / backlog error types.
//!
//! Provides [`TriageError`] — a structured error envelope for triage and
//! backlog operations. Implements discriminating `From<std::io::Error>` and
//! `From<serde_json::Error>` so callers can lift raw I/O or JSON failures
//! without an extra `.map_err`.

/// Triage / backlog subsystem error type.
#[derive(Debug, thiserror::Error)]
pub enum TriageError {
    #[error("Backlog operation failed: {0}")]
    Backlog(String),

    #[error("Classification failed: {0}")]
    Classification(String),

    #[error("Router generation failed: {0}")]
    Router(String),

    #[error("Persistence error: {0}")]
    Persistence(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("I/O error: {0}")]
    Io(std::io::Error),

    #[error("Serialization error: {0}")]
    Serde(serde_json::Error),
}

impl From<std::io::Error> for TriageError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => Self::NotFound(err.to_string()),
            std::io::ErrorKind::PermissionDenied => {
                Self::Persistence(format!("permission denied: {err}"))
            }
            _ => Self::Persistence(err.to_string()),
        }
    }
}

impl From<serde_json::Error> for TriageError {
    fn from(err: serde_json::Error) -> Self {
        Self::Persistence(format!("serialization: {err}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_io_not_found_maps_to_not_found() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "missing");
        let e: TriageError = io_err.into();
        assert!(
            matches!(e, TriageError::NotFound(ref m) if m == "missing"),
            "expected NotFound, got {e:?}"
        );
    }

    #[test]
    fn from_io_permission_denied_maps_to_persistence() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "nope");
        let e: TriageError = io_err.into();
        assert!(matches!(e, TriageError::Persistence(ref m) if m.contains("permission denied")));
    }

    #[test]
    fn from_io_other_maps_to_persistence() {
        let io_err = std::io::Error::new(std::io::ErrorKind::BrokenPipe, "pipe");
        let e: TriageError = io_err.into();
        assert!(matches!(e, TriageError::Persistence(_)));
    }

    #[test]
    fn from_serde_for_triage_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: TriageError = json_err.into();
        assert!(matches!(e, TriageError::Persistence(m) if m.contains("serialization")));
    }

    #[test]
    fn display_for_each_variant() {
        let cases = [
            (TriageError::Backlog("b".into()), "Backlog operation failed"),
            (TriageError::Classification("c".into()), "Classification failed"),
            (TriageError::Router("r".into()), "Router generation failed"),
            (TriageError::Persistence("p".into()), "Persistence error"),
            (TriageError::NotFound("n".into()), "Not found"),
            (TriageError::InvalidInput("i".into()), "Invalid input"),
        ];
        for (err, expected_prefix) in cases {
            let display = err.to_string();
            assert!(
                display.contains(expected_prefix),
                "expected '{expected_prefix}' in display, got '{display}'"
            );
        }
    }
}
