//! Logger Trait

use super::{Level, LogEntry};
use async_trait::async_trait;

#[async_trait]
pub trait Logger: Send + Sync {
    async fn log(&self, entry: LogEntry) -> Result<(), LogError>;
    fn level(&self) -> Level;
}

#[derive(Debug, Clone)]
pub enum LogError {
    Io(String),
    Serialization(String),
}

impl std::fmt::Display for LogError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogError::Io(s) => write!(f, "IO error: {}", s),
            LogError::Serialization(s) => write!(f, "Serialization error: {}", s),
        }
    }
}

impl std::error::Error for LogError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn log_error_io_display() {
        let err = LogError::Io("disk full".into());
        assert_eq!(format!("{}", err), "IO error: disk full");
    }

    #[test]
    fn log_error_serialization_display() {
        let err = LogError::Serialization("invalid utf-8".into());
        assert_eq!(format!("{}", err), "Serialization error: invalid utf-8");
    }

    #[test]
    fn log_error_implements_std_error() {
        fn assert_error(_: &dyn std::error::Error) {}
        assert_error(&LogError::Io("e".into()));
        assert_error(&LogError::Serialization("e".into()));
    }

    #[test]
    fn log_error_debug() {
        let err = LogError::Io("oops".into());
        let debug = format!("{:?}", err);
        assert!(debug.contains("Io") || debug.contains("oops"));
    }

    #[test]
    fn log_error_clone() {
        let a = LogError::Io("e1".into());
        let b = a.clone();
        assert_eq!(format!("{}", a), format!("{}", b));
    }
}
