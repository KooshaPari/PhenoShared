//! File adapter for reading and tokenizing NetScript (.ns) source files.

use std::fs;
use std::io;
use std::path::Path;

use crate::domain::{Lexer, Token};

/// Adapter that reads a NetScript file and tokenizes its contents.
pub struct FileAdapter;

impl Default for FileAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl FileAdapter {
    pub fn new() -> Self {
        Self
    }

    /// Read a file at the given path and tokenize its contents.
    pub fn run_file(&self, path: impl AsRef<Path>) -> io::Result<Vec<Token>> {
        let contents = fs::read_to_string(path)?;
        let mut lexer = Lexer::new(&contents);
        Ok(lexer.tokenize())
    }

    /// Tokenize the contents of a file path, returning a formatted string
    /// representation of the tokens for display.
    pub fn run_file_display(&self, path: impl AsRef<Path>) -> io::Result<String> {
        let tokens = self.run_file(path)?;
        let mut output = String::new();
        for token in tokens {
            output.push_str(&format!("{:?}\n", token));
        }
        Ok(output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_file_adapter_new() {
        let adapter = FileAdapter::new();
        let _ = adapter;
    }

    #[test]
    fn test_file_adapter_default() {
        let adapter = FileAdapter;
        let _ = adapter;
    }

    #[test]
    fn test_file_adapter_run_file() {
        let mut tmpfile = tempfile::NamedTempFile::new().unwrap();
        let input = "let x = 42;";
        write!(tmpfile, "{}", input).unwrap();
        let adapter = FileAdapter::new();
        let tokens = adapter.run_file(tmpfile.path()).unwrap();
        let types: Vec<_> = tokens.iter().map(|t| t.token_type.clone()).collect();
        assert!(types.contains(&crate::domain::TokenType::Let));
        assert!(types.contains(&crate::domain::TokenType::Integer(42)));
    }

    #[test]
    fn test_file_adapter_run_file_display() {
        let mut tmpfile = tempfile::NamedTempFile::new().unwrap();
        write!(tmpfile, "42;").unwrap();
        let adapter = FileAdapter::new();
        let output = adapter.run_file_display(tmpfile.path()).unwrap();
        assert!(output.contains("Integer(42)"));
    }

    #[test]
    fn test_file_adapter_missing_file() {
        let adapter = FileAdapter::new();
        let result = adapter.run_file("/nonexistent/path/file.ns");
        assert!(result.is_err());
    }
}
