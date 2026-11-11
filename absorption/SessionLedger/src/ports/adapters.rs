//! In-process adapters for the core port traits.
//!
//! These adapters provide a dependency-light MVP for local use and tests.
//! Production deployments can replace them with OmniRoute memory and
//! pheno-tracing integrations without changing domain code.

use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicU64, Ordering},
        RwLock,
    },
};

use super::{Compressor, MemoryStore, PortError, TraceSink};

#[derive(Debug, Clone)]
struct MemoryEntry {
    session_id: String,
    key: String,
    content: String,
}

/// Thread-safe, process-local [`MemoryStore`] backed by a [`HashMap`].
///
/// Recall performs a case-insensitive substring match over the session id,
/// key, and content. Results are returned in insertion order, up to `top_k`.
#[derive(Debug, Default)]
pub struct InMemoryMemoryStore {
    entries: RwLock<HashMap<String, MemoryEntry>>,
    next_id: AtomicU64,
}

impl MemoryStore for InMemoryMemoryStore {
    fn store(&self, session_id: &str, key: &str, content: &str) -> Result<String, PortError> {
        let sequence = self.next_id.fetch_add(1, Ordering::Relaxed);
        let id = format!("memory-{sequence:020}");
        let entry = MemoryEntry {
            session_id: session_id.to_owned(),
            key: key.to_owned(),
            content: content.to_owned(),
        };
        self.entries
            .write()
            .map_err(|error| PortError::Backend(format!("memory store lock poisoned: {error}")))?
            .insert(id.clone(), entry);
        Ok(id)
    }

    fn recall(&self, query: &str, top_k: usize) -> Result<Vec<String>, PortError> {
        if top_k == 0 {
            return Ok(Vec::new());
        }

        let query = query.to_lowercase();
        let entries = self
            .entries
            .read()
            .map_err(|error| PortError::Backend(format!("memory store lock poisoned: {error}")))?;
        let mut matches = entries
            .iter()
            .filter(|(_, entry)| {
                entry.session_id.to_lowercase().contains(&query)
                    || entry.key.to_lowercase().contains(&query)
                    || entry.content.to_lowercase().contains(&query)
            })
            .map(|(id, entry)| (id, entry.content.clone()))
            .collect::<Vec<_>>();
        matches.sort_unstable_by(|left, right| left.0.cmp(right.0));
        Ok(matches.into_iter().take(top_k).map(|(_, content)| content).collect())
    }
}

/// Reversible passthrough compressor for builds without compression enabled.
#[derive(Debug, Default, Clone, Copy)]
pub struct PassthroughCompressor;

impl Compressor for PassthroughCompressor {
    fn compress(&self, data: &str) -> Result<Vec<u8>, PortError> {
        Ok(data.as_bytes().to_vec())
    }

    fn decompress(&self, data: &[u8]) -> Result<String, PortError> {
        String::from_utf8(data.to_vec())
            .map_err(|error| PortError::Backend(format!("passthrough data is not UTF-8: {error}")))
    }
}

/// Zstd-backed [`Compressor`] using a configurable compression level.
#[cfg(feature = "compress")]
#[derive(Debug, Clone, Copy)]
pub struct ZstdCompressor {
    level: i32,
}

#[cfg(feature = "compress")]
impl ZstdCompressor {
    /// Create a compressor with the supplied zstd compression level.
    #[must_use]
    pub const fn new(level: i32) -> Self {
        Self { level }
    }
}

#[cfg(feature = "compress")]
impl Default for ZstdCompressor {
    fn default() -> Self {
        Self::new(3)
    }
}

#[cfg(feature = "compress")]
impl Compressor for ZstdCompressor {
    fn compress(&self, data: &str) -> Result<Vec<u8>, PortError> {
        zstd::stream::encode_all(data.as_bytes(), self.level)
            .map_err(|error| PortError::Backend(format!("zstd compress: {error}")))
    }

    fn decompress(&self, data: &[u8]) -> Result<String, PortError> {
        let decoded = zstd::stream::decode_all(data)
            .map_err(|error| PortError::Backend(format!("zstd decompress: {error}")))?;
        String::from_utf8(decoded)
            .map_err(|error| PortError::Backend(format!("zstd output is not UTF-8: {error}")))
    }
}

/// [`TraceSink`] that emits an info-level tracing span and event.
#[derive(Debug, Default, Clone, Copy)]
pub struct TracingTraceSink;

impl TraceSink for TracingTraceSink {
    fn span(&self, name: &str) {
        let span = tracing::info_span!("session_ledger.port", operation = name);
        let _guard = span.enter();
        tracing::info!("port operation");
    }
}

/// [`TraceSink`] that intentionally discards all trace notifications.
#[derive(Debug, Default, Clone, Copy)]
pub struct NoopTraceSink;

impl TraceSink for NoopTraceSink {
    fn span(&self, _name: &str) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn memory_store_recalls_substrings_in_insertion_order() {
        let store = InMemoryMemoryStore::default();
        let first = store
            .store("session-a", "database", "Use SQLite for persistence")
            .expect("store first memory");
        let second = store
            .store("session-b", "api", "Expose a database health endpoint")
            .expect("store second memory");
        store.store("session-c", "ui", "Render the timeline").expect("store unrelated memory");

        assert_ne!(first, second);
        assert_eq!(
            store.recall("DATABASE", 10).expect("recall memories"),
            vec![
                "Use SQLite for persistence".to_owned(),
                "Expose a database health endpoint".to_owned()
            ]
        );
    }

    #[test]
    fn memory_store_honors_top_k_and_searches_metadata() {
        let store = InMemoryMemoryStore::default();
        store.store("alpha", "one", "first").expect("store first");
        store.store("alpha", "two", "second").expect("store second");

        assert_eq!(store.recall("alpha", 1).expect("limited recall"), vec!["first"]);
        assert!(store.recall("alpha", 0).expect("empty recall").is_empty());
        assert_eq!(store.recall("two", 5).expect("key recall"), vec!["second"]);
    }

    #[test]
    fn passthrough_compressor_round_trips_unicode() {
        let compressor = PassthroughCompressor;
        let compressed = compressor.compress("ledger 🧠").expect("compress");
        assert_eq!(compressor.decompress(&compressed).expect("decompress"), "ledger 🧠");
    }

    #[test]
    fn passthrough_compressor_rejects_invalid_utf8() {
        let error = PassthroughCompressor.decompress(&[0xff]).expect_err("invalid UTF-8 must fail");
        assert!(matches!(error, PortError::Backend(_)));
    }

    #[cfg(feature = "compress")]
    #[test]
    fn zstd_compressor_round_trips_and_rejects_invalid_data() {
        let compressor = ZstdCompressor::default();
        let source = "repeatable context ".repeat(100);
        let compressed = compressor.compress(&source).expect("compress");

        assert!(compressed.len() < source.len());
        assert_eq!(compressor.decompress(&compressed).expect("decompress"), source);
        assert!(matches!(compressor.decompress(b"not zstd"), Err(PortError::Backend(_))));
    }

    #[test]
    fn trace_sinks_accept_operation_names() {
        TracingTraceSink.span("compile");
        NoopTraceSink.span("compile");
    }
}
