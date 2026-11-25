//! Log Level

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default, Serialize, Deserialize)]
pub enum Level {
    Trace,
    Debug,
    #[default]
    Info,
    Warn,
    Error,
    Fatal,
}

impl Level {
    pub fn as_str(&self) -> &'static str {
        match self {
            Level::Trace => "TRACE",
            Level::Debug => "DEBUG",
            Level::Info => "INFO",
            Level::Warn => "WARN",
            Level::Error => "ERROR",
            Level::Fatal => "FATAL",
        }
    }
}

impl std::fmt::Display for Level {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn level_default_is_info() {
        assert_eq!(Level::default(), Level::Info);
    }

    #[test]
    fn level_ordering() {
        assert!(Level::Trace < Level::Debug);
        assert!(Level::Debug < Level::Info);
        assert!(Level::Info < Level::Warn);
        assert!(Level::Warn < Level::Error);
        assert!(Level::Error < Level::Fatal);
    }

    #[test]
    fn level_as_str() {
        assert_eq!(Level::Trace.as_str(), "TRACE");
        assert_eq!(Level::Debug.as_str(), "DEBUG");
        assert_eq!(Level::Info.as_str(), "INFO");
        assert_eq!(Level::Warn.as_str(), "WARN");
        assert_eq!(Level::Error.as_str(), "ERROR");
        assert_eq!(Level::Fatal.as_str(), "FATAL");
    }

    #[test]
    fn level_display() {
        assert_eq!(format!("{}", Level::Warn), "WARN");
    }

    #[test]
    fn level_serde_roundtrip() {
        let json = serde_json::to_string(&Level::Error).unwrap();
        let back: Level = serde_json::from_str(&json).unwrap();
        assert_eq!(back, Level::Error);
    }

    #[test]
    fn level_threshold_comparison() {
        // Info-level logger should NOT log Debug or Trace
        assert!(Level::Debug < Level::Info);
        assert!(Level::Info >= Level::Info);
        assert!(Level::Warn >= Level::Info);
    }
}
