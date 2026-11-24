pub mod config;
pub mod health;
pub mod nodes;
pub mod queries;
pub mod relationships;
pub mod store;

pub use config::GraphConfig;
pub use health::GraphHealth;
pub use nodes::NodeStore;
pub use queries::GraphQueries;
pub use relationships::RelationshipStore;
pub use store::{GraphError, GraphStore};

/// Top-level error type for the graph subsystem.
///
/// Composes the per-module [`GraphError`] and exposes a discriminating
/// `From<std::io::Error>` / `From<serde_json::Error>` so callers can lift
/// raw I/O or JSON failures into the structured error envelope.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Graph error: {0}")]
    Graph(#[from] GraphError),
    #[error("Config error: {0}")]
    Config(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Serde(#[from] serde_json::Error),
}

impl From<std::io::Error> for GraphError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => Self::ConnectionError(format!("not found: {err}")),
            std::io::ErrorKind::PermissionDenied => {
                Self::ConnectionError(format!("permission denied: {err}"))
            }
            _ => Self::ConnectionError(err.to_string()),
        }
    }
}

impl From<serde_json::Error> for GraphError {
    fn from(err: serde_json::Error) -> Self {
        Self::QueryError(format!("serialization: {err}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_io_not_found_maps_to_connection_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "missing");
        let e: GraphError = io_err.into();
        assert!(
            matches!(e, GraphError::ConnectionError(ref m) if m.contains("not found")),
            "expected ConnectionError, got {e:?}"
        );
    }

    #[test]
    fn from_io_permission_denied_maps_to_connection_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "nope");
        let e: GraphError = io_err.into();
        assert!(matches!(e, GraphError::ConnectionError(ref m) if m.contains("permission denied")));
    }

    #[test]
    fn from_io_other_maps_to_connection_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::BrokenPipe, "pipe");
        let e: GraphError = io_err.into();
        assert!(matches!(e, GraphError::ConnectionError(_)));
    }

    #[test]
    fn from_serde_for_graph_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: GraphError = json_err.into();
        assert!(matches!(e, GraphError::QueryError(m) if m.contains("serialization")));
    }

    #[test]
    fn from_io_into_top_level_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::ConnectionReset, "reset");
        let e: Error = io_err.into();
        assert!(matches!(e, Error::Io(_)));
    }

    #[test]
    fn from_serde_into_top_level_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: Error = json_err.into();
        assert!(matches!(e, Error::Serde(_)));
    }
}
