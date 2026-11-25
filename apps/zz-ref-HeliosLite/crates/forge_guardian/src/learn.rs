//! P0.1.4 — Learning store for the guardian policy engine.
//!
//! Persists adjudication decisions so the heuristic risk judge can "learn"
//! from history (promote a past decision into an override, or demote a
//! bad call). The intent is a durable, append-only preference layer that
//! the rule engine can consult without invoking the LLM every time.
//!
//! Design decisions (from the P0.1 ADR):
//! - File-backed (NDJSON), not a new DB — single process, low volume, and
//!   aligned with `forge_audit`'s streaming log philosophy.
//! - Append-only with an in-memory index; compaction is a future concern.
//! - Decisions are keyed by `(operation_kind, target)` so a learned
//!   override for `write /Users/x/code` applies to future writes to the
//!   same path regardless of the exact surrounding args.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};

use crate::risk::{RiskFactor, RiskLevel};

/// A single learned decision bound to a `(operation, target)` key.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LearnedDecision {
    /// The normalized operation key, e.g. `write:/Users/x/code`.
    pub key: String,
    /// The override applied. `Allow`/`Deny`/`Confirm` mirror policies.
    pub override_permission: LearnedPermission,
    /// Consecutive times this decision was confirmed by the user/flow.
    pub strength: u32,
    /// Optional human-readable reason (from the confirm prompt).
    pub reason: Option<String>,
    /// Optional risk snapshot at decision time.
    pub risk_level: Option<RiskLevel>,
    /// Optional contributing factor labels (for audit).
    pub factors: Vec<RiskFactor>,
}

/// A neutral, serializable permission override for the learning store.
///
/// This is intentionally separate from the domain `Permission` type so the
/// crate does not need to re-declare it and can stay decoupled.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum LearnedPermission {
    Allow,
    Deny,
    Confirm,
}

impl LearnedPermission {
    pub fn label(&self) -> &'static str {
        match self {
            LearnedPermission::Allow => "allow",
            LearnedPermission::Deny => "deny",
            LearnedPermission::Confirm => "confirm",
        }
    }
}

/// Error type for the learning store.
#[derive(Debug, thiserror::Error)]
pub enum LearnError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("could not parse stored decision on line {line}: {source}")]
    Parse {
        line: usize,
        #[source]
        source: serde_json::Error,
    },
}

/// An in-memory + file-backed learning store.
#[derive(Clone)]
pub struct LearningStore {
    inner: Arc<Mutex<StoreInner>>,
    path: PathBuf,
}

struct StoreInner {
    /// key -> latest learned decision.
    index: HashMap<String, LearnedDecision>,
}

impl std::fmt::Debug for LearningStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LearningStore")
            .field("path", &self.path)
            .field("entries", &self.inner.lock().unwrap().index.len())
            .finish()
    }
}

impl LearningStore {
    /// Open (or create) a learning store at `path`, loading any prior
    /// decisions. Returns an empty store if `path` does not exist yet.
    pub fn open(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref().to_path_buf();
        let entries = if path.exists() {
            load_entries(&path)?
        } else {
            HashMap::new()
        };
        Ok(LearningStore {
            inner: Arc::new(Mutex::new(StoreInner { index: entries })),
            path,
        })
    }

    /// Look up a learned decision for `key`.
    pub fn get(&self, key: &str) -> Option<LearnedDecision> {
        self.inner.lock().unwrap().index.get(key).cloned()
    }

    /// Record a new (or reinforced) decision for `key`.
    ///
    /// If `key` was already learned with the same override, its strength is
    /// incremented (the "promote" path). Otherwise a fresh entry is appended.
    pub fn record(
        &self,
        key: &str,
        override_permission: LearnedPermission,
        reason: Option<String>,
        risk_level: Option<RiskLevel>,
        factors: Vec<RiskFactor>,
    ) -> Result<(), LearnError> {
        let mut inner = self.inner.lock().unwrap();
        let existing = inner.index.get_mut(key);
        let decision = match existing {
            Some(prev) if prev.override_permission == override_permission => {
                prev.strength += 1;
                prev.reason = reason.or_else(|| prev.reason.clone());
                prev.risk_level = risk_level.or(prev.risk_level);
                if !factors.is_empty() {
                    prev.factors = factors;
                }
                prev.clone()
            }
            _ => LearnedDecision {
                key: key.to_string(),
                override_permission,
                strength: 1,
                reason,
                risk_level,
                factors,
            },
        };

        if inner
            .index
            .insert(key.to_string(), decision.clone())
            .is_none()
        {
            // Append to the durable log only on first insertion; reinforcing an
            // existing entry only bumps its in-memory strength.
            append_line(&self.path, &decision)?;
        }

        Ok(())
    }

    /// Remove a learned decision for `key` ("demote"). Compaction of the
    /// backing file is deferred; `demote` only edits the in-memory index.
    pub fn demote(&self, key: &str) -> bool {
        self.inner.lock().unwrap().index.remove(key).is_some()
    }

    /// Number of learned decisions loaded.
    pub fn len(&self) -> usize {
        self.inner.lock().unwrap().index.len()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Iterator over the current decisions (deterministic by key).
    pub fn iter(&self) -> Vec<LearnedDecision> {
        let mut all: Vec<_> = self.inner.lock().unwrap().index.values().cloned().collect();
        all.sort_by(|a, b| a.key.cmp(&b.key));
        all
    }
}

fn load_entries(path: &Path) -> std::io::Result<HashMap<String, LearnedDecision>> {
    let file = std::fs::File::open(path)?;
    let reader = BufReader::new(file);
    let mut index = HashMap::new();
    for (idx, line) in reader.lines().enumerate() {
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let decision: LearnedDecision = serde_json::from_str(trimmed).map_err(|source| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                LearnError::Parse { line: idx + 1, source },
            )
        })?;
        index.insert(decision.key.clone(), decision);
    }
    Ok(index)
}

fn append_line(path: &Path, decision: &LearnedDecision) -> std::io::Result<()> {
    use std::fs::OpenOptions as FsOpenOptions;
    let mut file = FsOpenOptions::new().create(true).append(true).open(path)?;
    writeln!(file, "{}", serde_json::to_string(decision).unwrap())
        .map_err(|_| std::io::Error::other("serialization failed"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp_file(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join("forge_guardian_learn_tests");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(name);
        let _ = std::fs::remove_file(&path);
        path
    }

    #[test]
    fn empty_store_has_no_decisions() {
        let store = LearningStore::open(tmp_file("empty.jsonl")).unwrap();
        assert!(store.is_empty());
        assert_eq!(store.len(), 0);
        assert!(store.get("write:/x").is_none());
    }

    #[test]
    fn record_then_get_roundtrip() {
        let path = tmp_file("roundtrip.jsonl");
        let store = LearningStore::open(&path).unwrap();
        store
            .record(
                "write:/x",
                LearnedPermission::Allow,
                Some("user confirmed".to_string()),
                Some(RiskLevel::Medium),
                Vec::new(),
            )
            .unwrap();
        let got = store.get("write:/x").unwrap();
        assert_eq!(got.override_permission, LearnedPermission::Allow);
        assert_eq!(got.strength, 1);
        assert_eq!(got.reason.as_deref(), Some("user confirmed"));
        assert_eq!(got.risk_level, Some(RiskLevel::Medium));
    }

    #[test]
    fn reinforce_increments_strength_but_writes_once() {
        let path = tmp_file("reinforce.jsonl");
        let store = LearningStore::open(&path).unwrap();
        store
            .record("k", LearnedPermission::Allow, None, None, Vec::new())
            .unwrap();
        store
            .record("k", LearnedPermission::Allow, None, None, Vec::new())
            .unwrap();
        let got = store.get("k").unwrap();
        assert_eq!(got.strength, 2);

        // Re-open from disk: the file only contains one entry, so strength
        // resets to 1 (compaction is deferred per design).
        let reopened = LearningStore::open(&path).unwrap();
        let got2 = reopened.get("k").unwrap();
        assert_eq!(got2.strength, 1);
    }

    #[test]
    fn different_override_replaces_entry() {
        let path = tmp_file("replace.jsonl");
        let store = LearningStore::open(&path).unwrap();
        store
            .record("k", LearnedPermission::Allow, None, None, Vec::new())
            .unwrap();
        store
            .record("k", LearnedPermission::Deny, None, None, Vec::new())
            .unwrap();
        let got = store.get("k").unwrap();
        // In-memory: replaced with strength reset to 1.
        assert_eq!(got.override_permission, LearnedPermission::Deny);
        assert_eq!(got.strength, 1);
    }

    #[test]
    fn demote_removes_entry() {
        let path = tmp_file("demote.jsonl");
        let store = LearningStore::open(&path).unwrap();
        store
            .record("k", LearnedPermission::Allow, None, None, Vec::new())
            .unwrap();
        assert!(store.demote("k"));
        assert!(store.get("k").is_none());
        assert!(!store.demote("k"));
    }

    #[test]
    fn reload_from_disk() {
        let path = tmp_file("reload.jsonl");
        {
            let store = LearningStore::open(&path).unwrap();
            store
                .record("a", LearnedPermission::Allow, None, None, Vec::new())
                .unwrap();
            store
                .record("b", LearnedPermission::Deny, None, None, Vec::new())
                .unwrap();
        }
        let reopened = LearningStore::open(&path).unwrap();
        assert_eq!(reopened.len(), 2);
        assert_eq!(
            reopened.get("a").unwrap().override_permission,
            LearnedPermission::Allow
        );
        assert_eq!(
            reopened.get("b").unwrap().override_permission,
            LearnedPermission::Deny
        );
    }
}
