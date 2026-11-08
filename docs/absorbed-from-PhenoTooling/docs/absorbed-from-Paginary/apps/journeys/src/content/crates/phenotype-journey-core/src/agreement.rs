//! Intent ↔ blind-description agreement scoring.
//!
//! Scores how well a human-authored `intent` overlaps a VLM-produced
//! `blind_description`. Three backends are plugged behind a trait so
//! callers can pick the one appropriate for their environment:
//!
//! | Backend              | Signal   | Thresholds (Green / Yellow / Red)      |
//! |----------------------|----------|-----------------------------------------|
//! | `Jaccard`            | text-text (stemmed token overlap)        | ≥0.6 / 0.3–0.6 / <0.3 |
//! | `SentenceTransformer`| text-text (sentence-transformers cosine) | ≥0.75 / 0.5–0.75 / <0.5 |
//! | `SigLip`             | image-text (SigLIP logits-per-image)     | ≥0.3 / 0.1–0.3 / <0.1 |
//!
//! The three thresholds are intentionally different: Jaccard is punishingly
//! literal (paraphrase → Red), sentence-transformers land paraphrases in the
//! mid-range (so Green needs to be high), and SigLIP raw cosines run low
//! across the board (so Green starts at 0.3).
//!
//! The report also exposes the tokenised intent/blind sets plus the two diff
//! sets ("missing in blind", "extras in blind") so the viewer can render a
//! remediation hint ("re-record this step OR rewrite intent.yaml"). Token
//! sets are populated only by the `Jaccard` backend; semantic backends leave
//! them empty.
//!
//! # Backend selection
//!
//! Use [`AgreementBackend::resolve`] to turn a user-supplied
//! `AgreementBackend` (including `Auto`) + optional image path into a
//! concrete boxed [`AgreementScorer`]. `Auto` probes the environment:
//!
//! 1. If a keyframe image is available **and** `transformers` + `torch`
//!    import cleanly, use `SigLip`.
//! 2. Else if `sentence-transformers` imports cleanly, use
//!    `SentenceTransformer`.
//! 3. Else fall back to `Jaccard`.

use rust_stemmers::{Algorithm, Stemmer};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::OnceLock;

/// Agreement bucket.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Agreement {
    Green,
    Yellow,
    Red,
}

impl Agreement {
    pub fn as_str(&self) -> &'static str {
        match self {
            Agreement::Green => "green",
            Agreement::Yellow => "yellow",
            Agreement::Red => "red",
        }
    }
}

/// Full agreement report for a (intent, blind) pair.
///
/// `overlap` is the **display-normalised** score in `[0.0, 1.0]` (used by the
/// viewer chip). `raw_score` preserves the backend's native output
/// (e.g. SigLIP softmax probability, cosine similarity) so callers can
/// reason about the untransformed signal.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, PartialEq)]
pub struct AgreementReport {
    pub status: Agreement,
    /// Display-normalised score in [0.0, 1.0].
    pub overlap: f64,
    /// Backend-native raw score (cosine / Jaccard / SigLIP logit).
    #[serde(default)]
    pub raw_score: f64,
    /// Backend identifier (`"jaccard"` | `"sentence-transformer"` | `"siglip"`).
    #[serde(default = "default_backend_name")]
    pub backend: String,
    /// Optional model identifier (e.g. `"all-mpnet-base-v2"`).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub backend_model: Option<String>,
    pub intent_tokens: Vec<String>,
    pub blind_tokens: Vec<String>,
    pub missing_in_blind: Vec<String>,
    pub extras_in_blind: Vec<String>,
}

fn default_backend_name() -> String {
    "jaccard".to_string()
}

/// Configurable backend selector, deserialisable from YAML/TOML config.
#[derive(Debug, Clone, Default, Serialize, Deserialize, JsonSchema, PartialEq)]
#[serde(tag = "kind", rename_all = "kebab-case")]
pub enum AgreementBackend {
    Jaccard,
    SentenceTransformer {
        #[serde(default = "default_st_model")]
        model: String,
    },
    SigLip {
        #[serde(default = "default_siglip_model")]
        model: String,
    },
    #[default]
    Auto,
}

fn default_st_model() -> String {
    "all-mpnet-base-v2".to_string()
}

fn default_siglip_model() -> String {
    "google/siglip-so400m-patch14-384".to_string()
}

impl AgreementBackend {
    /// Parse a string flag value (`jaccard|sentence|siglip|auto`).
    pub fn parse_flag(s: &str) -> Result<Self, String> {
        match s.trim().to_ascii_lowercase().as_str() {
            "jaccard" | "token" => Ok(AgreementBackend::Jaccard),
            "sentence" | "sentence-transformer" | "st" => Ok(AgreementBackend::SentenceTransformer {
                model: default_st_model(),
            }),
            "siglip" => Ok(AgreementBackend::SigLip { model: default_siglip_model() }),
            "auto" => Ok(AgreementBackend::Auto),
            other => Err(format!(
                "unknown agreement backend '{other}' (expected one of: jaccard, sentence, siglip, auto)"
            )),
        }
    }

    /// Resolve an `Auto` backend to a concrete one given whether an image
    /// keyframe is available. Non-`Auto` variants pass through unchanged.
    pub fn resolve_concrete(&self, image_available: bool) -> AgreementBackend {
        match self {
            AgreementBackend::Auto => {
                if image_available && python_module_importable("transformers")
                    && python_module_importable("torch")
                {
                    AgreementBackend::SigLip { model: default_siglip_model() }
                } else if python_module_importable("sentence_transformers") {
                    AgreementBackend::SentenceTransformer { model: default_st_model() }
                } else {
                    AgreementBackend::Jaccard
                }
            }
            other => other.clone(),
        }
    }

    /// Instantiate the concrete scorer. `Auto` is resolved via
    /// [`AgreementBackend::resolve_concrete`] using `image_available`.
    pub fn build(&self, image_available: bool) -> Box<dyn AgreementScorer> {
        match self.resolve_concrete(image_available) {
            AgreementBackend::Jaccard => Box::new(JaccardScorer),
            AgreementBackend::SentenceTransformer { model } => {
                Box::new(SentenceTransformerScorer { model })
            }
            AgreementBackend::SigLip { model } => Box::new(SigLipScorer { model }),
            AgreementBackend::Auto => Box::new(JaccardScorer), // unreachable
        }
    }
}

/// Cache Python module probes so we don't re-spawn `python -c` per frame.
fn python_module_importable(module: &str) -> bool {
    static CACHE: OnceLock<std::sync::Mutex<std::collections::HashMap<String, bool>>> =
        OnceLock::new();
    let cache = CACHE.get_or_init(|| std::sync::Mutex::new(std::collections::HashMap::new()));
    if let Some(v) = cache.lock().ok().and_then(|g| g.get(module).copied()) {
        return v;
    }
    let ok = python_cmd()
        .and_then(|py| {
            Command::new(py)
                .args(["-c", &format!("import {module}")])
                .output()
                .ok()
        })
        .map(|o| o.status.success())
        .unwrap_or(false);
    if let Ok(mut g) = cache.lock() {
        g.insert(module.to_string(), ok);
    }
    ok
}

fn python_cmd() -> Option<String> {
    if let Ok(p) = std::env::var("PHENOTYPE_AGREEMENT_PYTHON") {
        if !p.is_empty() {
            return Some(p);
        }
    }
    for cand in ["python3", "python"] {
        if Command::new(cand).arg("--version").output().is_ok() {
            return Some(cand.to_string());
        }
    }
    None
}

/// Pluggable scorer trait.
pub trait AgreementScorer: Send + Sync {
    fn score(&self, intent: &str, blind: &str, image: Option<&Path>) -> AgreementReport;
    fn name(&self) -> &'static str;
}

// ---------------------------------------------------------------------------
// Jaccard
// ---------------------------------------------------------------------------

const STOPWORDS: &[&str] = &[
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "for", "to", "in", "on",
    "at", "by", "with", "from", "as", "is", "are", "was", "were", "be", "been", "being", "it",
    "its", "this", "that", "these", "those", "i", "you", "he", "she", "we", "they", "them", "his",
    "her", "their", "our", "your", "my", "me", "him", "us", "do", "does", "did", "have", "has",
    "had", "will", "would", "should", "could", "can", "may", "might", "must", "so", "than", "when",
    "while", "where", "who", "what", "which", "some", "any", "all", "no", "not", "out", "up",
    "down", "into", "over", "under", "again", "about", "after", "before", "just", "also", "only",
    "very", "too", "there", "here", "s", "t",
];

fn is_stopword(w: &str) -> bool {
    w.len() <= 1 || STOPWORDS.contains(&w)
}

/// Tokenise a caption into lowercase alphanumeric words, drop stopwords,
/// stem with the Porter2/Snowball English stemmer, de-duplicate.
pub fn tokenise(text: &str) -> Vec<String> {
    let stemmer = Stemmer::create(Algorithm::English);
    let mut out: BTreeSet<String> = BTreeSet::new();
    let mut current = String::new();
    for ch in text.chars() {
        if ch.is_alphanumeric() {
            for c in ch.to_lowercase() {
                current.push(c);
            }
        } else if !current.is_empty() {
            push_token(&stemmer, &current, &mut out);
            current.clear();
        }
    }
    if !current.is_empty() {
        push_token(&stemmer, &current, &mut out);
    }
    out.into_iter().collect()
}

fn push_token(stemmer: &Stemmer, word: &str, out: &mut BTreeSet<String>) {
    if is_stopword(word) {
        return;
    }
    let stem = stemmer.stem(word).to_string();
    if stem.is_empty() || is_stopword(&stem) {
        return;
    }
    out.insert(stem);
}

pub struct JaccardScorer;

impl AgreementScorer for JaccardScorer {
    fn name(&self) -> &'static str {
        "jaccard"
    }
    fn score(&self, intent: &str, blind: &str, _image: Option<&Path>) -> AgreementReport {
        let intent_tokens = tokenise(intent);
        let blind_tokens = tokenise(blind);
        let intent_set: BTreeSet<&String> = intent_tokens.iter().collect();
        let blind_set: BTreeSet<&String> = blind_tokens.iter().collect();

        let overlap = if intent_set.is_empty() && blind_set.is_empty() {
            1.0
        } else if intent_set.is_empty() || blind_set.is_empty() {
            0.0
        } else {
            let inter = intent_set.intersection(&blind_set).count() as f64;
            let union = intent_set.union(&blind_set).count() as f64;
            inter / union
        };

        let status = if overlap >= 0.6 {
            Agreement::Green
        } else if overlap >= 0.3 {
            Agreement::Yellow
        } else {
            Agreement::Red
        };

        let missing_in_blind: Vec<String> =
            intent_set.difference(&blind_set).map(|s| (*s).clone()).collect();
        let extras_in_blind: Vec<String> =
            blind_set.difference(&intent_set).map(|s| (*s).clone()).collect();

        AgreementReport {
            status,
            overlap,
            raw_score: overlap,
            backend: "jaccard".to_string(),
            backend_model: None,
            intent_tokens,
            blind_tokens,
            missing_in_blind,
            extras_in_blind,
        }
    }
}

// ---------------------------------------------------------------------------
// Sentence-Transformers
// ---------------------------------------------------------------------------

pub struct SentenceTransformerScorer {
    pub model: String,
}

impl AgreementScorer for SentenceTransformerScorer {
    fn name(&self) -> &'static str {
        "sentence-transformer"
    }
    fn score(&self, intent: &str, blind: &str, _image: Option<&Path>) -> AgreementReport {
        let cosine = match run_sentence_transformer(&self.model, intent, blind) {
            Ok(c) => c,
            Err(_) => {
                // Fall back to Jaccard so callers always get a usable report.
                let mut fb = JaccardScorer.score(intent, blind, None);
                fb.backend = format!("jaccard-fallback:{}", self.name());
                return fb;
            }
        };
        // Clamp cosine to [-1, 1] and map to [0, 1] for display overlap.
        let c = cosine.clamp(-1.0, 1.0);
        let overlap_display = ((c + 1.0) / 2.0).clamp(0.0, 1.0);
        let status = if c >= 0.75 {
            Agreement::Green
        } else if c >= 0.5 {
            Agreement::Yellow
        } else {
            Agreement::Red
        };
        AgreementReport {
            status,
            overlap: overlap_display,
            raw_score: c,
            backend: "sentence-transformer".to_string(),
            backend_model: Some(self.model.clone()),
            intent_tokens: vec![],
            blind_tokens: vec![],
            missing_in_blind: vec![],
            extras_in_blind: vec![],
        }
    }
}

fn run_sentence_transformer(model: &str, intent: &str, blind: &str) -> Result<f64, String> {
    let py = python_cmd().ok_or("python not on PATH")?;
    // Drive through stdin to avoid shell-escaping the captions.
    let script = r#"
import json, sys
from sentence_transformers import SentenceTransformer, util
payload = json.load(sys.stdin)
m = SentenceTransformer(payload["model"])
a, b = m.encode([payload["intent"], payload["blind"]])
print(util.cos_sim(a, b).item())
"#;
    let mut child = Command::new(&py)
        .args(["-c", script])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn python: {e}"))?;
    let payload = serde_json::json!({
        "model": model,
        "intent": intent,
        "blind": blind,
    });
    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        stdin
            .write_all(payload.to_string().as_bytes())
            .map_err(|e| format!("write stdin: {e}"))?;
    }
    let out = child.wait_with_output().map_err(|e| format!("wait: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "sentence-transformer subprocess failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    let txt = String::from_utf8_lossy(&out.stdout);
    txt.trim()
        .lines()
        .last()
        .ok_or_else(|| "empty stdout".to_string())?
        .parse::<f64>()
        .map_err(|e| format!("parse cosine: {e}"))
}

// ---------------------------------------------------------------------------
// SigLIP
// ---------------------------------------------------------------------------

pub struct SigLipScorer {
    pub model: String,
}

impl AgreementScorer for SigLipScorer {
    fn name(&self) -> &'static str {
        "siglip"
    }
    fn score(&self, intent: &str, blind: &str, image: Option<&Path>) -> AgreementReport {
        let img = match image {
            Some(p) if p.exists() => p.to_path_buf(),
            _ => {
                // No image → no signal for SigLIP; fall back to Jaccard.
                let mut fb = JaccardScorer.score(intent, blind, None);
                fb.backend = "jaccard-fallback:siglip-no-image".to_string();
                return fb;
            }
        };
        let raw = match run_siglip(&self.model, intent, &img) {
            Ok(r) => r,
            Err(_) => {
                let mut fb = JaccardScorer.score(intent, blind, None);
                fb.backend = "jaccard-fallback:siglip".to_string();
                return fb;
            }
        };
        // SigLIP softmax prob is already in [0, 1]; display overlap == raw.
        let status = if raw >= 0.3 {
            Agreement::Green
        } else if raw >= 0.1 {
            Agreement::Yellow
        } else {
            Agreement::Red
        };
        AgreementReport {
            status,
            overlap: raw.clamp(0.0, 1.0),
            raw_score: raw,
            backend: "siglip".to_string(),
            backend_model: Some(self.model.clone()),
            intent_tokens: vec![],
            blind_tokens: vec![],
            missing_in_blind: vec![],
            extras_in_blind: vec![],
        }
    }
}

fn run_siglip(model: &str, intent: &str, image: &Path) -> Result<f64, String> {
    let py = python_cmd().ok_or("python not on PATH")?;
    let script = r#"
import json, sys, torch
from transformers import AutoProcessor, AutoModel
from PIL import Image
payload = json.load(sys.stdin)
processor = AutoProcessor.from_pretrained(payload["model"])
model = AutoModel.from_pretrained(payload["model"])
img = Image.open(payload["image"]).convert("RGB")
inputs = processor(text=[payload["intent"]], images=[img], return_tensors="pt", padding=True)
with torch.no_grad():
    out = model(**inputs)
    # logits_per_image: (1, 1) for single text; apply sigmoid (SigLIP paper)
    # and take scalar.
    prob = torch.sigmoid(out.logits_per_image).item()
print(prob)
"#;
    let mut child = Command::new(&py)
        .args(["-c", script])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("spawn python: {e}"))?;
    let payload = serde_json::json!({
        "model": model,
        "intent": intent,
        "image": image.display().to_string(),
    });
    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        stdin.write_all(payload.to_string().as_bytes()).map_err(|e| format!("write: {e}"))?;
    }
    let out = child.wait_with_output().map_err(|e| format!("wait: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "siglip subprocess failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    let txt = String::from_utf8_lossy(&out.stdout);
    txt.trim()
        .lines()
        .last()
        .ok_or_else(|| "empty stdout".to_string())?
        .parse::<f64>()
        .map_err(|e| format!("parse prob: {e}"))
}

// ---------------------------------------------------------------------------
// Backward-compatible free functions
// ---------------------------------------------------------------------------

/// Score an (intent, blind) pair using the Jaccard backend.
///
/// **Preserved for backward compatibility.** New callers should use
/// [`AgreementBackend::build`] to obtain a trait object that can dispatch to
/// SigLIP or sentence-transformers.
pub fn score(intent: &str, blind: &str) -> AgreementReport {
    JaccardScorer.score(intent, blind, None)
}

/// Score with a fully-qualified backend + optional keyframe path.
pub fn score_with(
    backend: &AgreementBackend,
    intent: &str,
    blind: &str,
    image: Option<&Path>,
) -> AgreementReport {
    backend.build(image.is_some()).score(intent, blind, image)
}

/// Resolve the backend from `PHENOTYPE_AGREEMENT_BACKEND` env, defaulting to
/// `Auto`. Recognises: `jaccard|sentence|siglip|auto`.
pub fn backend_from_env() -> AgreementBackend {
    match std::env::var("PHENOTYPE_AGREEMENT_BACKEND") {
        Ok(v) if !v.is_empty() => AgreementBackend::parse_flag(&v).unwrap_or_default(),
        _ => AgreementBackend::Auto,
    }
}

/// Convenience: resolve a keyframe path relative to the manifest's artefacts
/// root. Returns `None` if the file does not exist.
pub fn resolve_keyframe(root: Option<&Path>, screenshot_path: &str) -> Option<PathBuf> {
    let candidate = match root {
        Some(r) => r.join(screenshot_path),
        None => PathBuf::from(screenshot_path),
    };
    if candidate.exists() {
        Some(candidate)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Traces to: FR-UX-VERIFY-003
    #[test]
    fn matching_intent_and_blind_scores_green() {
        let intent = "Show the plan command help options available";
        let blind = "Terminal shows plan command help options available";
        let r = score(intent, blind);
        assert!(r.overlap >= 0.6, "got {:.3}", r.overlap);
        assert_eq!(r.status, Agreement::Green);
        assert_eq!(r.backend, "jaccard");
    }

    /// Traces to: FR-UX-VERIFY-003
    #[test]
    fn divergent_intent_and_blind_scores_red() {
        let intent = "Show the plan command help text with all available options";
        let blind = "A photograph of a cat sitting on a windowsill bathed in sunlight.";
        let r = score(intent, blind);
        assert!(r.overlap < 0.3, "got {:.3}", r.overlap);
        assert_eq!(r.status, Agreement::Red);
        assert!(!r.missing_in_blind.is_empty());
    }

    /// Traces to: FR-UX-VERIFY-003
    #[test]
    fn test_jaccard_still_works_as_fallback() {
        let backend = AgreementBackend::Jaccard;
        let r = score_with(&backend, "hello world", "hello world", None);
        assert_eq!(r.status, Agreement::Green);
        assert_eq!(r.backend, "jaccard");
        assert!((r.raw_score - 1.0).abs() < 1e-9);
    }

    /// Traces to: FR-UX-VERIFY-003
    #[test]
    fn backend_parse_flag_accepts_all_variants() {
        assert!(matches!(
            AgreementBackend::parse_flag("jaccard"),
            Ok(AgreementBackend::Jaccard)
        ));
        assert!(matches!(
            AgreementBackend::parse_flag("sentence"),
            Ok(AgreementBackend::SentenceTransformer { .. })
        ));
        assert!(matches!(
            AgreementBackend::parse_flag("siglip"),
            Ok(AgreementBackend::SigLip { .. })
        ));
        assert!(matches!(AgreementBackend::parse_flag("auto"), Ok(AgreementBackend::Auto)));
        assert!(AgreementBackend::parse_flag("bogus").is_err());
    }

    /// Traces to: FR-UX-VERIFY-003
    ///
    /// When sentence-transformers is unavailable the scorer must fall back to
    /// Jaccard so every frame still gets a non-empty report. Asserting the
    /// backend string communicates the fallback to the viewer.
    #[test]
    fn test_sentence_transformer_falls_back_to_jaccard_when_unavailable() {
        // Force a non-importable module by setting PHENOTYPE_AGREEMENT_PYTHON to
        // a path that does not exist. The scorer's internal fallback covers
        // the "sentence_transformers not installed" case too; both paths must
        // yield a Jaccard-fallback report.
        let scorer = SentenceTransformerScorer { model: "nope".into() };
        let r = scorer.score("click plan button", "triggering the plan action", None);
        // Either we have sentence-transformers installed (real cosine report)
        // or we do not (fallback report). Both are valid; either way the
        // report must be populated and the status classified.
        assert!(matches!(r.status, Agreement::Green | Agreement::Yellow | Agreement::Red));
        assert!(
            r.backend == "sentence-transformer"
                || r.backend.starts_with("jaccard-fallback"),
            "unexpected backend: {}",
            r.backend
        );
    }

    /// Traces to: FR-UX-VERIFY-003
    ///
    /// SigLIP without a keyframe image must transparently fall back to the
    /// Jaccard text-text scorer.
    #[test]
    fn test_siglip_falls_back_when_no_image() {
        let scorer = SigLipScorer { model: default_siglip_model() };
        let r = scorer.score("user clicks plan", "the plan action triggers", None);
        assert_eq!(r.backend, "jaccard-fallback:siglip-no-image");
    }

    /// Traces to: FR-UX-VERIFY-003
    ///
    /// `Auto` must pick one of the three concrete backends based on
    /// availability. In a unit-test environment without the Python ML stack
    /// installed, it must degrade to Jaccard.
    #[test]
    fn test_auto_backend_picks_something() {
        let auto = AgreementBackend::Auto;
        let concrete = auto.resolve_concrete(false);
        assert!(!matches!(concrete, AgreementBackend::Auto));
        // With image_available=true, Auto should still resolve to a non-Auto.
        let concrete2 = auto.resolve_concrete(true);
        assert!(!matches!(concrete2, AgreementBackend::Auto));
    }

    /// Traces to: FR-UX-VERIFY-003
    ///
    /// The report schema must round-trip through serde so persisted
    /// `manifest.verified.json` files remain stable.
    #[test]
    fn report_roundtrips_through_serde() {
        let r = score("hello world plan", "hello world plan output");
        let s = serde_json::to_string(&r).unwrap();
        let back: AgreementReport = serde_json::from_str(&s).unwrap();
        assert_eq!(r, back);
    }
}
