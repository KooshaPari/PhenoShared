use anyhow::{Context, Result};
use regex::Regex;
use serde_json::Value;
use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};

use crate::types::{
    self, BaselineDelta, BaselineEntry, BaselineFile, Probe, ProbeRunResult, Requirement,
    RequirementResult, workspace_root_of,
};

// ---------------------------------------------------------------------------
// evaluate_requirement
// ---------------------------------------------------------------------------

pub(crate) fn evaluate_requirement(
    req: &Requirement,
    baseline: &mut BaselineFile,
    is_hard: bool,
) -> Result<RequirementResult> {
    if req.skip.unwrap_or(false) {
        return Ok(RequirementResult {
            id: req.id.clone(),
            description: req.description.clone(),
            probe: types::probe_name(req),
            passed: true,
            score: Some(0.0),
            value: Value::Null,
            baseline_comparison: None,
            message: Some("skipped".to_string()),
            skipped: true,
        });
    }

    let result = run_probe(req)?;

    let baseline_delta = compare_with_baseline(req, &result.value, &result.score, baseline);
    Ok(RequirementResult {
        id: req.id.clone(),
        description: req.description.clone(),
        probe: types::probe_name(req),
        passed: if is_hard { result.passed } else { true },
        score: Some(result.score),
        value: result.value,
        baseline_comparison: baseline_delta,
        message: result.message,
        skipped: false,
    })
}

// ---------------------------------------------------------------------------
// Probe dispatchers
// ---------------------------------------------------------------------------

fn run_probe(req: &Requirement) -> Result<ProbeRunResult> {
    match &req.probe {
        Probe::CommandExitCode {
            command,
            args,
            cwd,
            expected_exit_code,
        } => probe_command_exit_code(req, command, args, cwd, *expected_exit_code),
        Probe::FileHashChanged {
            path,
            expected_hash,
            expect_changed,
        } => probe_file_hash_changed(req, path, expected_hash, *expect_changed),
        Probe::FileSizeBytes {
            path,
            expected_min_bytes,
            expected_max_bytes,
        } => probe_file_size_bytes(req, path, *expected_min_bytes, *expected_max_bytes),
        Probe::LocCount {
            path,
            expected_min_lines,
            expected_max_lines,
        } => probe_loc_count(req, path, *expected_min_lines, *expected_max_lines),
        Probe::CommandExtract {
            command,
            args,
            cwd,
            regex,
            jsonpath,
            expected,
            delegate_bench_guard,
        } => probe_command_extract(
            req,
            command,
            args,
            cwd,
            regex,
            jsonpath,
            expected,
            *delegate_bench_guard,
        ),
        Probe::LogAbsent {
            path,
            pattern,
            regex,
            expected_absent,
        } => probe_log_absent(req, path, pattern, *regex, *expected_absent),
    }
}

fn probe_command_exit_code(
    req: &Requirement,
    command: &str,
    args: &[String],
    cwd: &Option<std::path::PathBuf>,
    expected_exit_code: i32,
) -> Result<ProbeRunResult> {
    let output = Command::new(command)
        .args(args)
        .current_dir(cwd.as_deref().unwrap_or(Path::new(".")))
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
    let exit_code = output.ok().and_then(|status| status.code()).unwrap_or(-1);
    let passed = exit_code == expected_exit_code;
    let score = if passed {
        req.weight.unwrap_or(1.0)
    } else {
        0.0
    };

    Ok(ProbeRunResult {
        passed,
        value: Value::from(exit_code),
        score,
        message: Some(format!("expected_exit_code={}", expected_exit_code)),
    })
}

fn probe_file_hash_changed(
    req: &Requirement,
    path: &Path,
    expected_hash: &Option<String>,
    expect_changed: bool,
) -> Result<ProbeRunResult> {
    let hash = types::file_sha(path)?;
    let changed = if let Some(expected) = expected_hash {
        hash != *expected
    } else {
        false
    };
    let passed = if expect_changed { changed } else { !changed };
    let weight = req.weight.unwrap_or(1.0);
    let score = if passed { weight } else { 0.0 };
    Ok(ProbeRunResult {
        passed,
        value: Value::String(hash),
        score,
        message: Some(format!("expect_changed={}", expect_changed)),
    })
}

fn probe_file_size_bytes(
    req: &Requirement,
    path: &Path,
    expected_min_bytes: Option<u64>,
    expected_max_bytes: Option<u64>,
) -> Result<ProbeRunResult> {
    let size = types::file_size(path)?;
    let min_ok = expected_min_bytes.is_none_or(|min| size >= min);
    let max_ok = expected_max_bytes.is_none_or(|max| size <= max);
    let passed = min_ok && max_ok;
    let weight = req.weight.unwrap_or(1.0);
    let score = if passed { weight } else { 0.0 };
    Ok(ProbeRunResult {
        passed,
        value: Value::from(size),
        score,
        message: Some(format!("size={}", size)),
    })
}

fn probe_loc_count(
    req: &Requirement,
    path: &Path,
    expected_min_lines: Option<u64>,
    expected_max_lines: Option<u64>,
) -> Result<ProbeRunResult> {
    let lines = types::count_loc(path)?;
    let min_ok = expected_min_lines.is_none_or(|min| lines >= min);
    let max_ok = expected_max_lines.is_none_or(|max| lines <= max);
    let passed = min_ok && max_ok;
    let weight = req.weight.unwrap_or(1.0);
    let score = if passed { weight } else { 0.0 };
    Ok(ProbeRunResult {
        passed,
        value: Value::from(lines),
        score,
        message: Some(format!("lines={}", lines)),
    })
}

fn probe_command_extract(
    req: &Requirement,
    command: &str,
    args: &[String],
    cwd: &Option<std::path::PathBuf>,
    regex: &Option<String>,
    jsonpath: &Option<String>,
    expected: &Option<Value>,
    delegate_bench_guard: bool,
) -> Result<ProbeRunResult> {
    let output = types::command_output(command, args, cwd.as_deref())?;
    let extracted = match (regex, jsonpath) {
        (Some(pattern), _) => {
            let re = Regex::new(pattern).context("invalid regex")?;
            if let Some(captures) = re.captures(&output) {
                if let Some(first) = captures.get(0) {
                    Value::String(first.as_str().to_string())
                } else {
                    Value::Null
                }
            } else {
                Value::Null
            }
        }
        (_, Some(path_expr)) => types::extract_jsonpath(&output, path_expr)?,
        (None, None) => Value::String(output.trim().to_string()),
    };

    let passed = match expected {
        Some(expected_value) => extracted == *expected_value,
        None => !extracted.is_null(),
    };

    let score = if passed {
        req.weight.unwrap_or(1.0)
    } else {
        0.0
    };

    let mut detail = format!("command_extract expected={:?}", expected);
    if delegate_bench_guard {
        match crate::run_bench_guard_probe(workspace_root_of(cwd)) {
            Ok(bench_msg) => {
                detail.push_str(&format!(" | delegated_bench_guard={}", bench_msg));
            }
            Err(err) => {
                detail.push_str(&format!(" | delegated_bench_guard=FAILED: {}", err));
            }
        }
    }

    Ok(ProbeRunResult {
        passed,
        value: extracted,
        score,
        message: Some(detail),
    })
}

fn probe_log_absent(
    req: &Requirement,
    path: &Path,
    pattern: &str,
    use_regex: bool,
    expected_absent: bool,
) -> Result<ProbeRunResult> {
    let text = fs::read_to_string(path)
        .with_context(|| format!("failed to read {}", path.display()))?;
    let is_present = if use_regex {
        let re = Regex::new(pattern).context("invalid regex")?;
        re.is_match(&text)
    } else {
        text.contains(pattern)
    };
    let passed = (expected_absent && !is_present) || (!expected_absent && is_present);
    let weight = req.weight.unwrap_or(1.0);
    let score = if passed { weight } else { 0.0 };
    Ok(ProbeRunResult {
        passed,
        value: Value::Bool(!is_present),
        score,
        message: Some(format!("pattern_present={}", is_present)),
    })
}

// ---------------------------------------------------------------------------
// Baseline comparison
// ---------------------------------------------------------------------------

pub(crate) fn compare_with_baseline(
    req: &Requirement,
    value: &Value,
    score: &f64,
    baseline: &mut BaselineFile,
) -> Option<BaselineDelta> {
    let previous = baseline.requirements.get(&req.id).cloned();
    let changed = previous.as_ref().is_none_or(|entry| entry.value != *value);
    let ratio = match (previous.as_ref().map(|entry| &entry.value), value) {
        (Some(Value::Number(base)), Value::Number(cur)) => {
            let base = base.as_f64().unwrap_or(0.0);
            let current = cur.as_f64().unwrap_or(0.0);
            if base == 0.0 {
                None
            } else {
                Some((current / base).clamp(0.0, 1.5))
            }
        }
        _ => None,
    };

    baseline.requirements.insert(
        req.id.clone(),
        BaselineEntry {
            value: value.clone(),
            score: Some(*score),
        },
    );

    previous.map(|entry| BaselineDelta {
        baseline: entry.value,
        changed,
        score_ratio: ratio,
    })
}
