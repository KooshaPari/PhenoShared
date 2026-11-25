//! Merge / lost-work recovery acceptance (FR-011).
//!
//! Traceability: localizes unfinished work after merge — maps to FR-011 crash
//! recovery / unfinished-work surface (also T-035 / T-024).

use session_ledger::{
    distill, Corpus, LostWorkLocalizer, MergeExecutor, Message, Role, Session, UnfinishedReason,
};

fn scoped_session(id: &str, corpus: Corpus, messages: &[(Role, &str, i64)]) -> Session {
    let mut session = Session::new(id, corpus);
    session.cwd = Some("/workspace/session-ledger".into());
    session.messages = messages
        .iter()
        .map(|(role, content, ts_ms)| {
            let mut message = Message::new(*role, *content);
            message.ts_ms = Some(*ts_ms);
            message
        })
        .collect();
    session
}

#[test]
fn fr011_merged_scope_localizes_unfinished_work_from_one_of_many_sessions() {
    let completed_one = scoped_session(
        "session-a",
        Corpus::Forge,
        &[(Role::User, "Add the merge API", 10), (Role::Assistant, "Done", 20)],
    );
    let crashed = scoped_session(
        "session-b",
        Corpus::Cursor,
        &[
            (Role::User, "Run the recovery migration", 30),
            (Role::Assistant, "Starting the migration", 40),
            (Role::Tool, "process terminated", 50),
        ],
    );
    let completed_two = scoped_session(
        "session-c",
        Corpus::Codex,
        &[(Role::User, "Document the result", 60), (Role::Assistant, "Status: completed", 70)],
    );
    let sessions = [completed_two, crashed, completed_one];

    let merged = MergeExecutor::default()
        .merge(&sessions, "dedup-recovery")
        .expect("same-scope sessions should merge");
    assert_eq!(merged.manifest.sessions.len(), 3);
    assert_eq!(merged.session.messages.len(), 7);
    assert_eq!(merged.session.messages[0].ts_ms, Some(10));
    assert_eq!(merged.session.messages[6].ts_ms, Some(70));

    let localized_sessions = LostWorkLocalizer::from_sessions(&sessions);
    assert_eq!(localized_sessions.len(), 1);
    assert_eq!(localized_sessions[0].session_id, "session-b");
    assert_eq!(localized_sessions[0].reason, UnfinishedReason::InterruptedExecution);
    assert_eq!(localized_sessions[0].summary, "Run the recovery migration");

    let bundles = sessions.iter().map(distill::compile).collect::<Vec<_>>();
    let localized_bundles =
        LostWorkLocalizer::from_bundles(&bundles).expect("compiled worklogs should localize");
    assert_eq!(localized_bundles, localized_sessions);
}
