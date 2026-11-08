//! App layer — composition root. Wires adapters to domain.

use crate::adapters::CliAdapter;
use crate::domain::{Lexer, Token};

pub struct App {
    adapter: CliAdapter,
}

impl Default for App {
    fn default() -> Self {
        Self::new()
    }
}

impl App {
    pub fn new() -> Self {
        Self {
            adapter: CliAdapter::new(),
        }
    }

    pub fn run_cli(&self) -> std::io::Result<()> {
        self.adapter.run_interactive()
    }

    pub fn run_once(&self, input: &str) -> Vec<Token> {
        let mut lexer = Lexer::new(input);
        lexer.tokenize()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use assert_cmd::Command;
    use predicates::str::contains;

    #[test]
    fn test_app_new() {
        let app = App::new();
        let tokens = app.run_once("42");
        assert!(!tokens.is_empty());
        assert_eq!(tokens[0].token_type, crate::domain::TokenType::Integer(42));
    }

    #[test]
    fn test_app_default() {
        let app = App::default();
        let tokens = app.run_once("true");
        assert!(!tokens.is_empty());
        assert_eq!(
            tokens[0].token_type,
            crate::domain::TokenType::Boolean(true)
        );
    }

    #[test]
    fn test_app_run_once_complex() {
        let app = App::new();
        let tokens = app.run_once("let x = 42;");
        let types: Vec<_> = tokens.iter().map(|t| t.token_type.clone()).collect();
        assert!(types.contains(&crate::domain::TokenType::Let));
        assert!(types.contains(&crate::domain::TokenType::Identifier("x".to_string())));
        assert!(types.contains(&crate::domain::TokenType::Integer(42)));
    }

    #[test]
    fn test_app_run_cli() {
        let mut cmd = Command::cargo_bin("netscript").unwrap();
        cmd.write_stdin("42\n");
        cmd.assert().success().stdout(contains("Integer(42)"));
    }
}
