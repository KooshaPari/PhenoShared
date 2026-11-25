#![no_main]

use libfuzzer_sys::fuzz_target;
use session_ledger::OkfDocument;

fuzz_target!(|input: &[u8]| {
    let Ok(document) = serde_json::from_slice::<OkfDocument>(input) else {
        return;
    };

    let encoded = serde_json::to_vec(&document).expect("parsed OKF must serialize");
    let reparsed: OkfDocument =
        serde_json::from_slice(&encoded).expect("serialized OKF must parse");
    assert_eq!(document, reparsed);
});
