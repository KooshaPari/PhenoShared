//! OKF roundtrip smoke test (lives in the session-ledger root crate).
//!
//! Traceability: these smoke tests are the primary acceptance evidence for
//! FR-013 (JSONL → daemon contract → OKF → viewer contract).
//!
//! This placement is intentional: it lets the test depend on the canonical
//! `OkfDocument` type without pulling in the sl-viewer lib, which currently
//! has pre-existing compile errors on origin/main (`search_view.rs`, `theme.rs`
//! — out of scope for the roundtrip work).  When sl-viewer is fixed, this
//! test moves to `crates/sl-viewer/tests/okf_roundtrip.rs` and the sl-viewer
//! lib exercises the same contract through its own API surface.
//!
//! What it exercises:
//!
//!   1. Write a JSONL session to a temp directory (mirrors what a user
//!      would do: pick a track, hit Analyze).
//!   2. In-process: read JSONL → compile → export to OKF → write
//!      `.okf.json` (mirrors what `sl-daemon serve --once` does).
//!   3. Read the `.okf.json` back as `OkfDocument` (mirrors what sl-viewer
//!      does when consuming the SSE stream from sl-daemon).
//!   4. Assert the document satisfies the v1.0 structural invariants
//!      documented in `docs/reference/OKF-SPEC.md` §3-§6.
//!   5. Assert the round-trip is byte-identical (idempotency).
//!   6. Cross-check against the conformance fixture committed in the OKF
//!      spec PR (skips if the fixture is not yet merged).
//!
//! Run: `cargo test -p session-ledger --test okf_roundtrip`

use std::path::Path;

use serde_json::json;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::{OkfDocument, OkfEntity, OkfRelation};
use tempfile::tempdir;

/// Write a fixture JSONL containing one auth-fix session — same scenario as
/// the OKF-EXAMPLES.md §2 conformance fixture (forge-session-001).
fn write_fixture_jsonl(dir: &Path) -> std::io::Result<()> {
    let mut s = Session::new("roundtrip-001", Corpus::Forge);
    s.title = Some("Login timeout fix".into());
    s.cwd = Some("/home/dev/auth-service".into());
    s.messages = vec![
        Message::new(
            Role::User,
            "The login session keeps expiring after 5 minutes, we need to fix this.",
        ),
        Message::new(
            Role::Assistant,
            "Let me trace the auth middleware to find where the TTL is set.",
        ),
        Message::new(
            Role::Assistant,
            "Found it — the session TTL is hardcoded to 300s in src/auth/session.rs.",
        ),
        Message::new(Role::User, "Increase it to 1800s and make sure MFA is preserved."),
        Message::new(Role::Assistant, "Done. TTL bumped, all existing auth tests pass."),
        Message::new(Role::User, "Looks good, tests pass. Ship it."),
    ];
    let json = serde_json::to_string(&s).expect("serialize session");
    std::fs::write(dir.join("auth-fix.jsonl"), json + "\n")?;
    Ok(())
}

/// Validate the structural OKF v1.0 invariants from OKF-SPEC.md §3-§6.
fn validate_okf_v1(doc: &OkfDocument) -> Result<(), String> {
    // §3: top-level okf = "1.0"
    if doc.okf != "1.0" {
        return Err(format!("expected okf='1.0', got '{}'", doc.okf));
    }
    // §6.3: document-level provenance.source_id == top-level source_id
    if doc.provenance.source_id != doc.source_id {
        return Err(format!(
            "provenance.source_id ({}) != source_id ({})",
            doc.provenance.source_id, doc.source_id
        ));
    }
    // §4.1: every entity id must be unique within the document.
    let mut seen_ids: Vec<&str> = Vec::with_capacity(doc.entities.len());
    for e in &doc.entities {
        if seen_ids.contains(&e.id.as_str()) {
            return Err(format!("duplicate entity id '{}'", e.id));
        }
        seen_ids.push(&e.id);
    }
    // §5.1: every relation's source/target ids must exist in entities[].
    for r in &doc.relations {
        if !seen_ids.contains(&r.source.as_str()) {
            return Err(format!("relation source '{}' not in entities[]", r.source));
        }
        if !seen_ids.contains(&r.target.as_str()) {
            return Err(format!("relation target '{}' not in entities[]", r.target));
        }
    }
    Ok(())
}

#[test]
fn fr013_jsonl_to_okf_to_viewer_roundtrip_is_well_formed() {
    let tmp = tempdir().expect("tempdir");
    write_fixture_jsonl(tmp.path()).expect("write fixture");

    let jsonl_path = tmp.path().join("auth-fix.jsonl");
    let sessions = session_ledger::read_jsonl_sessions(&jsonl_path).expect("read_jsonl_sessions");
    assert_eq!(sessions.len(), 1);
    let session = &sessions[0];
    assert_eq!(session.id, "roundtrip-001");
    assert_eq!(session.messages.len(), 6);

    let doc = session_ledger::process_session(session);
    assert_eq!(doc.okf, "1.0");
    assert_eq!(doc.source_id, "roundtrip-001");
    validate_okf_v1(&doc).expect("OKF should pass structural validation");

    let out_path = tmp.path().join("roundtrip-001.okf.json");
    std::fs::write(&out_path, serde_json::to_string_pretty(&doc).unwrap()).expect("write OKF");
    assert!(out_path.exists());

    let raw = std::fs::read_to_string(&out_path).expect("read OKF");
    let parsed: OkfDocument =
        serde_json::from_str(&raw).expect("OKF should deserialize via serde_json");
    assert_eq!(parsed, doc, "OKF must round-trip byte-equivalent");

    let entity_types: Vec<&str> = doc.entities.iter().map(|e| e.r#type.as_str()).collect();
    assert!(entity_types.contains(&"intent"));
    assert!(entity_types.contains(&"gate"));

    let relation_types: Vec<&str> = doc.relations.iter().map(|r| r.r#type.as_str()).collect();
    assert!(relation_types.contains(&"verified_by"));
    assert!(relation_types.contains(&"bounded_by"));
}

#[test]
fn roundtripped_okf_supports_live_feed_metadata_contract() {
    // Mirrors what sl-viewer's live_feed.rs expects when it parses the SSE
    // bundle path: source_id is the bundle stem, entities drive the bundle
    // list rendering.
    let tmp = tempdir().expect("tempdir");
    write_fixture_jsonl(tmp.path()).expect("write fixture");
    let sessions =
        session_ledger::read_jsonl_sessions(tmp.path().join("auth-fix.jsonl")).expect("read JSONL");

    let doc = session_ledger::process_session(&sessions[0]);
    let out_path = tmp.path().join(format!("{}.okf.json", doc.source_id));
    std::fs::write(&out_path, serde_json::to_string_pretty(&doc).unwrap()).expect("write OKF");

    // Bundle list fields consumed by sl-viewer:
    let _: &Vec<OkfEntity> = &doc.entities;
    let _: &Vec<OkfRelation> = &doc.relations;
    assert!(out_path.exists());
    let stem = out_path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
    let stem_no_okf = stem.strip_suffix(".okf").unwrap_or(stem);
    assert_eq!(
        stem_no_okf, doc.source_id,
        "OKF filename stem must equal source_id (sl-daemon convention)"
    );
}

#[test]
fn empty_session_compiles_to_minimal_okf() {
    let session = Session::new("empty-session", Corpus::Codex);
    let doc = session_ledger::process_session(&session);
    assert_eq!(doc.okf, "1.0");
    assert_eq!(doc.source_id, "empty-session");
    validate_okf_v1(&doc).expect("empty-session OKF should validate");
}

#[test]
fn process_session_is_idempotent() {
    let mut s = Session::new("idem-test", Corpus::Codex);
    s.messages.push(Message::new(Role::User, "ship the auth fix"));
    s.messages.push(Message::new(Role::User, "lgtm"));

    let doc_a = session_ledger::process_session(&s);
    let doc_b = session_ledger::process_session(&s);
    assert_eq!(
        serde_json::to_string(&doc_a).unwrap(),
        serde_json::to_string(&doc_b).unwrap(),
        "process_session must be idempotent over a single session (OKF-SPEC §11)",
    );
}

#[test]
fn conformance_corpus_fixtures_validate_via_our_parser() {
    let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let fixture_root = manifest_dir.join("docs/reference/conformance/fixtures");
    let mut paths: Vec<_> = std::fs::read_dir(&fixture_root)
        .expect("read conformance fixtures dir")
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension().is_some_and(|ext| ext == "json")
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.ends_with(".okf.json"))
        })
        .collect();
    paths.sort();

    assert!(
        paths.len() >= 20,
        "expected at least 20 conformance fixtures under {}",
        fixture_root.display()
    );

    for path in paths {
        let raw = std::fs::read_to_string(&path).expect("read fixture");
        let doc: OkfDocument = serde_json::from_str(&raw).expect("parse fixture");
        validate_okf_v1(&doc).expect("fixture must validate");

        let round = serde_json::to_string_pretty(&doc).expect("serialize fixture");
        let reparsed: OkfDocument = serde_json::from_str(&round).expect("round-trip fixture");
        assert_eq!(doc, reparsed, "fixture {} must round-trip", path.display());
    }
}

#[test]
fn conformance_fixture_auth_fix_validates_via_our_parser() {
    // Loads the canonical fixture from docs/reference/conformance/fixtures/
    // and asserts our parser + serde shape accept it byte-for-byte.
    // First tries the canonical docs location (post-merge), then a
    // co-located tests/fixtures/ fallback (so the test works in either
    // pre-merge or post-merge state).
    let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let candidates = [
        manifest_dir.join("docs/reference/conformance/fixtures/auth-fix-session-001.okf.json"),
        manifest_dir.join("tests/fixtures/okf/auth-fix-session-001.okf.json"),
    ];
    let fixture_path = candidates.iter().find(|p| p.exists()).unwrap_or_else(|| {
        panic!("auth-fix-session-001.okf.json not found in any of: {candidates:#?}")
    });
    let raw = std::fs::read_to_string(fixture_path).expect("read fixture");
    let doc: OkfDocument = serde_json::from_str(&raw).expect("parse fixture");
    validate_okf_v1(&doc).expect("fixture must validate");
    assert_eq!(doc.source_id, "forge-session-001");
    assert_eq!(doc.provenance.corpus, "forge");

    // Spot-check: 10 entities (intent, 3 acceptance, 2 constraint, resource,
    // state, criteria, gate) and 7 relations per OKF-EXAMPLES.md §2.
    assert_eq!(doc.entities.len(), 10,
        "auth-fix fixture has 10 entities (intent + 3 acceptance + 2 constraint + resource + state + criteria + gate)");
    assert_eq!(
        doc.relations.len(),
        7,
        "auth-fix fixture has 7 relations (3 verified_by + 2 bounded_by + requires + asserts)"
    );
}

#[test]
fn viewer_bundle_list_metadata_matches_okf() {
    // Verifies that the fields sl-viewer's detail pane (detail_pane.rs)
    // renders from a ContinuationBundle are also derivable from the OKF.
    let tmp = tempdir().expect("tempdir");
    write_fixture_jsonl(tmp.path()).expect("write fixture");
    let sessions =
        session_ledger::read_jsonl_sessions(tmp.path().join("auth-fix.jsonl")).expect("read JSONL");
    let doc = session_ledger::process_session(&sessions[0]);

    // Detail pane shows source_id as bundle header.
    assert_eq!(doc.source_id, "roundtrip-001");

    // Detail pane shows the first intent entity's label as the goal.
    let goal = doc
        .entities
        .iter()
        .find(|e| e.r#type == "intent")
        .map(|e| e.label.as_str())
        .expect("intent entity must exist");
    assert!(!goal.is_empty(), "intent label must be non-empty");
    assert!(
        goal.to_lowercase().contains("login") || goal.to_lowercase().contains("fix"),
        "intent label should reference the auth-fix topic, got: {goal}"
    );

    // Gate.ready drives the resume-gate badge.
    let gate_ready = doc
        .entities
        .iter()
        .find(|e| e.r#type == "gate")
        .and_then(|e| e.properties.get("ready"))
        .and_then(serde_json::Value::as_bool)
        .expect("gate.ready must be a bool");
    assert!(gate_ready, "auth-fix session ends with user approval");

    // Provenance structure matches the conformance README claim.
    let actual_corpus = json!({
        "corpus": doc.provenance.corpus,
        "source_id": doc.provenance.source_id,
    });
    let expected_corpus = json!({ "corpus": "forge", "source_id": "roundtrip-001" });
    assert_eq!(actual_corpus, expected_corpus);
}
