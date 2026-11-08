use anyhow::{Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
use phenotype_journey_core::{
    assertions::{run_on_manifest, AssertionReport, ViolationKind},
    manifest_schema,
    pipeline::{
        extract_keyframes, record_all, sync_artefacts, verify_all, ExtractOptions, RecordOptions,
        SyncKind, SyncOptions, VerifyBackend, VerifyOptions,
    },
    validate_manifest, verify_manifest, Annotation, AnnotationKind, AnnotationStyle, Manifest,
    Step, StepAssertions, VerifyMode,
};
use phenotype_journeys_observability::prelude::{info, init_tracing, instrument};
use serde::Deserialize;
use std::path::{Path, PathBuf};

#[derive(Parser, Debug)]
#[command(
    name = "phenotype-journey",
    version,
    about = "Phenotype journey harness"
)]
struct Cli {
    #[command(subcommand)]
    command: Cmd,
}

#[derive(Subcommand, Debug)]
enum Cmd {
    /// Record a single VHS tape and emit a journey manifest stub.
    Record {
        #[arg(long)]
        tape: Option<PathBuf>,
        /// Output directory for a single recording.
        #[arg(long, default_value = "./out")]
        out: PathBuf,
        /// Batch mode: record every `*.tape` under this dir and emit
        /// `record-summary.json`. Replaces `record-all.sh`.
        #[arg(long)]
        tapes_dir: Option<PathBuf>,
        /// Output dir for batch-mode recordings (*.gif + *.mp4).
        #[arg(long)]
        recordings_dir: Option<PathBuf>,
        /// Batch-mode tape filter (basename, no extension).
        #[arg(long, value_name = "NAME")]
        only: Option<String>,
        /// Max concurrent tapes (default 1 — VHS serialises on PTY).
        #[arg(long, default_value_t = 1)]
        parallel: usize,
        /// Working directory for `vhs` invocations (tapes use relative paths).
        #[arg(long)]
        cwd: Option<PathBuf>,
        /// Extra PATH entries (colon-separated) prepended for `vhs`.
        #[arg(long, value_delimiter = ':')]
        path_prepend: Vec<PathBuf>,
        /// Where to write `record-summary.json` (default: `<tapes_dir>/..` root).
        #[arg(long)]
        summary_path: Option<PathBuf>,
    },
    /// Extract keyframes from one or all MP4 recordings. Replaces
    /// `extract-keyframes.sh`. Always clears stale frames before extracting.
    ExtractKeyframes {
        #[arg(long)]
        recordings_dir: PathBuf,
        #[arg(long)]
        keyframes_dir: PathBuf,
        /// Limit to one tape (basename, no extension).
        #[arg(long)]
        tape: Option<String>,
        /// Fallback threshold — if fewer I-frames than this are found, switch
        /// to 1 fps sampling.
        #[arg(long, default_value_t = 3)]
        min_iframes: usize,
    },
    /// Run Claude describe+judge verification on an existing manifest (single file)
    /// or a full manifests/ tree (batch mode, replaces verify-manifests.sh).
    Verify {
        /// Single-manifest mode: path to manifest.json.
        manifest: Option<PathBuf>,
        /// Force live Anthropic API (requires ANTHROPIC_API_KEY and `live` feature at build time).
        #[arg(long)]
        live: bool,

        // --- First-class ergonomic surface for the phenodocs CI gate ---
        /// Explicit single-manifest path (alias of the positional `manifest`).
        /// Required by the phenodocs PR #168 gate contract; preferred over
        /// the positional form for script-friendly invocations.
        #[arg(long, value_name = "PATH", conflicts_with = "manifest")]
        manifest_path: Option<PathBuf>,
        /// Docs root containing the journey artefacts (recordings/,
        /// cli-journeys/keyframes/, manifests/). When supplied, used as the
        /// artefacts root for the verify pipeline so the gate can resolve
        /// `<docs-root>/cli-journeys/keyframes/<id>/frame-###.png` paths.
        #[arg(long, value_name = "PATH")]
        docs_root: Option<PathBuf>,

        // --- Batch mode (replaces verify-manifests.sh) ---
        /// Batch: directory containing `<journey>/manifest.json` subdirs.
        #[arg(long)]
        manifests_dir: Option<PathBuf>,
        /// Batch: tapes dir (for `<journey>.intents.yaml` overlay).
        #[arg(long)]
        tapes_dir: Option<PathBuf>,
        /// Batch: artefacts root (where `keyframes/<journey>/` lives).
        #[arg(long)]
        artefacts: Option<PathBuf>,
        /// Batch: force mock backend (built-in canned responder). Default if
        /// ANTHROPIC_API_KEY is unset.
        #[arg(long)]
        mock: bool,
        /// Batch: force real Anthropic API backend.
        #[arg(long)]
        api: bool,
    },
    /// Validate a manifest against the canonical JSONSchema.
    Validate { manifest: PathBuf },
    /// Sync journey/doc artefacts from a source dir into a destination dir.
    /// Replaces docs-site sync-*.sh scripts.
    Sync {
        #[arg(long)]
        from: PathBuf,
        #[arg(long)]
        to: PathBuf,
        /// Sync preset. `auto` inspects the source layout.
        #[arg(long, value_enum, default_value_t = CliSyncKind::Auto)]
        kind: CliSyncKind,
    },
    /// Emit the canonical JSONSchema for manifests.
    Schema,
    /// Scan every `manifest.json` under one or more roots and fail if any
    /// lacks a sibling `manifest.verified.json`. Hard gate for CI/push.
    ///
    /// Example:
    ///   phenotype-journey check-verified \
    ///     --root docs-site/public --root apps
    CheckVerified {
        /// One or more roots to scan recursively for `manifests/<id>/manifest.json`.
        #[arg(long, required = true)]
        root: Vec<PathBuf>,
    },
    /// Run ground-truth assertions against keyframes (OCR + sentinel checks).
    ///
    /// Reads `<tape>.intents.yaml` (sibling to the manifest's tape) to pull
    /// per-step assertions, OCR's the matching keyframes, and prints a
    /// per-step report. With `--strict`, exits non-zero on any violation.
    Assert {
        manifest: PathBuf,
        /// Artefacts root containing `keyframes/<journey>/frame-*.png`.
        /// Defaults to the manifest's parent-of-parent (i.e. `apps/cli-journeys/`).
        #[arg(long)]
        artefacts: Option<PathBuf>,
        /// Optional explicit path to the intents YAML.
        /// Default: `<artefacts>/tapes/<journey>.intents.yaml`.
        #[arg(long)]
        intents: Option<PathBuf>,
        /// Exit non-zero on any violation.
        #[arg(long)]
        strict: bool,
    },
    /// Auto-generate bounding-box annotations for every keyframe in a manifest.
    ///
    /// `tesseract` mode runs `tesseract <frame> - tsv` and emits one annotation
    /// per detected text region (line-level by default, or per-word with
    /// `--ocr-words`). `vlm` mode is a stub for future Anthropic-vision calls.
    Annotate {
        manifest: PathBuf,
        /// Annotation provider.
        #[arg(long, value_enum, default_value_t = AnnotateProvider::Tesseract)]
        provider: AnnotateProvider,
        /// Emit one annotation per WORD (noisier); default is per-line.
        #[arg(long)]
        ocr_words: bool,
        /// Artefacts root containing `keyframes/<journey>/frame-*.png`.
        /// Defaults to the manifest's parent-of-parent-of-parent.
        #[arg(long)]
        artefacts: Option<PathBuf>,
        /// Minimum tesseract confidence (0-100) to keep an annotation.
        #[arg(long, default_value_t = 60)]
        min_conf: i32,
        /// Where to write annotations.
        #[arg(long, value_enum, default_value_t = AnnotateTarget::Stdout)]
        to: AnnotateTarget,
        /// When `--to yaml`, the intents YAML to merge into.
        /// Default: `<artefacts>/tapes/<journey>.intents.yaml`.
        #[arg(long)]
        yaml: Option<PathBuf>,
    },
}

#[derive(Copy, Clone, Debug, ValueEnum, PartialEq, Eq)]
enum AnnotateProvider {
    Tesseract,
    Vlm,
}

#[derive(Copy, Clone, Debug, ValueEnum, PartialEq, Eq)]
enum AnnotateTarget {
    /// Print the annotated manifest JSON to stdout.
    Stdout,
    /// Rewrite `manifest.verified.json` sibling to the input manifest.
    Manifest,
    /// Merge back into the intents YAML (Path-A authoring).
    Yaml,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
enum CliSyncKind {
    CliJourneys,
    GuiJourneys,
    StreamlitJourneys,
    Adrs,
    Research,
    Auto,
}

impl From<CliSyncKind> for SyncKind {
    fn from(k: CliSyncKind) -> Self {
        match k {
            CliSyncKind::CliJourneys => SyncKind::CliJourneys,
            CliSyncKind::GuiJourneys => SyncKind::GuiJourneys,
            CliSyncKind::StreamlitJourneys => SyncKind::StreamlitJourneys,
            CliSyncKind::Adrs => SyncKind::Adrs,
            CliSyncKind::Research => SyncKind::Research,
            CliSyncKind::Auto => SyncKind::Auto,
        }
    }
}

#[instrument(skip_all, fields(command = "main"))]
fn main() -> Result<()> {
    let otlp_endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:4317".to_string());
    // Retain guard until process exit so SdkTracerProvider::shutdown flushes spans.
    let _otel_guard = init_tracing("phenotype-journey", &otlp_endpoint)
        .context("failed to initialise OTLP tracing")?;
    info!(
        version = env!("CARGO_PKG_VERSION"),
        "phenotype-journey starting"
    );
    let cli = Cli::parse();
    match cli.command {
        Cmd::Record {
            tape,
            out,
            tapes_dir,
            recordings_dir,
            only,
            parallel,
            cwd,
            path_prepend,
            summary_path,
        } => cmd_record_dispatch(
            tape,
            out,
            tapes_dir,
            recordings_dir,
            only,
            parallel,
            cwd,
            path_prepend,
            summary_path,
        ),
        Cmd::ExtractKeyframes {
            recordings_dir,
            keyframes_dir,
            tape,
            min_iframes,
        } => cmd_extract_keyframes(recordings_dir, keyframes_dir, tape, min_iframes),
        Cmd::Verify {
            manifest,
            live,
            manifest_path,
            docs_root,
            manifests_dir,
            tapes_dir,
            artefacts,
            mock,
            api,
        } => cmd_verify_dispatch(VerifyDispatchArgs {
            manifest,
            live,
            manifest_path,
            docs_root,
            manifests_dir,
            tapes_dir,
            artefacts,
            mock,
            api,
        }),
        Cmd::Validate { manifest } => cmd_validate(manifest),
        Cmd::Sync { from, to, kind } => cmd_sync(from, to, kind.into()),
        Cmd::Schema => cmd_schema(),
        Cmd::CheckVerified { root } => cmd_check_verified(root),
        Cmd::Assert {
            manifest,
            artefacts,
            intents,
            strict,
        } => cmd_assert(manifest, artefacts, intents, strict),
        Cmd::Annotate {
            manifest,
            provider,
            ocr_words,
            artefacts,
            min_conf,
            to,
            yaml,
        } => cmd_annotate(manifest, provider, ocr_words, artefacts, min_conf, to, yaml),
    }
}

#[allow(clippy::too_many_arguments)]
fn cmd_record_dispatch(
    tape: Option<PathBuf>,
    out: PathBuf,
    tapes_dir: Option<PathBuf>,
    recordings_dir: Option<PathBuf>,
    only: Option<String>,
    parallel: usize,
    cwd: Option<PathBuf>,
    path_prepend: Vec<PathBuf>,
    summary_path: Option<PathBuf>,
) -> Result<()> {
    if let Some(tapes) = tapes_dir {
        let recordings = recordings_dir
            .ok_or_else(|| anyhow::anyhow!("--recordings-dir required with --tapes-dir"))?;
        let opts = RecordOptions {
            tapes_dir: tapes.clone(),
            recordings_dir: recordings,
            tape: only,
            cwd,
            parallel,
            extra_path: path_prepend,
        };
        let summary = record_all(&opts).with_context(|| "record_all failed")?;
        let default_summary = tapes
            .parent()
            .map(|p| p.join("record-summary.json"))
            .unwrap_or_else(|| PathBuf::from("record-summary.json"));
        let dest = summary_path.unwrap_or(default_summary);
        std::fs::write(&dest, serde_json::to_vec_pretty(&summary)?)?;
        println!(
            "Recorded {}/{} tapes ({} failed). Summary: {}",
            summary.passed,
            summary.total_tapes,
            summary.failed,
            dest.display()
        );
        if summary.failed > 0 {
            anyhow::bail!("{} tape(s) failed to record", summary.failed);
        }
        Ok(())
    } else {
        let tape = tape.ok_or_else(|| anyhow::anyhow!("--tape or --tapes-dir required"))?;
        cmd_record(tape, out)
    }
}

fn cmd_extract_keyframes(
    recordings_dir: PathBuf,
    keyframes_dir: PathBuf,
    tape: Option<String>,
    min_iframes: usize,
) -> Result<()> {
    let opts = ExtractOptions {
        recordings_dir,
        keyframes_dir,
        tape,
        min_iframes,
    };
    let results = extract_keyframes(&opts)?;
    for r in &results {
        println!(
            "  {}: {} keyframes{}",
            r.tape,
            r.keyframes,
            if r.used_fallback {
                " (1fps fallback)"
            } else {
                ""
            }
        );
    }
    println!("Keyframe extraction complete: {} tape(s)", results.len());
    Ok(())
}

/// Arguments for `cmd_verify_dispatch` — grouped to satisfy the
/// `clippy::too_many_arguments` lint while keeping the CLI match arm readable.
struct VerifyDispatchArgs {
    manifest: Option<PathBuf>,
    live: bool,
    manifest_path: Option<PathBuf>,
    docs_root: Option<PathBuf>,
    manifests_dir: Option<PathBuf>,
    tapes_dir: Option<PathBuf>,
    artefacts: Option<PathBuf>,
    mock: bool,
    api: bool,
}

fn cmd_verify_dispatch(args: VerifyDispatchArgs) -> Result<()> {
    let VerifyDispatchArgs {
        manifest,
        live,
        manifest_path,
        docs_root,
        manifests_dir,
        tapes_dir,
        artefacts,
        mock,
        api,
    } = args;
    // First-class surface for the phenodocs CI gate: `--manifest` (alias
    // `--manifest-path`) + `--docs-root` resolves the artefacts root
    // unambiguously. Wired through `cmd_verify_with_root` so the docs root
    // also drives the assertion engine's keyframe lookup.
    if let Some(mp) = manifest_path.or(manifest.clone()) {
        return cmd_verify_with_root(mp, live, docs_root);
    }

    if let Some(mdir) = manifests_dir {
        let tapes = tapes_dir
            .ok_or_else(|| anyhow::anyhow!("--tapes-dir required with --manifests-dir"))?;
        let art = artefacts
            .or_else(|| mdir.parent().map(|p| p.to_path_buf()))
            .ok_or_else(|| anyhow::anyhow!("could not derive --artefacts root"))?;
        let backend = if api {
            VerifyBackend::Api
        } else if mock {
            VerifyBackend::Mock
        } else if std::env::var("ANTHROPIC_API_KEY").is_ok() {
            eprintln!("Using real Anthropic API (ANTHROPIC_API_KEY is set)");
            VerifyBackend::Api
        } else {
            eprintln!("ANTHROPIC_API_KEY not set; using built-in mock");
            VerifyBackend::Mock
        };
        let opts = VerifyOptions {
            manifests_dir: mdir,
            tapes_dir: tapes,
            artefacts_root: art,
            backend,
        };
        let r = verify_all(&opts)?;
        println!(
            "Verification complete: {}/{} passed ({} failed)",
            r.total - r.failed,
            r.total,
            r.failed
        );
        if r.failed > 0 {
            anyhow::bail!("{} journey(s) failed verification", r.failed);
        }
        Ok(())
    } else {
        let mpath = manifest
            .ok_or_else(|| anyhow::anyhow!("either `manifest` or --manifests-dir required"))?;
        cmd_verify(mpath, live)
    }
}

fn cmd_record(tape: PathBuf, out: PathBuf) -> Result<()> {
    std::fs::create_dir_all(&out).with_context(|| format!("create {}", out.display()))?;
    let status = std::process::Command::new("vhs")
        .arg(&tape)
        .arg("--output")
        .arg(
            out.join(
                tape.file_stem()
                    .map(|s| s.to_string_lossy().to_string() + ".mp4")
                    .unwrap_or_else(|| "out.mp4".into()),
            ),
        )
        .status()
        .with_context(|| "failed to invoke `vhs` — install charmbracelet/vhs")?;
    anyhow::ensure!(status.success(), "vhs exited non-zero");
    println!("recorded {} -> {}", tape.display(), out.display());
    Ok(())
}

fn cmd_verify(path: PathBuf, live: bool) -> Result<()> {
    let mode = if live {
        VerifyMode::Live
    } else {
        VerifyMode::Mock
    };
    let v = verify_manifest(&path, mode).with_context(|| format!("verify {}", path.display()))?;
    println!("{}", serde_json::to_string_pretty(&v)?);
    Ok(())
}

/// First-class verify path: load the manifest, run the assertion engine
/// (with the docs root as the artefacts root for keyframe lookup), and run
/// the Claude-describe+judge loop. Emits a unified JSON envelope that the
/// phenodocs PR #168 gate parses to decide pass/fail.
///
/// When `docs_root` is `None`, the manifest is verified in mock mode and the
/// assertion engine is skipped (matches the original `cmd_verify` semantics).
fn cmd_verify_with_root(
    manifest_path: PathBuf,
    live: bool,
    docs_root: Option<PathBuf>,
) -> Result<()> {
    let mode = if live {
        VerifyMode::Live
    } else {
        VerifyMode::Mock
    };
    let v = verify_manifest(&manifest_path, mode)
        .with_context(|| format!("verify {}", manifest_path.display()))?;

    // Always materialise a `Manifest` so the assertion engine can run.
    let raw = std::fs::read_to_string(&manifest_path)
        .with_context(|| format!("read {}", manifest_path.display()))?;
    let manifest: Manifest =
        serde_json::from_str(&raw).with_context(|| format!("parse {}", manifest_path.display()))?;

    let mut envelope = serde_json::json!({
        "manifest": manifest_path.display().to_string(),
        "verify": v,
    });

    if let Some(docs) = docs_root {
        // Run the OCR-backed assertion engine against the docs root. The
        // convention is `<docs-root>/cli-journeys/keyframes/<id>/frame-###.png`,
        // but the engine accepts any artefacts root, so we pass the docs root
        // directly — phenodocs layouts co-locate keyframes under
        // `docs/journeys/cli-journeys/keyframes/`, which is a subtree of
        // `docs_root`, and the engine resolves per-journey subdirs.
        match run_on_manifest(&manifest, &docs) {
            Ok(report) => {
                envelope["assertions"] = serde_json::to_value(&report)?;
            }
            Err(e) => {
                // Surface the error but still emit the JSON envelope so the
                // gate can render a useful diagnostic. Non-zero exit comes
                // from the violation check below.
                envelope["assertions_error"] = serde_json::Value::String(e.to_string());
            }
        }
    }

    println!("{}", serde_json::to_string_pretty(&envelope)?);

    // Exit non-zero if the verification or assertions failed.
    if !v.all_intents_passed {
        anyhow::bail!(
            "verify: all_intents_passed=false for {}",
            manifest_path.display()
        );
    }
    if let Some(report) = envelope
        .get("assertions")
        .and_then(|a| a.get("passed"))
        .and_then(|p| p.as_bool())
    {
        if !report {
            anyhow::bail!(
                "verify: assertion violations in {}",
                manifest_path.display()
            );
        }
    }
    Ok(())
}

fn cmd_validate(path: PathBuf) -> Result<()> {
    let raw = std::fs::read_to_string(&path).with_context(|| format!("read {}", path.display()))?;
    let value: serde_json::Value = serde_json::from_str(&raw)?;
    validate_manifest(&value)?;
    println!("ok: {}", path.display());
    Ok(())
}

fn cmd_sync(from: PathBuf, to: PathBuf, kind: SyncKind) -> Result<()> {
    anyhow::ensure!(
        from.is_dir(),
        "--from must be a directory: {}",
        from.display()
    );
    let opts = SyncOptions {
        from,
        to: to.clone(),
        kind,
    };
    let n = sync_artefacts(&opts)?;
    println!("Synced {} items to {}", n, to.display());
    Ok(())
}

fn cmd_schema() -> Result<()> {
    println!("{}", serde_json::to_string_pretty(&manifest_schema())?);
    Ok(())
}

/// Hard gate for CI/push: every `manifest.json` under each root MUST have a
/// sibling `manifest.verified.json`. Prints each offender and exits non-zero
/// if any are missing. Strict by design — not gated by any env var.
fn cmd_check_verified(roots: Vec<PathBuf>) -> Result<()> {
    let mut manifests: Vec<PathBuf> = Vec::new();
    for root in &roots {
        if !root.exists() {
            eprintln!("warn: root does not exist, skipping: {}", root.display());
            continue;
        }
        collect_manifest_jsons(root, &mut manifests)?;
    }
    manifests.sort();

    let mut unverified: Vec<PathBuf> = Vec::new();
    for m in &manifests {
        let sibling = m
            .parent()
            .map(|p| p.join("manifest.verified.json"))
            .unwrap_or_else(|| PathBuf::from("manifest.verified.json"));
        if !sibling.exists() {
            unverified.push(m.clone());
        }
    }

    if unverified.is_empty() {
        println!(
            "check-verified: OK ({} manifests, all have manifest.verified.json)",
            manifests.len()
        );
        return Ok(());
    }

    eprintln!(
        "check-verified: FAIL — {} of {} manifest(s) lack a sibling manifest.verified.json:",
        unverified.len(),
        manifests.len()
    );
    for m in &unverified {
        eprintln!("  missing verified: {}", m.display());
    }
    anyhow::bail!(
        "{} unverified manifest(s); run `phenotype-journey verify --manifests-dir ...` before push",
        unverified.len()
    );
}

/// Recursively walk `root` and append every path that matches
/// `<...>/manifests/<id>/manifest.json`. Skips hidden dirs (`.git`, `node_modules`,
/// `target`, `dist`) to keep the scan fast on large repos.
fn collect_manifest_jsons(root: &Path, out: &mut Vec<PathBuf>) -> Result<()> {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let rd = match std::fs::read_dir(&dir) {
            Ok(rd) => rd,
            Err(_) => continue,
        };
        for entry in rd.flatten() {
            let p = entry.path();
            if p.is_dir() {
                let name = p.file_name().and_then(|s| s.to_str()).unwrap_or("");
                if name.starts_with('.')
                    || matches!(name, "node_modules" | "target" | "dist" | "build")
                {
                    continue;
                }
                stack.push(p);
            } else if p.file_name().and_then(|s| s.to_str()) == Some("manifest.json") {
                // Must live at `<...>/manifests/<id>/manifest.json`.
                let is_manifest = p
                    .parent()
                    .and_then(|parent| parent.parent())
                    .and_then(|grand| grand.file_name())
                    .and_then(|s| s.to_str())
                    == Some("manifests");
                if is_manifest {
                    out.push(p);
                }
            }
        }
    }
    Ok(())
}

fn cmd_assert(
    manifest_path: PathBuf,
    artefacts: Option<PathBuf>,
    intents: Option<PathBuf>,
    strict: bool,
) -> Result<()> {
    let raw = std::fs::read_to_string(&manifest_path)
        .with_context(|| format!("read {}", manifest_path.display()))?;
    let mut manifest: Manifest = serde_json::from_str(&raw)?;

    // Artefacts root defaults to two levels up from manifest.json
    // (manifests/<id>/manifest.json -> <root>).
    let artefacts_root = match artefacts {
        Some(p) => p,
        None => manifest_path
            .parent()
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .ok_or_else(|| anyhow::anyhow!("could not derive artefacts root; pass --artefacts"))?,
    };

    // Intents YAML defaults to <artefacts>/tapes/<journey>.intents.yaml
    let intents_path = intents.unwrap_or_else(|| {
        artefacts_root
            .join("tapes")
            .join(format!("{}.intents.yaml", manifest.id))
    });

    if intents_path.exists() {
        overlay_assertions(&mut manifest, &intents_path)
            .with_context(|| format!("overlay {}", intents_path.display()))?;
    } else {
        eprintln!(
            "warn: no intents YAML at {} — continuing with manifest-embedded assertions only",
            intents_path.display()
        );
    }

    let report = run_on_manifest(&manifest, &artefacts_root)
        .with_context(|| format!("assert {}", manifest.id))?;

    print_report(&report);

    if report.no_assertions {
        eprintln!(
            "warn: journey '{}' has zero steps with assertions — consider adding must_contain / must_not_contain",
            report.journey_id
        );
    }

    if strict && !report.passed {
        anyhow::bail!(
            "{} assertion violation(s) in journey '{}'",
            report.violations.len(),
            report.journey_id
        );
    }
    Ok(())
}

fn print_report(report: &AssertionReport) {
    println!("journey: {}", report.journey_id);
    if report.violations.is_empty() {
        println!("  passed: 0 violations");
    } else {
        println!("  FAILED: {} violation(s)", report.violations.len());
        for v in &report.violations {
            let kind = match v.kind {
                ViolationKind::MustContain => "must_contain",
                ViolationKind::MustContainRegex => "must_contain_regex",
                ViolationKind::MustNotContain => "must_not_contain",
                ViolationKind::ExitCode => "exit_code",
                ViolationKind::InvalidRegex => "invalid_regex",
            };
            println!(
                "    step {}: {} expected={:?} got=\"{}\"",
                v.step_index, kind, v.expected, v.got_snippet
            );
        }
    }
}

#[derive(Debug, Deserialize)]
struct IntentsFile {
    // kept: parsed from YAML to validate shape; not yet wired into the manifest overlay
    #[allow(dead_code)]
    #[serde(default)]
    journey: Option<String>,
    #[serde(default)]
    steps: Vec<IntentStep>,
}

#[derive(Debug, Deserialize)]
struct IntentStep {
    index: u32,
    // kept: parsed from YAML for shape validation; manifest supplies the canonical intent string
    #[serde(default)]
    #[allow(dead_code)]
    intent: Option<String>,
    #[serde(default)]
    assertions: Option<StepAssertions>,
}

/// Overlay per-step `assertions` from the intents YAML onto the manifest's
/// in-memory Steps. Non-destructive: manifest-embedded assertions win when
/// both define the same step.
fn overlay_assertions(manifest: &mut Manifest, intents_path: &Path) -> Result<()> {
    let raw = std::fs::read_to_string(intents_path)?;
    let parsed: IntentsFile = serde_yaml::from_str(&raw)
        .with_context(|| format!("parse yaml {}", intents_path.display()))?;
    for intent in parsed.steps {
        if let Some(a) = intent.assertions {
            if let Some(step) = find_step_mut(&mut manifest.steps, intent.index) {
                if step.assertions.is_none() {
                    step.assertions = Some(a);
                }
            }
        }
    }
    Ok(())
}

fn find_step_mut(steps: &mut [Step], index: u32) -> Option<&mut Step> {
    steps.iter_mut().find(|s| s.index == index)
}

// ---------------------------------------------------------------------------
// annotate (Path-B: auto-generation from OCR / VLM)
// ---------------------------------------------------------------------------

/// Catppuccin Macchiato palette cycled per-annotation when the caller doesn't
/// specify a color. Matches the docs-site theme.
const PALETTE: &[&str] = &[
    "#f38ba8", // red
    "#a6e3a1", // green
    "#f9e2af", // yellow
    "#89b4fa", // blue
    "#cba6f7", // mauve
    "#94e2d5", // teal
    "#fab387", // peach
];

fn cmd_annotate(
    manifest_path: PathBuf,
    provider: AnnotateProvider,
    ocr_words: bool,
    artefacts: Option<PathBuf>,
    min_conf: i32,
    to: AnnotateTarget,
    yaml: Option<PathBuf>,
) -> Result<()> {
    if provider == AnnotateProvider::Vlm {
        // TODO(vlm): wire up Anthropic vision API here. Agent data-labeling
        // pipelines plug in via this subcommand; the tesseract baseline
        // provides initial regions that the VLM can refine/label.
        anyhow::bail!(
            "vlm provider is not yet implemented (tracked: phenotype-journeys#annotate-vlm)"
        );
    }

    let raw = std::fs::read_to_string(&manifest_path)
        .with_context(|| format!("read {}", manifest_path.display()))?;
    let mut manifest: Manifest = serde_json::from_str(&raw)?;

    let artefacts_root = match artefacts {
        Some(p) => p,
        None => manifest_path
            .parent()
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .ok_or_else(|| anyhow::anyhow!("could not derive artefacts root; pass --artefacts"))?,
    };

    let level = if ocr_words {
        TsvLevel::Word
    } else {
        TsvLevel::Line
    };

    let steps_len = manifest.steps.len();
    for step in manifest.steps.iter_mut() {
        let frame = artefacts_root
            .join("keyframes")
            .join(&manifest.id)
            .join(&step.screenshot_path);
        if !frame.exists() {
            eprintln!(
                "warn: skipping step {}: keyframe {} not found",
                step.index,
                frame.display()
            );
            continue;
        }
        let anns = tesseract_annotate(&frame, level, min_conf)
            .with_context(|| format!("tesseract on {}", frame.display()))?;
        if !anns.is_empty() {
            step.annotations = Some(anns);
        }
    }

    match to {
        AnnotateTarget::Stdout => {
            println!("{}", serde_json::to_string_pretty(&manifest)?);
        }
        AnnotateTarget::Manifest => {
            let target = manifest_path
                .parent()
                .map(|p| p.join("manifest.verified.json"))
                .unwrap_or_else(|| PathBuf::from("manifest.verified.json"));
            std::fs::write(&target, serde_json::to_vec_pretty(&manifest)?)?;
            eprintln!("wrote {}", target.display());
        }
        AnnotateTarget::Yaml => {
            let yaml_path = yaml.unwrap_or_else(|| {
                artefacts_root
                    .join("tapes")
                    .join(format!("{}.intents.yaml", manifest.id))
            });
            merge_annotations_into_yaml(&yaml_path, &manifest)
                .with_context(|| format!("merge into {}", yaml_path.display()))?;
            eprintln!("merged annotations into {}", yaml_path.display());
        }
    }

    eprintln!(
        "annotated {} keyframes via tesseract ({} level, min_conf={})",
        steps_len,
        if ocr_words { "word" } else { "line" },
        min_conf
    );
    Ok(())
}

#[derive(Copy, Clone)]
enum TsvLevel {
    Word,
    Line,
}

/// Run `tesseract <frame> - tsv` and synthesise annotations from the TSV
/// output. Tesseract's TSV schema:
///
///     level page_num block_num par_num line_num word_num left top width height conf text
///
/// `level` codes: 1=page 2=block 3=par 4=line 5=word. We aggregate
/// word-level rows into their parent line when `TsvLevel::Line` is selected
/// (tesseract does not emit a line-level bbox directly in TSV; we union the
/// word bboxes per (block,par,line) triple).
fn tesseract_annotate(frame: &Path, level: TsvLevel, min_conf: i32) -> Result<Vec<Annotation>> {
    let out = std::process::Command::new("tesseract")
        .arg(frame)
        .arg("-")
        .arg("tsv")
        .output()
        .with_context(|| "failed to invoke `tesseract` — install with `brew install tesseract`")?;
    if !out.status.success() {
        anyhow::bail!(
            "tesseract exited non-zero on {}: {}",
            frame.display(),
            String::from_utf8_lossy(&out.stderr)
        );
    }
    let tsv = String::from_utf8_lossy(&out.stdout);
    parse_tesseract_tsv(&tsv, level, min_conf)
}

/// Pure-function TSV parser (exposed for tests — private helper).
fn parse_tesseract_tsv(tsv: &str, level: TsvLevel, min_conf: i32) -> Result<Vec<Annotation>> {
    let mut lines = tsv.lines();
    let header = lines.next().unwrap_or("");
    // Accept either tab- or whitespace-separated header.
    if !header.starts_with("level") {
        // Non-TSV output (e.g. plain text fallback). Return empty.
        return Ok(Vec::new());
    }

    // (block, par, line) -> (x0, y0, x1, y1, words)
    use std::collections::BTreeMap;
    // Key: (block_idx, par_idx, line_idx). Value: (x0, y0, x1, y1, word_list).
    type LineKey = (i32, i32, i32);
    type LineVal = (i32, i32, i32, i32, Vec<String>);
    let mut lines_map: BTreeMap<LineKey, LineVal> = BTreeMap::new();
    let mut words: Vec<Annotation> = Vec::new();
    let mut palette_idx: usize = 0;

    for row in lines {
        let cols: Vec<&str> = row.split('\t').collect();
        if cols.len() < 12 {
            continue;
        }
        let lvl: i32 = cols[0].parse().unwrap_or(0);
        if lvl != 5 {
            continue; // only word rows carry text + bbox.
        }
        let block: i32 = cols[2].parse().unwrap_or(0);
        let par: i32 = cols[3].parse().unwrap_or(0);
        let line: i32 = cols[4].parse().unwrap_or(0);
        let left: i32 = cols[6].parse().unwrap_or(0);
        let top: i32 = cols[7].parse().unwrap_or(0);
        let width: i32 = cols[8].parse().unwrap_or(0);
        let height: i32 = cols[9].parse().unwrap_or(0);
        // Newer tesseract versions emit floats (e.g. `93.277351`) in the conf
        // column; older versions emit integers. Accept both via f32.
        let conf: i32 = cols[10].parse::<f32>().map(|f| f as i32).unwrap_or(-1);
        let text = cols[11].trim().to_string();
        if text.is_empty() || conf < min_conf || width <= 0 || height <= 0 {
            continue;
        }

        match level {
            TsvLevel::Word => {
                words.push(Annotation {
                    bbox: [
                        left.max(0) as u32,
                        top.max(0) as u32,
                        width as u32,
                        height as u32,
                    ],
                    label: text,
                    color: Some(PALETTE[palette_idx % PALETTE.len()].to_string()),
                    style: AnnotationStyle::Solid,
                    note: Some(format!("tesseract conf={conf}")),
                    kind: AnnotationKind::Highlight,
                });
                palette_idx += 1;
            }
            TsvLevel::Line => {
                let entry = lines_map.entry((block, par, line)).or_insert((
                    i32::MAX,
                    i32::MAX,
                    0,
                    0,
                    Vec::new(),
                ));
                entry.0 = entry.0.min(left);
                entry.1 = entry.1.min(top);
                entry.2 = entry.2.max(left + width);
                entry.3 = entry.3.max(top + height);
                entry.4.push(text);
            }
        }
    }

    if matches!(level, TsvLevel::Line) {
        for (_, (x0, y0, x1, y1, ws)) in lines_map {
            let label = ws.join(" ");
            if label.is_empty() {
                continue;
            }
            let w = (x1 - x0).max(1);
            let h = (y1 - y0).max(1);
            words.push(Annotation {
                bbox: [x0.max(0) as u32, y0.max(0) as u32, w as u32, h as u32],
                label: truncate(&label, 64),
                color: Some(PALETTE[palette_idx % PALETTE.len()].to_string()),
                style: AnnotationStyle::Solid,
                note: Some(format!("tesseract line: {label}")),
                kind: AnnotationKind::Region,
            });
            palette_idx += 1;
        }
    }

    Ok(words)
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        let t: String = s.chars().take(max - 1).collect();
        format!("{t}…")
    }
}

/// Merge a manifest's newly-generated annotations back into the intents YAML,
/// preserving existing keys. Non-destructive: only replaces the `annotations`
/// key under each matching `index`, and appends new step entries as needed.
fn merge_annotations_into_yaml(yaml_path: &Path, manifest: &Manifest) -> Result<()> {
    use serde_yaml::{Mapping, Value};

    let raw = if yaml_path.exists() {
        std::fs::read_to_string(yaml_path)?
    } else {
        format!("journey: {}\nsteps: []\n", manifest.id)
    };
    let mut doc: Value = serde_yaml::from_str(&raw).unwrap_or(Value::Mapping(Mapping::new()));
    if doc.is_null() {
        doc = Value::Mapping(Mapping::new());
    }
    let map = doc.as_mapping_mut().ok_or_else(|| {
        anyhow::anyhow!("{}: top-level YAML must be a mapping", yaml_path.display())
    })?;

    // Ensure steps: is a sequence.
    let steps_key = Value::String("steps".into());
    let steps_val = map
        .entry(steps_key.clone())
        .or_insert(Value::Sequence(Vec::new()));
    let steps_seq = steps_val
        .as_sequence_mut()
        .ok_or_else(|| anyhow::anyhow!("steps: must be a sequence"))?;

    for step in &manifest.steps {
        let Some(anns) = &step.annotations else {
            continue;
        };
        // Find existing entry with matching index.
        let found = steps_seq.iter_mut().find(|v| {
            v.as_mapping()
                .and_then(|m| m.get(Value::String("index".into())))
                .and_then(|v| v.as_u64())
                .map(|u| u as u32 == step.index)
                .unwrap_or(false)
        });
        let ann_yaml: Value = serde_yaml::to_value(anns)?;
        if let Some(existing) = found {
            let m = existing.as_mapping_mut().unwrap();
            m.insert(Value::String("annotations".into()), ann_yaml);
        } else {
            let mut new = Mapping::new();
            new.insert(
                Value::String("index".into()),
                Value::Number(step.index.into()),
            );
            new.insert(
                Value::String("intent".into()),
                Value::String(step.intent.clone()),
            );
            new.insert(Value::String("annotations".into()), ann_yaml);
            steps_seq.push(Value::Mapping(new));
        }
    }

    let out = serde_yaml::to_string(&doc)?;
    std::fs::write(yaml_path, out)?;
    Ok(())
}

#[cfg(test)]
mod annotate_tests {
    use super::*;

    #[test]
    fn parse_tsv_line_level_unions_words() {
        let tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n\
                   5\t1\t1\t1\t1\t1\t10\t20\t30\t15\t95\thello\n\
                   5\t1\t1\t1\t1\t2\t45\t20\t25\t15\t90\tworld\n\
                   5\t1\t1\t1\t2\t1\t10\t40\t50\t15\t88\tfoo";
        let anns = parse_tesseract_tsv(tsv, TsvLevel::Line, 60).unwrap();
        assert_eq!(anns.len(), 2);
        // First line: x=10, y=20, spans to x=70, y=35 => 60 x 15.
        assert_eq!(anns[0].bbox, [10, 20, 60, 15]);
        assert_eq!(anns[0].label, "hello world");
        // Second line: single "foo".
        assert_eq!(anns[1].bbox, [10, 40, 50, 15]);
    }

    #[test]
    fn parse_tsv_word_level_keeps_all() {
        let tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n\
                   5\t1\t1\t1\t1\t1\t10\t20\t30\t15\t95\thello\n\
                   5\t1\t1\t1\t1\t2\t45\t20\t25\t15\t90\tworld";
        let anns = parse_tesseract_tsv(tsv, TsvLevel::Word, 60).unwrap();
        assert_eq!(anns.len(), 2);
        assert_eq!(anns[0].label, "hello");
        assert_eq!(anns[1].label, "world");
    }

    #[test]
    fn parse_tsv_skips_low_confidence() {
        let tsv = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n\
                   5\t1\t1\t1\t1\t1\t10\t20\t30\t15\t95\tkeep\n\
                   5\t1\t1\t1\t2\t1\t10\t40\t30\t15\t10\tdrop";
        let anns = parse_tesseract_tsv(tsv, TsvLevel::Line, 60).unwrap();
        assert_eq!(anns.len(), 1);
        assert_eq!(anns[0].label, "keep");
    }
}
