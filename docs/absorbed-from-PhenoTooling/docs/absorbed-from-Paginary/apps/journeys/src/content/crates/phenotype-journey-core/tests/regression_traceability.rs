//! Regression test for the traceability-report tape.
//!
//! The tape was silently broken: keyframe 2 showed
//! `error: unexpected argument '--markdown-out' found`, but the Claude-judge
//! still passed the manifest. This test pins the pre-fix OCR dump as a
//! fixture and proves that `run_on_manifest` — configured with the same
//! must_not_contain assertions the retrofitted YAML declares — produces a
//! `MustNotContain { expected: "error:" }` violation.
//!
//! If the assertion layer ever regresses (e.g. the OCR path breaks, or the
//! violation kinds are mis-wired), this test fails.

use phenotype_journey_core::{
    assertions::{run_on_manifest, ViolationKind, OCR_CMD_ENV},
    Manifest, Step, StepAssertions,
};
use std::path::PathBuf;

fn fixture_text() -> String {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/traceability-report-broken-ocr.txt");
    std::fs::read_to_string(p).expect("fixture must exist")
}

#[test]
fn prefix_recording_flags_error_substring() {
    // Stage the fixture as a fake keyframe. We OCR by `cat` + override env.
    let tmp = std::env::temp_dir().join(format!(
        "phenotype-journey-regression-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let kf_dir = tmp.join("keyframes").join("traceability-report");
    std::fs::create_dir_all(&kf_dir).unwrap();
    let frame_path = kf_dir.join("frame-002.png");
    std::fs::write(&frame_path, fixture_text()).unwrap();

    std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");

    let manifest = Manifest {
        id: "traceability-report".into(),
        intent: "Generate traceability markdown report".into(),
        recording: None,
        recording_gif: None,
        keyframe_count: 1,
        passed: true,
        steps: vec![Step {
            index: 2,
            slug: "frame-2".into(),
            intent: "Cargo compiles and launches the traceability tool".into(),
            screenshot_path: "frame-002.png".into(),
            description: None,
            blind_description: None,
            judge_score: None,
            assertions: Some(StepAssertions {
                must_contain: vec![],
                must_contain_regex: vec![],
                must_not_contain: vec![
                    "error:".into(),
                    "unexpected argument".into(),
                ],
                expected_exit: None,
                ocr_required: true,
            }),
            annotations: None,
            agreement: None,
        }],
        verification: None,
    };

    let report = run_on_manifest(&manifest, &tmp).unwrap();
    std::env::remove_var(OCR_CMD_ENV);

    assert!(!report.passed, "expected violations, got none");
    assert_eq!(
        report.violations.len(),
        2,
        "both error: and unexpected argument must trip: {:?}",
        report.violations
    );
    let kinds: Vec<_> = report.violations.iter().map(|v| &v.kind).collect();
    assert!(kinds.iter().all(|k| **k == ViolationKind::MustNotContain));
    let expected: Vec<&str> = report
        .violations
        .iter()
        .map(|v| v.expected.as_str())
        .collect();
    assert!(expected.contains(&"error:"));
    assert!(expected.contains(&"unexpected argument"));
}
