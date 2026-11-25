//! Domain layer — pure logic, no IO, no framework dependencies.

pub mod lexer;
pub mod parser;

pub use lexer::{LexError, Lexer, Loc, Span, Token, TokenType};
pub use parser::{
    parse_source, BinaryOp, Expr, LiteralValue, ParseError, Parser, Program, Stmt, UnaryOp,
};
