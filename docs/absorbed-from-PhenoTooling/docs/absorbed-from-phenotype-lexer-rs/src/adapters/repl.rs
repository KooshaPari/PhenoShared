//! REPL adapter with readline support for interactive NetScript sessions.

use std::io::{self, Write};

use rustyline::error::ReadlineError;
use rustyline::DefaultEditor;

use crate::domain::{Lexer, Token};

/// Interactive REPL adapter using rustyline for history and line editing.
pub struct ReplAdapter {
    prompt: String,
}

impl Default for ReplAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl ReplAdapter {
    pub fn new() -> Self {
        Self {
            prompt: "ns> ".to_string(),
        }
    }

    pub fn run_interactive(&self) -> io::Result<()> {
        let mut rl = DefaultEditor::new().map_err(io::Error::other)?;
        let stdout = io::stdout();
        let mut stdout_lock = stdout.lock();
        let mut stderr = io::stderr();

        writeln!(stderr, "NetScript REPL (interactive mode)")?;
        writeln!(
            stderr,
            "Type expressions and press Enter. Type .exit to quit."
        )?;

        loop {
            let readline = rl.readline(&self.prompt);
            match readline {
                Ok(line) => {
                    let input = line.trim();
                    if input == ".exit" {
                        writeln!(stderr, "Bye!")?;
                        break;
                    }
                    if input.is_empty() {
                        continue;
                    }
                    let _ = rl.add_history_entry(input);
                    let mut lexer = Lexer::new(input);
                    let tokens = lexer.tokenize();
                    for token in tokens {
                        writeln!(stdout_lock, "{:?}", token)?;
                    }
                }
                Err(ReadlineError::Interrupted) => {
                    writeln!(stderr, "^C")?;
                    break;
                }
                Err(ReadlineError::Eof) => {
                    break;
                }
                Err(err) => {
                    writeln!(stderr, "Error: {:?}", err)?;
                    break;
                }
            }
        }
        Ok(())
    }

    pub fn run_once(&self, input: &str) -> Vec<Token> {
        let mut lexer = Lexer::new(input);
        lexer.tokenize()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_repl_adapter_new() {
        let repl = ReplAdapter::new();
        assert_eq!(repl.prompt, "ns> ");
    }

    #[test]
    fn test_repl_adapter_default() {
        let repl = ReplAdapter::default();
        assert_eq!(repl.prompt, "ns> ");
    }

    #[test]
    fn test_repl_run_once() {
        let repl = ReplAdapter::new();
        let tokens = repl.run_once("42");
        assert!(!tokens.is_empty());
        assert_eq!(tokens[0].token_type, crate::domain::TokenType::Integer(42));
    }
}
