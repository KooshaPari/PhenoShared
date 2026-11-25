//! Audit store trait + in-memory / on-disk implementations.

use crate::event::AuditEvent;
use chrono::Utc;
use std::io::Write;
use std::path::{Path, PathBuf};
use thiserror::Error;

/// Error type for the audit store.
#[derive(Debug, Error)]
pub enum AuditError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Persistence backend for audit records.
pub trait AuditStore: Send + Sync {
    /// Append a single event (serialized as one JSON line).
    fn append(&mut self, event: &AuditEvent) -> Result<(), AuditError>;
    /// Flush any buffered state to durable storage.
    fn flush(&mut self) -> Result<(), AuditError>;
}

/// In-memory store (for tests and short-lived subagent scopes).
#[derive(Default)]
pub struct MemoryAuditStore {
    lines: Vec<String>,
}

impl MemoryAuditStore {
    pub fn new() -> Self {
        Self::default()
    }
    /// Return a copy of the buffered NDJSON lines.
    pub fn lines(&self) -> &[String] {
        &self.lines
    }
}

impl AuditStore for MemoryAuditStore {
    fn append(&mut self, event: &AuditEvent) -> Result<(), AuditError> {
        let line = serde_json::to_string(event)?;
        self.lines.push(line);
        Ok(())
    }
    fn flush(&mut self) -> Result<(), AuditError> {
        Ok(())
    }
}

/// On-disk store writing NDJSON lines to a file.
pub struct OnDiskAuditStore {
    path: PathBuf,
    writer: std::io::BufWriter<std::fs::File>,
}

impl OnDiskAuditStore {
    /// Open (or create) the audit log at `path` in append mode.
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, AuditError> {
        let file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path.as_ref())?;
        Ok(Self {
            path: path.as_ref().to_path_buf(),
            writer: std::io::BufWriter::new(file),
        })
    }

    /// Return the log file path.
    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl AuditStore for OnDiskAuditStore {
    fn append(&mut self, event: &AuditEvent) -> Result<(), AuditError> {
        let mut line = serde_json::to_string(event)?;
        line.push('\n');
        self.writer.write_all(line.as_bytes())?;
        Ok(())
    }
    fn flush(&mut self) -> Result<(), AuditError> {
        self.writer.flush()?;
        Ok(())
    }
}

/// Build a new `OnDiskAuditStore` under a base data dir, inferring a
/// per-day filename so the log never grows without bound.
#[allow(dead_code)] // public convenience constructor; consumed once audit is wired to callers
pub fn daily_audit_store(base_dir: &Path) -> Result<OnDiskAuditStore, AuditError> {
    std::fs::create_dir_all(base_dir)?;
    let date = Utc::now().format("%Y-%m-%d");
    let path = base_dir.join(format!("audit-{date}.ndjson"));
    OnDiskAuditStore::open(path)
}

/// A convenience sink that appends to the store and is cheap to clone.
#[derive(Clone)]
pub struct AuditSink {
    inner: std::sync::Arc<std::sync::Mutex<Box<dyn AuditStore>>>,
}

impl AuditSink {
    pub fn new(store: Box<dyn AuditStore>) -> Self {
        Self { inner: std::sync::Arc::new(std::sync::Mutex::new(store)) }
    }
    /// Append an event, ignoring errors (non-fatal logging path).
    pub fn record(&self, event: AuditEvent) {
        if let Ok(mut guard) = self.inner.lock() {
            let _ = guard.append(&event);
        }
    }
    /// Flush the underlying store.
    pub fn flush(&self) {
        if let Ok(mut guard) = self.inner.lock() {
            let _ = guard.flush();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::{ToolCallDecision, ToolCallEvent, ToolCallPhase};

    fn sample_tool_event() -> AuditEvent {
        AuditEvent::ToolCall(ToolCallEvent {
            ts_ms: 1_700_000_000_000,
            conversation_id: Some("conv-1".into()),
            agent_id: Some("forge".into()),
            tool: "write".into(),
            phase: ToolCallPhase::End,
            decision: Some(ToolCallDecision::Allowed),
            risk: Some(0.2),
            duration_ms: Some(12),
            summary: Some("wrote src/lib.rs".into()),
        })
    }

    fn sample_spawn_event() -> AuditEvent {
        AuditEvent::SubagentSpawn {
            ts_ms: 1_700_000_000_001,
            parent_id: Some("conv-1".into()),
            child_id: Some("conv-2".into()),
            agent: "muse".into(),
            mode: "fresh".into(),
        }
    }

    #[test]
    fn memory_store_accumulates_ndjson_lines() {
        let mut store = MemoryAuditStore::new();
        store.append(&sample_tool_event()).unwrap();
        store.append(&sample_spawn_event()).unwrap();
        assert_eq!(store.lines().len(), 2);
        // Each line is one valid, tagged JSON object.
        for line in store.lines() {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            assert!(v.get("type").is_some());
        }
    }

    #[test]
    fn audit_event_round_trips_with_tag() {
        let line = serde_json::to_string(&sample_tool_event()).unwrap();
        let v: serde_json::Value = serde_json::from_str(&line).unwrap();
        assert_eq!(v["type"], "tool_call");
        assert_eq!(v["tool"], "write");
        assert_eq!(v["phase"], "end");
        assert_eq!(v["decision"], "allowed");
    }

    #[test]
    fn option_fields_are_skipped_when_absent() {
        let ev = AuditEvent::ToolCall(ToolCallEvent {
            ts_ms: 1,
            conversation_id: None,
            agent_id: None,
            tool: "read".into(),
            phase: ToolCallPhase::Start,
            decision: None,
            risk: None,
            duration_ms: None,
            summary: None,
        });
        let v: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&ev).unwrap()).unwrap();
        assert!(v.get("conversation_id").is_none());
        assert!(v.get("decision").is_none());
        assert!(v.get("risk").is_none());
    }

    #[test]
    fn subagent_spawn_serializes_with_agent_and_mode() {
        let v: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&sample_spawn_event()).unwrap()).unwrap();
        assert_eq!(v["type"], "subagent_spawn");
        assert_eq!(v["agent"], "muse");
        assert_eq!(v["mode"], "fresh");
        assert_eq!(v["parent_id"], "conv-1");
        assert_eq!(v["child_id"], "conv-2");
    }

    #[test]
    fn on_disk_store_writes_and_flushes_ndjson() {
        let dir = std::env::temp_dir().join(format!("forge_audit_test_{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("audit-test.ndjson");
        let mut store = OnDiskAuditStore::open(&path).unwrap();
        store.append(&sample_tool_event()).unwrap();
        store.flush().unwrap();
        let contents = std::fs::read_to_string(&path).unwrap();
        assert_eq!(contents.lines().count(), 1);
        assert!(contents.trim_end().ends_with('}'));
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn sink_records_into_shared_on_disk_store() {
        let dir =
            std::env::temp_dir().join(format!("forge_audit_sink_test_{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("audit-sink.ndjson");
        let sink = AuditSink::new(Box::new(OnDiskAuditStore::open(&path).unwrap()));
        let sink2 = sink.clone();
        sink.record(sample_tool_event());
        sink2.record(sample_spawn_event());
        sink.flush();
        let contents = std::fs::read_to_string(&path).unwrap();
        assert_eq!(contents.lines().count(), 2);
        std::fs::remove_dir_all(&dir).ok();
    }
}
