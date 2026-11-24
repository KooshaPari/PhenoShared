//! Property evidence for `session_ledger::distill::compile` and
//! `compile_and_store` (the deterministic compilation pipeline
//! that turns a `Session` into a `ContinuationBundle`).
//!
//! The compile pipeline is the SSOT for "what does an injectable
//! bundle look like?". If it stops emitting the documented slice
//! kinds, or `is_injectable()` ever returns false, downstream
//! resume / inject / search all break.

use proptest::prelude::*;
use session_ledger::distill::{compile, compile_and_store, DistillOutput};
use session_ledger::domain::bundle::BundleKind;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::ports::adapters::InMemoryMemoryStore;
use session_ledger::ports::MemoryStore;

const ALL_KINDS: &[BundleKind] = &[
    BundleKind::Acceptance,
    BundleKind::Intent,
    BundleKind::Context,
    BundleKind::Contract,
    BundleKind::Provenance,
    BundleKind::Worklog,
];

proptest! {
    /// `compile(session)` always returns a bundle whose `source_id`
    /// equals `session.id`.
    #[test]
    fn compile_carries_session_id(
        session_id in "[a-zA-Z0-9_-]{1,16}",
    ) {
        let session = Session::new(&session_id, Corpus::Forge);
        let bundle = compile(&session);
        prop_assert_eq!(bundle.source_id, session.id);
    }

    /// `compile(session)` always returns an injectable bundle
    /// (i.e., it carries an `Acceptance` slice). This is the
    /// load-bearing contract for resume.
    #[test]
    fn compile_is_always_injectable(
        session_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..4_usize,
        messages in proptest::collection::vec(
            (0..5_usize, role_choice()),
            0..5,
        ),
    ) {
        let corpus = [Corpus::Forge, Corpus::Codex, Corpus::Cursor, Corpus::ClaudeCode][corpus_idx];
        let mut session = Session::new(&session_id, corpus);
        for (i, role) in messages {
            session.messages.push(Message::new(role, format!("message-{i}")));
        }
        let bundle = compile(&session);
        prop_assert!(bundle.is_injectable(),
            "compile({session_id}) did not produce an injectable bundle");
        prop_assert!(bundle.has(BundleKind::Acceptance));
    }

    /// `compile(session)` always emits one slice for every documented
    /// kind — even when the session is empty.
    #[test]
    fn compile_emits_all_documented_slice_kinds(
        session_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..4_usize,
    ) {
        let corpus = [Corpus::Forge, Corpus::Codex, Corpus::Cursor, Corpus::ClaudeCode][corpus_idx];
        let session = Session::new(&session_id, corpus);
        let bundle = compile(&session);
        for kind in ALL_KINDS {
            prop_assert!(bundle.has(*kind),
                "compile({session_id}) missing {kind:?} slice");
        }
    }

    /// `compile(session)` always returns a bundle whose
    /// `total_token_estimate()` equals the sum of per-slice
    /// `token_estimate` values.
    #[test]
    fn compile_token_total_equals_sum(
        n_messages in 0_usize..5,
    ) {
        let mut session = Session::new("token-sum", Corpus::Forge);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("user message {i}")));
        }
        let bundle = compile(&session);
        let sum: u32 = bundle.bundles.iter().map(|slice| slice.token_estimate).sum();
        prop_assert_eq!(bundle.total_token_estimate(), sum);
    }

    /// `compile(session)` is deterministic across calls.
    #[test]
    fn compile_is_deterministic(
        n_messages in 0_usize..4,
        corpus_idx in 0..4_usize,
    ) {
        let corpus = [Corpus::Forge, Corpus::Codex, Corpus::Cursor, Corpus::ClaudeCode][corpus_idx];
        let mut session = Session::new("det", corpus);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("msg-{i}")));
        }
        let a = compile(&session);
        let b = compile(&session);
        prop_assert_eq!(a, b);
    }

    /// The `Worklog` slice's body deserializes to a `WorklogProjection`
    /// whose `message_count` equals `session.messages.len()`.
    #[test]
    fn compile_worklog_carries_message_count(
        n_messages in 0_usize..5,
    ) {
        let mut session = Session::new("wl", Corpus::Forge);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("m-{i}")));
        }
        let bundle = compile(&session);
        let worklog = bundle
            .bundles
            .iter()
            .find(|slice| slice.kind == BundleKind::Worklog)
            .expect("compile must emit Worklog slice");
        let projection: session_ledger::domain::worklog::WorklogProjection =
            serde_json::from_value(worklog.body.clone()).expect("worklog body should deserialize");
        prop_assert_eq!(projection.message_count, n_messages);
    }

    /// `compile_and_store` returns an injectable bundle with the same
    /// `source_id` as the input session.
    #[test]
    fn compile_and_store_returns_injectable_bundle(
        session_id in "[a-zA-Z0-9_-]{1,16}",
        n_messages in 0_usize..3,
    ) {
        let mut session = Session::new(&session_id, Corpus::Forge);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("do it {i}")));
        }
        let store = InMemoryMemoryStore::default();
        let output: DistillOutput = compile_and_store(&session, &store)
            .expect("compile_and_store must succeed for well-formed session");
        let source_id = output.bundle.source_id.clone();
        prop_assert_eq!(source_id, session.id);
        prop_assert!(output.bundle.is_injectable());
    }

    /// `compile_and_store` writes exactly 3 episodic memories
    /// (intent, contract, context) to the memory store.
    #[test]
    fn compile_and_store_writes_three_memories(
        n_messages in 0_usize..3,
    ) {
        let mut session = Session::new("store-3", Corpus::Forge);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("Goal: m-{i}\nConstraint: c-{i}")));
        }
        let store = InMemoryMemoryStore::default();
        let output = compile_and_store(&session, &store).expect("compile_and_store");
        prop_assert_eq!(output.memories.len(), 3,
            "expected 3 memories (intent / contract / context), got {}", output.memories.len());
        let recalled = store
            .recall("session/store-3/episodic", 10)
            .expect("recall stored facts");
        prop_assert_eq!(recalled.len(), 3);
    }

    /// `compile_and_store` is deterministic — same session + store
    /// produce the same DistillOutput.
    #[test]
    fn compile_and_store_is_deterministic(
        n_messages in 0_usize..3,
    ) {
        let mut session = Session::new("det-store", Corpus::Forge);
        for i in 0..n_messages {
            session.messages.push(Message::new(Role::User, format!("m {i}")));
        }
        let store_a = InMemoryMemoryStore::default();
        let store_b = InMemoryMemoryStore::default();
        let out_a = compile_and_store(&session, &store_a).expect("compile_and_store a");
        let out_b = compile_and_store(&session, &store_b).expect("compile_and_store b");
        prop_assert_eq!(out_a.bundle, out_b.bundle);
        prop_assert_eq!(out_a.memories.len(), out_b.memories.len());
    }
}

// ── Strategy helpers ───────────────────────────────────────────────────────

fn role_choice() -> impl Strategy<Value = Role> {
    prop::sample::select(vec![
        Role::User,
        Role::Assistant,
        Role::Subagent,
        Role::Tool,
        Role::System,
    ])
}
