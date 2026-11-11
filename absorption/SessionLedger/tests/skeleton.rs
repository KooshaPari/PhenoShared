//! Skeleton integration tests proving the domain compiles and behaves.
//!
//! Traceability: JSONL ingest / distill paths cover FR-001; injectable
//! [`ContinuationBundle`] compile covers FR-012.

use session_ledger::distill;
use session_ledger::domain::dedup::DedupKey;
use session_ledger::domain::intent::IntentState;
use session_ledger::domain::session::Corpus;
use session_ledger::{
    parse_jsonl_sessions, process_session, Bundle, BundleKind, ContinuationBundle, Message, Role,
    Session,
};

fn sample_session() -> Session {
    let mut s = Session::new("sess-1", Corpus::Forge);
    s.cwd = Some("/workspace/user/proj".into());
    s.title = Some("fix the thing".into());
    s.messages.push(Message::new(Role::User, "please fix the bug"));
    s.messages.push(Message::new(Role::Assistant, "on it"));
    s.messages.push(Message::new(Role::User, "also add a test"));
    s
}

#[test]
fn fr012_compiled_bundle_is_injectable_and_complete() {
    let s = sample_session();
    let bundle = distill::compile(&s);
    assert!(bundle.is_injectable(), "must carry an Acceptance gate");
    for kind in [
        BundleKind::Acceptance,
        BundleKind::Intent,
        BundleKind::Context,
        BundleKind::Contract,
        BundleKind::Provenance,
        BundleKind::Worklog,
    ] {
        assert!(bundle.has(kind), "missing bundle kind {kind:?}");
    }
    assert_eq!(s.user_turns(), 2);
}

#[test]
fn bundle_without_acceptance_is_not_injectable() {
    let mut b = ContinuationBundle::new("x");
    b.push(Bundle::new(BundleKind::Context, serde_json::json!({})));
    assert!(!b.is_injectable());
}

#[test]
fn intent_fsm_is_forward_only_and_prune_gated() {
    assert!(IntentState::Pending.can_transition(IntentState::Extracting));
    assert!(IntentState::Extracted.can_transition(IntentState::Verified));
    assert!(IntentState::Verified.can_transition(IntentState::Pruned));
    // illegal: cannot skip straight to pruned
    assert!(!IntentState::Pending.can_transition(IntentState::Pruned));
    // ADR-103: only verified intent prunes
    assert!(IntentState::Verified.is_prune_eligible());
    assert!(!IntentState::Extracted.is_prune_eligible());
    assert!(IntentState::Pruned.is_terminal());
}

#[test]
fn dedup_key_collapses_same_scope_and_topic() {
    let a = sample_session();
    let mut b = sample_session();
    b.id = "sess-2".into(); // different session, same scope+topic
    let ka = DedupKey::derive(&a, "fix-the-bug");
    let kb = DedupKey::derive(&b, "fix-the-bug");
    assert_eq!(ka, kb, "duplicate-scoped chats must share a dedup key");

    let kc = DedupKey::derive(&a, "unrelated-topic");
    assert_ne!(ka, kc);
}

#[test]
fn bundle_roundtrips_through_json() {
    let bundle = distill::compile(&sample_session());
    let s = serde_json::to_string(&bundle).expect("serialize");
    let back: ContinuationBundle = serde_json::from_str(&s).expect("deserialize");
    assert_eq!(bundle, back);
}

// ---------------------------------------------------------------------------
// Pipeline integration: JSONL ingestion → distill compilation → OKF export
// ---------------------------------------------------------------------------

fn sample_jsonl() -> String {
    let mut s1 = Session::new("pipeline-int-1", Corpus::Forge);
    s1.cwd = Some("/home/user/proj".into());
    s1.title = Some("fix pagination".into());
    s1.messages.push(Message::new(
        Role::User,
        "fix the pagination bug but don't change the database schema",
    ));
    s1.messages.push(Message::new(Role::Assistant, "on it"));
    s1.messages.push(Message::new(Role::User, "looks good, tests pass now"));

    let mut s2 = Session::new("pipeline-int-2", Corpus::Codex);
    s2.cwd = Some("/home/user/proj".into());
    s2.title = Some("add auth".into());
    s2.messages.push(Message::new(Role::User, "add JWT authentication to the API"));
    s2.messages.push(Message::new(Role::Assistant, "I'll add jsonwebtoken and middleware"));
    s2.messages.push(Message::new(Role::User, "lgtm, ship it"));

    let mut buf = String::new();
    buf.push_str(&serde_json::to_string(&s1).expect("serialize s1"));
    buf.push('\n');
    buf.push_str(&serde_json::to_string(&s2).expect("serialize s2"));
    buf.push('\n');
    buf
}

#[test]
fn fr001_pipeline_round_trips_jsonl_through_ingest_distill_export() {
    let jsonl = sample_jsonl();

    // Stage 1: Ingestion — parse JSONL into sessions.
    let sessions = parse_jsonl_sessions(jsonl.as_bytes()).expect("parse JSONL");
    assert_eq!(sessions.len(), 2, "should parse two sessions");

    // Stage 2: process_session compiles AND exports in one step.
    let docs: Vec<_> = sessions.iter().map(process_session).collect();
    assert_eq!(docs.len(), 2, "should produce two documents");

    // First document: forge session "fix pagination"
    let first = &docs[0];
    assert_eq!(first.source_id, "pipeline-int-1");
    assert_eq!(first.provenance.corpus, "forge");
    assert!(first.entities.iter().any(|e| e.r#type == "gate"), "should have gate entity");
    assert!(first.entities.iter().any(|e| e.r#type == "intent"), "should have intent entity");
    assert!(
        first.entities.iter().any(|e| e.r#type == "constraint"),
        "should have constraint entity"
    );
    assert!(
        first.relations.iter().any(|r| r.r#type == "bounded_by"),
        "should have bounded_by edge"
    );

    // Second document: codex session "add auth"
    let second = &docs[1];
    assert_eq!(second.source_id, "pipeline-int-2");
    assert_eq!(second.provenance.corpus, "codex");

    // Round-trip through JSON serialization.
    for doc in &docs {
        let json_str = serde_json::to_string_pretty(doc).expect("serialize");
        let back: session_ledger::OkfDocument =
            serde_json::from_str(&json_str).expect("deserialize OKF document");
        assert_eq!(doc, &back, "OKF document round-trips through JSON");
    }
}

// ---------------------------------------------------------------------------
// T03: focused single-session JSONL → OKF round-trip
// ---------------------------------------------------------------------------

fn forge_jsonl_roundtrip_fixture() -> String {
    // Minimal but realistic forge-format Session: id, cwd, title, 3 messages.
    // Serializes each Session as one JSON object per line.
    let mut s = Session::new("t03-forge-roundtrip", Corpus::Forge);
    s.cwd = Some("/workspace/user/projects/SessionLedger".into());
    s.title = Some("wire ingest→distill→export and prove JSONL round-trip".into());
    s.messages.push(Message::new(
        Role::User,
        "wire the ingest→distill→export pipeline and prove a JSONL round-trip",
    ));
    s.messages.push(Message::new(
        Role::Assistant,
        "compiling the session into a ContinuationBundle and exporting an OkfDocument",
    ));
    s.messages.push(Message::new(
        Role::User,
        "looks good — verify the OKF document has non-empty context or bundle",
    ));

    let mut buf = String::new();
    buf.push_str(&serde_json::to_string(&s).expect("serialize forge session"));
    buf.push('\n');
    buf
}

#[test]
fn real_jsonl_roundtrip_produces_okf_document() {
    // (1) Build a minimal valid forge-format JSONL string in-memory:
    //     one session with id, cwd, and 2+ messages.
    let jsonl = forge_jsonl_roundtrip_fixture();
    assert!(jsonl.contains("t03-forge-roundtrip"));
    assert!(jsonl.contains("\"corpus\":\"forge\""));
    assert!(jsonl.contains("\"cwd\":"));

    // (2) Parse it through the production JSONL ingestion entry point.
    let sessions = parse_jsonl_sessions(jsonl.as_bytes()).expect("parse JSONL fixture");

    // (3) Exactly one session round-tripped out of the JSONL.
    assert_eq!(sessions.len(), 1, "JSONL fixture should yield exactly one session");
    let session = &sessions[0];
    assert_eq!(session.id, "t03-forge-roundtrip");
    assert_eq!(session.corpus, Corpus::Forge);
    assert!(session.cwd.as_deref().is_some_and(|s| !s.is_empty()));
    assert!(session.title.as_deref().is_some_and(|s| !s.is_empty()));
    assert!(
        session.messages.len() >= 2,
        "fixture must carry 2+ messages to satisfy the round-trip contract"
    );

    // (4) Run the full compile → export pipeline on the parsed session.
    let doc = process_session(session);

    // (5) The OkfDocument must carry a non-empty bundle or context.
    //     The OKF surface has no direct `context`/`bundle` fields; the compiled
    //     bundle manifests as the entity graph, and the Context bundle
    //     produces `resource` (cwd) and `state` (title) entities. Require
    //     either: (a) the bundle produced entities, OR (b) the document
    //     carries context entities.
    let has_bundle_entities =
        doc.entities.iter().any(|e| matches!(e.r#type.as_str(), "intent" | "gate" | "criteria"));
    let has_context_entities =
        doc.entities.iter().any(|e| matches!(e.r#type.as_str(), "resource" | "state"));

    assert!(
        has_bundle_entities || has_context_entities,
        "OKF document must carry a non-empty bundle (intent/gate/criteria) or \
         context (resource/state) — got entities: {:?}",
        doc.entities.iter().map(|e| e.r#type.as_str()).collect::<Vec<_>>()
    );

    // The context entities (when present) must reflect the round-tripped values.
    if let Some(res) = doc.entities.iter().find(|e| e.r#type == "resource") {
        assert_eq!(res.properties["cwd"], session.cwd.as_deref().unwrap());
    }
    if let Some(state) = doc.entities.iter().find(|e| e.r#type == "state") {
        assert_eq!(state.properties["title"], session.title.as_deref().unwrap());
    }
}
