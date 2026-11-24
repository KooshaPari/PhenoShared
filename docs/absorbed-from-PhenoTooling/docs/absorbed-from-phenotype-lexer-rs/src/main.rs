//! NetScript CLI entry point.

use netscript::App;

fn main() -> std::io::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    run_with_args(&args)
}

fn run_with_args(args: &[String]) -> std::io::Result<()> {
    if let Some(input) = parse_args(args) {
        let app = App::new();
        let tokens = app.run_once(input);
        for token in tokens {
            println!("{:?}", token);
        }
        Ok(())
    } else {
        App::new().run_cli()
    }
}

fn parse_args(args: &[String]) -> Option<&str> {
    if args.len() > 1 {
        Some(&args[1])
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_args_with_input() {
        let args = vec!["netscript".to_string(), "42".to_string()];
        assert_eq!(parse_args(&args), Some("42"));
    }

    #[test]
    fn test_parse_args_no_input() {
        let args = vec!["netscript".to_string()];
        assert_eq!(parse_args(&args), None);
    }

    #[test]
    fn test_parse_args_multiple_args() {
        let args = vec![
            "netscript".to_string(),
            "let x = 1;".to_string(),
            "extra".to_string(),
        ];
        assert_eq!(parse_args(&args), Some("let x = 1;"));
    }

    #[test]
    fn test_run_with_args_single_argument() {
        let args = vec!["netscript".to_string(), "42".to_string()];
        let result = run_with_args(&args);
        assert!(result.is_ok());
    }

    #[test]
    fn test_run_with_args_string_literal() {
        let args = vec!["netscript".to_string(), "\"hello\"".to_string()];
        let result = run_with_args(&args);
        assert!(result.is_ok());
    }

    #[test]
    fn test_run_with_args_complex_expression() {
        let args = vec!["netscript".to_string(), "if true { return 1; }".to_string()];
        let result = run_with_args(&args);
        assert!(result.is_ok());
    }
}
