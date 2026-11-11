//! Plugin / extension trait system for SessionLedger.
//!
//! Provides three extension points:
//! - IngestionAdapter — turn raw bytes/JSONL into session records
//! - Exporter — write session records in alternative formats beyond OKF
//! - Port — implement custom storage backends
//!
//! All traits are object-safe so they can be stored as `Arc<dyn Trait>`.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Unique identifier for a plugin (e.g. "jsonl-ingest", "okf-exporter").
pub type PluginId = String;

/// Metadata describing a registered plugin.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginMeta {
    pub id: PluginId,
    pub version: String,
    pub description: String,
}

/// Errors that can occur during plugin execution.
#[derive(Debug)]
pub enum PluginError {
    InvalidPayload(String),
    IoFailure(String),
    NotFound(PluginId),
}

impl std::fmt::Display for PluginError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PluginError::InvalidPayload(msg) => write!(f, "invalid payload: {}", msg),
            PluginError::IoFailure(msg) => write!(f, "I/O failure: {}", msg),
            PluginError::NotFound(id) => write!(f, "plugin not found: {}", id),
        }
    }
}

impl std::error::Error for PluginError {}

/// Trait for ingestion adapters that convert raw input into session records.
pub trait IngestionAdapter: Send + Sync {
    fn id(&self) -> PluginId;
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn description(&self) -> &str {
        ""
    }
    fn accept(&self, content_type: &str) -> bool;
    fn ingest(&self, payload: &[u8]) -> Result<Vec<SessionRecord>, PluginError>;
}

/// A single session record — minimal shape that all adapters produce.
#[derive(Debug, Clone, PartialEq)]
pub struct SessionRecord {
    pub session_id: String,
    pub started_at_unix_millis: u128,
    pub ended_at_unix_millis: u128,
    pub tool: String,
    pub token_count: u64,
    pub events: Vec<SessionEvent>,
}

/// A single event inside a session record.
#[derive(Debug, Clone, PartialEq)]
pub struct SessionEvent {
    pub event_id: String,
    pub timestamp_unix_millis: u128,
    pub kind: String,
    pub payload: HashMap<String, String>,
}

/// Trait for exporters that write session records in alternative formats.
pub trait Exporter: Send + Sync {
    fn id(&self) -> PluginId;
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn description(&self) -> &str {
        ""
    }
    fn export(&self, records: &[SessionRecord]) -> Result<Vec<u8>, PluginError>;
}

/// Trait for storage ports.
pub trait Port: Send + Sync {
    fn id(&self) -> PluginId;
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn description(&self) -> &str {
        ""
    }
    fn put(&self, key: &str, value: &[u8]) -> Result<(), PluginError>;
    fn get(&self, key: &str) -> Result<Option<Vec<u8>>, PluginError>;
    fn delete(&self, key: &str) -> Result<(), PluginError>;
}

/// Central registry — discovers and dispatches to all loaded plugins.
pub struct PluginRegistry {
    ingesters: Mutex<Vec<Arc<dyn IngestionAdapter>>>,
    exporters: Mutex<Vec<Arc<dyn Exporter>>>,
    ports: Mutex<Vec<Arc<dyn Port>>>,
    enabled: Mutex<bool>,
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl PluginRegistry {
    pub fn new() -> Self {
        Self {
            ingesters: Mutex::new(Vec::new()),
            exporters: Mutex::new(Vec::new()),
            ports: Mutex::new(Vec::new()),
            enabled: Mutex::new(true),
        }
    }

    pub fn register_ingester(&self, plugin: Arc<dyn IngestionAdapter>) {
        self.ingesters.lock().unwrap().push(plugin);
    }

    pub fn register_exporter(&self, plugin: Arc<dyn Exporter>) {
        self.exporters.lock().unwrap().push(plugin);
    }

    pub fn register_port(&self, plugin: Arc<dyn Port>) {
        self.ports.lock().unwrap().push(plugin);
    }

    pub fn list_ingesters(&self) -> Vec<PluginMeta> {
        self.ingesters
            .lock()
            .unwrap()
            .iter()
            .map(|p| PluginMeta {
                id: p.id(),
                version: p.version().to_string(),
                description: p.description().to_string(),
            })
            .collect()
    }

    pub fn list_exporters(&self) -> Vec<PluginMeta> {
        self.exporters
            .lock()
            .unwrap()
            .iter()
            .map(|p| PluginMeta {
                id: p.id(),
                version: p.version().to_string(),
                description: p.description().to_string(),
            })
            .collect()
    }

    pub fn list_ports(&self) -> Vec<PluginMeta> {
        self.ports
            .lock()
            .unwrap()
            .iter()
            .map(|p| PluginMeta {
                id: p.id(),
                version: p.version().to_string(),
                description: p.description().to_string(),
            })
            .collect()
    }

    pub fn find_ingester(&self, content_type: &str) -> Option<Arc<dyn IngestionAdapter>> {
        if !*self.enabled.lock().unwrap() {
            return None;
        }
        self.ingesters.lock().unwrap().iter().find(|p| p.accept(content_type)).cloned()
    }

    pub fn total_plugins(&self) -> usize {
        self.ingesters.lock().unwrap().len()
            + self.exporters.lock().unwrap().len()
            + self.ports.lock().unwrap().len()
    }

    pub fn disable(&self) {
        *self.enabled.lock().unwrap() = false;
    }
    pub fn enable(&self) {
        *self.enabled.lock().unwrap() = true;
    }
    pub fn is_enabled(&self) -> bool {
        *self.enabled.lock().unwrap()
    }
}

/// Built-in JSONL ingestion adapter — parses one JSON object per line.
pub struct JsonlIngester;

impl JsonlIngester {
    pub fn new() -> Self {
        Self
    }
}

impl Default for JsonlIngester {
    fn default() -> Self {
        Self::new()
    }
}

impl IngestionAdapter for JsonlIngester {
    fn id(&self) -> PluginId {
        "jsonl".into()
    }
    fn description(&self) -> &str {
        "JSONL one-record-per-line ingestion adapter"
    }
    fn accept(&self, content_type: &str) -> bool {
        content_type.contains("json") || content_type.contains("ndjson")
    }
    fn ingest(&self, payload: &[u8]) -> Result<Vec<SessionRecord>, PluginError> {
        let text = std::str::from_utf8(payload)
            .map_err(|e| PluginError::InvalidPayload(format!("utf-8: {}", e)))?;
        let mut records = Vec::new();
        for (idx, line) in text.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let line_no = idx + 1;
            // Simple parse — accept JSON or fall back to a stub record.
            if line.trim_start().starts_with('{') {
                records.push(SessionRecord {
                    session_id: format!("jsonl-{}", line_no),
                    started_at_unix_millis: 0,
                    ended_at_unix_millis: 0,
                    tool: "jsonl".into(),
                    token_count: 0,
                    events: vec![SessionEvent {
                        event_id: format!("e-{}", line_no),
                        timestamp_unix_millis: 0,
                        kind: "raw".into(),
                        payload: HashMap::from([("line".into(), line.into())]),
                    }],
                });
            }
        }
        Ok(records)
    }
}

/// Built-in CSV exporter — flattens records into a CSV byte stream.
pub struct CsvExporter;

impl CsvExporter {
    pub fn new() -> Self {
        Self
    }
}

impl Default for CsvExporter {
    fn default() -> Self {
        Self::new()
    }
}

impl Exporter for CsvExporter {
    fn id(&self) -> PluginId {
        "csv".into()
    }
    fn description(&self) -> &str {
        "CSV one-row-per-record exporter"
    }
    fn export(&self, records: &[SessionRecord]) -> Result<Vec<u8>, PluginError> {
        let mut buf = String::new();
        buf.push_str(
            "session_id,tool,started_at_unix_millis,ended_at_unix_millis,token_count,event_count\n",
        );
        for r in records {
            buf.push_str(&format!(
                "{},{},{},{},{},{}\n",
                csv_field(&r.session_id),
                csv_field(&r.tool),
                r.started_at_unix_millis,
                r.ended_at_unix_millis,
                r.token_count,
                r.events.len()
            ));
        }
        Ok(buf.into_bytes())
    }
}

fn csv_field(value: &str) -> String {
    if value.bytes().any(|byte| matches!(byte, b',' | b'"' | b'\n' | b'\r')) {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_owned()
    }
}

/// Built-in in-memory port — HashMap-backed storage for tests and ephemeral use.
pub struct InMemoryPort {
    store: Mutex<HashMap<String, Vec<u8>>>,
}

impl InMemoryPort {
    pub fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }
    pub fn len(&self) -> usize {
        self.store.lock().unwrap().len()
    }
    pub fn is_empty(&self) -> bool {
        self.store.lock().unwrap().is_empty()
    }
    pub fn keys(&self) -> Vec<String> {
        self.store.lock().unwrap().keys().cloned().collect()
    }
}

impl Default for InMemoryPort {
    fn default() -> Self {
        Self::new()
    }
}

impl Port for InMemoryPort {
    fn id(&self) -> PluginId {
        "in-memory".into()
    }
    fn description(&self) -> &str {
        "HashMap-backed in-memory port for tests and ephemeral use"
    }
    fn put(&self, key: &str, value: &[u8]) -> Result<(), PluginError> {
        self.store.lock().unwrap().insert(key.into(), value.to_vec());
        Ok(())
    }
    fn get(&self, key: &str) -> Result<Option<Vec<u8>>, PluginError> {
        Ok(self.store.lock().unwrap().get(key).cloned())
    }
    fn delete(&self, key: &str) -> Result<(), PluginError> {
        self.store.lock().unwrap().remove(key);
        Ok(())
    }
}

/// Construct a registry pre-loaded with all built-in adapters/exporters/ports.
pub fn default_registry() -> PluginRegistry {
    let r = PluginRegistry::new();
    r.register_ingester(Arc::new(JsonlIngester::new()));
    r.register_exporter(Arc::new(CsvExporter::new()));
    r.register_port(Arc::new(InMemoryPort::new()));
    r
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_registry_has_all_three_categories() {
        let r = default_registry();
        assert_eq!(r.list_ingesters().len(), 1);
        assert_eq!(r.list_exporters().len(), 1);
        assert_eq!(r.list_ports().len(), 1);
        assert_eq!(r.total_plugins(), 3);
    }

    #[test]
    fn jsonl_ingester_parses_simple_input() {
        let ing = JsonlIngester::new();
        let payload = b"{\"a\":1}\n{\"b\":2}\n";
        let records = ing.ingest(payload).unwrap();
        assert_eq!(records.len(), 2);
        assert_eq!(records[0].session_id, "jsonl-1");
        assert_eq!(records[1].session_id, "jsonl-2");
    }

    #[test]
    fn jsonl_ingester_skips_blank_lines() {
        let ing = JsonlIngester::new();
        let payload = b"{\"a\":1}\n\n{\"b\":2}\n";
        let records = ing.ingest(payload).unwrap();
        assert_eq!(records.len(), 2);
    }

    #[test]
    fn jsonl_ingester_accepts_content_types() {
        let ing = JsonlIngester::new();
        assert!(ing.accept("application/json"));
        assert!(ing.accept("application/x-ndjson"));
        assert!(!ing.accept("text/csv"));
    }

    #[test]
    fn csv_exporter_produces_csv_with_header() {
        let exp = CsvExporter::new();
        let records = vec![SessionRecord {
            session_id: "s1".into(),
            started_at_unix_millis: 1000,
            ended_at_unix_millis: 2000,
            tool: "claude_code".into(),
            token_count: 500,
            events: vec![],
        }];
        let csv = exp.export(&records).unwrap();
        let csv_str = String::from_utf8(csv).unwrap();
        assert!(csv_str.starts_with("session_id,"));
        assert!(csv_str.contains("s1,claude_code"));
    }

    #[test]
    fn csv_exporter_quotes_delimiters_and_newlines() {
        let record = SessionRecord {
            session_id: "s,\"1".into(),
            started_at_unix_millis: 0,
            ended_at_unix_millis: 0,
            tool: "tool\nname".into(),
            token_count: 0,
            events: vec![],
        };
        let csv = String::from_utf8(CsvExporter::new().export(&[record]).unwrap()).unwrap();
        assert!(csv.contains("\"s,\"\"1\",\"tool\nname\",0,0,0,0"));
    }

    #[test]
    fn in_memory_port_roundtrip() {
        let p = InMemoryPort::new();
        p.put("key1", b"hello").unwrap();
        assert_eq!(p.get("key1").unwrap(), Some(b"hello".to_vec()));
        p.delete("key1").unwrap();
        assert_eq!(p.get("key1").unwrap(), None);
    }

    #[test]
    fn in_memory_port_keys() {
        let p = InMemoryPort::new();
        p.put("a", b"1").unwrap();
        p.put("b", b"2").unwrap();
        assert_eq!(p.len(), 2);
        let mut keys = p.keys();
        keys.sort();
        assert_eq!(keys, vec!["a", "b"]);
    }

    #[test]
    fn registry_finds_ingester_by_content_type() {
        let r = default_registry();
        assert!(r.find_ingester("application/json").is_some());
        assert!(r.find_ingester("text/plain").is_none());
    }

    #[test]
    fn registry_disable_blocks_dispatch() {
        let r = default_registry();
        r.disable();
        assert!(!r.is_enabled());
        assert!(r.find_ingester("application/json").is_none());
        r.enable();
        assert!(r.is_enabled());
        assert!(r.find_ingester("application/json").is_some());
    }

    #[test]
    fn plugin_meta_construction() {
        let m = PluginMeta { id: "x".into(), version: "1.0.0".into(), description: "test".into() };
        assert_eq!(m.id, "x");
        assert_eq!(m.version, "1.0.0");
    }

    #[test]
    fn plugin_error_display() {
        let e = PluginError::InvalidPayload("bad bytes".into());
        assert!(format!("{}", e).contains("bad bytes"));
    }

    #[test]
    fn session_event_construction() {
        let mut p = HashMap::new();
        p.insert("key".into(), "value".into());
        let e = SessionEvent {
            event_id: "e1".into(),
            timestamp_unix_millis: 100,
            kind: "tool_use".into(),
            payload: p,
        };
        assert_eq!(e.event_id, "e1");
        assert_eq!(e.payload.get("key"), Some(&"value".to_string()));
    }

    #[test]
    fn multiple_plugins_aggregate() {
        let r = PluginRegistry::new();
        r.register_ingester(Arc::new(JsonlIngester::new()));
        r.register_ingester(Arc::new(JsonlIngester::new()));
        assert_eq!(r.list_ingesters().len(), 2);
    }
}
