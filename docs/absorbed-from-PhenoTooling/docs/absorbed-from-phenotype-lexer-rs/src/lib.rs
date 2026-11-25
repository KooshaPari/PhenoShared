//! NetScript — a minimal scripting language lexer and tokenizer.
//!
//! Hexagonal architecture:
//! - `domain` — pure logic (Token, TokenType, Lexer)
//! - `ports` — trait contracts (LexerPort, Tokenizer)
//! - `adapters` — concrete implementations (CliAdapter)
//! - `app` — composition root (App)
//!
//! # Examples
//!
//! Basic tokenization with the lexer:
//!
//! ```
//! use netscript::Lexer;
//! let mut lexer = Lexer::new("let x = 42;");
//! let tokens = lexer.tokenize();
//! assert!(!tokens.is_empty());
//! assert_eq!(tokens.last().unwrap().token_type, netscript::TokenType::Eof);
//! ```
//!
//! Using the `App` facade:
//!
//! ```
//! use netscript::{App, TokenType};
//! let app = App::new();
//! let tokens = app.run_once("print(\"hello\");");
//! assert_eq!(tokens[0].token_type, TokenType::Print);
//! ```
//!
//! Identifying keywords and identifiers:
//!
//! ```
//! use netscript::{Lexer, TokenType};
//! let mut lexer = Lexer::new("if true { return 1; }");
//! let token = lexer.next_token();
//! assert_eq!(token.token_type, TokenType::If);
//! ```

pub mod adapters;
pub mod app;
pub mod domain;
pub mod ports;

pub use adapters::CliAdapter;
pub use app::App;
pub use domain::{
    parse_source, BinaryOp, Expr, LexError, Lexer, LiteralValue, Loc, ParseError, Parser, Program,
    Span, Stmt, Token, TokenType, UnaryOp,
};
pub use ports::{LexerPort, Tokenizer};
