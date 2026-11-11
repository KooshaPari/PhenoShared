//! Property evidence for `session_ledger::distill::dedup_compiler::DedupCompiler`.
//!
//! The dedup compiler is the deterministic scope-keyed manifest pipeline that
//! compiles same-scope sessions into a typed, token-sized Dedup slice. If
//! `DedupKey::derive` drifts, manifest dedup breaks, or scope validation
//! stops rejecting mixed-cwd inputs, every merge downstream consumes stale
//! dedup data.

use proptest::prelude::*;
use session_ledger::distill::dedup_compiler::{DedupCompileError, DedupCompiler};
use session_ledger::distill::token_estimator::CharCountTokenEstimator;
use session_ledger::domain::bundle::BundleKind;
use session_ledger::domain::dedup::DedupManifest;
use session_ledger::domain::session::{Corpus, Session};

fn make_session(id: &str, cwd: Option<&str>, corpus: Corpus) -> Session {
    let mut session = Session::new(id, corpus);
    session.cwd = cwd.map(str::to_owned);
    session
}

// ── Empty inputs ───────────────────────────────────────────────────────────

proptest! {
    /// Empty sessions always return `Err(EmptySessions)`.
    #[test]
    fn empty_input_returns_empty_sessions_error(topic in "[a-zA-Z][a-zA-Z0-9-_]{0,30}") {
        let compiler = DedupCompiler::new(CharCountTokenEstimator);
        let result = compiler.compile(&[], &topic);
        prop_assert_eq!(result.err(), Some(DedupCompileError::EmptySessions));
    }

    /// Whitespace-only or empty topic always returns `Err(EmptyTopic)` even
    /// with non-empty sessions.
    #[test]
    fn blank_topic_returns_empty_topic_error(ws in "[ \t\n]{1,8}") {
        let compiler = DedupCompiler::new(CharCountTokenEstimator);
        let sessions = [make_session("s1", Some("/repo"), Corpus::Forge)];
        let result = compiler.compile(&sessions, &ws);
        prop_assert_eq!(result.err(), Some(DedupCompileError::EmptyTopic));
    }
}

// ── Topic normalization ────────────────────────────────────────────────────

proptest! {
    /// Topic is trimmed and lowercased before use.
    #[test]
    fn topic_is_normalized(body in "[A-Z][a-zA-Z0-9-]{0,20}") {
        let owned = body.clone();
        let upper = owned.to_uppercase();
        let topic = format!("  {upper}  ");
        let sessions = [make_session("s1", Some("/repo"), Corpus::Forge)];
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest.topic_slug, owned.to_lowercase());
    }
}

// ── Output shape ───────────────────────────────────────────────────────────

proptest! {
    /// Output bundle always has `kind = BundleKind::Dedup` and a positive
    /// `token_estimate`.
    #[test]
    fn output_bundle_has_dedup_kind_and_positive_estimate(
        n in 1_usize..4,
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let sessions: Vec<Session> = (0..n)
            .map(|i| make_session(&format!("s{i}"), Some("/repo"), Corpus::Forge))
            .collect();
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic)
            .expect("compilation should succeed");
        prop_assert_eq!(bundle.kind, BundleKind::Dedup);
        prop_assert!(bundle.token_estimate > 0);
    }

    /// Manifest body always deserializes to `DedupManifest`.
    #[test]
    fn manifest_body_deserializes(
        n in 1_usize..4,
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let sessions: Vec<Session> = (0..n)
            .map(|i| make_session(&format!("s{i}"), Some("/repo"), Corpus::Forge))
            .collect();
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest.sessions.len(), n);
    }
}

// ── DedupKey invariants ────────────────────────────────────────────────────

proptest! {
    /// `dedup_key` is exactly 64 hex chars (sha256 fingerprint).
    #[test]
    fn dedup_key_length_is_64(topic in "[a-z][a-z0-9-]{0,10}") {
        let sessions = [make_session("s1", Some("/repo"), Corpus::Forge)];
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest.dedup_key.as_str().len(), 64);
    }

    /// Same scope → same dedup_key regardless of input order.
    #[test]
    fn dedup_key_independent_of_input_order(
        ids in proptest::collection::hash_set("[a-z]{1,3}", 2..4),
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let mut ids: Vec<String> = ids.into_iter().collect();
        ids.sort();
        let sessions_a: Vec<Session> = ids
            .iter()
            .map(|i| make_session(i.as_str(), Some("/repo"), Corpus::Forge))
            .collect();
        let mut sessions_b = sessions_a.clone();
        sessions_b.reverse();
        let bundle_a = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions_a, &topic)
            .expect("compilation should succeed");
        let bundle_b = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions_b, &topic)
            .expect("compilation should succeed");
        let manifest_a: DedupManifest =
            serde_json::from_value(bundle_a.body).expect("manifest should deserialize");
        let manifest_b: DedupManifest =
            serde_json::from_value(bundle_b.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest_a.dedup_key, manifest_b.dedup_key);
    }

    /// Different topic → different dedup_key (same sessions).
    #[test]
    fn dedup_key_differs_by_topic(
        topic_a in "[a-z]{1,6}",
        topic_b in "[a-z]{7,12}",
    ) {
        let sessions = [make_session("s1", Some("/repo"), Corpus::Forge)];
        let bundle_a = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic_a)
            .expect("compilation should succeed");
        let bundle_b = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic_b)
            .expect("compilation should succeed");
        let manifest_a: DedupManifest =
            serde_json::from_value(bundle_a.body).expect("manifest should deserialize");
        let manifest_b: DedupManifest =
            serde_json::from_value(bundle_b.body).expect("manifest should deserialize");
        prop_assert_ne!(manifest_a.dedup_key, manifest_b.dedup_key);
    }

    /// Different cwd → different dedup_key.
    #[test]
    fn dedup_key_differs_by_cwd(
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let session_a = make_session("s1", Some("/repo-a"), Corpus::Forge);
        let session_b = make_session("s1", Some("/repo-b"), Corpus::Forge);
        let bundle_a = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[session_a], &topic)
            .expect("compilation should succeed");
        let bundle_b = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[session_b], &topic)
            .expect("compilation should succeed");
        let manifest_a: DedupManifest =
            serde_json::from_value(bundle_a.body).expect("manifest should deserialize");
        let manifest_b: DedupManifest =
            serde_json::from_value(bundle_b.body).expect("manifest should deserialize");
        prop_assert_ne!(manifest_a.dedup_key, manifest_b.dedup_key);
    }
}

// ── Dedup / ordering ───────────────────────────────────────────────────────

proptest! {
    /// Duplicate members (same id + corpus) appear once, preserving first
    /// occurrence order.
    #[test]
    fn duplicate_member_deduped(topic in "[a-z][a-z0-9-]{0,10}") {
        let session = make_session("s1", Some("/repo"), Corpus::Forge);
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[session.clone(), session.clone(), session], &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest.sessions.len(), 1);
    }

    /// Members preserve input order in the manifest.
    #[test]
    fn members_preserve_input_order(
        ids in proptest::collection::hash_set("[a-z]{1,3}", 2..5),
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let ids: Vec<String> = ids.into_iter().collect();
        let sessions: Vec<Session> = ids
            .iter()
            .map(|i| make_session(i.as_str(), Some("/repo"), Corpus::Forge))
            .collect();
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        let manifest_ids: Vec<&str> = manifest.sessions.iter()
            .map(|m| m.session_id.as_str())
            .collect();
        let input_ids: Vec<&str> = ids.iter().map(String::as_str).collect();
        prop_assert_eq!(manifest_ids, input_ids);
    }

    /// Different corpora for same cwd produce different members.
    #[test]
    fn corpora_preserved_per_member(topic in "[a-z][a-z0-9-]{0,10}") {
        let s_forge = make_session("s1", Some("/repo"), Corpus::Forge);
        let s_cursor = make_session("s2", Some("/repo"), Corpus::Cursor);
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[s_forge, s_cursor], &topic)
            .expect("compilation should succeed");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");
        prop_assert_eq!(manifest.sessions.len(), 2);
        prop_assert_eq!(manifest.sessions[0].corpus, Corpus::Forge);
        prop_assert_eq!(manifest.sessions[1].corpus, Corpus::Cursor);
    }
}

// ── Scope validation ───────────────────────────────────────────────────────

proptest! {
    /// Mixed-scope sessions return `Err(ScopeMismatch)` with the offending
    /// session_id.
    #[test]
    fn mixed_scopes_return_scope_mismatch(topic in "[a-z][a-z0-9-]{0,10}") {
        let s_a = make_session("aaa", Some("/repo-a"), Corpus::Forge);
        let s_b = make_session("bbb", Some("/repo-b"), Corpus::Forge);
        let err = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[s_a, s_b], &topic)
            .expect_err("mixed scopes must be rejected");
        match err {
            DedupCompileError::ScopeMismatch { session_id, .. } => {
                prop_assert_eq!(session_id, "bbb");
            }
            other => prop_assert!(false, "expected ScopeMismatch, got {other:?}"),
        }
    }
}

// ── Determinism ────────────────────────────────────────────────────────────

proptest! {
    /// Compilation is deterministic across repeated calls.
    #[test]
    fn compile_is_deterministic(
        n in 1_usize..4,
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let sessions: Vec<Session> = (0..n)
            .map(|i| make_session(&format!("s{i}"), Some("/repo"), Corpus::Forge))
            .collect();
        let compiler = DedupCompiler::new(CharCountTokenEstimator);
        let a = compiler.compile(&sessions, &topic).expect("compilation should succeed");
        let b = compiler.compile(&sessions, &topic).expect("compilation should succeed");
        prop_assert_eq!(a.kind, b.kind);
        prop_assert_eq!(a.token_estimate, b.token_estimate);
        prop_assert_eq!(a.body, b.body);
    }
}

// ── Token scaling ──────────────────────────────────────────────────────────

proptest! {
    /// `token_estimate` is monotonic non-decreasing in session count.
    #[test]
    fn token_estimate_monotonic_in_count(
        topic in "[a-z][a-z0-9-]{0,10}",
    ) {
        let sessions_1 = [make_session("s1", Some("/repo"), Corpus::Forge)];
        let sessions_2 = [
            make_session("s1", Some("/repo"), Corpus::Forge),
            make_session("s2", Some("/repo"), Corpus::Forge),
        ];
        let bundle_1 = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions_1, &topic)
            .expect("compilation should succeed");
        let bundle_2 = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions_2, &topic)
            .expect("compilation should succeed");
        prop_assert!(bundle_2.token_estimate >= bundle_1.token_estimate);
    }
}
