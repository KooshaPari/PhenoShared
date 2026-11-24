use insta::assert_debug_snapshot;
use netscript::Lexer;

#[test]
fn snapshot_simple_assignment() {
    let mut lexer = Lexer::new("let x = 42;");
    let tokens = lexer.tokenize();
    assert_debug_snapshot!(tokens);
}

#[test]
fn snapshot_function_call() {
    let mut lexer = Lexer::new("print(\"hello\");");
    let tokens = lexer.tokenize();
    assert_debug_snapshot!(tokens);
}

#[test]
fn snapshot_if_statement() {
    let mut lexer = Lexer::new("if x > 0 { return 1; }");
    let tokens = lexer.tokenize();
    assert_debug_snapshot!(tokens);
}
