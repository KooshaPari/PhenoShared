// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Common utilities for heliosHarness

use std::io;
use std::path::Path;
use thiserror::Error;
use tracing::{debug, instrument};

/// Error types for utils
///
/// `UtilsError` is derived with `thiserror` and implements
/// `From<std::io::Error>` so that I/O failures during utility helpers
/// (file reads, stdin/stdout) propagate with `?` instead of a manual
/// `.map_err` at every call site.
#[derive(Debug, Error)]
pub enum UtilsError {
    #[error("Parse error: {0}")]
    Parse(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Overflow: {0}")]
    Overflow(String),

    /// I/O error encountered by a util helper.
    #[error("I/O error: {0}")]
    Io(#[from] io::Error),
}

/// Result alias for utility helpers.
pub type Result<T> = std::result::Result<T, UtilsError>;

/// Read an entire UTF-8 text file into a `String`.
///
/// Returns [`UtilsError::Io`] for any I/O failure and
/// [`UtilsError::Parse`] for invalid UTF-8, keeping callers free of
/// `?`-incompatible conversions.
#[instrument(skip(path), fields(path = %path.display()))]
pub fn read_text_file(path: &Path) -> Result<String> {
    let content = std::fs::read_to_string(path)?;
    debug!(bytes = content.len(), "read text file");
    Ok(content)
}

/// Fast string hashing (FNV-1a variant)
pub fn hash_str(s: &str) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for byte in s.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

/// Parse key-value pairs from string
pub fn parse_kv(s: &str, delimiter: char, pair_sep: char) -> Vec<(String, String)> {
    s.split(delimiter)
        .filter_map(|pair| {
            let mut parts = pair.split(pair_sep);
            match (parts.next(), parts.next()) {
                (Some(k), Some(v)) => Some((k.trim().to_string(), v.trim().to_string())),
                _ => None,
            }
        })
        .collect()
}

/// Parse tags from string
pub fn parse_tags(s: &str) -> Vec<String> {
    s.split(',').map(|t| t.trim().to_string()).filter(|t| !t.is_empty()).collect()
}

/// Check if string is palindrome
pub fn is_palindrome(s: &str) -> bool {
    let bytes = s.as_bytes();
    bytes.iter().zip(bytes.iter().rev()).all(|(a, b)| a == b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash() {
        assert_eq!(hash_str("test"), hash_str("test"));
        assert_ne!(hash_str("test"), hash_str("other"));
    }

    #[test]
    fn test_parse_kv() {
        let result = parse_kv("a=1,b=2", ',', '=');
        assert_eq!(result.len(), 2);
        assert_eq!(result[0], ("a".to_string(), "1".to_string()));
    }

    #[test]
    fn test_parse_kv_with_spaces() {
        let result = parse_kv(" a = 1 , b = 2 ", ',', '=');
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_parse_kv_invalid() {
        let result = parse_kv("invalid", ',', '=');
        assert!(result.is_empty());
    }

    #[test]
    fn test_parse_tags() {
        let tags = parse_tags("tag1,tag2,tag3");
        assert_eq!(tags.len(), 3);
    }

    #[test]
    fn test_parse_tags_with_spaces() {
        let tags = parse_tags(" tag1 , tag2 , tag3 ");
        assert_eq!(tags.len(), 3);
    }

    #[test]
    fn test_parse_tags_empty() {
        let tags = parse_tags("");
        assert!(tags.is_empty());
    }

    #[test]
    fn test_palindrome() {
        assert!(is_palindrome("radar"));
        assert!(is_palindrome("level"));
        assert!(is_palindrome(""));
        assert!(!is_palindrome("hello"));
    }

    #[test]
    fn test_palindrome_single_char() {
        assert!(is_palindrome("a"));
    }

    /// Traces to: FR-HELIOS-IO-007
    /// `From<io::Error>` must map to the `Io` variant.
    #[test]
    fn utils_error_from_io() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "missing");
        let err: UtilsError = io_err.into();
        assert!(matches!(err, UtilsError::Io(_)));
    }

    /// Traces to: FR-HELIOS-IO-007
    /// `read_text_file` must yield `UtilsError::Io` for missing files
    /// and a populated `String` for existing ones.
    #[test]
    fn read_text_file_round_trip() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_utils_read_text_test.txt");
        std::fs::write(&path, "hello world").unwrap();
        let content = read_text_file(&path).expect("read should succeed");
        assert_eq!(content, "hello world");
        let _ = std::fs::remove_file(&path);
    }

    /// Traces to: FR-HELIOS-IO-007
    /// `read_text_file` must surface a missing file as `UtilsError::Io`.
    #[test]
    fn read_text_file_missing_yields_io() {
        let path = std::path::PathBuf::from("/nonexistent/helios_utils_missing.txt");
        let err = read_text_file(&path).expect_err("expected error");
        assert!(matches!(err, UtilsError::Io(_)));
    }
}
