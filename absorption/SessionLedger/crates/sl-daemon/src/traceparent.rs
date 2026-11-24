//! Minimal W3C Trace Context (`traceparent`) parse / propagate helpers.
//!
//! Spec: <https://www.w3.org/TR/trace-context/#traceparent-header>
//!
//! Cross-process parentage for the file ETL path uses an optional sidecar
//! `{jsonl-path}.traceparent` (single header line). Workers attach the parent
//! fields to `process_session` spans and write a child header next to each
//! emitted `.okf.json` so the next hop can continue the same trace.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

/// Canonical HTTP / sidecar header name.
pub const HEADER: &str = "traceparent";

/// Parsed W3C `traceparent` version `00` fields (lowercase hex).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceParent {
    pub trace_id: String,
    pub parent_id: String,
    pub flags: String,
}

impl TraceParent {
    /// Parse the commonly deployed W3C trace-context version (`00`).
    ///
    /// Rejects non-ASCII, wrong length, uppercase hex, and all-zero ids.
    pub fn parse(value: &str) -> Option<Self> {
        let value = value.trim();
        if value.len() != 55 || !value.is_ascii() {
            return None;
        }
        let bytes = value.as_bytes();
        if &bytes[0..3] != b"00-" || bytes[35] != b'-' || bytes[52] != b'-' {
            return None;
        }
        let trace_id = &value[3..35];
        let parent_id = &value[36..52];
        let flags = &value[53..55];
        let is_lower_hex = |part: &str| {
            part.bytes().all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        };
        if !is_lower_hex(trace_id)
            || !is_lower_hex(parent_id)
            || !is_lower_hex(flags)
            || trace_id.bytes().all(|byte| byte == b'0')
            || parent_id.bytes().all(|byte| byte == b'0')
        {
            return None;
        }
        Some(Self {
            trace_id: trace_id.to_owned(),
            parent_id: parent_id.to_owned(),
            flags: flags.to_owned(),
        })
    }

    /// Render the wire header value `00-<trace-id>-<parent-id>-<flags>`.
    pub fn format(&self) -> String {
        format!("00-{}-{}-{}", self.trace_id, self.parent_id, self.flags)
    }

    /// Continue this context under a new span id (same `trace_id` / `flags`).
    ///
    /// Returns `None` if `span_id` is not 16 lowercase hex chars or is all zeros.
    pub fn with_span_id(&self, span_id: &str) -> Option<Self> {
        if span_id.len() != 16
            || !span_id.is_ascii()
            || !span_id.bytes().all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
            || span_id.bytes().all(|byte| byte == b'0')
        {
            return None;
        }
        Some(Self {
            trace_id: self.trace_id.clone(),
            parent_id: span_id.to_owned(),
            flags: self.flags.clone(),
        })
    }

    /// Allocate a new span id and return the child `traceparent` for outbound hops.
    pub fn child(&self) -> Self {
        self.with_span_id(&new_span_id()).expect("generated span id is valid")
    }

    /// Load a parent context from `{path}.traceparent` when present and valid.
    pub fn load_sidecar(path: &Path) -> Option<Self> {
        let sidecar = sidecar_path(path);
        let raw = std::fs::read_to_string(sidecar).ok()?;
        let line = raw.lines().next().unwrap_or(raw.as_str());
        Self::parse(line)
    }

    /// Persist this header as a single-line sidecar next to `path`.
    pub fn write_sidecar(&self, path: &Path) -> std::io::Result<()> {
        std::fs::write(sidecar_path(path), format!("{}\n", self.format()))
    }
}

impl std::fmt::Display for TraceParent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.format())
    }
}

/// Sidecar path convention: `{path}.traceparent`.
pub fn sidecar_path(path: &Path) -> std::path::PathBuf {
    let mut buf = path.as_os_str().to_owned();
    buf.push(".traceparent");
    std::path::PathBuf::from(buf)
}

/// Best-effort 16-hex span id without extra RNG dependencies.
fn new_span_id() -> String {
    let mut hasher = DefaultHasher::new();
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos().hash(&mut hasher);
    std::thread::current().id().hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";

    #[test]
    fn parses_valid_traceparent() {
        let parsed = TraceParent::parse(SAMPLE).unwrap();
        assert_eq!(parsed.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736");
        assert_eq!(parsed.parent_id, "00f067aa0ba902b7");
        assert_eq!(parsed.flags, "01");
        assert_eq!(parsed.format(), SAMPLE);
    }

    #[test]
    fn trims_whitespace_before_parse() {
        assert_eq!(TraceParent::parse(&format!("  {SAMPLE}\n")).unwrap().format(), SAMPLE);
    }

    #[test]
    fn rejects_malformed_or_zero_traceparent() {
        assert!(TraceParent::parse("not-a-traceparent").is_none());
        assert!(
            TraceParent::parse("00-00000000000000000000000000000000-00f067aa0ba902b7-01").is_none()
        );
        assert!(
            TraceParent::parse("00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01").is_none()
        );
        assert!(
            TraceParent::parse("00-4BF92F3577B34DA6A3CE929D0E0E4736-00F067AA0BA902B7-01").is_none()
        );
    }

    #[test]
    fn child_keeps_trace_id_and_changes_span() {
        let parent = TraceParent::parse(SAMPLE).unwrap();
        let child = parent.child();
        assert_eq!(child.trace_id, parent.trace_id);
        assert_eq!(child.flags, parent.flags);
        assert_ne!(child.parent_id, parent.parent_id);
        assert_eq!(child.parent_id.len(), 16);
        assert!(TraceParent::parse(&child.format()).is_some());
    }

    #[test]
    fn with_span_id_rejects_invalid() {
        let parent = TraceParent::parse(SAMPLE).unwrap();
        assert!(parent.with_span_id("0000000000000000").is_none());
        assert!(parent.with_span_id("short").is_none());
        assert!(parent.with_span_id("00F067AA0BA902B7").is_none());
    }

    #[test]
    fn sidecar_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let jsonl = dir.path().join("session.jsonl");
        std::fs::write(&jsonl, b"{}\n").unwrap();
        let parent = TraceParent::parse(SAMPLE).unwrap();
        parent.write_sidecar(&jsonl).unwrap();

        let loaded = TraceParent::load_sidecar(&jsonl).unwrap();
        assert_eq!(loaded, parent);
        assert_eq!(sidecar_path(&jsonl), dir.path().join("session.jsonl.traceparent"));
    }

    #[test]
    fn load_sidecar_missing_or_invalid_is_none() {
        let dir = tempfile::tempdir().unwrap();
        let jsonl = dir.path().join("missing.jsonl");
        assert!(TraceParent::load_sidecar(&jsonl).is_none());
        std::fs::write(sidecar_path(&jsonl), "nope\n").unwrap();
        assert!(TraceParent::load_sidecar(&jsonl).is_none());
    }
}
