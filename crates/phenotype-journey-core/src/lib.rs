//! # phenotype-journey-core
//!
//! Shared types and verification logic for Phenotype journey manifests.
//!
//! A *journey* is a recorded (CLI tape, UI test, or Playwright trace) sequence
//! of intents that prove a user-facing capability works. Manifests describe
//! the recording plus per-step intent/screenshot pairs, and are optionally
//! verified by a Claude-describe + Claude-judge loop.

pub mod agreement;
pub mod assertions;
pub mod pipeline;
pub mod verify;
#[cfg(all(feature = "vision", target_os = "macos"))]
pub mod vision;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Optional ground-truth assertions for a step.
///
/// When populated, the `phenotype-journey assert` subcommand OCRs the matching
/// keyframe and applies these constraints as hard gates. Tapes without
/// assertions still record and verify as before, but the verifier emits a
/// warning per journey that carries zero assertions.
#[derive(Debug, Clone, Default, Serialize, Deserialize, JsonSchema, PartialEq, Eq)]
pub struct StepAssertions {
    /// Substrings that MUST appear in the OCR'd frame text.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub must_contain: Vec<String>,
    /// Regular expressions that MUST match somewhere in the OCR'd frame text.
    /// Used to tolerate OCR mangling (e.g. `EXIT[_ ]?[0-9O@]` to match
    /// `__EXIT_0__`, `EXIT_O`, `-EXIT_1__`, etc.).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub must_contain_regex: Vec<String>,
    /// Substrings that MUST NOT appear in the OCR'd frame text.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub must_not_contain: Vec<String>,
    /// If set, the LAST keyframe of the journey must contain `__EXIT_<N>__`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expected_exit: Option<i32>,
    /// If true, OCR must succeed for this step; defaults to true whenever any
    /// contain/not_contain assertion is set.
    #[serde(default)]
    pub ocr_required: bool,
}

impl StepAssertions {
    pub fn is_empty(&self) -> bool {
        self.must_contain.is_empty()
            && self.must_contain_regex.is_empty()
            && self.must_not_contain.is_empty()
            && self.expected_exit.is_none()
    }
}

/// Rendering kind for an annotation.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, JsonSchema, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum AnnotationKind {
    #[default]
    Region,
    Pointer,
    Highlight,
}

/// Border style for an annotation.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, JsonSchema, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum AnnotationStyle {
    #[default]
    Solid,
    Dashed,
}

/// Bounding-box annotation overlaid onto a step's keyframe.
///
/// Coordinates are in **source image pixels** (top-left origin). The viewer
/// sets SVG `viewBox` to the image's natural dimensions so these values map
/// 1:1 and scale with the rendered image size.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, PartialEq)]
pub struct Annotation {
    /// `[x, y, width, height]` in source image pixels.
    pub bbox: [u32; 4],
    /// Short human-readable label (rendered as a pill in the lightbox).
    pub label: String,
    /// Optional color (hex, e.g. `#f38ba8`). Falls back to a Catppuccin palette.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<String>,
    /// Border style (default: solid).
    #[serde(default, skip_serializing_if = "is_default_style")]
    pub style: AnnotationStyle,
    /// Longer hover tooltip.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
    /// Annotation kind (default: region).
    #[serde(default, skip_serializing_if = "is_default_kind")]
    pub kind: AnnotationKind,
}

fn is_default_style(s: &AnnotationStyle) -> bool {
    *s == AnnotationStyle::Solid
}

fn is_default_kind(k: &AnnotationKind) -> bool {
    *k == AnnotationKind::Region
}

/// A single step (keyframe) in a journey.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct Step {
    pub index: u32,
    pub slug: String,
    pub intent: String,
    pub screenshot_path: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// Blind-describe pass output: what the Claude-describe agent saw in this
    /// keyframe WITHOUT knowing the author's intent. Rendered alongside the
    /// author intent in the docs so reviewers see both the intent and the
    /// independent observation.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub blind_description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub judge_score: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub assertions: Option<StepAssertions>,
    /// Optional bounding-box annotations (ground truth for VLM labeling +
    /// rendered as overlays in the docs lightbox).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub annotations: Option<Vec<Annotation>>,
    /// Intent ↔ blind-description agreement report, populated during
    /// `verify` and consumed by the journey viewer's status chip + diff
    /// panel (Green ≥0.6, Yellow 0.3–0.6, Red <0.3).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agreement: Option<agreement::AgreementReport>,
}

/// Verification payload added by `phenotype-journey verify`.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct Verification {
    pub overall_score: f64,
    pub describe_confidence: f64,
    pub judge_confidence: f64,
    pub all_intents_passed: bool,
    /// Either `"mock"` or `"api"` (live Anthropic call).
    pub mode: String,
    /// RFC-3339 timestamp.
    pub timestamp: String,
    /// Ground-truth assertion violations (empty when none).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub assertion_violations: Vec<assertions::Violation>,
}

/// Top-level manifest persisted as `manifest.json` / `manifest.verified.json`.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
pub struct Manifest {
    pub id: String,
    pub intent: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub recording: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub recording_gif: Option<String>,
    #[serde(default)]
    pub keyframe_count: u32,
    #[serde(default)]
    pub passed: bool,
    #[serde(default)]
    pub steps: Vec<Step>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub verification: Option<Verification>,
}

/// Mode for `verify_manifest`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerifyMode {
    /// Deterministic, offline: produces a canned high-confidence verification.
    Mock,
    /// Calls the live Anthropic API (requires the `live` feature + `ANTHROPIC_API_KEY`).
    Live,
}

#[derive(Debug, Error)]
pub enum JourneyError {
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
    #[error("schema validation failed: {0}")]
    Schema(String),
    #[error("verify backend error: {0}")]
    Backend(String),
    #[error("not configured for live mode (enable `live` feature and set ANTHROPIC_API_KEY)")]
    LiveUnavailable,
    #[error("ocr backend error: {0}")]
    Ocr(String),
}

/// Produce the canonical JSONSchema for [`Manifest`].
pub fn manifest_schema() -> serde_json::Value {
    let schema = schemars::schema_for!(Manifest);
    serde_json::to_value(schema).expect("schema serialisation cannot fail")
}

/// Validate a manifest JSON blob against the canonical schema.
pub fn validate_manifest(value: &serde_json::Value) -> Result<(), JourneyError> {
    let schema = manifest_schema();
    let validator =
        jsonschema::validator_for(&schema).map_err(|e| JourneyError::Schema(e.to_string()))?;
    let errors: Vec<String> = validator
        .iter_errors(value)
        .map(|e| e.to_string())
        .collect();
    if !errors.is_empty() {
        return Err(JourneyError::Schema(errors.join("; ")));
    }
    Ok(())
}

/// Verify a manifest on disk and return the populated [`Verification`].
///
/// In [`VerifyMode::Mock`] the returned verification is deterministic and
/// does not require network access — this mirrors the behaviour of the
/// original `verify-manifests.sh` script when `ANTHROPIC_API_KEY` is unset.
pub fn verify_manifest(
    path: impl AsRef<std::path::Path>,
    mode: VerifyMode,
) -> Result<Verification, JourneyError> {
    let raw = std::fs::read_to_string(path.as_ref())?;
    let manifest: Manifest = serde_json::from_str(&raw)?;
    verify::run(&manifest, mode)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_manifest() -> Manifest {
        Manifest {
            id: "first-plan".into(),
            intent: "Run your first plan".into(),
            recording: Some("recordings/first-plan.mp4".into()),
            recording_gif: Some("recordings/first-plan.gif".into()),
            keyframe_count: 2,
            passed: true,
            steps: vec![
                Step {
                    index: 0,
                    slug: "frame-0".into(),
                    intent: "Open CLI".into(),
                    screenshot_path: "frame-001.png".into(),
                    description: None,
                    blind_description: None,
                    judge_score: None,
                    assertions: None,
                    annotations: None,
                    agreement: None,
                },
                Step {
                    index: 1,
                    slug: "frame-1".into(),
                    intent: "See output".into(),
                    screenshot_path: "frame-002.png".into(),
                    description: None,
                    blind_description: None,
                    judge_score: None,
                    assertions: None,
                    annotations: None,
                    agreement: None,
                },
            ],
            verification: None,
        }
    }

    #[test]
    fn mock_mode_returns_all_passed() {
        let m = sample_manifest();
        let v = verify::run(&m, VerifyMode::Mock).expect("mock must succeed");
        assert_eq!(v.mode, "mock");
        assert!(v.all_intents_passed);
        assert!(v.overall_score > 0.0 && v.overall_score <= 1.0);
        assert!(!v.timestamp.is_empty());
    }

    #[test]
    fn schema_roundtrip_validates() {
        let m = sample_manifest();
        let value = serde_json::to_value(&m).unwrap();
        validate_manifest(&value).expect("sample manifest must validate");
    }

    #[test]
    fn annotations_roundtrip() {
        let a = Annotation {
            bbox: [10, 20, 100, 28],
            label: "MLA".into(),
            color: Some("#f38ba8".into()),
            style: AnnotationStyle::Dashed,
            note: Some("Multi-Head Latent Attention".into()),
            kind: AnnotationKind::Highlight,
        };
        let s = serde_json::to_string(&a).unwrap();
        let back: Annotation = serde_json::from_str(&s).unwrap();
        assert_eq!(a, back);
    }

    #[test]
    fn annotation_defaults_elided() {
        // Minimal annotation: only bbox + label; default style/kind must be skipped.
        let a = Annotation {
            bbox: [0, 0, 10, 10],
            label: "x".into(),
            color: None,
            style: AnnotationStyle::Solid,
            note: None,
            kind: AnnotationKind::Region,
        };
        let s = serde_json::to_string(&a).unwrap();
        assert!(!s.contains("style"), "default style must be skipped: {s}");
        assert!(!s.contains("kind"), "default kind must be skipped: {s}");
        let back: Annotation = serde_json::from_str(&s).unwrap();
        assert_eq!(a, back);
    }

    #[test]
    fn step_with_annotations_roundtrip() {
        let mut m = sample_manifest();
        m.steps[0].annotations = Some(vec![Annotation {
            bbox: [120, 340, 180, 28],
            label: "MLA".into(),
            color: Some("#f38ba8".into()),
            style: AnnotationStyle::Solid,
            note: None,
            kind: AnnotationKind::Region,
        }]);
        let v = serde_json::to_value(&m).unwrap();
        validate_manifest(&v).expect("schema allows annotations");
        let back: Manifest = serde_json::from_value(v).unwrap();
        assert_eq!(back.steps[0].annotations.as_ref().unwrap().len(), 1);
    }

    #[test]
    fn assertions_roundtrip() {
        let a = StepAssertions {
            must_contain: vec!["hello".into()],
            must_contain_regex: vec![r"\d+".into()],
            must_not_contain: vec!["error:".into()],
            expected_exit: Some(0),
            ocr_required: true,
        };
        let s = serde_json::to_string(&a).unwrap();
        let back: StepAssertions = serde_json::from_str(&s).unwrap();
        assert_eq!(a, back);
    }
}
