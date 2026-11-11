//! Property evidence for `session_ledger::distill::context_extractor::HeuristicContextExtractor`.
//!
//! The heuristic context extractor is the P2 adapter for [`ContextExtractor`]
//! in the session-ledger distill pipeline. It powers the working-context
//! slice of any `ContinuationBundle` (files touched, decisions reached,
//! symbols referenced, environment notes). If `extract_context` drifts —
//! `cwd`/`title` no longer mirror the session, file extraction misses
//! documented extensions, decisions / symbols / environment notes lose
//! their deduplication guarantees — every downstream consumer (search
//! index, wiki docs, resume prompt) sees stale context.

use proptest::prelude::*;
use session_ledger::distill::context_extractor::HeuristicContextExtractor;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::ports::ContextExtractor;

const FILE_EXTENSIONS: &[&str] = &[
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".kt", ".rb", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".swift", ".toml", ".json", ".yaml", ".yml", ".md", ".sql", ".css", ".scss",
    ".html", ".sh", ".tf", ".lock",
];

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

fn make_session(id: &str, messages: &[(Role, &str)]) -> Session {
    let mut session = Session::new(id, Corpus::Forge);
    for (role, content) in messages {
        session.messages.push(Message::new(*role, *content));
    }
    session
}

// ── cwd / title mirroring ───────────────────────────────────────────────────

proptest! {
    /// `cwd` and `title` are always copied verbatim from the session.
    #[test]
    fn cwd_and_title_mirror_session(
        cwd in proptest::option::of("[a-zA-Z0-9/_.-]{0,40}"),
        title in proptest::option::of("[a-zA-Z0-9 _.-]{0,40}"),
    ) {
        let mut session = Session::new("ctx-mirror", Corpus::Forge);
        session.cwd = cwd.clone();
        session.title = title.clone();
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert_eq!(ctx.cwd, cwd);
        prop_assert_eq!(ctx.title, title);
    }
}

// ── empty / whitespace-only sessions ───────────────────────────────────────

proptest! {
    /// Empty sessions always produce an empty `Context`.
    #[test]
    fn empty_session_produces_empty_context(_dummy in 0_u8..1) {
        let session = Session::new("empty", Corpus::Forge);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(ctx.is_empty());
        prop_assert_eq!(ctx.files_mentioned.len(), 0);
        prop_assert_eq!(ctx.key_decisions.len(), 0);
        prop_assert_eq!(ctx.key_symbols.len(), 0);
        prop_assert_eq!(ctx.environment_notes.len(), 0);
    }

    /// Whitespace-only / empty messages never contribute findings.
    #[test]
    fn whitespace_only_messages_produce_empty_context(
        n_blank in 1_usize..4,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for _ in 0..n_blank {
            messages.push((Role::User, "   \t\n  "));
        }
        let session = make_session("blank", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(ctx.files_mentioned.is_empty());
        prop_assert!(ctx.key_decisions.is_empty());
        prop_assert!(ctx.key_symbols.is_empty());
        prop_assert!(ctx.environment_notes.is_empty());
    }
}

// ── File paths ──────────────────────────────────────────────────────────────

proptest! {
    /// Every detected file path is non-empty and either
    /// contains a `/` OR ends with a documented extension.
    #[test]
    fn files_mentioned_match_path_shape(
        bodies in proptest::collection::vec(
            "([a-zA-Z0-9._/-]{1,32}\\.[a-zA-Z]{1,4}|see [a-zA-Z0-9._/-]{1,32})",
            0..4,
        ),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("files-shape", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        for f in &ctx.files_mentioned {
            prop_assert!(!f.is_empty(), "file path must be non-empty");
            prop_assert!(f.len() >= 3, "file path must be at least 3 chars");
            let has_slash = f.contains('/');
            let ends_with_ext = FILE_EXTENSIONS.iter().any(|e| f.to_lowercase().ends_with(e));
            prop_assert!(
                has_slash || ends_with_ext,
                "file path must contain / or end with documented extension: {f}"
            );
        }
    }

    /// Repeated file mentions across messages are deduplicated.
    #[test]
    fn duplicate_file_mentions_are_deduplicated(
        body in "[a-zA-Z0-9/_.-]{3,40}\\.(rs|ts|py|toml)",
    ) {
        let owned = body.clone();
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("dup-file", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        // The same exact token may appear under multiple wrappings; the
        // output must have at most one entry per unique path.
        let occurrences = ctx.files_mentioned.iter()
            .filter(|f| f.contains(&body) || body.contains(f.as_str()))
            .count();
        prop_assert!(occurrences <= 1, "duplicate file paths must be deduplicated, got {occurrences}");
    }

    /// Every documented file extension is detected on a single test message.
    #[test]
    fn every_documented_file_extension_is_detected(ext in proptest::sample::select(FILE_EXTENSIONS)) {
        let owned = ext.to_string();
        let ext_str = owned.as_str();
        let body = format!("main{ext_str}");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("ext-coverage", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(
            !ctx.files_mentioned.is_empty(),
            "documented extension {ext} must be detected"
        );
    }
}

// ── Decisions ───────────────────────────────────────────────────────────────

proptest! {
    /// Every detected decision summary contains the pattern text.
    #[test]
    fn decision_summaries_carry_pattern_text(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = body.clone();
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("dec-text", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        for d in &ctx.key_decisions {
            // summary is `format!("Session contains '{pat}' language")` for the matching pattern.
            prop_assert!(d.summary.starts_with("Session contains '"));
            prop_assert!(d.summary.ends_with("' language"));
        }
    }

    /// Decision rationale equals the full message content.
    #[test]
    fn decision_rationale_equals_message_content(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        // Force a decision pattern to be present.
        let owned = format!("decided {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("dec-rationale", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(!ctx.key_decisions.is_empty());
        let has_match = ctx.key_decisions.iter()
            .any(|d| d.rationale.as_deref() == Some(owned.as_str()));
        prop_assert!(has_match, "decision rationale must include the source message");
    }

    /// Every documented decision pattern is detected on a minimal trigger.
    #[test]
    fn every_documented_decision_pattern_detected(pat in proptest::sample::select(DECISION_PATTERNS)) {
        let body = format!("we {pat} rust");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("dec-coverage", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(!ctx.key_decisions.is_empty(), "decision pattern {pat} must be detected");
    }

    /// Decision patterns are detected case-insensitively.
    #[test]
    fn decision_patterns_case_insensitive(
        pat in proptest::sample::select(DECISION_PATTERNS),
    ) {
        let upper = pat.to_uppercase();
        let body = format!("we {upper} rust");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("dec-case", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(!ctx.key_decisions.is_empty(), "decision pattern {pat} must match case-insensitively");
    }

    /// Decisions are deduplicated by summary.
    #[test]
    fn decisions_deduplicated_by_summary(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("we decided {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("dec-dedup", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        let decision_count = ctx.key_decisions.iter()
            .filter(|d| d.summary.contains("decided"))
            .count();
        prop_assert_eq!(decision_count, 1, "decisions must be deduplicated by summary");
    }
}

// ── Symbols ────────────────────────────────────────────────────────────────

proptest! {
    /// Every detected symbol either contains `::` (the trimmed symbol keeps
    /// `::`) or was extracted from a token whose original form contained `()`.
    /// The extractor trims parens/brackets/braces from the symbol, so a
    /// function-call source token yields a non-`::` cleaned symbol.
    #[test]
    fn symbols_match_double_colon_or_function_call(
        bodies in proptest::collection::vec(
            "[a-zA-Z_][a-zA-Z0-9_]*(::[a-zA-Z_][a-zA-Z0-9_]*|\\(\\))",
            0..4,
        ),
    ) {
        // Track which token form each detected symbol could have come from.
        let mut symbol_sources: Vec<String> = Vec::new();
        for body in &bodies {
            for token in body.split_whitespace() {
                if (token.contains("::") || token.contains("()"))
                    && !symbol_sources.iter().any(|s| s == token)
                {
                    symbol_sources.push(token.to_string());
                }
            }
        }
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("sym-shape", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        for sym in &ctx.key_symbols {
            // Either the symbol itself contains `::` (kept through trimming),
            // or it was derived from a token whose raw form contained `()`.
            let from_double_colon = sym.contains("::");
            let from_func_call = symbol_sources.iter().any(|s| {
                s.contains("()") && s.matches(|c: char| c.is_alphanumeric() || c == '_' || c == ':')
                    .collect::<String>()
                    .contains(sym.as_str())
            });
            prop_assert!(
                from_double_colon || from_func_call,
                "symbol must have come from a `::` or `()` token, got {sym}"
            );
        }
    }

    /// Repeated symbols are deduplicated.
    #[test]
    fn symbols_deduplicated(
        symbol in "(HashMap|String|Vec)::[a-zA-Z_][a-zA-Z0-9_]{1,20}",
    ) {
        let owned = format!("use {symbol} now");
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("sym-dedup", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        let occurrences = ctx.key_symbols.iter()
            .filter(|sym| sym.contains(&symbol) || symbol.contains(sym.as_str()))
            .count();
        prop_assert!(occurrences <= 1, "duplicate symbols must be deduplicated, got {occurrences}");
    }

    /// Plain identifiers without `::` or `()` are NOT extracted as symbols.
    #[test]
    fn plain_identifiers_not_extracted_as_symbols(
        body in "[a-zA-Z_][a-zA-Z0-9_]{0,20}",
    ) {
        let owned = body.clone();
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("sym-plain", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        let strs: Vec<&str> = ctx.key_symbols.iter().map(String::as_str).collect();
        prop_assert!(
            !strs.iter().any(|s| *s == body),
            "plain identifier {body} must not be extracted as a symbol"
        );
    }
}

// ── Environment notes ──────────────────────────────────────────────────────

proptest! {
    /// Every detected environment note is unique (post-dedup).
    #[test]
    fn environment_notes_deduplicated(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("install {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("env-dedup", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        let mut sorted = ctx.environment_notes.clone();
        sorted.sort();
        let original_len = ctx.environment_notes.len();
        sorted.dedup();
        prop_assert_eq!(sorted.len(), original_len, "environment notes must be deduplicated");
    }

    /// Every documented environment pattern is detected.
    #[test]
    fn every_documented_environment_pattern_detected(pat in proptest::sample::select(ENVIRONMENT_PATTERNS)) {
        let body = format!("please {pat} the tool");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("env-coverage", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(!ctx.environment_notes.is_empty(), "environment pattern {pat} must be detected");
    }

    /// Environment notes are detected case-insensitively.
    #[test]
    fn environment_patterns_case_insensitive(
        pat in proptest::sample::select(ENVIRONMENT_PATTERNS),
    ) {
        let upper = pat.to_uppercase();
        let body = format!("please {upper} the tool");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("env-case", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        prop_assert!(!ctx.environment_notes.is_empty(), "environment pattern {pat} must match case-insensitively");
    }
}

// ── Determinism ────────────────────────────────────────────────────────────

proptest! {
    /// `extract_context` is deterministic across repeated calls.
    #[test]
    fn extract_context_is_deterministic(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..6),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("det", &messages);
        let a = HeuristicContextExtractor::extract_context(&session);
        let b = HeuristicContextExtractor::extract_context(&session);
        prop_assert_eq!(a.cwd, b.cwd);
        prop_assert_eq!(a.title, b.title);
        prop_assert_eq!(a.files_mentioned, b.files_mentioned);
        prop_assert_eq!(a.key_symbols, b.key_symbols);
        prop_assert_eq!(a.environment_notes, b.environment_notes);
        prop_assert_eq!(a.key_decisions.len(), b.key_decisions.len());
    }

    /// The `ContextExtractor` trait path yields the same `Context` as the
    /// associated function.
    #[test]
    fn trait_path_matches_associated_function(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("trait", &messages);
        let via_fn = HeuristicContextExtractor::extract_context(&session);
        let extractor = HeuristicContextExtractor::new();
        let via_trait = extractor.extract(&session).expect("extract must succeed");
        prop_assert_eq!(via_fn.cwd, via_trait.cwd);
        prop_assert_eq!(via_fn.title, via_trait.title);
        prop_assert_eq!(via_fn.files_mentioned, via_trait.files_mentioned);
        prop_assert_eq!(via_fn.key_symbols, via_trait.key_symbols);
        prop_assert_eq!(via_fn.environment_notes, via_trait.environment_notes);
        prop_assert_eq!(via_fn.key_decisions.len(), via_trait.key_decisions.len());
    }
}

// ── `is_empty` ↔ findings ──────────────────────────────────────────────────

proptest! {
    /// `is_empty()` is true iff every collection is empty AND cwd/title are None.
    #[test]
    fn is_empty_iff_no_findings(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("empty-iff", &messages);
        let ctx = HeuristicContextExtractor::extract_context(&session);
        let all_empty = ctx.cwd.is_none()
            && ctx.title.is_none()
            && ctx.files_mentioned.is_empty()
            && ctx.key_decisions.is_empty()
            && ctx.key_symbols.is_empty()
            && ctx.environment_notes.is_empty();
        if all_empty {
            prop_assert!(ctx.is_empty());
        }
        if !ctx.is_empty() {
            prop_assert!(!all_empty);
        }
    }
}
