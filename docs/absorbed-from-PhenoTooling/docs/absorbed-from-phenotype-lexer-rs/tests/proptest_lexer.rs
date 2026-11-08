use netscript::{Lexer, TokenType};
use proptest::prelude::*;

proptest! {
    #[test]
    fn lexer_never_panics_on_any_input(input in "\\PC*") {
        let mut lexer = Lexer::new(&input);
        let _ = lexer.tokenize();
    }

    #[test]
    fn lexer_always_ends_with_eof(input in "\\PC*") {
        let mut lexer = Lexer::new(&input);
        let tokens = lexer.tokenize();
        assert!(!tokens.is_empty());
        assert_eq!(tokens.last().unwrap().token_type, TokenType::Eof);
    }

    #[test]
    fn integer_tokenization(input in "[0-9]{1,10}") {
        let mut lexer = Lexer::new(&input);
        let token = lexer.next_token();
        if let TokenType::Integer(_) = token.token_type {}
    }
}
