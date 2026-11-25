#![no_main]

use libfuzzer_sys::fuzz_target;
use session_ledger::{parse_jsonl_sessions, Session};

fuzz_target!(|input: &[u8]| {
    let Ok(sessions) = parse_jsonl_sessions(input) else {
        return;
    };

    // Successful parses must be stable under JSONL re-encode → re-parse.
    let mut encoded = String::new();
    for session in &sessions {
        encoded.push_str(&serde_json::to_string(session).expect("session serializes"));
        encoded.push('\n');
    }
    let reparsed = parse_jsonl_sessions(encoded.as_bytes()).expect("roundtrip JSONL parses");
    assert_eq!(sessions, reparsed);

    for session in sessions {
        let bytes = serde_json::to_vec(&session).expect("session serializes");
        let again: Session = serde_json::from_slice(&bytes).expect("session deserializes");
        assert_eq!(session, again);
    }
});
