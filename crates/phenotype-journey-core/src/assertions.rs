//! Ground-truth assertions applied to journey keyframes via OCR.
//!
//! The assertion layer shells out to `tesseract` for OCR (or a command
//! overridden via `PHENOTYPE_JOURNEY_OCR_CMD` for tests). Each step with
//! assertions is evaluated; the overall journey passes only when no
//! violations are produced. The layer intentionally fails loudly when
//! `tesseract` is not installed — silent skip is not allowed.

use crate::{JourneyError, Manifest, Step};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// Kind of assertion that failed.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, PartialEq, Eq)]
pub enum ViolationKind {
    MustContain,
    MustContainRegex,
    MustNotContain,
    ExitCode,
    InvalidRegex,
}

/// A single assertion violation.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, PartialEq, Eq)]
pub struct Violation {
    pub step_index: u32,
    pub kind: ViolationKind,
    pub expected: String,
    pub got_snippet: String,
}

/// Aggregate per-journey assertion result.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct AssertionReport {
    pub journey_id: String,
    pub violations: Vec<Violation>,
    pub passed: bool,
    /// True when the journey's manifest had zero steps with assertions.
    pub no_assertions: bool,
}

/// Environment variable that overrides the OCR command. The override is
/// expected to be a shell command that takes a PNG path as its final
/// positional argument and prints extracted text to stdout.
///
/// Example (test harness):
///     PHENOTYPE_JOURNEY_OCR_CMD="cat {{PATH}}"
///
/// The literal `{{PATH}}` substring is replaced with the keyframe path; if
/// absent, the path is appended as the last arg.
pub const OCR_CMD_ENV: &str = "PHENOTYPE_JOURNEY_OCR_CMD";

/// Environment variable selecting the OCR backend. Recognised values:
///
/// * `tesseract` (default) — shell out to `tesseract` (or honour
///   [`OCR_CMD_ENV`] if set).
/// * `vision` — Apple Vision `VNRecognizeTextRequest` (macOS only, requires
///   the `vision` cargo feature). Fails loudly when the feature is not
///   compiled in or the host is not macOS.
pub const OCR_BACKEND_ENV: &str = "PHENOTYPE_JOURNEY_OCR_BACKEND";

/// Run all assertions for a manifest.
///
/// * `manifest_path` – path to the `manifest.json` (used only to derive the
///   journey id — the manifest content is read separately so callers can also
///   pass an already-materialised [`Manifest`] via [`run_on_manifest`]).
/// * `artefacts_root` – directory containing the `keyframes/<journey>/` tree.
pub fn run_assertions(
    manifest_path: impl AsRef<Path>,
    artefacts_root: impl AsRef<Path>,
) -> Result<AssertionReport, JourneyError> {
    let raw = std::fs::read_to_string(manifest_path.as_ref())?;
    let manifest: Manifest = serde_json::from_str(&raw)?;
    run_on_manifest(&manifest, artefacts_root)
}

/// In-memory variant: evaluate an already-parsed manifest.
pub fn run_on_manifest(
    manifest: &Manifest,
    artefacts_root: impl AsRef<Path>,
) -> Result<AssertionReport, JourneyError> {
    let artefacts_root = artefacts_root.as_ref();
    let mut violations: Vec<Violation> = Vec::new();
    let steps_with_assertions: Vec<&Step> = manifest
        .steps
        .iter()
        .filter(|s| s.assertions.as_ref().is_some_and(|a| !a.is_empty()))
        .collect();
    let no_assertions = steps_with_assertions.is_empty();

    for step in &steps_with_assertions {
        let a = step.assertions.as_ref().expect("filtered");
        if !a.must_contain.is_empty()
            || !a.must_contain_regex.is_empty()
            || !a.must_not_contain.is_empty()
        {
            let frame_path = keyframe_path(artefacts_root, &manifest.id, step);
            let text = ocr_text(&frame_path)?;
            for needle in &a.must_contain {
                if !text.contains(needle) {
                    violations.push(Violation {
                        step_index: step.index,
                        kind: ViolationKind::MustContain,
                        expected: needle.clone(),
                        got_snippet: snippet(&text, 160),
                    });
                }
            }
            for pattern in &a.must_contain_regex {
                match regex::Regex::new(pattern) {
                    Ok(re) => {
                        if !re.is_match(&text) {
                            violations.push(Violation {
                                step_index: step.index,
                                kind: ViolationKind::MustContainRegex,
                                expected: pattern.clone(),
                                got_snippet: snippet(&text, 160),
                            });
                        }
                    }
                    Err(e) => {
                        violations.push(Violation {
                            step_index: step.index,
                            kind: ViolationKind::InvalidRegex,
                            expected: pattern.clone(),
                            got_snippet: format!("invalid regex: {e}"),
                        });
                    }
                }
            }
            for needle in &a.must_not_contain {
                if text.contains(needle) {
                    violations.push(Violation {
                        step_index: step.index,
                        kind: ViolationKind::MustNotContain,
                        expected: needle.clone(),
                        got_snippet: find_snippet(&text, needle, 80),
                    });
                }
            }
        }
    }

    // Exit-code sentinel: if ANY step declares `expected_exit`, OCR the LAST
    // keyframe of the journey and look for `__EXIT_<N>__`.
    //
    // OCR-tolerance: both Tesseract and Apple Vision mangle pairs of leading /
    // trailing underscores (collapsing `__` → `_` or dropping one side), so we
    // accept any of the canonical sentinel, a single-underscore variant, or
    // the bare `EXIT N` form. The shell still emits the canonical string; we
    // only loosen the *recogniser*, not the producer.
    let last_exit: Option<(u32, i32)> = manifest.steps.iter().find_map(|s| {
        s.assertions
            .as_ref()
            .and_then(|a| a.expected_exit)
            .map(|e| (s.index, e))
    });
    if let Some((step_index, expected)) = last_exit {
        if let Some(last) = manifest.steps.last() {
            let frame_path = keyframe_path(artefacts_root, &manifest.id, last);
            let text = ocr_text(&frame_path)?;
            let canonical = format!("__EXIT_{}__", expected);
            let tolerant_variants = [
                canonical.clone(),
                format!("_EXIT_{}_", expected),
                format!("EXIT_{}_", expected),
                format!("_EXIT_{}", expected),
                format!("EXIT {}", expected),
                format!("EXIT_{}", expected),
            ];
            let matched = tolerant_variants.iter().any(|v| text.contains(v));
            if !matched {
                violations.push(Violation {
                    step_index,
                    kind: ViolationKind::ExitCode,
                    expected: canonical,
                    got_snippet: snippet(&text, 160),
                });
            }
        }
    }

    let passed = violations.is_empty();
    Ok(AssertionReport {
        journey_id: manifest.id.clone(),
        violations,
        passed,
        no_assertions,
    })
}

fn keyframe_path(artefacts_root: &Path, journey_id: &str, step: &Step) -> PathBuf {
    // Convention: <artefacts_root>/keyframes/<journey_id>/<screenshot_path>
    // `screenshot_path` is typically a bare filename like `frame-003.png`.
    artefacts_root
        .join("keyframes")
        .join(journey_id)
        .join(&step.screenshot_path)
}

fn snippet(text: &str, max: usize) -> String {
    let collapsed: String = text
        .chars()
        .map(|c| if c == '\n' { ' ' } else { c })
        .collect();
    if collapsed.chars().count() <= max {
        collapsed
    } else {
        let truncated: String = collapsed.chars().take(max).collect();
        format!("{truncated}…")
    }
}

fn find_snippet(text: &str, needle: &str, pad: usize) -> String {
    if let Some(idx) = text.find(needle) {
        let start = floor_char_boundary(text, idx.saturating_sub(pad));
        let end = ceil_char_boundary(text, (idx + needle.len() + pad).min(text.len()));
        text[start..end].replace('\n', " ")
    } else {
        snippet(text, 160)
    }
}

fn floor_char_boundary(s: &str, mut idx: usize) -> usize {
    while idx > 0 && !s.is_char_boundary(idx) {
        idx -= 1;
    }
    idx
}

fn ceil_char_boundary(s: &str, mut idx: usize) -> usize {
    while idx < s.len() && !s.is_char_boundary(idx) {
        idx += 1;
    }
    idx
}

/// Invoke the OCR command on a single PNG and return the decoded text.
///
/// Resolution order:
/// 1. `PHENOTYPE_JOURNEY_OCR_CMD` env override (used by tests + custom pipelines).
/// 2. `PHENOTYPE_JOURNEY_OCR_BACKEND=vision` — Apple Vision `VNRecognizeTextRequest`
///    (macOS only; requires the `vision` cargo feature). Fails loudly when
///    the backend is unavailable — no silent fallback.
/// 3. `tesseract <path> -` (default).
///
/// Returns [`JourneyError::Ocr`] when the backend is missing or exits non-zero.
pub fn ocr_text(frame_path: &Path) -> Result<String, JourneyError> {
    if let Ok(cmd) = std::env::var(OCR_CMD_ENV) {
        return run_override(&cmd, frame_path);
    }
    if let Ok(backend) = std::env::var(OCR_BACKEND_ENV) {
        match backend.as_str() {
            "vision" => return run_vision(frame_path),
            "tesseract" | "" => {}
            other => {
                return Err(JourneyError::Ocr(format!(
                    "unknown {OCR_BACKEND_ENV}={other}; expected `tesseract` or `vision`"
                )));
            }
        }
    }
    run_tesseract(frame_path)
}

#[cfg(all(feature = "vision", target_os = "macos"))]
fn run_vision(frame_path: &Path) -> Result<String, JourneyError> {
    crate::vision::ocr_vision(frame_path)
}

#[cfg(not(all(feature = "vision", target_os = "macos")))]
fn run_vision(_frame_path: &Path) -> Result<String, JourneyError> {
    Err(JourneyError::Ocr(format!(
        "{OCR_BACKEND_ENV}=vision requires the `vision` cargo feature on a macOS host; \
         rebuild with `--features vision` on macOS or unset the env var."
    )))
}

fn run_tesseract(frame_path: &Path) -> Result<String, JourneyError> {
    let output = std::process::Command::new("tesseract")
        .arg(frame_path)
        .arg("-")
        .output()
        .map_err(|e| {
            JourneyError::Ocr(format!(
                "`tesseract` invocation failed ({e}). Install tesseract (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian) or override with {OCR_CMD_ENV}."
            ))
        })?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(JourneyError::Ocr(format!(
            "tesseract exited non-zero on {}: {stderr}",
            frame_path.display()
        )));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

fn run_override(cmd: &str, frame_path: &Path) -> Result<String, JourneyError> {
    let path_str = frame_path.to_string_lossy().into_owned();
    let expanded = if cmd.contains("{{PATH}}") {
        cmd.replace("{{PATH}}", &path_str)
    } else {
        format!("{cmd} {}", shell_escape(&path_str))
    };
    let output = std::process::Command::new("sh")
        .arg("-c")
        .arg(&expanded)
        .output()
        .map_err(|e| JourneyError::Ocr(format!("override command failed: {e}")))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(JourneyError::Ocr(format!(
            "override command exited non-zero: {stderr}"
        )));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

fn shell_escape(s: &str) -> String {
    if s.chars()
        .all(|c| c.is_ascii_alphanumeric() || "/._-+:=".contains(c))
    {
        s.to_string()
    } else {
        format!("'{}'", s.replace('\'', "'\\''"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Step, StepAssertions};
    use serial_test::serial;
    use std::io::Write;

    fn write_fixture(dir: &Path, journey: &str, file: &str, content: &str) -> PathBuf {
        let kf_dir = dir.join("keyframes").join(journey);
        std::fs::create_dir_all(&kf_dir).unwrap();
        let path = kf_dir.join(file);
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(content.as_bytes()).unwrap();
        path
    }

    fn mk_manifest(id: &str, steps: Vec<Step>) -> Manifest {
        Manifest {
            id: id.into(),
            intent: "test".into(),
            recording: None,
            recording_gif: None,
            keyframe_count: steps.len() as u32,
            passed: true,
            steps,
            verification: None,
        }
    }

    fn step(index: u32, file: &str, a: StepAssertions) -> Step {
        Step {
            index,
            slug: format!("frame-{index}"),
            intent: "s".into(),
            screenshot_path: file.into(),
            description: None,
            blind_description: None,
            judge_score: None,
            assertions: Some(a),
            annotations: None,
            agreement: None,
        }
    }

    #[test]
    #[serial]
    fn must_contain_violation() {
        let tmp = tempdir_abs();
        write_fixture(&tmp, "j", "frame-001.png", "hello world");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![step(
                0,
                "frame-001.png",
                StepAssertions {
                    must_contain: vec!["nope".into()],
                    ..Default::default()
                },
            )],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(!r.passed);
        assert_eq!(r.violations.len(), 1);
        assert_eq!(r.violations[0].kind, ViolationKind::MustContain);
        assert_eq!(r.violations[0].expected, "nope");
    }

    #[test]
    #[serial]
    fn must_not_contain_violation() {
        let tmp = tempdir_abs();
        write_fixture(&tmp, "j", "frame-001.png", "error: unexpected argument");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![step(
                0,
                "frame-001.png",
                StepAssertions {
                    must_not_contain: vec!["error:".into()],
                    ..Default::default()
                },
            )],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(!r.passed);
        assert_eq!(r.violations[0].kind, ViolationKind::MustNotContain);
    }

    #[test]
    #[serial]
    fn exit_code_violation() {
        let tmp = tempdir_abs();
        // Last frame lacks the sentinel.
        write_fixture(&tmp, "j", "frame-001.png", "intro");
        write_fixture(&tmp, "j", "frame-002.png", "no sentinel here");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![
                step(0, "frame-001.png", StepAssertions::default()),
                step(
                    1,
                    "frame-002.png",
                    StepAssertions {
                        expected_exit: Some(0),
                        ..Default::default()
                    },
                ),
            ],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(!r.passed);
        assert_eq!(r.violations[0].kind, ViolationKind::ExitCode);
        assert_eq!(r.violations[0].expected, "__EXIT_0__");
    }

    #[test]
    #[serial]
    fn exit_code_passes_when_sentinel_present() {
        let tmp = tempdir_abs();
        write_fixture(&tmp, "j", "frame-001.png", "final line __EXIT_0__ ok");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![step(
                0,
                "frame-001.png",
                StepAssertions {
                    expected_exit: Some(0),
                    ..Default::default()
                },
            )],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(r.passed, "violations: {:?}", r.violations);
    }

    #[test]
    #[serial]
    fn must_contain_regex_matches() {
        let tmp = tempdir_abs();
        // Simulates OCR-mangled `__EXIT_1__` as `-EXIT_1__`.
        write_fixture(&tmp, "j", "frame-001.png", "final line -EXIT_1__ done");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![step(
                0,
                "frame-001.png",
                StepAssertions {
                    must_contain_regex: vec![r"EXIT[_ ]?[0-9O@]".into()],
                    ..Default::default()
                },
            )],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(r.passed, "violations: {:?}", r.violations);
    }

    #[test]
    #[serial]
    fn must_contain_regex_violation_and_invalid() {
        let tmp = tempdir_abs();
        write_fixture(&tmp, "j", "frame-001.png", "plain text with no digits");
        std::env::set_var(OCR_CMD_ENV, "cat {{PATH}}");
        let m = mk_manifest(
            "j",
            vec![step(
                0,
                "frame-001.png",
                StepAssertions {
                    must_contain_regex: vec![
                        r"EXIT[_ ]?\d".into(),  // non-matching
                        "(unterminated".into(), // invalid regex
                    ],
                    ..Default::default()
                },
            )],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        std::env::remove_var(OCR_CMD_ENV);
        assert!(!r.passed);
        assert_eq!(r.violations.len(), 2);
        let kinds: Vec<_> = r.violations.iter().map(|v| &v.kind).collect();
        assert!(kinds.contains(&&ViolationKind::MustContainRegex));
        assert!(kinds.contains(&&ViolationKind::InvalidRegex));
    }

    #[test]
    fn no_assertions_flag() {
        let tmp = tempdir_abs();
        write_fixture(&tmp, "j", "frame-001.png", "hi");
        let m = mk_manifest(
            "j",
            vec![Step {
                index: 0,
                slug: "frame-0".into(),
                intent: "i".into(),
                screenshot_path: "frame-001.png".into(),
                description: None,
                blind_description: None,
                judge_score: None,
                assertions: None,
                annotations: None,
                agreement: None,
            }],
        );
        let r = run_on_manifest(&m, &tmp).unwrap();
        assert!(r.passed);
        assert!(r.no_assertions);
    }

    fn tempdir_abs() -> PathBuf {
        let base = std::env::temp_dir().join(format!(
            "phenotype-journey-test-{}-{}",
            std::process::id(),
            rand_suffix()
        ));
        std::fs::create_dir_all(&base).unwrap();
        base
    }

    fn rand_suffix() -> String {
        use std::time::{SystemTime, UNIX_EPOCH};
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos().to_string())
            .unwrap_or_else(|_| "x".into())
    }
}
