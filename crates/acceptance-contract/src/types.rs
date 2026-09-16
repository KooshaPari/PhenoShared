use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcceptanceContract {
    #[serde(default)]
    pub hard_requirements: Vec<Requirement>,
    #[serde(default)]
    pub soft_requirements: Vec<Requirement>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Requirement {
    pub id: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub weight: Option<f64>,
    #[serde(default)]
    pub skip: Option<bool>,
    pub probe: Probe,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Probe {
    CommandExitCode {
        command: String,
        #[serde(default)]
        args: Vec<String>,
        #[serde(default)]
        cwd: Option<PathBuf>,
        #[serde(default = "default_exit_code")]
        expected_exit_code: i32,
    },
    FileHashChanged {
        path: PathBuf,
        #[serde(default)]
        expected_hash: Option<String>,
        #[serde(default = "default_file_hash_changed")]
        expect_changed: bool,
    },
    FileSizeBytes {
        path: PathBuf,
        #[serde(default)]
        expected_min_bytes: Option<u64>,
        #[serde(default)]
        expected_max_bytes: Option<u64>,
    },
    LocCount {
        path: PathBuf,
        #[serde(default)]
        expected_min_lines: Option<u64>,
        #[serde(default)]
        expected_max_lines: Option<u64>,
    },
    CommandExtract {
        command: String,
        #[serde(default)]
        args: Vec<String>,
        #[serde(default)]
        cwd: Option<PathBuf>,
        #[serde(default)]
        regex: Option<String>,
        #[serde(default)]
        jsonpath: Option<String>,
        #[serde(default)]
        expected: Option<Value>,
        #[serde(default)]
        delegate_bench_guard: bool,
    },
    LogAbsent {
        path: PathBuf,
        pattern: String,
        #[serde(default)]
        regex: bool,
        #[serde(default)]
        expected_absent: bool,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BaselineFile {
    #[serde(default)]
    pub schema_version: String,
    #[serde(default)]
    pub requirements: HashMap<String, BaselineEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaselineEntry {
    pub value: Value,
    #[serde(default)]
    pub score: Option<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct RequirementResult {
    pub id: String,
    #[serde(default)]
    pub description: Option<String>,
    pub probe: String,
    pub passed: bool,
    pub score: Option<f64>,
    pub value: Value,
    #[serde(default)]
    pub baseline_comparison: Option<BaselineDelta>,
    #[serde(default)]
    pub message: Option<String>,
    #[serde(default)]
    pub skipped: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct BaselineDelta {
    pub baseline: Value,
    pub changed: bool,
    pub score_ratio: Option<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ScoreCard {
    pub contract_path: PathBuf,
    pub hard_requirements: Vec<RequirementResult>,
    pub soft_requirements: Vec<RequirementResult>,
    pub hard_passed: bool,
    pub total_soft_score: f64,
    pub max_soft_score: f64,
    pub soft_percentage: f64,
    #[serde(default)]
    pub delegated_checks: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ExecutionContext {
    pub skip_delegation: bool,
    pub update_baseline: bool,
}

/// Internal result of running a single probe.
pub(crate) struct ProbeRunResult {
    pub passed: bool,
    pub value: Value,
    pub score: f64,
    pub message: Option<String>,
}

// ---------------------------------------------------------------------------
// Serde defaults
// ---------------------------------------------------------------------------

pub(crate) fn default_exit_code() -> i32 {
    0
}

pub(crate) fn default_file_hash_changed() -> bool {
    false
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

pub(crate) fn command_output(
    command: &str,
    args: &[String],
    cwd: Option<&Path>,
) -> Result<String> {
    let mut cmd = Command::new(command);
    cmd.args(args);
    if let Some(dir) = cwd {
        cmd.current_dir(dir);
    }

    let output = cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).output()?;
    if !output.status.success() {
        let code = output
            .status
            .code()
            .map(|code| code.to_string())
            .unwrap_or_else(|| "unknown".to_string());
        return Err(anyhow!("command failed with exit code {}", code));
    }

    let text = String::from_utf8(output.stdout)
        .or_else(|_| String::from_utf8(output.stderr))
        .context("command output was not valid utf-8")?;
    Ok(text)
}

pub(crate) fn count_loc(path: &Path) -> Result<u64> {
    let content =
        fs::read_to_string(path).with_context(|| format!("failed to read {}", path.display()))?;
    Ok(content.lines().count() as u64)
}

pub(crate) fn file_sha(path: &Path) -> Result<String> {
    let bytes = fs::read(path).with_context(|| format!("failed to read {}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    let digest = hasher.finalize();
    let mut hex_str = String::with_capacity(digest.len() * 2);
    for byte in digest.iter() {
        use std::fmt::Write;
        let _ = write!(&mut hex_str, "{byte:02x}");
    }
    Ok(hex_str)
}

pub(crate) fn file_size(path: &Path) -> Result<u64> {
    Ok(fs::metadata(path)
        .with_context(|| format!("failed to stat {}", path.display()))?
        .len())
}

// ---------------------------------------------------------------------------
// File I/O
// ---------------------------------------------------------------------------

pub fn load_contract(path: &Path) -> Result<AcceptanceContract> {
    let bytes = fs::read_to_string(path)
        .with_context(|| format!("failed to read contract {}", path.display()))?;
    serde_yaml::from_str(&bytes)
        .or_else(|_| serde_json::from_str(&bytes).map_err(anyhow::Error::from))
        .with_context(|| format!("failed to parse contract {} as yaml/json", path.display()))
}

pub fn load_baseline(path: &Path) -> Result<BaselineFile> {
    if !path.exists() {
        return Ok(BaselineFile {
            schema_version: "1.0".to_string(),
            requirements: HashMap::new(),
        });
    }

    let bytes = fs::read_to_string(path)
        .with_context(|| format!("failed to read baseline {}", path.display()))?;
    if bytes.trim().is_empty() {
        return Ok(BaselineFile {
            schema_version: "1.0".to_string(),
            requirements: HashMap::new(),
        });
    }

    serde_json::from_str(&bytes)
        .with_context(|| format!("failed to parse baseline {}", path.display()))
}

pub fn save_baseline(path: &Path, baseline: &BaselineFile) -> Result<()> {
    let json = serde_json::to_string_pretty(baseline)?;
    fs::write(path, json)
        .with_context(|| format!("failed to write baseline {}", path.display()))?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Probe utilities
// ---------------------------------------------------------------------------

pub(crate) fn probe_name(req: &Requirement) -> String {
    match &req.probe {
        Probe::CommandExitCode { .. } => "command_exit_code".to_string(),
        Probe::FileHashChanged { .. } => "file_hash_changed".to_string(),
        Probe::FileSizeBytes { .. } => "file_size_bytes".to_string(),
        Probe::LocCount { .. } => "loc_count".to_string(),
        Probe::CommandExtract { .. } => "command_extract".to_string(),
        Probe::LogAbsent { .. } => "log_absent".to_string(),
    }
}

pub(crate) fn extract_jsonpath(raw: &str, expr: &str) -> Result<Value> {
    if expr.trim().is_empty() {
        return Ok(Value::Null);
    }

    let value: Value = serde_json::from_str(raw)
        .with_context(|| "command_extract requested jsonpath but output is not JSON".to_string())?;
    let expr = expr.trim().trim_start_matches('$');
    if expr.is_empty() {
        return Ok(value);
    }

    let mut current = &value;
    let mut offset = 0;
    while offset < expr.len() {
        if expr.as_bytes()[offset] == b'.' {
            offset += 1;
            continue;
        }

        if expr.as_bytes()[offset] == b'[' {
            let end = expr[offset..]
                .find(']')
                .ok_or_else(|| anyhow!("invalid jsonpath: missing ] in {}", expr))?;
            let inner = expr[(offset + 1)..(offset + end)].trim();
            let idx: usize = inner.parse().context("array index must be numeric")?;
            current = current
                .get(idx)
                .ok_or_else(|| anyhow!("jsonpath index {} not found", idx))?;
            offset += end + 1;
            continue;
        }

        let next_dot = expr[offset..].find('.').unwrap_or(expr.len() - offset) + offset;
        let segment = expr[offset..next_dot].trim();
        if segment.is_empty() {
            return Err(anyhow!("invalid jsonpath segment"));
        }

        current = current
            .get(segment)
            .ok_or_else(|| anyhow!("jsonpath segment {} not found", segment))?;
        offset = next_dot;
    }

    Ok(current.clone())
}

pub(crate) fn workspace_root_of(cwd: &Option<PathBuf>) -> &Path {
    cwd.as_deref().unwrap_or_else(|| Path::new("."))
}
