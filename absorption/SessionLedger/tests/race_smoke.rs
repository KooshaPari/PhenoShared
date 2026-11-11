//! Threaded smoke tests for deterministic merge, dedup, and OKF output.
//!
//! Companion: `tests/race_model.rs` covers bounded channel + cancel
//! conservation (loom-lite). Both run under `.github/workflows/race-smoke.yml`.

use std::sync::{Arc, Barrier};
use std::thread;

use session_ledger::{process_session, Corpus, MergeExecutor, Message, Role, Session};

const TOPIC: &str = "race-smoke";
const WORKERS: usize = 8;
const ROUNDS: usize = 32;

fn message(role: Role, content: &str, ts_ms: i64) -> Message {
    let mut message = Message::new(role, content);
    message.ts_ms = Some(ts_ms);
    message
}

fn session(id: &str, corpus: Corpus, messages: Vec<Message>) -> Session {
    let mut session = Session::new(id, corpus);
    session.cwd = Some("/workspace/session-ledger".to_owned());
    session.messages = messages;
    session
}

fn race_sessions() -> Vec<Session> {
    vec![
        session(
            "alpha",
            Corpus::Forge,
            vec![
                message(Role::User, "Implement deterministic merge", 10),
                message(Role::Assistant, "Sorting by canonical members", 30),
            ],
        ),
        session(
            "beta",
            Corpus::Cursor,
            vec![
                message(Role::User, "Check duplicate recovery", 20),
                message(Role::Tool, "cargo test --test properties", 40),
            ],
        ),
        session(
            "gamma",
            Corpus::Codex,
            vec![
                message(Role::User, "Looks good, tests pass", 50),
                message(Role::Assistant, "Ready for CI", 60),
            ],
        ),
    ]
}

#[test]
fn concurrent_merge_and_okf_outputs_are_deterministic() {
    let sessions = Arc::new(race_sessions());
    let expected_merge =
        MergeExecutor::default().merge(&sessions, TOPIC).expect("baseline merge should succeed");
    let expected_okf = process_session(&expected_merge.session);
    let start = Arc::new(Barrier::new(WORKERS));

    let handles = (0..WORKERS)
        .map(|worker_index| {
            let sessions = Arc::clone(&sessions);
            let start = Arc::clone(&start);
            thread::spawn(move || {
                start.wait();
                let mut observed = Vec::with_capacity(ROUNDS);

                for round in 0..ROUNDS {
                    let mut input = sessions.as_ref().clone();
                    let len = input.len();
                    input.rotate_left((worker_index + round) % len);
                    if round % 2 == 0 {
                        input.push(input[0].clone());
                    }
                    if round % 3 == 0 {
                        input.reverse();
                    }

                    let merged = MergeExecutor::default()
                        .merge(&input, TOPIC)
                        .expect("same-scope sessions should merge from every worker");
                    let okf = process_session(&merged.session);
                    observed.push((merged, okf));
                }

                observed
            })
        })
        .collect::<Vec<_>>();

    for handle in handles {
        let observations = handle.join().expect("race worker should not panic");
        for (merged, okf) in observations {
            assert_eq!(merged, expected_merge);
            assert_eq!(okf, expected_okf);
        }
    }
}
