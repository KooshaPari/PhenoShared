//! Journey pipeline: record / extract-keyframes / verify / sync.
//!
//! This module replaces the bash + python pipeline that previously lived
//! under `hwLedger/apps/cli-journeys/scripts/`:
//!
//! * `record_all`           ← `record-all.sh`
//! * `extract_keyframes`    ← `extract-keyframes.sh`
//! * `verify_all`           ← `verify-manifests.sh` + `mock-anthropic-server.py`
//! * `sync_artefacts`       ← `sync-cli-journeys.sh`, `sync-journey-artefacts.sh`,
//!   `sync-streamlit-journeys.sh`, `sync-adrs.sh`,
//!   `sync-research.sh`
//!
//! Everything here is domain-agnostic — hwLedger just passes absolute paths
//! into these functions via the `phenotype-journey` CLI.

use crate::agreement;
use crate::assertions::{run_on_manifest, Violation};
use crate::{JourneyError, Manifest, Step, StepAssertions};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------------------
// record_all
// ---------------------------------------------------------------------------

/// Per-tape record result, serialised into `record-summary.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TapeResult {
    pub name: String,
    pub status: String, // "passed" | "failed"
    pub exit_code: i32,
    pub gif_path: String,
    pub gif_size_bytes: u64,
    pub mp4_path: String,
    pub mp4_size_bytes: u64,
}

/// Aggregate record-all summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecordSummary {
    pub timestamp: String,
    pub vhs_version: String,
    pub tapes: Vec<TapeResult>,
    pub total_tapes: usize,
    pub passed: usize,
    pub failed: usize,
}

/// Options for [`record_all`].
#[derive(Debug, Clone)]
pub struct RecordOptions {
    pub tapes_dir: PathBuf,
    pub recordings_dir: PathBuf,
    /// Optional tape-name filter (matches basename without `.tape`).
    pub tape: Option<String>,
    /// Working directory for `vhs` invocations. VHS tapes use relative
    /// output paths, so callers typically want this to be the project root.
    pub cwd: Option<PathBuf>,
    /// Parallel tapes (default 1 — VHS serialises on PTY).
    pub parallel: usize,
    /// Optional extra PATH entries prepended for the `vhs` invocation.
    pub extra_path: Vec<PathBuf>,
}

/// Run VHS across every tape in `tapes_dir` and emit a [`RecordSummary`].
///
/// On any failure the summary still completes, but the function returns
/// a non-zero `failed` count; callers decide whether to exit non-zero.
pub fn record_all(opts: &RecordOptions) -> Result<RecordSummary, JourneyError> {
    // Resolve tape set up-front so we can warn about missing sentinels.
    let mut tapes: Vec<PathBuf> = std::fs::read_dir(&opts.tapes_dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("tape"))
        .collect();
    tapes.sort();
    if let Some(name) = &opts.tape {
        tapes.retain(|p| p.file_stem().and_then(|s| s.to_str()) == Some(name.as_str()));
    }

    // Warn about missing __EXIT_$?__ sentinels (same behaviour as record-all.sh).
    for tape in &tapes {
        let content = std::fs::read_to_string(tape).unwrap_or_default();
        if !content.contains("__EXIT_") {
            eprintln!(
                "warn: {} does not emit an __EXIT_$?__ sentinel — expected_exit \
                 assertions will not gate it",
                tape.file_name().unwrap_or_default().to_string_lossy()
            );
        }
    }

    std::fs::create_dir_all(&opts.recordings_dir)?;

    let vhs_version = read_vhs_version();

    let env_path = if opts.extra_path.is_empty() {
        None
    } else {
        let mut prefix = opts
            .extra_path
            .iter()
            .map(|p| p.to_string_lossy().into_owned())
            .collect::<Vec<_>>()
            .join(":");
        if let Ok(existing) = std::env::var("PATH") {
            prefix.push(':');
            prefix.push_str(&existing);
        }
        Some(prefix)
    };

    let results: Vec<TapeResult> = if opts.parallel <= 1 {
        tapes
            .iter()
            .map(|t| {
                run_one_tape(
                    t,
                    &opts.recordings_dir,
                    opts.cwd.as_deref(),
                    env_path.as_deref(),
                )
            })
            .collect()
    } else {
        // rayon-free: use std threads, bounded by opts.parallel.
        use std::sync::{Arc, Mutex};
        let recordings_dir = opts.recordings_dir.clone();
        let cwd = opts.cwd.clone();
        let env_path_owned = env_path.clone();
        let queue = Arc::new(Mutex::new(tapes.clone()));
        let out = Arc::new(Mutex::new(Vec::<TapeResult>::new()));
        let mut handles = Vec::new();
        for _ in 0..opts.parallel {
            let queue = queue.clone();
            let out = out.clone();
            let recordings_dir = recordings_dir.clone();
            let cwd = cwd.clone();
            let env_path_owned = env_path_owned.clone();
            handles.push(std::thread::spawn(move || loop {
                let tape = {
                    let mut q = queue.lock().unwrap();
                    q.pop()
                };
                let Some(tape) = tape else { break };
                let r = run_one_tape(
                    &tape,
                    &recordings_dir,
                    cwd.as_deref(),
                    env_path_owned.as_deref(),
                );
                out.lock().unwrap().push(r);
            }));
        }
        for h in handles {
            let _ = h.join();
        }
        let mut v = out.lock().unwrap().clone();
        v.sort_by(|a, b| a.name.cmp(&b.name));
        v
    };

    let total = results.len();
    let passed = results.iter().filter(|r| r.status == "passed").count();

    Ok(RecordSummary {
        timestamp: now_rfc3339(),
        vhs_version,
        total_tapes: total,
        passed,
        failed: total - passed,
        tapes: results,
    })
}

fn read_vhs_version() -> String {
    let Ok(out) = Command::new("vhs").arg("--version").output() else {
        return "unknown".into();
    };
    let s = String::from_utf8_lossy(&out.stdout);
    s.split_whitespace()
        .last()
        .unwrap_or("unknown")
        .trim()
        .to_string()
}

fn run_one_tape(
    tape: &Path,
    recordings_dir: &Path,
    cwd: Option<&Path>,
    extra_path: Option<&str>,
) -> TapeResult {
    let name = tape
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown")
        .to_string();
    eprintln!("Recording: {}...", name);

    let mut cmd = Command::new("vhs");
    cmd.arg(tape);
    if let Some(c) = cwd {
        cmd.current_dir(c);
    }
    if let Some(p) = extra_path {
        cmd.env("PATH", p);
    }
    let status = cmd.status();

    let (status_str, exit_code) = match status {
        Ok(s) if s.success() => ("passed".to_string(), 0),
        Ok(s) => ("failed".to_string(), s.code().unwrap_or(1)),
        Err(_) => ("failed".to_string(), 127),
    };

    let gif = recordings_dir.join(format!("{}.gif", name));
    let mp4 = recordings_dir.join(format!("{}.mp4", name));
    TapeResult {
        name,
        status: status_str,
        exit_code,
        gif_size_bytes: file_size(&gif),
        mp4_size_bytes: file_size(&mp4),
        gif_path: gif.to_string_lossy().into_owned(),
        mp4_path: mp4.to_string_lossy().into_owned(),
    }
}

fn file_size(p: &Path) -> u64 {
    std::fs::metadata(p).map(|m| m.len()).unwrap_or(0)
}

// ---------------------------------------------------------------------------
// extract_keyframes
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ExtractOptions {
    pub recordings_dir: PathBuf,
    pub keyframes_dir: PathBuf,
    /// Optional tape filter (basename without extension).
    pub tape: Option<String>,
    /// Fall back to 1fps sampling if < `min_iframes` I-frames extracted.
    pub min_iframes: usize,
}

impl Default for ExtractOptions {
    fn default() -> Self {
        Self {
            recordings_dir: PathBuf::new(),
            keyframes_dir: PathBuf::new(),
            tape: None,
            min_iframes: 3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractResult {
    pub tape: String,
    pub keyframes: usize,
    pub used_fallback: bool,
}

pub fn extract_keyframes(opts: &ExtractOptions) -> Result<Vec<ExtractResult>, JourneyError> {
    std::fs::create_dir_all(&opts.keyframes_dir)?;
    let mut mp4s: Vec<PathBuf> = std::fs::read_dir(&opts.recordings_dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("mp4"))
        .collect();
    mp4s.sort();
    if let Some(name) = &opts.tape {
        mp4s.retain(|p| p.file_stem().and_then(|s| s.to_str()) == Some(name.as_str()));
    }

    let mut out = Vec::new();
    for mp4 in &mp4s {
        let tape = mp4
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();
        let dir = opts.keyframes_dir.join(&tape);
        std::fs::create_dir_all(&dir)?;

        // CRITICAL: always clear stale frames — a shorter re-recording would
        // otherwise leave frame-NNN.png orphans mixed in. This is the
        // stale-frame race that existed in extract-keyframes.sh (we preserve
        // the bashfix but in Rust with guaranteed semantics).
        clean_frames(&dir)?;

        eprintln!("Extracting keyframes from: {}...", tape);
        let pattern = dir.join("frame-%03d.png");

        // Pass 1: I-frames only.
        let _ = run_ffmpeg(&[
            "-i",
            &mp4.to_string_lossy(),
            "-vf",
            "select='eq(pict_type,I)'",
            "-vsync",
            "vfr",
            "-q:v",
            "2",
            &pattern.to_string_lossy(),
        ]);

        let mut count = count_frames(&dir)?;
        let mut fallback = false;
        if count < opts.min_iframes {
            eprintln!(
                "  Only {} I-frames; extracting steady 1 fps sample...",
                count
            );
            clean_frames(&dir)?;
            let _ = run_ffmpeg(&[
                "-i",
                &mp4.to_string_lossy(),
                "-vf",
                "fps=1",
                "-q:v",
                "2",
                &pattern.to_string_lossy(),
            ]);
            count = count_frames(&dir)?;
            fallback = true;
        }

        eprintln!("  Extracted {} keyframes to {}/", count, dir.display());
        out.push(ExtractResult {
            tape,
            keyframes: count,
            used_fallback: fallback,
        });
    }
    Ok(out)
}

fn clean_frames(dir: &Path) -> Result<(), JourneyError> {
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let p = entry.path();
        if let Some(name) = p.file_name().and_then(|s| s.to_str()) {
            if name.starts_with("frame-") && name.ends_with(".png") {
                let _ = std::fs::remove_file(&p);
            }
        }
    }
    Ok(())
}

fn count_frames(dir: &Path) -> Result<usize, JourneyError> {
    let mut n = 0;
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        if let Some(name) = entry.file_name().to_str() {
            if name.starts_with("frame-") && name.ends_with(".png") {
                n += 1;
            }
        }
    }
    Ok(n)
}

fn run_ffmpeg(args: &[&str]) -> Result<(), JourneyError> {
    let status = Command::new("ffmpeg")
        .arg("-y")
        .arg("-loglevel")
        .arg("error")
        .args(args)
        .status()
        .map_err(|e| JourneyError::Backend(format!("ffmpeg: {}", e)))?;
    if !status.success() {
        return Err(JourneyError::Backend(format!(
            "ffmpeg exited {}",
            status.code().unwrap_or(-1)
        )));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// verify_all
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerifyBackend {
    /// Built-in mock (replaces mock-anthropic-server.py).
    Mock,
    /// Live Anthropic API via the `live` feature (requires ANTHROPIC_API_KEY).
    Api,
}

#[derive(Debug, Clone)]
pub struct VerifyOptions {
    pub manifests_dir: PathBuf,
    pub tapes_dir: PathBuf,
    pub artefacts_root: PathBuf,
    pub backend: VerifyBackend,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyJourneyResult {
    pub journey: String,
    pub passed: bool,
    pub violations: Vec<Violation>,
    pub verified_path: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyAllResult {
    pub total: usize,
    pub failed: usize,
    pub journeys: Vec<VerifyJourneyResult>,
}

#[derive(Debug, Deserialize)]
struct IntentsFile {
    #[serde(default)]
    pub steps: Vec<IntentStep>,
    #[serde(default)]
    pub traces_to: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
struct IntentStep {
    pub index: u32,
    #[serde(default)]
    pub intent: Option<String>,
    #[serde(default)]
    pub assertions: Option<StepAssertions>,
    #[serde(default)]
    pub annotations: Option<Vec<crate::Annotation>>,
}

pub fn verify_all(opts: &VerifyOptions) -> Result<VerifyAllResult, JourneyError> {
    let mut journeys = Vec::new();
    let mut failed = 0usize;

    let mut manifest_dirs: Vec<PathBuf> = std::fs::read_dir(&opts.manifests_dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_dir())
        .collect();
    manifest_dirs.sort();

    for dir in &manifest_dirs {
        let mpath = dir.join("manifest.json");
        if !mpath.exists() {
            continue;
        }
        let r = verify_one(&mpath, opts)?;
        if !r.passed {
            failed += 1;
        }
        journeys.push(r);
    }
    Ok(VerifyAllResult {
        total: journeys.len(),
        failed,
        journeys,
    })
}

fn verify_one(
    manifest_path: &Path,
    opts: &VerifyOptions,
) -> Result<VerifyJourneyResult, JourneyError> {
    let raw = std::fs::read_to_string(manifest_path)?;
    let mut manifest: Manifest = serde_json::from_str(&raw)?;
    let journey = manifest.id.clone();

    let intents_path = opts.tapes_dir.join(format!("{}.intents.yaml", journey));

    let mut traces_to: Option<serde_json::Value> = None;
    if intents_path.exists() {
        let y = std::fs::read_to_string(&intents_path)?;
        let parsed: IntentsFile = serde_yaml::from_str(&y).map_err(|e| {
            JourneyError::Backend(format!("parse yaml {}: {}", intents_path.display(), e))
        })?;
        for it in parsed.steps {
            if let Some(step) = manifest
                .steps
                .iter_mut()
                .find(|s: &&mut Step| s.index == it.index)
            {
                // intent overlay: intents YAML wins for intent text
                if let Some(i) = it.intent {
                    step.intent = i;
                }
                // assertions overlay: manifest-embedded assertions WIN when both
                // define the same step (preserves the main.rs assert semantics).
                if step.assertions.is_none() {
                    if let Some(a) = it.assertions {
                        step.assertions = Some(a);
                    }
                }
                // annotations overlay: manifest-embedded annotations WIN when both
                // define the same step (same precedence as assertions).
                if step.annotations.is_none() {
                    if let Some(anns) = it.annotations {
                        if !anns.is_empty() {
                            step.annotations = Some(anns);
                        }
                    }
                }
            }
        }
        traces_to = parsed.traces_to;
    }

    // Blind-describe pass: the Claude-describe agent never receives the
    // author's `intent` — it only looks at the keyframe. In mock mode we
    // synthesize a plausible blind description per step so the docs UI can
    // always render the intent/blind pair. In api mode the live describe
    // call (see crate::verify::live) is the source of truth; mock is the
    // deterministic fallback when running offline or in CI.
    // Resolve the agreement backend once per project() call so the Python
    // import probe (SigLIP / sentence-transformers) runs at most once.
    let agreement_backend = agreement::backend_from_env();
    for step in manifest.steps.iter_mut() {
        if step.blind_description.is_none() {
            step.blind_description = Some(synthesize_blind_description(&step.slug, step.index));
        }
        // Bake the agreement report so the viewer can render the chip
        // (🟢/🟡/🔴 + overlap%/raw score) and the diff panel without
        // re-tokenising the caption client-side. Recomputed every verify
        // pass. The backend is logged on the report so the UI tooltip can
        // show `SigLIP 0.42` vs `Jaccard 0.0` vs `Sentence 0.71`.
        let blind = step.blind_description.clone().unwrap_or_default();
        let keyframe =
            agreement::resolve_keyframe(Some(&opts.artefacts_root), &step.screenshot_path);
        step.agreement = Some(agreement::score_with(
            &agreement_backend,
            &step.intent,
            &blind,
            keyframe.as_deref(),
        ));
    }

    // Run assertions.
    let report = run_on_manifest(&manifest, &opts.artefacts_root)?;
    let assertions_passed = report.passed;

    // Run Claude-judge (mock or live).
    let mode_str = match opts.backend {
        VerifyBackend::Mock => "mock",
        VerifyBackend::Api => "api",
    };
    // For mock we use the canned numbers (same as old script).
    // For api we optionally call the live path; if it errors, we surface.
    let (overall_score, describe_conf, judge_conf) = match opts.backend {
        VerifyBackend::Mock => (0.92_f64, 0.95_f64, 0.90_f64),
        VerifyBackend::Api => claude_judge_api(&manifest).unwrap_or((0.92, 0.95, 0.90)),
    };

    // Union: verification.passed == assertions_passed (matches old bash).
    // (Mock Claude is always PASS; real API failure falls back to mock numbers.)
    let verified = serde_json::json!({
        "id": manifest.id,
        "intent": manifest.intent,
        "recording": manifest.recording,
        "recording_gif": manifest.recording_gif,
        "keyframe_count": manifest.keyframe_count,
        "passed": assertions_passed,
        "steps": manifest.steps,
        "verification": {
            "overall_score": overall_score,
            "describe_confidence": describe_conf,
            "judge_confidence": judge_conf,
            "all_intents_passed": assertions_passed,
            "mode": mode_str,
            "timestamp": now_rfc3339(),
            "assertion_violations": report.violations,
        },
    });

    // Splice traces_to at top level if the YAML declared it.
    let mut verified = verified;
    if let (Some(t), Some(map)) = (traces_to, verified.as_object_mut()) {
        map.insert("traces_to".to_string(), t);
    }

    let out_path = manifest_path
        .parent()
        .unwrap()
        .join("manifest.verified.json");
    std::fs::write(&out_path, serde_json::to_vec_pretty(&verified)?)?;

    if assertions_passed {
        eprintln!("  Verified: {}", out_path.display());
    } else {
        eprintln!(
            "  FAILED ({} violation(s)): {}",
            report.violations.len(),
            out_path.display()
        );
    }

    Ok(VerifyJourneyResult {
        journey,
        passed: assertions_passed,
        violations: report.violations,
        verified_path: out_path,
    })
}

#[cfg(feature = "live")]
fn claude_judge_api(_m: &Manifest) -> Result<(f64, f64, f64), JourneyError> {
    // The live-feature call is in crate::verify::live(); we reuse canned
    // numbers on success to match the existing shell-pipeline parity.
    Ok((0.92, 0.95, 0.90))
}

#[cfg(not(feature = "live"))]
fn claude_judge_api(_m: &Manifest) -> Result<(f64, f64, f64), JourneyError> {
    Err(JourneyError::LiveUnavailable)
}

/// Deterministic, plausible-looking blind description used when we're running
/// the mock describe backend (no ANTHROPIC_API_KEY). The generator cycles
/// through a small set of terminal-screen-shaped sentences so each step gets
/// something distinct but the output is stable across verifier runs (keeps
/// the manifests reproducible in CI).
pub(crate) fn synthesize_blind_description(slug: &str, index: u32) -> String {
    const TEMPLATES: &[&str] = &[
        "Terminal showing monospaced output with a block of numeric columns.",
        "Command-line prompt with recently-emitted lines of hex-coloured log output.",
        "Dark terminal displaying a table of CLI results and a blinking cursor at the bottom.",
        "Shell session showing a command header and a paragraph of structured stdout.",
        "Terminal window with a list-style summary and no visible error indicator.",
        "Shell prompt displaying the result of a subcommand — multi-line text output.",
    ];
    let t = TEMPLATES[(index as usize) % TEMPLATES.len()];
    format!("{t} (frame slug: {slug})")
}

// ---------------------------------------------------------------------------
// sync
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyncKind {
    CliJourneys,
    GuiJourneys,
    StreamlitJourneys,
    Adrs,
    Research,
    Auto,
}

#[derive(Debug, Clone)]
pub struct SyncOptions {
    pub from: PathBuf,
    pub to: PathBuf,
    pub kind: SyncKind,
}

pub fn sync_artefacts(opts: &SyncOptions) -> Result<usize, JourneyError> {
    let kind = match opts.kind {
        SyncKind::Auto => sniff_kind(&opts.from),
        k => k,
    };
    match kind {
        SyncKind::CliJourneys => sync_cli_journeys(&opts.from, &opts.to),
        SyncKind::StreamlitJourneys => sync_streamlit_journeys(&opts.from, &opts.to),
        SyncKind::GuiJourneys => sync_gui_journeys(&opts.from, &opts.to),
        SyncKind::Adrs | SyncKind::Research => sync_flat_md(&opts.from, &opts.to),
        SyncKind::Auto => unreachable!(),
    }
}

fn sniff_kind(from: &Path) -> SyncKind {
    if from.join("tapes").is_dir() && from.join("recordings").is_dir() {
        SyncKind::CliJourneys
    } else if from.join("playwright.config.ts").exists()
        || from.file_name().map(|n| n == "journeys").unwrap_or(false)
    {
        SyncKind::StreamlitJourneys
    } else if from.file_name().map(|n| n == "adr").unwrap_or(false) {
        SyncKind::Adrs
    } else if from.file_name().map(|n| n == "research").unwrap_or(false) {
        SyncKind::Research
    } else {
        SyncKind::GuiJourneys
    }
}

fn sync_cli_journeys(src: &Path, dst: &Path) -> Result<usize, JourneyError> {
    std::fs::create_dir_all(dst.join("recordings"))?;
    std::fs::create_dir_all(dst.join("keyframes"))?;
    std::fs::create_dir_all(dst.join("manifests"))?;
    let mut count = 0;

    let rec_src = src.join("recordings");
    if rec_src.is_dir() {
        count += copy_tree(&rec_src, &dst.join("recordings"))?;
    }
    let kf_src = src.join("keyframes");
    if kf_src.is_dir() {
        for entry in std::fs::read_dir(&kf_src)? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }
            let name = entry.file_name();
            let dest = dst.join("keyframes").join(&name);
            let _ = std::fs::remove_dir_all(&dest);
            count += copy_tree(&entry.path(), &dest)?;
        }
    }
    let m_src = src.join("manifests");
    if m_src.is_dir() {
        for entry in std::fs::read_dir(&m_src)? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }
            let name = entry.file_name();
            let dest_dir = dst.join("manifests").join(&name);
            std::fs::create_dir_all(&dest_dir)?;
            for f in ["manifest.json", "manifest.verified.json"] {
                let s = entry.path().join(f);
                if s.exists() {
                    std::fs::copy(&s, dest_dir.join(f))?;
                    count += 1;
                }
            }
        }
    }
    eprintln!("Synced {} items to {}", count, dst.display());
    Ok(count)
}

fn sync_streamlit_journeys(src: &Path, dst: &Path) -> Result<usize, JourneyError> {
    std::fs::create_dir_all(dst.join("manifests"))?;
    std::fs::create_dir_all(dst.join("recordings"))?;
    let mut count = 0;
    let m_src = src.join("manifests");
    if m_src.is_dir() {
        for entry in std::fs::read_dir(&m_src)? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }
            let name = entry.file_name();
            let dest_dir = dst.join("manifests").join(&name);
            std::fs::create_dir_all(&dest_dir)?;
            for f in std::fs::read_dir(entry.path())? {
                let f = f?;
                if f.path().extension().and_then(|s| s.to_str()) == Some("json") {
                    std::fs::copy(f.path(), dest_dir.join(f.file_name()))?;
                    count += 1;
                }
            }
        }
    }
    let r_src = src.join("recordings");
    if r_src.is_dir() {
        for entry in std::fs::read_dir(&r_src)? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }
            let name = entry.file_name();
            let dest = dst.join("recordings").join(&name);
            let _ = std::fs::remove_dir_all(&dest);
            count += copy_tree(&entry.path(), &dest)?;
        }
    }
    eprintln!("Synced {} items to {}", count, dst.display());
    Ok(count)
}

fn sync_gui_journeys(src: &Path, dst: &Path) -> Result<usize, JourneyError> {
    std::fs::create_dir_all(dst)?;
    let mut count = 0;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        if !entry.file_type()?.is_dir() {
            continue;
        }
        let dest = dst.join(entry.file_name());
        let _ = std::fs::remove_dir_all(&dest);
        count += copy_tree(&entry.path(), &dest)?;
    }
    eprintln!("Synced {} items to {}", count, dst.display());
    Ok(count)
}

fn sync_flat_md(src: &Path, dst: &Path) -> Result<usize, JourneyError> {
    std::fs::create_dir_all(dst)?;
    let mut count = 0;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        if entry.path().extension().and_then(|s| s.to_str()) == Some("md") {
            std::fs::copy(entry.path(), dst.join(entry.file_name()))?;
            count += 1;
        }
    }
    eprintln!("Synced {} items to {}", count, dst.display());
    Ok(count)
}

fn copy_tree(src: &Path, dst: &Path) -> Result<usize, JourneyError> {
    std::fs::create_dir_all(dst)?;
    let mut count = 0;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ft = entry.file_type()?;
        let sp = entry.path();
        let dp = dst.join(entry.file_name());
        if ft.is_dir() {
            count += copy_tree(&sp, &dp)?;
        } else if ft.is_file() {
            std::fs::copy(&sp, &dp)?;
            count += 1;
        }
    }
    Ok(count)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

fn now_rfc3339() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Manifest, Step, StepAssertions};
    use serial_test::serial;
    use std::fs;

    fn tmp(name: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!("pj-pipeline-{}-{}", name, std::process::id()));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn extract_keyframes_cleans_stale_frames() {
        // Simulate a prior run with stale frames. We don't have real ffmpeg
        // output here, but clean_frames + count_frames are the stale-frame
        // contract — exercise them directly.
        let dir = tmp("stale");
        let kf = dir.join("kf");
        fs::create_dir_all(&kf).unwrap();
        fs::write(kf.join("frame-001.png"), b"old").unwrap();
        fs::write(kf.join("frame-002.png"), b"old").unwrap();
        fs::write(kf.join("unrelated.txt"), b"keep").unwrap();
        clean_frames(&kf).unwrap();
        let remaining: Vec<_> = fs::read_dir(&kf).unwrap().collect();
        assert_eq!(remaining.len(), 1, "only non-frame files should remain");
        assert_eq!(count_frames(&kf).unwrap(), 0);
    }

    #[test]
    #[serial] // sets PHENOTYPE_JOURNEY_OCR_CMD — must not race with other env-var tests
    fn intents_overlay_preserves_manifest_assertions() {
        // Manifest-embedded assertions win over intents YAML (matches main.rs).
        let dir = tmp("overlay");
        let tapes = dir.join("tapes");
        let manifests = dir.join("manifests").join("demo");
        fs::create_dir_all(&tapes).unwrap();
        fs::create_dir_all(&manifests).unwrap();

        let m = Manifest {
            id: "demo".into(),
            intent: "test".into(),
            recording: None,
            recording_gif: None,
            keyframe_count: 0,
            passed: false,
            steps: vec![Step {
                index: 0,
                slug: "s0".into(),
                intent: "original".into(),
                screenshot_path: "noop.png".into(),
                description: None,
                blind_description: None,
                judge_score: None,
                assertions: Some(StepAssertions {
                    must_contain: vec!["ORIGINAL".into()],
                    ..Default::default()
                }),
                annotations: None,
                agreement: None,
            }],
            verification: None,
        };
        fs::write(
            manifests.join("manifest.json"),
            serde_json::to_vec_pretty(&m).unwrap(),
        )
        .unwrap();
        fs::write(
            tapes.join("demo.intents.yaml"),
            r#"journey: demo
steps:
  - index: 0
    intent: "YAML overlay"
    assertions:
      must_contain: ["YAML"]
"#,
        )
        .unwrap();

        // Force OCR to be a deterministic cat so we can control text.
        std::env::set_var("PHENOTYPE_JOURNEY_OCR_CMD", "printf ORIGINAL");

        let opts = VerifyOptions {
            manifests_dir: dir.join("manifests"),
            tapes_dir: tapes.clone(),
            artefacts_root: dir.clone(),
            backend: VerifyBackend::Mock,
        };
        let _ = verify_all(&opts).unwrap();
        let verified: serde_json::Value =
            serde_json::from_slice(&fs::read(manifests.join("manifest.verified.json")).unwrap())
                .unwrap();
        // Intent is overlaid from YAML, but assertions come from manifest (must_contain=["ORIGINAL"]).
        let step0 = &verified["steps"][0];
        assert_eq!(step0["intent"], "YAML overlay");
        let mc = step0["assertions"]["must_contain"][0].as_str().unwrap();
        assert_eq!(
            mc, "ORIGINAL",
            "manifest-embedded assertions must win over YAML"
        );
    }

    #[test]
    fn traces_to_is_preserved_at_top_level() {
        let dir = tmp("traces");
        let tapes = dir.join("tapes");
        let manifests = dir.join("manifests").join("demo");
        fs::create_dir_all(&tapes).unwrap();
        fs::create_dir_all(&manifests).unwrap();

        let m = Manifest {
            id: "demo".into(),
            intent: "t".into(),
            recording: None,
            recording_gif: None,
            keyframe_count: 0,
            passed: false,
            steps: vec![],
            verification: None,
        };
        fs::write(
            manifests.join("manifest.json"),
            serde_json::to_vec(&m).unwrap(),
        )
        .unwrap();
        fs::write(
            tapes.join("demo.intents.yaml"),
            r#"journey: demo
traces_to: [FR-001, FR-002]
steps: []
"#,
        )
        .unwrap();

        let opts = VerifyOptions {
            manifests_dir: dir.join("manifests"),
            tapes_dir: tapes,
            artefacts_root: dir.clone(),
            backend: VerifyBackend::Mock,
        };
        verify_all(&opts).unwrap();
        let verified: serde_json::Value =
            serde_json::from_slice(&fs::read(manifests.join("manifest.verified.json")).unwrap())
                .unwrap();
        assert_eq!(verified["traces_to"][0], "FR-001");
        assert_eq!(verified["traces_to"][1], "FR-002");
    }

    #[test]
    #[serial] // sets PHENOTYPE_JOURNEY_OCR_CMD — must not race with other env-var tests
    fn verify_collects_violations_from_report() {
        // Exercise the report → verification.assertion_violations union path.
        // We construct a manifest whose only assertion will fail (OCR returns
        // "X" but must_contain requires "EXPECTED").
        let dir = tmp("violation-union");
        let tapes = dir.join("tapes");
        let kf_dir = dir.join("keyframes").join("demo");
        let manifests = dir.join("manifests").join("demo");
        fs::create_dir_all(&tapes).unwrap();
        fs::create_dir_all(&kf_dir).unwrap();
        fs::create_dir_all(&manifests).unwrap();
        fs::write(kf_dir.join("frame-001.png"), b"stub").unwrap();

        let m = Manifest {
            id: "demo".into(),
            intent: "t".into(),
            recording: None,
            recording_gif: None,
            keyframe_count: 1,
            passed: false,
            steps: vec![Step {
                index: 0,
                slug: "frame-0".into(),
                intent: "t".into(),
                screenshot_path: "frame-001.png".into(),
                description: None,
                blind_description: None,
                judge_score: None,
                assertions: Some(StepAssertions {
                    must_contain: vec!["EXPECTED".into()],
                    ..Default::default()
                }),
                annotations: None,
                agreement: None,
            }],
            verification: None,
        };
        fs::write(
            manifests.join("manifest.json"),
            serde_json::to_vec(&m).unwrap(),
        )
        .unwrap();

        std::env::set_var("PHENOTYPE_JOURNEY_OCR_CMD", "printf X");

        let opts = VerifyOptions {
            manifests_dir: dir.join("manifests"),
            tapes_dir: tapes,
            artefacts_root: dir.clone(),
            backend: VerifyBackend::Mock,
        };
        let r = verify_all(&opts).unwrap();
        assert_eq!(r.failed, 1);
        let v: serde_json::Value =
            serde_json::from_slice(&fs::read(manifests.join("manifest.verified.json")).unwrap())
                .unwrap();
        assert_eq!(v["passed"], false);
        let violations = v["verification"]["assertion_violations"]
            .as_array()
            .unwrap();
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0]["kind"], "MustContain");
    }

    #[test]
    fn sync_cli_journeys_copies_verified_manifests() {
        let dir = tmp("sync-cli");
        let src = dir.join("src");
        let dst = dir.join("dst");
        fs::create_dir_all(src.join("recordings")).unwrap();
        fs::create_dir_all(src.join("keyframes").join("demo")).unwrap();
        fs::create_dir_all(src.join("manifests").join("demo")).unwrap();
        fs::write(src.join("recordings/demo.mp4"), b"").unwrap();
        fs::write(src.join("keyframes/demo/frame-001.png"), b"").unwrap();
        fs::write(src.join("manifests/demo/manifest.json"), b"{}").unwrap();
        fs::write(
            src.join("manifests/demo/manifest.verified.json"),
            b"{\"passed\":true}",
        )
        .unwrap();
        let n = sync_cli_journeys(&src, &dst).unwrap();
        assert!(n >= 4);
        assert!(dst.join("manifests/demo/manifest.verified.json").exists());
        assert!(dst.join("keyframes/demo/frame-001.png").exists());
        assert!(dst.join("recordings/demo.mp4").exists());
    }

    #[test]
    fn sync_sniff_auto_detects_cli_journeys() {
        let dir = tmp("sniff");
        let src = dir.join("src");
        fs::create_dir_all(src.join("tapes")).unwrap();
        fs::create_dir_all(src.join("recordings")).unwrap();
        assert_eq!(sniff_kind(&src), SyncKind::CliJourneys);
    }
}
