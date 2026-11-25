//! OTLP file exporter: writes spans to a rolling JSON-lines file.
//!
//! Usable as a fallback sink when no OTLP endpoint is reachable. Files rotate
//! by date (`tracely-YYYY-MM-DD.jsonl`), one JSON object per line per span.

use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use anyhow::Context;

/// A single exported span, serialized as one JSON line.
#[derive(Debug, Clone, serde::Serialize)]
pub struct SpanData {
    /// Span start time, Unix nanoseconds.
    pub timestamp: u64,
    /// Trace identifier (hex).
    pub trace_id: String,
    /// Span identifier (hex).
    pub span_id: String,
    /// Span name.
    pub name: String,
    /// Span duration in nanoseconds.
    pub duration_ns: u64,
    /// Status string (e.g. `"ok"`, `"error"`).
    pub status: String,
    /// Arbitrary key/value attributes.
    pub attributes: HashMap<String, String>,
}

/// Writes spans to a date-rotated JSON-lines file in `dir`.
///
/// `Send + Sync` via an internal `Mutex<BufWriter<File>>`. The active file is
/// re-opened when the calendar date changes, so long-running processes roll
/// over at midnight (UTC).
pub struct FileExporter {
    dir: PathBuf,
    inner: Mutex<Inner>,
}

struct Inner {
    /// Date (`YYYY-MM-DD`) the current writer targets.
    date: String,
    writer: BufWriter<File>,
}

impl FileExporter {
    /// Create an exporter writing into `dir`, creating the directory if absent.
    pub fn new(dir: impl Into<PathBuf>) -> anyhow::Result<Self> {
        let dir = dir.into();
        fs::create_dir_all(&dir)
            .with_context(|| format!("creating exporter directory {}", dir.display()))?;

        let date = today();
        let writer = open_writer(&dir, &date)?;
        Ok(Self {
            dir,
            inner: Mutex::new(Inner { date, writer }),
        })
    }

    /// Append each span as a JSON line to the current date's file.
    pub fn export(&self, spans: &[SpanData]) -> anyhow::Result<()> {
        let mut inner = self
            .inner
            .lock()
            .map_err(|_| anyhow::anyhow!("file exporter mutex poisoned"))?;

        let date = today();
        if date != inner.date {
            inner.writer.flush().context("flushing before rotation")?;
            inner.writer = open_writer(&self.dir, &date)?;
            inner.date = date;
        }

        for span in spans {
            let line = serde_json::to_string(span).context("serializing span")?;
            inner
                .writer
                .write_all(line.as_bytes())
                .context("writing span line")?;
            inner.writer.write_all(b"\n").context("writing newline")?;
        }
        Ok(())
    }

    /// Flush buffered spans to disk.
    pub fn flush(&self) -> anyhow::Result<()> {
        let mut inner = self
            .inner
            .lock()
            .map_err(|_| anyhow::anyhow!("file exporter mutex poisoned"))?;
        inner.writer.flush().context("flushing exporter")?;
        Ok(())
    }
}

fn today() -> String {
    chrono::Utc::now().format("%Y-%m-%d").to_string()
}

fn open_writer(dir: &Path, date: &str) -> anyhow::Result<BufWriter<File>> {
    let path = dir.join(format!("tracely-{date}.jsonl"));
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .with_context(|| format!("opening export file {}", path.display()))?;
    Ok(BufWriter::new(file))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(tag: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!(
            "tracely-fe-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        p
    }

    fn sample_span(name: &str) -> SpanData {
        let mut attributes = HashMap::new();
        attributes.insert("service".to_string(), "test".to_string());
        SpanData {
            timestamp: 1_700_000_000_000_000_000,
            trace_id: "abc123".to_string(),
            span_id: "def456".to_string(),
            name: name.to_string(),
            duration_ns: 42,
            status: "ok".to_string(),
            attributes,
        }
    }

    fn read_current_file(dir: &Path) -> String {
        let path = dir.join(format!("tracely-{}.jsonl", today()));
        fs::read_to_string(path).unwrap()
    }

    #[test]
    fn new_creates_missing_directory() {
        let dir = temp_dir("mkdir");
        assert!(!dir.exists());
        let _exporter = FileExporter::new(&dir).unwrap();
        assert!(dir.exists());
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn export_writes_valid_json_line() {
        let dir = temp_dir("json");
        let exporter = FileExporter::new(&dir).unwrap();
        exporter.export(&[sample_span("op")]).unwrap();
        exporter.flush().unwrap();

        let contents = read_current_file(&dir);
        let line = contents.lines().next().unwrap();
        let parsed: serde_json::Value = serde_json::from_str(line).unwrap();
        assert_eq!(parsed["name"], "op");
        assert_eq!(parsed["trace_id"], "abc123");
        assert_eq!(parsed["duration_ns"], 42);
        assert_eq!(parsed["attributes"]["service"], "test");
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn multiple_exports_append() {
        let dir = temp_dir("append");
        let exporter = FileExporter::new(&dir).unwrap();
        exporter.export(&[sample_span("first")]).unwrap();
        exporter.export(&[sample_span("second")]).unwrap();
        exporter.flush().unwrap();

        let contents = read_current_file(&dir);
        let lines: Vec<&str> = contents.lines().collect();
        assert_eq!(lines.len(), 2);
        assert!(lines[0].contains("first"));
        assert!(lines[1].contains("second"));
        fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn flush_does_not_error() {
        let dir = temp_dir("flush");
        let exporter = FileExporter::new(&dir).unwrap();
        exporter.export(&[sample_span("op")]).unwrap();
        assert!(exporter.flush().is_ok());
        fs::remove_dir_all(&dir).ok();
    }
}
