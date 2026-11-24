//! Write distilled continuation facts to long-term episodic memory.

use crate::domain::bundle::{BundleKind, ContinuationBundle};
use crate::ports::{MemoryStore, PortError, TraceSink};

/// A successful episodic-memory write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DistilledMemory {
    /// Identifier returned by the backing memory store.
    pub id: String,
    /// Session-scoped key used for the write.
    pub key: String,
    /// Bundle slice represented by the stored fact.
    pub kind: BundleKind,
}

/// Writes the resumable facts from a compiled bundle into a [`MemoryStore`].
///
/// Intent, contract, and context slices are stored as episodic JSON facts. Keys
/// include the source session id so stores with a shared namespace can retain
/// multiple compilations without losing scope.
pub struct DistillMemoryWriter<'a> {
    memory_store: &'a dyn MemoryStore,
    trace_sink: Option<&'a dyn TraceSink>,
}

impl<'a> DistillMemoryWriter<'a> {
    /// Create a writer without tracing.
    #[must_use]
    pub fn new(memory_store: &'a dyn MemoryStore) -> Self {
        Self { memory_store, trace_sink: None }
    }

    /// Create a writer that reports a span before each distill write.
    #[must_use]
    pub fn with_trace(memory_store: &'a dyn MemoryStore, trace_sink: &'a dyn TraceSink) -> Self {
        Self { memory_store, trace_sink: Some(trace_sink) }
    }

    /// Store intent, contract, and context slices as episodic memories.
    ///
    /// # Errors
    ///
    /// Returns [`PortError::Backend`] when JSON serialization or a memory-store
    /// write fails. Writes completed before an error remain persisted.
    pub fn write(&self, bundle: &ContinuationBundle) -> Result<Vec<DistilledMemory>, PortError> {
        let mut memories = Vec::new();

        for slice in bundle.bundles.iter().filter(|slice| is_episodic(slice.kind)) {
            if let Some(trace_sink) = self.trace_sink {
                trace_sink.span("distill.memory.write");
            }

            let kind = kind_name(slice.kind);
            let key = format!("session/{}/episodic/{kind}", bundle.source_id);
            let content = serde_json::to_string(&serde_json::json!({
                "memory_type": "episodic",
                "session_id": bundle.source_id,
                "kind": kind,
                "fact": slice.body,
            }))
            .map_err(|error| {
                PortError::Backend(format!("serialize episodic {kind} memory: {error}"))
            })?;
            let id = self.memory_store.store(&bundle.source_id, &key, &content)?;
            memories.push(DistilledMemory { id, key, kind: slice.kind });
        }

        Ok(memories)
    }
}

const fn is_episodic(kind: BundleKind) -> bool {
    matches!(kind, BundleKind::Intent | BundleKind::Contract | BundleKind::Context)
}

const fn kind_name(kind: BundleKind) -> &'static str {
    match kind {
        BundleKind::Acceptance => "acceptance",
        BundleKind::Contract => "contract",
        BundleKind::Context => "context",
        BundleKind::Intent => "intent",
        BundleKind::Provenance => "provenance",
        BundleKind::Worklog => "worklog",
        BundleKind::Dedup => "dedup",
    }
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicUsize, Ordering};

    use serde_json::json;

    use super::*;
    use crate::domain::bundle::Bundle;
    use crate::ports::adapters::InMemoryMemoryStore;

    #[derive(Default)]
    struct CountingTraceSink(AtomicUsize);

    impl TraceSink for CountingTraceSink {
        fn span(&self, name: &str) {
            assert_eq!(name, "distill.memory.write");
            self.0.fetch_add(1, Ordering::Relaxed);
        }
    }

    #[test]
    fn writes_session_scoped_episodic_facts_to_memory_store() {
        let store = InMemoryMemoryStore::default();
        let mut bundle = ContinuationBundle::new("session-42");
        bundle.push(Bundle::new(BundleKind::Intent, json!({"goal": "ship it"})));
        bundle.push(Bundle::new(BundleKind::Contract, json!({"constraints": ["no HTTP"]})));
        bundle.push(Bundle::new(BundleKind::Context, json!({"cwd": "/repo"})));
        bundle.push(Bundle::new(BundleKind::Worklog, json!({"message_count": 3})));

        let writes = DistillMemoryWriter::new(&store).write(&bundle).expect("write memories");

        assert_eq!(writes.len(), 3);
        assert_eq!(writes[0].key, "session/session-42/episodic/intent");
        assert_eq!(writes[1].key, "session/session-42/episodic/contract");
        assert_eq!(writes[2].key, "session/session-42/episodic/context");
        let recalled =
            store.recall("session/session-42/episodic/intent", 1).expect("recall intent");
        assert_eq!(recalled.len(), 1);
        assert!(recalled[0].contains(r#""memory_type":"episodic""#));
        assert!(recalled[0].contains(r#""goal":"ship it""#));
        assert!(store.recall("worklog", 10).expect("recall worklog").is_empty());
    }

    #[test]
    fn traces_each_episodic_write() {
        let store = InMemoryMemoryStore::default();
        let trace = CountingTraceSink::default();
        let mut bundle = ContinuationBundle::new("traced");
        bundle.push(Bundle::new(BundleKind::Intent, json!({"goal": "test tracing"})));
        bundle.push(Bundle::new(BundleKind::Acceptance, json!({"ready": true})));

        let writes = DistillMemoryWriter::with_trace(&store, &trace)
            .write(&bundle)
            .expect("write traced memory");

        assert_eq!(writes.len(), 1);
        assert_eq!(trace.0.load(Ordering::Relaxed), 1);
    }
}
