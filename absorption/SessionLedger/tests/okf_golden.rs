//! Golden OKF snapshots for T-037 / FR-013.
//!
//! These cases lock the complete deterministic `Session` -> `OkfDocument`
//! contract. Set `UPDATE_OKF_GOLDENS=1` when intentionally accepting an OKF
//! schema or distillation change.

use std::path::{Path, PathBuf};

use session_ledger::domain::session::{Corpus, Message, Role, Session};

fn fixture_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/okf")
        .join(format!("golden-{name}.okf.json"))
}

fn assert_golden(name: &str, session: &Session) {
    let actual = serde_json::to_value(session_ledger::process_session(session))
        .expect("serialize generated OKF");
    let path = fixture_path(name);

    if std::env::var("UPDATE_OKF_GOLDENS").as_deref() == Ok("1") {
        let mut rendered = serde_json::to_string_pretty(&actual).expect("render generated OKF");
        rendered.push('\n');
        std::fs::write(&path, rendered).expect("update OKF golden");
        return;
    }

    let expected_raw = std::fs::read_to_string(&path).expect("read OKF golden");
    let expected: serde_json::Value =
        serde_json::from_str(&expected_raw).expect("parse OKF golden");
    assert_eq!(
        actual,
        expected,
        "generated OKF differs from {}; review the contract change and rerun with \
         UPDATE_OKF_GOLDENS=1 if intentional",
        path.display()
    );
}

#[test]
fn empty_session_matches_golden() {
    let session = Session::new("golden-empty", Corpus::Codex);

    assert_golden("empty", &session);
}

#[test]
fn minimal_intent_matches_golden() {
    let mut session = Session::new("golden-minimal", Corpus::Cursor);
    session.messages.push(Message::new(Role::User, "Add dark mode to the dashboard"));

    assert_golden("minimal", &session);
}

#[test]
fn rich_auth_contract_matches_golden() {
    let mut session = Session::new("golden-auth", Corpus::Forge);
    session.cwd = Some("/workspace/auth-service".into());
    session.title = Some("Login timeout regression".into());
    session.messages = vec![
        Message::new(
            Role::User,
            "Fix the login timeout in src/auth/session.rs but don't change the public API.",
        ),
        Message::new(
            Role::Assistant,
            "I decided to preserve Session::new and updated src/auth/session.rs.",
        ),
        Message::new(Role::User, "Looks good; run cargo test and verify that MFA still works."),
    ];

    assert_golden("auth", &session);
}

#[test]
fn claude_code_tool_assisted_change_matches_golden() {
    let mut session = Session::new("golden-claude-tool", Corpus::ClaudeCode);
    session.cwd = Some("/workspace/payments".into());
    session.title = Some("Webhook retry hardening".into());
    session.messages = vec![
        Message::new(
            Role::User,
            "Add bounded webhook retries in src/webhooks.rs; do not change the event schema.",
        ),
        Message::new(Role::Assistant, "I will inspect the retry path and preserve compatibility."),
        Message::new(Role::Tool, "cargo test webhooks: 18 passed"),
        Message::new(
            Role::User,
            "Tests pass. Verify duplicate events remain idempotent, then ship it.",
        ),
    ];

    assert_golden("claude-tool", &session);
}

#[test]
fn factory_droid_delegated_refactor_matches_golden() {
    let mut session = Session::new("golden-factory-droid", Corpus::FactoryDroid);
    session.cwd = Some("C:\\work\\ledger".into());
    session.title = Some("Parser allocation cleanup".into());
    session.messages = vec![
        Message::new(
            Role::User,
            "Refactor src/parser.rs to reduce allocations, but preserve parse_record behavior.",
        ),
        Message::new(Role::Subagent, "Measured the hot loop and proposed borrowing input slices."),
        Message::new(
            Role::Assistant,
            "Applied the borrowing refactor without changing parse_record.",
        ),
        Message::new(Role::User, "Looks good; cargo test passes and the benchmark improved."),
    ];

    assert_golden("factory-droid", &session);
}
