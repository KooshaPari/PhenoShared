//! Pratt parser for NetScript — recursive-descent with precedence climbing.

use crate::domain::{Lexer, Token, TokenType};

/// An expression in the AST.
#[derive(Debug, Clone, PartialEq)]
pub enum Expr {
    Literal(LiteralValue),
    Identifier(String),
    Binary {
        left: Box<Expr>,
        operator: BinaryOp,
        right: Box<Expr>,
    },
    Unary {
        operator: UnaryOp,
        operand: Box<Expr>,
    },
    Grouping(Box<Expr>),
    Assign {
        name: String,
        value: Box<Expr>,
    },
    Call {
        callee: Box<Expr>,
        arguments: Vec<Expr>,
    },
}

/// A literal value.
#[derive(Debug, Clone, PartialEq)]
pub enum LiteralValue {
    Integer(i64),
    Float(f64),
    String(String),
    Boolean(bool),
}

/// Binary operators.
#[derive(Debug, Clone, PartialEq)]
pub enum BinaryOp {
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    EqualsEquals,
    BangEquals,
    Less,
    LessEquals,
    Greater,
    GreaterEquals,
    And,
    Or,
}

/// Unary operators.
#[derive(Debug, Clone, PartialEq)]
pub enum UnaryOp {
    Bang,
    Minus,
}

/// A statement in the AST.
#[derive(Debug, Clone, PartialEq)]
pub enum Stmt {
    Expression(Expr),
    Let {
        name: String,
        initializer: Expr,
    },
    If {
        condition: Expr,
        then_branch: Box<Stmt>,
        else_branch: Option<Box<Stmt>>,
    },
    While {
        condition: Expr,
        body: Box<Stmt>,
    },
    Return(Option<Expr>),
    Block(Vec<Stmt>),
    Function {
        name: String,
        parameters: Vec<String>,
        body: Box<Stmt>,
    },
    Print(Expr),
}

/// A program is a sequence of statements.
#[derive(Debug, Clone, PartialEq)]
pub struct Program {
    pub statements: Vec<Stmt>,
}

/// Parse error with a message.
#[derive(Debug, Clone, PartialEq)]
pub struct ParseError {
    pub message: String,
}

impl ParseError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

/// Pratt parser for NetScript.
pub struct Parser {
    tokens: Vec<Token>,
    current: usize,
}

impl Parser {
    pub fn new(tokens: Vec<Token>) -> Self {
        Self { tokens, current: 0 }
    }

    pub fn parse(&mut self) -> Result<Program, ParseError> {
        let mut statements = Vec::new();
        while !self.is_at_end() {
            statements.push(self.declaration()?);
        }
        Ok(Program { statements })
    }

    fn declaration(&mut self) -> Result<Stmt, ParseError> {
        if self.match_token(&[TokenType::Let]) {
            self.let_declaration()
        } else if self.match_token(&[TokenType::Fn]) {
            self.function_declaration()
        } else {
            self.statement()
        }
    }

    fn let_declaration(&mut self) -> Result<Stmt, ParseError> {
        let name = self.consume_identifier("expect variable name")?;
        self.consume(TokenType::Equals, "expect '=' after variable name")?;
        let initializer = self.expression()?;
        self.consume(
            TokenType::Semicolon,
            "expect ';' after variable declaration",
        )?;
        Ok(Stmt::Let { name, initializer })
    }

    fn function_declaration(&mut self) -> Result<Stmt, ParseError> {
        let name = self.consume_identifier("expect function name")?;
        self.consume(TokenType::LeftParen, "expect '(' after function name")?;
        let mut parameters = Vec::new();
        if !self.check(&TokenType::RightParen) {
            loop {
                parameters.push(self.consume_identifier("expect parameter name")?);
                if !self.match_token(&[TokenType::Comma]) {
                    break;
                }
            }
        }
        self.consume(TokenType::RightParen, "expect ')' after parameters")?;
        self.consume(TokenType::LeftBrace, "expect '{' before function body")?;
        let body = self.block()?;
        Ok(Stmt::Function {
            name,
            parameters,
            body: Box::new(body),
        })
    }

    fn statement(&mut self) -> Result<Stmt, ParseError> {
        if self.match_token(&[TokenType::If]) {
            self.if_statement()
        } else if self.match_token(&[TokenType::While]) {
            self.while_statement()
        } else if self.match_token(&[TokenType::Return]) {
            self.return_statement()
        } else if self.match_token(&[TokenType::Print]) {
            self.print_statement()
        } else if self.match_token(&[TokenType::LeftBrace]) {
            self.block()
        } else {
            self.expression_statement()
        }
    }

    fn if_statement(&mut self) -> Result<Stmt, ParseError> {
        let condition = self.expression()?;
        self.consume(TokenType::LeftBrace, "expect '{' after if condition")?;
        let then_branch = Box::new(self.block()?);
        let else_branch = if self.match_token(&[TokenType::Else]) {
            self.consume(TokenType::LeftBrace, "expect '{' after else")?;
            Some(Box::new(self.block()?))
        } else {
            None
        };
        Ok(Stmt::If {
            condition,
            then_branch,
            else_branch,
        })
    }

    fn while_statement(&mut self) -> Result<Stmt, ParseError> {
        let condition = self.expression()?;
        self.consume(TokenType::LeftBrace, "expect '{' after while condition")?;
        let body = Box::new(self.block()?);
        Ok(Stmt::While { condition, body })
    }

    fn return_statement(&mut self) -> Result<Stmt, ParseError> {
        let value = if self.check(&TokenType::Semicolon) {
            None
        } else {
            Some(self.expression()?)
        };
        self.consume(TokenType::Semicolon, "expect ';' after return value")?;
        Ok(Stmt::Return(value))
    }

    fn print_statement(&mut self) -> Result<Stmt, ParseError> {
        let value = self.expression()?;
        self.consume(TokenType::Semicolon, "expect ';' after print value")?;
        Ok(Stmt::Print(value))
    }

    fn block(&mut self) -> Result<Stmt, ParseError> {
        let mut statements = Vec::new();
        while !self.check(&TokenType::RightBrace) && !self.is_at_end() {
            statements.push(self.declaration()?);
        }
        self.consume(TokenType::RightBrace, "expect '}' after block")?;
        Ok(Stmt::Block(statements))
    }

    fn expression_statement(&mut self) -> Result<Stmt, ParseError> {
        let expr = self.expression()?;
        self.consume(TokenType::Semicolon, "expect ';' after expression")?;
        Ok(Stmt::Expression(expr))
    }

    fn expression(&mut self) -> Result<Expr, ParseError> {
        self.assignment()
    }

    fn assignment(&mut self) -> Result<Expr, ParseError> {
        let expr = self.or()?;
        if self.match_token(&[TokenType::Equals]) {
            let value = self.assignment()?;
            if let Expr::Identifier(name) = expr {
                return Ok(Expr::Assign {
                    name,
                    value: Box::new(value),
                });
            }
            return Err(ParseError::new("invalid assignment target"));
        }
        Ok(expr)
    }

    fn or(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.and()?;
        while self.match_token(&[TokenType::Or]) {
            let right = self.and()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator: BinaryOp::Or,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn and(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.equality()?;
        while self.match_token(&[TokenType::And]) {
            let right = self.equality()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator: BinaryOp::And,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn equality(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.comparison()?;
        while self.match_token(&[TokenType::BangEquals, TokenType::EqualsEquals]) {
            let operator = if self.previous().token_type == TokenType::BangEquals {
                BinaryOp::BangEquals
            } else {
                BinaryOp::EqualsEquals
            };
            let right = self.comparison()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn comparison(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.term()?;
        while self.match_token(&[
            TokenType::Greater,
            TokenType::GreaterEquals,
            TokenType::Less,
            TokenType::LessEquals,
        ]) {
            let operator = match self.previous().token_type {
                TokenType::Greater => BinaryOp::Greater,
                TokenType::GreaterEquals => BinaryOp::GreaterEquals,
                TokenType::Less => BinaryOp::Less,
                TokenType::LessEquals => BinaryOp::LessEquals,
                _ => unreachable!(),
            };
            let right = self.term()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn term(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.factor()?;
        while self.match_token(&[TokenType::Minus, TokenType::Plus]) {
            let operator = if self.previous().token_type == TokenType::Minus {
                BinaryOp::Minus
            } else {
                BinaryOp::Plus
            };
            let right = self.factor()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn factor(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.unary()?;
        while self.match_token(&[TokenType::Slash, TokenType::Star, TokenType::Percent]) {
            let operator = match self.previous().token_type {
                TokenType::Slash => BinaryOp::Slash,
                TokenType::Star => BinaryOp::Star,
                TokenType::Percent => BinaryOp::Percent,
                _ => unreachable!(),
            };
            let right = self.unary()?;
            expr = Expr::Binary {
                left: Box::new(expr),
                operator,
                right: Box::new(right),
            };
        }
        Ok(expr)
    }

    fn unary(&mut self) -> Result<Expr, ParseError> {
        if self.match_token(&[TokenType::Bang, TokenType::Minus]) {
            let operator = if self.previous().token_type == TokenType::Bang {
                UnaryOp::Bang
            } else {
                UnaryOp::Minus
            };
            let operand = Box::new(self.unary()?);
            return Ok(Expr::Unary { operator, operand });
        }
        self.call()
    }

    fn call(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.primary()?;
        loop {
            if self.match_token(&[TokenType::LeftParen]) {
                expr = self.finish_call(expr)?;
            } else {
                break;
            }
        }
        Ok(expr)
    }

    fn finish_call(&mut self, callee: Expr) -> Result<Expr, ParseError> {
        let mut arguments = Vec::new();
        if !self.check(&TokenType::RightParen) {
            loop {
                arguments.push(self.expression()?);
                if !self.match_token(&[TokenType::Comma]) {
                    break;
                }
            }
        }
        self.consume(TokenType::RightParen, "expect ')' after arguments")?;
        Ok(Expr::Call {
            callee: Box::new(callee),
            arguments,
        })
    }

    fn primary(&mut self) -> Result<Expr, ParseError> {
        let token = self.advance();
        match &token.token_type {
            TokenType::Integer(n) => Ok(Expr::Literal(LiteralValue::Integer(*n))),
            TokenType::Float(f) => Ok(Expr::Literal(LiteralValue::Float(*f))),
            TokenType::String(s) => Ok(Expr::Literal(LiteralValue::String(s.clone()))),
            TokenType::Boolean(b) => Ok(Expr::Literal(LiteralValue::Boolean(*b))),
            TokenType::Identifier(name) => Ok(Expr::Identifier(name.clone())),
            TokenType::LeftParen => {
                let expr = self.expression()?;
                self.consume(TokenType::RightParen, "expect ')' after expression")?;
                Ok(Expr::Grouping(Box::new(expr)))
            }
            TokenType::Error(err) => Err(ParseError::new(format!("lexer error: {}", err.message))),
            _ => Err(ParseError::new(format!(
                "unexpected token {:?}",
                token.token_type
            ))),
        }
    }

    // --- Utility helpers ---

    fn match_token(&mut self, types: &[TokenType]) -> bool {
        for t in types {
            if self.check(t) {
                self.advance();
                return true;
            }
        }
        false
    }

    fn check(&self, token_type: &TokenType) -> bool {
        if self.is_at_end() {
            return false;
        }
        self.peek().token_type == *token_type
    }

    fn advance(&mut self) -> Token {
        if !self.is_at_end() {
            self.current += 1;
        }
        self.previous()
    }

    fn is_at_end(&self) -> bool {
        self.peek().token_type == TokenType::Eof
    }

    fn peek(&self) -> Token {
        self.tokens[self.current].clone()
    }

    fn previous(&self) -> Token {
        self.tokens[self.current.saturating_sub(1)].clone()
    }

    fn consume(&mut self, token_type: TokenType, message: &str) -> Result<(), ParseError> {
        if self.check(&token_type) {
            self.advance();
            Ok(())
        } else {
            Err(ParseError::new(message))
        }
    }

    fn consume_identifier(&mut self, message: &str) -> Result<String, ParseError> {
        let token = self.advance();
        if let TokenType::Identifier(name) = token.token_type {
            Ok(name)
        } else {
            Err(ParseError::new(message))
        }
    }
}

/// Convenience: parse source string into an AST.
pub fn parse_source(input: &str) -> Result<Program, ParseError> {
    let mut lexer = Lexer::new(input);
    let tokens = lexer.tokenize();
    let mut parser = Parser::new(tokens);
    parser.parse()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_literal() {
        let result = parse_source("42;");
        assert!(result.is_ok());
        let program = result.unwrap();
        assert_eq!(program.statements.len(), 1);
        match &program.statements[0] {
            Stmt::Expression(Expr::Literal(LiteralValue::Integer(42))) => {}
            other => panic!("Expected literal expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_binary() {
        let result = parse_source("1 + 2;");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Expression(Expr::Binary {
                left,
                operator,
                right,
            }) => {
                assert!(matches!(
                    left.as_ref(),
                    Expr::Literal(LiteralValue::Integer(1))
                ));
                assert_eq!(*operator, BinaryOp::Plus);
                assert!(matches!(
                    right.as_ref(),
                    Expr::Literal(LiteralValue::Integer(2))
                ));
            }
            other => panic!("Expected binary expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_let() {
        let result = parse_source("let x = 42;");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Let { name, initializer } => {
                assert_eq!(name, "x");
                assert!(matches!(
                    initializer,
                    Expr::Literal(LiteralValue::Integer(42))
                ));
            }
            other => panic!("Expected let statement, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_if() {
        let result = parse_source("if true { let x = 1; }");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::If {
                condition,
                then_branch,
                else_branch,
            } => {
                assert!(matches!(
                    condition,
                    Expr::Literal(LiteralValue::Boolean(true))
                ));
                assert!(matches!(then_branch.as_ref(), Stmt::Block(_)));
                assert!(else_branch.is_none());
            }
            other => panic!("Expected if statement, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_precedence() {
        let result = parse_source("1 + 2 * 3;");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Expression(Expr::Binary {
                left,
                operator,
                right,
            }) => {
                assert!(matches!(
                    left.as_ref(),
                    Expr::Literal(LiteralValue::Integer(1))
                ));
                assert_eq!(*operator, BinaryOp::Plus);
                // right should be 2 * 3
                match right.as_ref() {
                    Expr::Binary {
                        left: l,
                        operator: op,
                        right: r,
                    } => {
                        assert!(matches!(
                            l.as_ref(),
                            Expr::Literal(LiteralValue::Integer(2))
                        ));
                        assert_eq!(*op, BinaryOp::Star);
                        assert!(matches!(
                            r.as_ref(),
                            Expr::Literal(LiteralValue::Integer(3))
                        ));
                    }
                    other => panic!("Expected multiplication on right, got {:?}", other),
                }
            }
            other => panic!("Expected binary expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_unary() {
        let result = parse_source("!true;");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Expression(Expr::Unary { operator, operand }) => {
                assert_eq!(*operator, UnaryOp::Bang);
                assert!(matches!(
                    operand.as_ref(),
                    Expr::Literal(LiteralValue::Boolean(true))
                ));
            }
            other => panic!("Expected unary expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_function() {
        let result = parse_source("fn add(a, b) { return a + b; }");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Function {
                name,
                parameters,
                body,
            } => {
                assert_eq!(name, "add");
                assert_eq!(parameters, &["a", "b"]);
                assert!(matches!(body.as_ref(), Stmt::Block(_)));
            }
            other => panic!("Expected function declaration, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_call() {
        let result = parse_source("foo(\"hello\");");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Expression(Expr::Call { callee, arguments }) => {
                assert!(matches!(callee.as_ref(), Expr::Identifier(name) if name == "foo"));
                assert_eq!(arguments.len(), 1);
                assert!(
                    matches!(arguments[0], Expr::Literal(LiteralValue::String(ref s)) if s == "hello")
                );
            }
            other => panic!("Expected call expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_grouping() {
        let result = parse_source("(1 + 2) * 3;");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::Expression(Expr::Binary {
                left,
                operator,
                right,
            }) => {
                assert_eq!(*operator, BinaryOp::Star);
                assert!(matches!(
                    right.as_ref(),
                    Expr::Literal(LiteralValue::Integer(3))
                ));
                match left.as_ref() {
                    Expr::Grouping(inner) => match inner.as_ref() {
                        Expr::Binary {
                            left: l,
                            operator: op,
                            right: r,
                        } => {
                            assert!(matches!(
                                l.as_ref(),
                                Expr::Literal(LiteralValue::Integer(1))
                            ));
                            assert_eq!(*op, BinaryOp::Plus);
                            assert!(matches!(
                                r.as_ref(),
                                Expr::Literal(LiteralValue::Integer(2))
                            ));
                        }
                        other => panic!("Expected grouped binary, got {:?}", other),
                    },
                    other => panic!("Expected grouping, got {:?}", other),
                }
            }
            other => panic!("Expected binary expression, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_while() {
        let result = parse_source("while true { let x = 1; }");
        assert!(result.is_ok());
        let program = result.unwrap();
        match &program.statements[0] {
            Stmt::While { condition, body } => {
                assert!(matches!(
                    condition,
                    Expr::Literal(LiteralValue::Boolean(true))
                ));
                assert!(matches!(body.as_ref(), Stmt::Block(_)));
            }
            other => panic!("Expected while statement, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_error() {
        let result = parse_source("let = 1;");
        assert!(result.is_err());
    }
}
