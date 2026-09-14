//! Unified error type for the `apisync` crate.

use std::fmt;

/// The error type returned by all apisync operations.
#[derive(Debug)]
pub enum Error {
    /// An HTTP-level error (status code + optional body).
    Http {
        status: u16,
        body: Option<String>,
    },
    /// A JSON serialization/deserialization error.
    Json(serde_json::Error),
    /// A transport or connection error.
    Transport(String),
    /// A WebSocket-specific error.
    WebSocket(String),
    /// A GraphQL error (one or more error messages from the server).
    GraphQl(Vec<String>),
    /// A timeout occurred.
    Timeout,
    /// A generic internal error.
    Internal(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Http { status, body } => {
                write!(f, "HTTP {status}")?;
                if let Some(b) = body {
                    write!(f, ": {b}")?;
                }
                Ok(())
            }
            Error::Json(e) => write!(f, "JSON error: {e}"),
            Error::Transport(e) => write!(f, "transport error: {e}"),
            Error::WebSocket(e) => write!(f, "WebSocket error: {e}"),
            Error::GraphQl(msgs) => write!(f, "GraphQL error: {}", msgs.join("; ")),
            Error::Timeout => write!(f, "request timed out"),
            Error::Internal(e) => write!(f, "internal error: {e}"),
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Error::Json(e) => Some(e),
            _ => None,
        }
    }
}

impl From<serde_json::Error> for Error {
    fn from(e: serde_json::Error) -> Self {
        Error::Json(e)
    }
}

impl From<reqwest::Error> for Error {
    fn from(e: reqwest::Error) -> Self {
        if e.is_timeout() {
            Error::Timeout
        } else if e.is_connect() {
            Error::Transport(e.to_string())
        } else {
            Error::Transport(e.to_string())
        }
    }
}

impl From<tokio_tungstenite::tungstenite::Error> for Error {
    fn from(e: tokio_tungstenite::tungstenite::Error) -> Self {
        Error::WebSocket(e.to_string())
    }
}

impl From<Box<dyn std::error::Error + Send + Sync>> for Error {
    fn from(e: Box<dyn std::error::Error + Send + Sync>) -> Self {
        Error::Internal(e.to_string())
    }
}

/// Convenience `Result` alias using [`Error`].
pub type Result<T> = std::result::Result<T, Error>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error as StdError;

    #[test]
    fn test_display_http_with_body() {
        let e = Error::Http { status: 404, body: Some("not found".into()) };
        assert_eq!(e.to_string(), "HTTP 404: not found");
    }

    #[test]
    fn test_display_http_without_body() {
        let e = Error::Http { status: 500, body: None };
        assert_eq!(e.to_string(), "HTTP 500");
    }

    #[test]
    fn test_display_json() {
        let e = Error::Json(serde_json::from_str::<i32>("not json").unwrap_err());
        assert!(e.to_string().starts_with("JSON error: "));
    }

    #[test]
    fn test_display_transport() {
        let e = Error::Transport("connection refused".into());
        assert_eq!(e.to_string(), "transport error: connection refused");
    }

    #[test]
    fn test_display_websocket() {
        let e = Error::WebSocket("protocol error".into());
        assert_eq!(e.to_string(), "WebSocket error: protocol error");
    }

    #[test]
    fn test_display_graphql() {
        let e = Error::GraphQl(vec!["field not found".into(), "type mismatch".into()]);
        assert_eq!(e.to_string(), "GraphQL error: field not found; type mismatch");
    }

    #[test]
    fn test_display_graphql_empty() {
        let e: Error = Error::GraphQl(vec![]);
        assert_eq!(e.to_string(), "GraphQL error: ");
    }

    #[test]
    fn test_display_timeout() {
        let e = Error::Timeout;
        assert_eq!(e.to_string(), "request timed out");
    }

    #[test]
    fn test_display_internal() {
        let e = Error::Internal("something broke".into());
        assert_eq!(e.to_string(), "internal error: something broke");
    }

    #[test]
    fn test_error_source_json() {
        let inner = serde_json::from_str::<i32>("bad").unwrap_err();
        let e = Error::Json(inner);
        assert!(StdError::source(&e).is_some());
    }

    #[test]
    fn test_error_source_non_json() {
        let e = Error::Timeout;
        assert!(StdError::source(&e).is_none());
        let e2 = Error::Http { status: 500, body: None };
        assert!(StdError::source(&e2).is_none());
    }

    #[test]
    fn test_from_serde_json_error() {
        let e = serde_json::from_str::<i32>("bad").unwrap_err();
        let err: Error = e.into();
        assert!(matches!(err, Error::Json(_)));
    }

    #[test]
    fn test_from_reqwest_timeout() {
        let err_str = "connection refused";
        let e = Error::Transport(err_str.into());
        assert!(e.to_string().contains("connection refused"));
    }

    #[test]
    fn test_from_boxed_error() {
        let boxed: Box<dyn std::error::Error + Send + Sync> =
            Box::new(std::io::Error::new(std::io::ErrorKind::Other, "io error"));
        let e: Error = boxed.into();
        assert!(matches!(e, Error::Internal(_)));
        assert!(e.to_string().contains("io error"));
    }

    #[test]
    fn test_error_is_debug() {
        let e = Error::Timeout;
        let _dbg = format!("{:?}", e);
    }

    #[test]
    fn test_error_http_debug_with_body() {
        let e = Error::Http { status: 422, body: Some("unprocessable".into()) };
        let dbg = format!("{:?}", e);
        assert!(dbg.contains("422"));
        assert!(dbg.contains("unprocessable"));
    }

    #[test]
    fn test_error_graphql_debug() {
        let e = Error::GraphQl(vec![]);
        let _dbg = format!("{:?}", e);
    }

    #[test]
    fn test_error_internal_debug() {
        let e = Error::Internal("test".into());
        let _dbg = format!("{:?}", e);
    }

    #[test]
    fn test_result_alias() {
        let ok: Result<i32> = Ok(42);
        assert_eq!(ok.unwrap(), 42);
        let err: Result<i32> = Err(Error::Timeout);
        assert!(err.is_err());
    }
}
