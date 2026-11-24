//! Ledger integrity verification module

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::Path;

/// Errors that can occur during ledger operations
#[derive(Debug, Clone)]
pub enum LedgerError {
    /// Failed to read the ledger file
    ReadError(String),
    /// Failed to write to the ledger file
    WriteError(String),
    /// A ledger line could not be parsed as JSON
    ParseError { line: usize, detail: String },
    /// The prev_hash chain is broken at the given line
    HashChainBroken { line: usize },
    /// The stored rolling_hash does not match the computed hash
    RollingHashMismatch { line: usize },
}

impl std::fmt::Display for LedgerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ReadError(msg) => write!(f, "Failed to read ledger: {msg}"),
            Self::WriteError(msg) => write!(f, "Failed to write ledger: {msg}"),
            Self::ParseError { line, detail } => {
                write!(f, "Parse error at line {line}: {detail}")
            }
            Self::HashChainBroken { line } => {
                write!(f, "Hash chain broken at line {line}")
            }
            Self::RollingHashMismatch { line } => {
                write!(f, "Rolling hash mismatch at line {line}")
            }
        }
    }
}

impl std::error::Error for LedgerError {}

/// Verifies the integrity of the action ledger using rolling hashes
#[derive(Debug, Clone)]
pub struct LedgerVerifier {
    ledger_path: std::path::PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrityReport {
    pub valid: bool,
    pub count: usize,
    pub errors: Vec<String>,
}

/// Strip the `rolling_hash` field from a JSON string for hashing.
/// This ensures the hash is computed over the canonical representation
/// (without the rolling_hash), matching what `record_artifact` hashes.
fn strip_rolling_hash(line: &str) -> String {
    // Find and remove the ,"rolling_hash":"..." suffix
    if let Some(pos) = line.rfind(",\"rolling_hash\":\"") {
        let prefix = &line[..pos];
        // Find the closing } after the rolling_hash value
        if let Some(end) = line[pos..].find('}') {
            format!("{}{}", prefix, &line[pos + end..])
        } else {
            line.to_string()
        }
    } else {
        line.to_string()
    }
}

impl LedgerVerifier {
    pub fn new(ledger_path: &Path) -> Self {
        Self {
            ledger_path: ledger_path.to_path_buf(),
        }
    }

    pub fn verify_integrity(&self) -> IntegrityReport {
        let mut report = IntegrityReport {
            valid: true,
            count: 0,
            errors: Vec::new(),
        };

        if !self.ledger_path.exists() {
            return report;
        }

        let content = match std::fs::read_to_string(&self.ledger_path) {
            Ok(c) => c,
            Err(e) => {
                report.valid = false;
                report
                    .errors
                    .push(format!("Failed to read ledger: {e}"));
                return report;
            }
        };

        let mut last_hash = String::new();

        for (i, line) in content.lines().enumerate() {
            last_hash = self.process_ledger_line(line, i, last_hash, &mut report);
        }

        report
    }

    fn process_ledger_line(
        &self,
        line: &str,
        i: usize,
        last_hash: String,
        report: &mut IntegrityReport,
    ) -> String {
        match serde_json::from_str::<serde_json::Value>(line) {
            Ok(entry) => {
                let prev_hash = entry
                    .get("prev_hash")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                if prev_hash != last_hash {
                    report.valid = false;
                    report.errors.push(format!(
                        "Hash chain broken at line {}: expected prev_hash='{}', got '{}'",
                        i + 1,
                        last_hash,
                        prev_hash
                    ));
                }

                // Hash the canonical form (without rolling_hash) to match record_artifact
                let canonical = strip_rolling_hash(line);
                let mut hasher = Sha256::new();
                hasher.update(canonical.as_bytes());
                let computed_hash = format!("{:x}", hasher.finalize());

                // Verify the stored rolling_hash matches what we computed
                if let Some(stored_hash) = entry.get("rolling_hash").and_then(|v| v.as_str()) {
                    if stored_hash != computed_hash {
                        report.valid = false;
                        report.errors.push(format!(
                            "Rolling hash mismatch at line {}: stored='{}', computed='{}'",
                            i + 1,
                            stored_hash,
                            computed_hash
                        ));
                    }
                }

                report.count += 1;
                computed_hash
            }
            Err(e) => {
                report.valid = false;
                report
                    .errors
                    .push(format!("Parse error at line {}: {}", i + 1, e));
                last_hash
            }
        }
    }
}

/// Immutable incident ledger with rolling hash chain
#[derive(Debug, Clone)]
pub struct IncidentLedger {
    ledger_path: std::path::PathBuf,
    last_hash: String,
}

impl IncidentLedger {
    pub fn new(ledger_path: &Path) -> Self {
        let mut last_hash = String::new();

        if ledger_path.exists() {
            if let Ok(content) = std::fs::read_to_string(ledger_path) {
                for line in content.lines() {
                    last_hash = Self::get_last_hash_from_line(line, &last_hash);
                }
            }
        }

        Self {
            ledger_path: ledger_path.to_path_buf(),
            last_hash,
        }
    }

    fn get_last_hash_from_line(line: &str, current: &str) -> String {
        match serde_json::from_str::<serde_json::Value>(line) {
            Ok(entry) => entry
                .get("rolling_hash")
                .and_then(|v| v.as_str())
                .map(String::from)
                .unwrap_or_else(|| current.to_string()),
            Err(_) => current.to_string(),
        }
    }

    /// Record an artifact entry and return the rolling hash.
    ///
    /// # Errors
    /// Returns `LedgerError::WriteError` if the file cannot be created or
    /// written to. The caller MUST NOT use the returned hash on error, as
    /// the entry was not persisted and the chain would be corrupted.
    pub fn record_artifact(
        &mut self,
        run_id: &str,
        action: &str,
        payload: &HashMap<String, serde_json::Value>,
    ) -> Result<String, LedgerError> {
        let prev_hash = self.last_hash.clone();

        let entry = serde_json::json!({
            "run_id": run_id,
            "action": action,
            "payload": payload,
            "prev_hash": prev_hash,
        });

        let content = serde_json::to_string(&entry)
            .map_err(|e| LedgerError::WriteError(format!("Serialization failed: {e}")))?;

        // Hash the canonical form (without rolling_hash) — this is what
        // LedgerVerifier::process_ledger_line also hashes.
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        let current_hash = format!("{:x}", hasher.finalize());

        // Append rolling_hash as a separate field in the JSON line
        let line = format!(
            "{},\"rolling_hash\":\"{}\"}}\n",
            content.trim_end_matches('}'),
            current_hash
        );

        if let Some(parent) = self.ledger_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| LedgerError::WriteError(format!("Failed to create directory: {e}")))?;
        }

        std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.ledger_path)
            .and_then(|mut f| std::io::Write::write_all(&mut f, line.as_bytes()))
            .map_err(|e| LedgerError::WriteError(format!("Failed to append to ledger: {e}"))?;

        // Only update the chain hash AFTER successful write
        self.last_hash = current_hash.clone();

        Ok(current_hash)
    }

    pub fn get_run_artifacts(&self, run_id: &str) -> Vec<serde_json::Value> {
        let mut out = Vec::new();

        if !self.ledger_path.exists() {
            return out;
        }

        if let Ok(content) = std::fs::read_to_string(&self.ledger_path) {
            for line in content.lines() {
                if let Ok(entry) = serde_json::from_str::<serde_json::Value>(line) {
                    if entry.get("run_id").and_then(|v| v.as_str()) == Some(run_id) {
                        out.push(entry);
                    }
                }
            }
        }

        out
    }

    pub fn verify_integrity(&self) -> bool {
        let verifier = LedgerVerifier::new(&self.ledger_path);
        verifier.verify_integrity().valid
    }
}
