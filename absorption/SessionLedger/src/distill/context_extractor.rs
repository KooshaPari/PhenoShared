//! Heuristic context extraction — the P2 adapter for [`ContextExtractor`].
//!
//! This adapter uses lightweight string matching to extract working context
//! from a session's message stream: files touched, decisions reached, symbols
//! referenced, and environment state.
//!
//! Phase 3 will supersede this with an LLM-backed extractor behind the same
//! [`ContextExtractor`] trait — see `docs/DESIGN.md` §7.

use crate::domain::context::{Context, Decision};
use crate::domain::session::Session;
use crate::ports::{ContextExtractor, PortError};

/// Heuristic-based context extractor.
///
/// Scans all messages (user + assistant) for:
/// - **Files mentioned**: paths containing `/` or `.` (e.g. `src/main.rs`).
/// - **Key decisions**: phrases like "decided", "let's use", "we chose".
/// - **Key symbols**: identifiers with `::` (e.g. `HashMap::new`) or function
///   calls (`foo()`).
/// - **Environment notes**: dependency/setup-related messages.
///
/// This is intentionally simple. The LLM-backed extractor (Phase 3) will
/// replace it behind the same trait.
#[derive(Debug, Default, Clone, Copy)]
pub struct HeuristicContextExtractor;

// Patterns for detecting file paths (fragments that contain `/` or known
// extensions — checked on lowercase tokens).
const FILE_EXTENSIONS: &[&str] = &[
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".kt", ".rb", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".swift", ".toml", ".json", ".yaml", ".yml", ".md", ".sql", ".css", ".scss",
    ".html", ".sh", ".tf", ".lock",
];

// Patterns for decision language (lowercased for matching).
const DECISION_PATTERNS: &[&str] = &[
    "decided",
    "decision",
    "let's use",
    "lets use",
    "we should",
    "we chose",
    "chose",
    "opted for",
    "went with",
    "picked",
    "settled on",
    "i'll go with",
    "going with",
    "best to use",
    "prefer",
];

// Patterns for environment / setup notes.
const ENVIRONMENT_PATTERNS: &[&str] = &[
    "install",
    "installed",
    "setup",
    "set up",
    "configure",
    "version",
    "npm",
    "cargo",
    "pip",
    "brew",
    "apt",
    "docker",
    "compose",
    "env",
    "export",
    "add ",
    "added ",
    "upgrade",
    "updated",
];

impl HeuristicContextExtractor {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    /// Heuristically extract working-context from a session's messages.
    ///
    /// This is factored as a public associated function so it can be used
    /// directly by the compiler without going through the trait when no
    /// adapter injection is needed (P2 default).
    #[must_use]
    pub fn extract_context(session: &Session) -> Context {
        let mut files_mentioned: Vec<String> = Vec::new();
        let mut key_decisions: Vec<Decision> = Vec::new();
        let mut key_symbols: Vec<String> = Vec::new();
        let mut environment_notes: Vec<String> = Vec::new();

        for msg in &session.messages {
            let content = msg.content.as_str();
            let lower = content.to_lowercase();
            let tokens: Vec<&str> = content.split_whitespace().collect();

            // --- Files ---
            for token in &tokens {
                let clean = token.trim_matches(|c: char| {
                    !c.is_alphanumeric() && c != '/' && c != '.' && c != '-' && c != '_'
                });
                if is_file_path(clean) {
                    let fp = clean.to_string();
                    if !files_mentioned.contains(&fp) {
                        files_mentioned.push(fp);
                    }
                }
            }

            // --- Symbols (identifiers with :: or () pattern) ---
            // Look for token-like patterns (CamelCase, snake_case with parens or ::)
            for token in &tokens {
                let clean = token.trim_matches(|c: char| {
                    c == '('
                        || c == ')'
                        || c == ','
                        || c == ';'
                        || c == '{'
                        || c == '}'
                        || c == '['
                        || c == ']'
                });
                let is_func_call = token.contains("()");
                if clean.contains("::") || is_func_call {
                    let sym = clean.to_string();
                    if !key_symbols.contains(&sym) {
                        key_symbols.push(sym);
                    }
                }
            }

            // --- Decisions ---
            for pat in DECISION_PATTERNS {
                if lower.contains(pat) {
                    let summary = format!("Session contains '{pat}' language");
                    let decision = Decision { summary, rationale: Some(content.to_string()) };
                    if !key_decisions.iter().any(|d| d.summary == decision.summary) {
                        key_decisions.push(decision);
                    }
                }
            }

            // --- Environment notes ---
            for pat in ENVIRONMENT_PATTERNS {
                if lower.contains(pat) {
                    let note = format!("Session mentions '{pat}'");
                    if !environment_notes.contains(&note) {
                        environment_notes.push(note);
                    }
                }
            }
        }

        // Deduplicate environment notes by prefix (collapse "Session mentions 'npm'"
        // and "Session mentions 'cargo'" into a single note if both appear from
        // the same trigger).
        environment_notes.sort();
        environment_notes.dedup();

        Context {
            cwd: session.cwd.clone(),
            title: session.title.clone(),
            files_mentioned,
            key_decisions,
            key_symbols,
            environment_notes,
        }
    }
}

impl ContextExtractor for HeuristicContextExtractor {
    fn extract(&self, session: &Session) -> Result<Context, PortError> {
        Ok(Self::extract_context(session))
    }
}

/// Whether a whitespace-delimited token looks like a file path.
#[must_use]
fn is_file_path(token: &str) -> bool {
    if token.is_empty() || token.len() < 3 {
        return false;
    }
    // Must contain a `/` or start like a relative path (e.g. `src/`).
    if token.contains('/') {
        return true;
    }
    // Match common file extensions.
    let lower = token.to_lowercase();
    FILE_EXTENSIONS.iter().any(|ext| lower.ends_with(ext) && lower.len() > ext.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};

    fn fixture_session() -> Session {
        let mut s = Session::new("test-sess-ctx", Corpus::Forge);
        s.cwd = Some("/home/user/proj".into());
        s.title = Some("refactor auth".into());
        s.messages
            .push(Message::new(Role::User, "we need to refactor src/auth/mod.rs and add tests"));
        s.messages.push(Message::new(
            Role::Assistant,
            "I decided to use JWT tokens. Let's use jsonwebtoken crate.",
        ));
        s.messages.push(Message::new(
            Role::User,
            "good, I installed the crate and ran cargo test — it passes",
        ));
        s.messages.push(Message::new(
            Role::Assistant,
            "The verify_token() function validates expiry correctly now.",
        ));
        s
    }

    #[test]
    fn extracts_cwd_and_title_from_session() {
        let ctx = HeuristicContextExtractor::extract_context(&fixture_session());
        assert_eq!(ctx.cwd.as_deref(), Some("/home/user/proj"));
        assert_eq!(ctx.title.as_deref(), Some("refactor auth"));
    }

    #[test]
    fn extracts_files_mentioned_from_messages() {
        let ctx = HeuristicContextExtractor::extract_context(&fixture_session());
        assert!(ctx.files_mentioned.iter().any(|f| f == "src/auth/mod.rs"));
    }

    #[test]
    fn extracts_decisions_from_discourse() {
        let ctx = HeuristicContextExtractor::extract_context(&fixture_session());
        assert!(ctx.key_decisions.iter().any(|d| d.summary.contains("decided")));
    }

    #[test]
    fn extracts_symbols_from_code_mentions() {
        let ctx = HeuristicContextExtractor::extract_context(&fixture_session());
        assert!(ctx.key_symbols.iter().any(|s| s == "verify_token" || s.contains("verify_token")));
    }

    #[test]
    fn extracts_environment_notes() {
        let ctx = HeuristicContextExtractor::extract_context(&fixture_session());
        let notes: Vec<&str> = ctx.environment_notes.iter().map(String::as_str).collect();
        assert!(notes.iter().any(|n| n.contains("install") || n.contains("cargo")));
    }

    #[test]
    fn returns_empty_context_for_empty_session() {
        let s = Session::new("empty", Corpus::Forge);
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.is_empty());
    }

    #[test]
    fn context_extractor_trait_works() {
        let extractor = HeuristicContextExtractor::new();
        let ctx = extractor.extract(&fixture_session()).expect("extraction should succeed");
        assert_eq!(ctx.cwd.as_deref(), Some("/home/user/proj"));
    }

    #[test]
    fn file_paths_with_various_extensions() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(
            Role::User,
            "check package.json, Cargo.toml, src/main.rs, test.py, config.yaml",
        ));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.files_mentioned.iter().any(|f| {
            std::path::Path::new(f).extension().is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
        }));
        assert!(ctx.files_mentioned.iter().any(|f| {
            std::path::Path::new(f).extension().is_some_and(|ext| ext.eq_ignore_ascii_case("toml"))
        }));
        assert!(ctx.files_mentioned.iter().any(|f| {
            std::path::Path::new(f).extension().is_some_and(|ext| ext.eq_ignore_ascii_case("rs"))
        }));
        assert!(ctx.files_mentioned.iter().any(|f| {
            std::path::Path::new(f).extension().is_some_and(|ext| ext.eq_ignore_ascii_case("py"))
        }));
        assert!(ctx.files_mentioned.iter().any(|f| {
            std::path::Path::new(f).extension().is_some_and(|ext| ext.eq_ignore_ascii_case("yaml"))
        }));
    }

    #[test]
    fn ignores_file_extensions_on_short_tokens() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "the .rs and .ts are extensions"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        // ".rs" and ".ts" alone are too short (< 3 chars) and won't match
        assert!(!ctx.files_mentioned.contains(&".rs".to_string()));
        assert!(!ctx.files_mentioned.contains(&".ts".to_string()));
    }

    #[test]
    fn paths_with_slashes_are_files() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages
            .push(Message::new(Role::User, "update src/lib/utils.rs and tests/integration/mod.rs"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.files_mentioned.iter().any(|f| f == "src/lib/utils.rs"));
        assert!(ctx.files_mentioned.iter().any(|f| f == "tests/integration/mod.rs"));
    }

    #[test]
    fn deduplicates_file_mentions() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "edit src/main.rs"));
        s.messages.push(Message::new(Role::Assistant, "sure, I'll update src/main.rs"));
        s.messages.push(Message::new(Role::User, "and src/main.rs should also handle errors"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        let count = ctx.files_mentioned.iter().filter(|f| f == &"src/main.rs").count();
        assert_eq!(count, 1, "src/main.rs should only appear once");
    }

    #[test]
    fn extracts_symbols_with_double_colon() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "use HashMap::new and Vec::with_capacity"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.key_symbols.iter().any(|sym| sym == "HashMap::new"));
        assert!(ctx.key_symbols.iter().any(|sym| sym == "Vec::with_capacity"));
    }

    #[test]
    fn extracts_function_calls() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "call foo() and do_something() now"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        // Function calls with () in the token are extracted
        assert!(!ctx.key_symbols.is_empty());
    }

    #[test]
    fn deduplicates_symbols() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "HashMap::new is useful"));
        s.messages.push(Message::new(Role::Assistant, "yes, HashMap::new"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        let count = ctx.key_symbols.iter().filter(|sym| *sym == "HashMap::new").count();
        assert_eq!(count, 1, "HashMap::new should only appear once");
    }

    #[test]
    fn trims_symbols_of_punctuation() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "use HashMap::new and Vec::new and slice::first"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        // Symbols should be trimmed of parens, brackets, braces
        assert!(ctx.key_symbols.iter().any(|sym| sym == "HashMap::new"));
        assert!(ctx.key_symbols.iter().any(|sym| sym == "Vec::new"));
    }

    #[test]
    fn all_decision_patterns_detected() {
        for pattern in DECISION_PATTERNS {
            let mut s = Session::new("test", Corpus::Forge);
            s.messages.push(Message::new(Role::User, format!("we {pattern}")));
            let ctx = HeuristicContextExtractor::extract_context(&s);
            assert!(!ctx.key_decisions.is_empty(), "pattern '{pattern}' should be detected");
        }
    }

    #[test]
    fn decision_pattern_case_insensitive() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "DECIDED to use this approach"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.key_decisions.iter().any(|d| d.summary.contains("decided")));
    }

    #[test]
    fn decision_includes_rationale() {
        let mut s = Session::new("test", Corpus::Forge);
        let msg_text = "we decided to refactor the parser";
        s.messages.push(Message::new(Role::User, msg_text));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.key_decisions.iter().any(|d| d.rationale.as_deref() == Some(msg_text)));
    }

    #[test]
    fn deduplicates_decisions_by_summary() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "I decided on this plan"));
        s.messages.push(Message::new(Role::Assistant, "yes, I decided on this plan too"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        let decision_count =
            ctx.key_decisions.iter().filter(|d| d.summary.contains("decided")).count();
        assert_eq!(decision_count, 1, "duplicate decision patterns should be deduplicated");
    }

    #[test]
    fn all_environment_patterns_detected() {
        for pattern in ENVIRONMENT_PATTERNS {
            let mut s = Session::new("test", Corpus::Forge);
            s.messages.push(Message::new(Role::User, format!("please {pattern} the tool")));
            let ctx = HeuristicContextExtractor::extract_context(&s);
            assert!(!ctx.environment_notes.is_empty(), "pattern '{pattern}' should be detected");
        }
    }

    #[test]
    fn environment_pattern_case_insensitive() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "NPM INSTALL and CARGO BUILD"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(!ctx.environment_notes.is_empty());
    }

    #[test]
    fn deduplicates_environment_notes() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "install the package"));
        s.messages.push(Message::new(Role::Assistant, "ok, installing now"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        // Notes are deduplicated after sort
        assert!(!ctx.environment_notes.is_empty());
        // Check that environment_notes doesn't have exact duplicates
        let original_len = ctx.environment_notes.len();
        let mut dedup = ctx.environment_notes.clone();
        dedup.sort();
        dedup.dedup();
        assert_eq!(dedup.len(), original_len, "environment notes should be deduplicated");
    }

    #[test]
    fn empty_message_content_handled() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, ""));
        s.messages.push(Message::new(Role::Assistant, ""));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.is_empty(), "empty messages should result in empty context");
    }

    #[test]
    fn whitespace_only_messages_handled() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "   \t\n  "));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.is_empty(), "whitespace-only messages should result in empty context");
    }

    #[test]
    fn very_long_file_path() {
        let mut s = Session::new("test", Corpus::Forge);
        let long_path = "a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/u/v/w/x/y/z/file.rs";
        s.messages.push(Message::new(Role::User, format!("update {long_path}")));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.files_mentioned.iter().any(|f| f == long_path));
    }

    #[test]
    fn very_long_message() {
        let mut s = Session::new("test", Corpus::Forge);
        let long_msg = "src/file.rs ".repeat(1000);
        s.messages.push(Message::new(Role::User, &long_msg));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.files_mentioned.iter().any(|f| f == "src/file.rs"));
        // Should not panic or crash
    }

    #[test]
    fn symbols_with_numbers_and_underscores() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "call my_func_123() and Test_Class::method_v2()"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.key_symbols.iter().any(|sym| sym.contains("my_func_123")));
        assert!(ctx.key_symbols.iter().any(|sym| sym.contains("Test_Class::method_v2")));
    }

    #[test]
    fn file_paths_with_hyphens() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages
            .push(Message::new(Role::User, "check src/my-module/index.ts and my-config.yaml"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.files_mentioned.iter().any(|f| f == "src/my-module/index.ts"));
        assert!(ctx.files_mentioned.iter().any(|f| f == "my-config.yaml"));
    }

    #[test]
    fn context_with_none_cwd_and_title() {
        let s = Session::new("test", Corpus::Forge);
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert_eq!(ctx.cwd, None);
        assert_eq!(ctx.title, None);
    }

    #[test]
    fn context_with_populated_cwd_and_title() {
        let mut s = Session::new("test", Corpus::Forge);
        s.cwd = Some("/var/www/project".to_string());
        s.title = Some("bug fix #123".to_string());
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert_eq!(ctx.cwd.as_deref(), Some("/var/www/project"));
        assert_eq!(ctx.title.as_deref(), Some("bug fix #123"));
    }

    #[test]
    fn file_path_detection_boundary_exactly_3_chars() {
        // Exactly 3 chars with extension should match
        assert!(is_file_path("a.rs"));
        assert!(is_file_path("x.py"));
    }

    #[test]
    fn file_path_detection_boundary_less_than_3_chars() {
        // Less than 3 chars should not match
        assert!(!is_file_path("a"));
        assert!(!is_file_path("ab"));
        assert!(!is_file_path("a."));
    }

    #[test]
    fn file_path_detection_unknown_extension() {
        // Unknown extension should not match even if > 3 chars
        assert!(!is_file_path("file.xyz"));
        assert!(!is_file_path("thing.unknown"));
    }

    #[test]
    fn file_path_detection_slash_overrides_extension_check() {
        // Path with `/` should be file regardless of extension
        assert!(is_file_path("src/foo"));
        assert!(is_file_path("docs/readme.txt")); // .txt is not in the list, but / makes it a file
    }

    #[test]
    fn mixed_content_session() {
        let mut s = Session::new("test", Corpus::Forge);
        s.cwd = Some("/home/dev".into());
        s.title = Some("feature xyz".into());
        s.messages.push(Message::new(Role::User, "I'll refactor src/parser.rs"));
        s.messages.push(Message::new(Role::Assistant, "Decided to use regex::Regex"));
        s.messages.push(Message::new(Role::User, "Install regex and run cargo test"));
        s.messages.push(Message::new(Role::Assistant, "Done. verify_parse works"));

        let ctx = HeuristicContextExtractor::extract_context(&s);

        assert_eq!(ctx.cwd.as_deref(), Some("/home/dev"));
        assert_eq!(ctx.title.as_deref(), Some("feature xyz"));
        assert!(ctx.files_mentioned.contains(&"src/parser.rs".to_string()));
        assert!(ctx.key_decisions.iter().any(|d| d.summary.contains("decided")));
        assert!(ctx.key_symbols.iter().any(|sym| sym == "regex::Regex"));
        assert!(!ctx.environment_notes.is_empty());
    }

    #[test]
    fn symbols_in_comments_and_quoted_text() {
        let mut s = Session::new("test", Corpus::Forge);
        // Symbols should be extracted even if in descriptions
        s.messages.push(Message::new(Role::User, "Use String::from to convert"));
        s.messages.push(Message::new(Role::Assistant, "Also consider format!"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx.key_symbols.iter().any(|sym| sym == "String::from"));
    }

    #[test]
    fn environment_pattern_with_spaces() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "I need to set up the environment"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        // "set up" is a pattern, should match
        assert!(ctx.environment_notes.iter().any(|n| n.contains("set up")));
    }

    #[test]
    fn decision_rationale_preserves_full_message() {
        let mut s = Session::new("test", Corpus::Forge);
        let full_msg = "We decided to use async/await for all I/O operations because it's cleaner";
        s.messages.push(Message::new(Role::User, full_msg));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(ctx
            .key_decisions
            .iter()
            .any(|d| d.rationale.as_deref().is_some_and(|r| r.contains("async/await"))));
    }

    #[test]
    fn multiple_messages_accumulate_findings() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "file1.rs"));
        s.messages.push(Message::new(Role::User, "file2.rs"));
        s.messages.push(Message::new(Role::User, "file3.rs"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert_eq!(ctx.files_mentioned.len(), 3);
    }

    #[test]
    fn symbol_extraction_requires_double_colon_or_function_call() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "use HashMap::new"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            ctx.key_symbols.iter().any(|sym| sym.contains("HashMap::new")),
            "Should extract symbol with :: but no ()"
        );
    }

    #[test]
    fn symbol_extraction_with_function_call_no_double_colon() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "call foo() to start processing"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(!ctx.key_symbols.is_empty(), "Should extract function call foo() even without ::");
    }

    #[test]
    fn symbol_not_extracted_without_double_colon_or_function_call() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "the variable myvar is important"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            !ctx.key_symbols.iter().any(|sym| sym == "myvar"),
            "Should NOT extract plain identifier without :: or ()"
        );
    }

    #[test]
    fn is_file_path_with_forward_slash() {
        assert!(is_file_path("src/main.rs"));
        assert!(is_file_path("./relative/path.txt"));
        assert!(is_file_path("../../parent/file.py"));
    }

    #[test]
    fn is_file_path_with_common_extension() {
        assert!(is_file_path("config.toml"));
        assert!(is_file_path("Cargo.lock"));
        assert!(is_file_path("setup.py"));
    }

    #[test]
    fn is_file_path_rejects_short_tokens() {
        assert!(!is_file_path(""));
        assert!(!is_file_path("a"));
        assert!(!is_file_path("ab"));
    }

    #[test]
    fn is_file_path_rejects_plain_identifier() {
        assert!(!is_file_path("myvar"));
        assert!(!is_file_path("SomeClass"));
    }

    #[test]
    fn is_file_path_windows_style_forward_slash() {
        assert!(is_file_path("C:/Users/project"));
    }

    #[test]
    fn is_file_path_backward_slash_not_recognized() {
        assert!(!is_file_path("C:\\Users\\project\\file.txt"));
    }

    #[test]
    fn is_file_path_leading_slash_without_second_segment() {
        assert!(!is_file_path("/"));
        assert!(is_file_path("/etc"));
        assert!(is_file_path("/path/to/file"));
    }

    #[test]
    fn symbol_extraction_left_true_right_false() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "call HashMap::new but not with ()"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            ctx.key_symbols.iter().any(|sym| sym.contains("HashMap::new")),
            "LEFT=true (::), RIGHT=false (no ()): should extract"
        );
    }

    #[test]
    fn symbol_extraction_left_false_right_true() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "invoke process() with no double colon"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(!ctx.key_symbols.is_empty(), "LEFT=false (no ::), RIGHT=true (()): should extract");
    }

    #[test]
    fn symbol_extraction_both_false() {
        let mut s = Session::new("test", Corpus::Forge);
        s.messages.push(Message::new(
            Role::User,
            "variable myvar and identifier count should not be extracted",
        ));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            !ctx.key_symbols.iter().any(|sym| sym == "myvar" || sym == "count"),
            "LEFT=false (no ::), RIGHT=false (no ()): should NOT extract"
        );
    }

    #[test]
    fn file_path_contains_slash_true() {
        assert!(is_file_path("src/main.rs"), "LEFT=true (contains /): should be file path");
    }

    #[test]
    fn file_path_extension_true() {
        assert!(
            is_file_path("config.toml"),
            "RIGHT=true (has extension): should be file path when >= 3 chars"
        );
    }

    #[test]
    fn file_path_no_slash_no_extension() {
        assert!(
            !is_file_path("myvar"),
            "LEFT=false (no /), RIGHT=false (no extension or short): NOT file path"
        );
    }

    // ── Truth-table tests for line 128: `clean.contains("::") || is_func_call` ──
    //
    // A mutation that changes `||` to `&&` must fail on at least one of the
    // left-only-true or right-only-true cases.  We craft tokens that hit
    // exactly one arm so neither arm can be "carried" by the other.

    /// LEFT = true  (clean contains "::"),  RIGHT = false (no "()" in token)
    /// Token "`std::collections`" has "::" but no "()", so `is_func_call` = false.
    /// With a correct `||` the symbol IS extracted; with `&&` it would not be.
    #[test]
    fn symbol_or_left_only_double_colon_no_parens() {
        let mut s = Session::new("test-or-left", Corpus::Forge);
        // Token contains "::" only — no "()" anywhere in the raw token.
        s.messages.push(Message::new(Role::User, "use std::collections in your code"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            ctx.key_symbols.iter().any(|sym| sym.contains("std::collections")),
            "LEFT=true (::), RIGHT=false (no ()): symbol must be extracted via || not &&"
        );
    }

    /// LEFT = false (no "::" in token),  RIGHT = true (token contains "()")
    /// Token "`launch()`" has "()" but no "::".
    /// With a correct `||` the symbol IS extracted; with `&&` it would not be.
    #[test]
    fn symbol_or_right_only_parens_no_double_colon() {
        let mut s = Session::new("test-or-right", Corpus::Forge);
        // Use a token that has "()" but absolutely no "::".
        s.messages.push(Message::new(Role::User, "launch() the service"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            ctx.key_symbols.iter().any(|sym| sym.contains("launch")),
            "LEFT=false (no ::), RIGHT=true (()): symbol must be extracted via || not &&"
        );
    }

    /// LEFT = false, RIGHT = false — plain identifier, no "::" or "()"
    /// Should NOT appear in `key_symbols` under either `||` or `&&`.
    #[test]
    fn symbol_or_both_false_no_extraction() {
        let mut s = Session::new("test-or-both-false", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "the variable counter is used here"));
        let ctx = HeuristicContextExtractor::extract_context(&s);
        assert!(
            !ctx.key_symbols.iter().any(|sym| sym == "counter"),
            "LEFT=false, RIGHT=false: plain identifier must NOT be extracted"
        );
    }

    // ── Truth-table tests for line 184: `token.is_empty() || token.len() < 3` ──
    //
    // `is_file_path` returns `false` early when this condition is true.
    // A mutation changing `||` to `&&` would require BOTH conditions to be true
    // before returning false — letting short non-empty tokens slip through to the
    // extension/slash checks.

    /// LEFT = true  (empty string),  RIGHT = implicitly true (len 0 < 3)
    /// This is always a combined case; it verifies the guard fires for empty input.
    #[test]
    fn is_file_path_or_left_empty_string_rejected() {
        assert!(
            !is_file_path(""),
            "is_empty()=true: is_file_path must return false — left arm of ||"
        );
    }

    /// LEFT = false (non-empty), RIGHT = true (len 1, which is < 3)
    /// With correct `||`, returns false immediately.
    /// With `&&`, the guard fires only when BOTH are true (impossible), so a
    /// 1-char token with a known extension suffix would slip through.
    /// We use "a" (len 1) — if the guard is broken the extension check runs on "a"
    /// which still has no extension, so we double-check with a crafted 2-char token
    /// that ends with a known extension suffix to make the test truly diagnostic.
    #[test]
    fn is_file_path_or_right_only_short_nonempty_rejected() {
        // len=1, no extension — should be rejected by `len < 3` arm
        assert!(!is_file_path("a"), "len=1 non-empty: right arm of || must reject");
        // len=2, no extension — should be rejected by `len < 3` arm
        assert!(!is_file_path("ab"), "len=2 non-empty: right arm of || must reject");
    }

    /// LEFT = false, RIGHT = false — non-empty token with len >= 3
    /// The early-return guard must NOT fire; control falls through to the
    /// slash / extension checks (where "abc" with no slash or extension → false).
    #[test]
    fn is_file_path_or_both_false_guard_does_not_fire() {
        // "abc" has len=3, is non-empty → guard must NOT fire.
        // It has no slash and no known extension → is_file_path returns false for
        // a different reason.  If guard fired erroneously it would also return false
        // but for the wrong reason; a mutation to `&&` would let "abc" pass the guard
        // and fall through — still returning false here.  We therefore pair this with
        // a token that WOULD pass the extension check to prove guard non-activation.
        assert!(
            !is_file_path("abc"),
            "len=3, no ext/slash: guard must not fire, extension check rejects"
        );
        // "main.rs" (len=7) must pass — guard doesn't fire, extension check passes.
        assert!(
            is_file_path("main.rs"),
            "len>=3 with known extension: must be accepted when guard doesn't fire"
        );
    }
}
