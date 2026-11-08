use crate::domain::{Token, TokenType};

/// Port defining the contract for a lexer.
pub trait LexerPort {
    /// Produce the next token from the input stream.
    fn next_token(&mut self) -> Token;

    /// Consume the entire input and return all tokens.
    fn tokenize(&mut self) -> Vec<Token>;
}

/// Higher-level port for tokenizing sources.
pub trait Tokenizer {
    fn tokenize(&self, input: &str) -> Vec<TokenType>;
}
