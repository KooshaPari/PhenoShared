use std::{
    fs::File,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
};

use serde_json::{Map, Value};

use crate::{
    domain::session::{Corpus, Message, Role, Session},
    ports::{CorpusSource, PortError},
};

/// Accounting for malformed records encountered while loading a native transcript.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct JsonIngestionReport {
    /// Number of records that produced at least one normalized message.
    pub ingested: usize,
    /// Malformed records, represented as `(line_number, reason)`.
    pub skipped: Vec<(usize, String)>,
}

impl JsonIngestionReport {
    /// Whether the transcript contained no malformed records.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.skipped.is_empty()
    }
}

#[derive(Debug, Clone)]
pub(crate) struct JsonCorpusSource {
    root: PathBuf,
    corpus: Corpus,
}

impl JsonCorpusSource {
    pub(crate) fn new(path: impl Into<PathBuf>, corpus: Corpus) -> Self {
        Self { root: path.into(), corpus }
    }

    pub(crate) fn load_with_report(
        &self,
        id: &str,
    ) -> Result<(Session, JsonIngestionReport), PortError> {
        let path = self
            .files()?
            .into_iter()
            .find_map(|(candidate, path)| (candidate == id).then_some(path))
            .ok_or_else(|| PortError::NotFound(id.to_owned()))?;
        parse_file(&path, id, self.corpus)
    }

    fn files(&self) -> Result<Vec<(String, PathBuf)>, PortError> {
        if self.root.is_file() {
            let id = self
                .root
                .file_name()
                .and_then(|name| name.to_str())
                .ok_or_else(|| PortError::Backend("transcript filename is not UTF-8".into()))?
                .to_owned();
            return Ok(vec![(id, self.root.clone())]);
        }
        if !self.root.is_dir() {
            return Err(PortError::Backend(format!(
                "corpus path is not a file or directory: {}",
                self.root.display()
            )));
        }

        let mut paths = Vec::new();
        collect_transcripts(&self.root, &mut paths)?;
        paths.sort();
        paths
            .into_iter()
            .map(|path| {
                let relative = path
                    .strip_prefix(&self.root)
                    .map_err(|error| PortError::Backend(format!("make transcript id: {error}")))?;
                let id = relative.to_string_lossy().replace('\\', "/");
                Ok((id, path))
            })
            .collect()
    }
}

impl CorpusSource for JsonCorpusSource {
    fn list(&self) -> Result<Vec<String>, PortError> {
        Ok(self.files()?.into_iter().map(|(id, _)| id).collect())
    }

    fn load(&self, id: &str) -> Result<Session, PortError> {
        self.load_with_report(id).map(|(session, _)| session)
    }
}

fn collect_transcripts(directory: &Path, paths: &mut Vec<PathBuf>) -> Result<(), PortError> {
    let entries = std::fs::read_dir(directory)
        .map_err(|error| PortError::Backend(format!("read {}: {error}", directory.display())))?;
    for entry in entries {
        let entry =
            entry.map_err(|error| PortError::Backend(format!("read directory entry: {error}")))?;
        let path = entry.path();
        if path.is_dir() {
            collect_transcripts(&path, paths)?;
        } else if is_transcript(&path) {
            paths.push(path);
        }
    }
    Ok(())
}

fn is_transcript(path: &Path) -> bool {
    match path.extension().and_then(|extension| extension.to_str()) {
        Some("json" | "jsonl") => true,
        Some("zst") => path
            .file_stem()
            .and_then(|stem| Path::new(stem).extension())
            .is_some_and(|extension| extension == "jsonl"),
        _ => false,
    }
}

#[cfg(test)]
mod transcript_tests {
    use super::is_transcript;

    #[test]
    fn accepts_plain_and_compressed_jsonl() {
        assert!(is_transcript(std::path::Path::new("session.jsonl")));
        assert!(is_transcript(std::path::Path::new("session.jsonl.zst")));
        assert!(!is_transcript(std::path::Path::new("session.txt.zst")));
    }

    #[cfg(feature = "compress")]
    #[test]
    fn parses_compressed_jsonl_transcript() {
        use super::parse_file;
        use crate::domain::session::Corpus;

        let dir = tempfile::tempdir().expect("temp dir");
        let path = dir.path().join("session.jsonl.zst");
        let content = format!(
            "{}\n{}\n",
            serde_json::json!({"type":"session_meta","payload":{"id":"compressed-1"}}),
            serde_json::json!({"type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"hello compressed"}]}})
        );
        let compressed = zstd::stream::encode_all(content.as_bytes(), 3).expect("compress");
        std::fs::write(&path, compressed).expect("write transcript");
        let (session, report) = parse_file(&path, "fallback", Corpus::Codex).expect("parse");
        assert_eq!(session.id, "compressed-1");
        assert_eq!(session.messages[0].content, "hello compressed");
        assert_eq!(report.ingested, 1);
    }
}

fn parse_file(
    path: &Path,
    fallback_id: &str,
    corpus: Corpus,
) -> Result<(Session, JsonIngestionReport), PortError> {
    let file = File::open(path)
        .map_err(|error| PortError::Backend(format!("open {}: {error}", path.display())))?;
    let mut session = Session::new(fallback_id, corpus);
    let mut report = JsonIngestionReport::default();

    if path.extension().and_then(|extension| extension.to_str()) == Some("json") {
        let value: Value = serde_json::from_reader(file)
            .map_err(|error| PortError::Backend(format!("parse {}: {error}", path.display())))?;
        apply_value(&value, &mut session, &mut report);
    } else {
        #[cfg(feature = "compress")]
        let lines: Box<dyn BufRead> =
            if path.extension().and_then(|extension| extension.to_str()) == Some("zst") {
                Box::new(BufReader::new(zstd::stream::read::Decoder::new(file).map_err(
                    |error| PortError::Backend(format!("decompress {}: {error}", path.display())),
                )?))
            } else {
                Box::new(BufReader::new(file))
            };
        #[cfg(not(feature = "compress"))]
        let lines: Box<dyn BufRead> = Box::new(BufReader::new(file));
        for (index, line) in lines.lines().enumerate() {
            let line_number = index + 1;
            let line = line.map_err(|error| {
                PortError::Backend(format!("read {} line {line_number}: {error}", path.display()))
            })?;
            if line.trim().is_empty() {
                continue;
            }
            match serde_json::from_str::<Value>(&line) {
                Ok(value) => apply_value(&value, &mut session, &mut report),
                Err(error) => report.skipped.push((line_number, error.to_string())),
            }
        }
    }
    Ok((session, report))
}

fn apply_value(value: &Value, session: &mut Session, report: &mut JsonIngestionReport) {
    apply_metadata(value, session);
    let before = session.messages.len();
    extract_messages(value, None, None, &mut session.messages);
    if session.messages.len() > before {
        report.ingested += 1;
    }
}

fn apply_metadata(value: &Value, session: &mut Session) {
    let Some(object) = value.as_object() else {
        return;
    };
    let metadata = if object.get("type").and_then(Value::as_str) == Some("session_meta") {
        object.get("payload").and_then(Value::as_object).unwrap_or(object)
    } else {
        object
    };

    if let Some(id) = string_field(
        metadata,
        &["sessionId", "session_id", "conversationId", "conversation_id", "id"],
    ) {
        id.clone_into(&mut session.id);
    }
    if session.cwd.is_none() {
        session.cwd =
            string_field(metadata, &["cwd", "workingDirectory", "workspace"]).map(str::to_owned);
    }
    if session.title.is_none() {
        session.title = string_field(metadata, &["title", "name"]).map(str::to_owned);
    }
}

fn extract_messages(
    value: &Value,
    inherited_role: Option<Role>,
    inherited_ts: Option<i64>,
    messages: &mut Vec<Message>,
) {
    match value {
        Value::Array(items) => {
            for item in items {
                extract_messages(item, inherited_role, inherited_ts, messages);
            }
        }
        Value::Object(object) => extract_object(object, inherited_role, inherited_ts, messages),
        _ => {}
    }
}

fn extract_object(
    object: &Map<String, Value>,
    inherited_role: Option<Role>,
    inherited_ts: Option<i64>,
    messages: &mut Vec<Message>,
) {
    let record_type = string_field(object, &["type"]);
    if matches!(record_type, Some("session_meta" | "turn_context" | "token_count")) {
        return;
    }

    let timestamp = timestamp(object).or(inherited_ts);
    let role = string_field(object, &["role"])
        .and_then(map_role)
        .or_else(|| {
            object
                .get("author")
                .and_then(Value::as_object)
                .and_then(|author| string_field(author, &["role"]))
                .and_then(map_role)
        })
        .or_else(|| record_type.and_then(map_event_type))
        .or(inherited_role);

    if let Some(message) = object.get("message") {
        if message.is_object() || message.is_array() {
            extract_messages(message, role, timestamp, messages);
        } else if let (Some(role), Some(content)) = (role, text_content(message)) {
            messages.push(Message { role, content, ts_ms: timestamp });
        }
        return;
    }

    if record_type == Some("response_item") {
        if let Some(payload) = object.get("payload") {
            extract_messages(payload, role, timestamp, messages);
        }
        return;
    }

    if matches!(record_type, Some("event_msg" | "user_message" | "agent_message")) {
        if let Some(payload) = object.get("payload") {
            extract_messages(payload, role, timestamp, messages);
        }
        return;
    }

    if let (Some(role), Some(content)) = (
        role,
        object.get("content").and_then(text_content).or_else(|| {
            object.get("text").or_else(|| object.get("output_text")).and_then(text_content)
        }),
    ) {
        if !content.is_empty() {
            messages.push(Message { role, content, ts_ms: timestamp });
        }
        return;
    }

    for key in
        ["messages", "conversation", "transcript", "items", "mapping", "nodes", "chat_messages"]
    {
        if let Some(nested) = object.get(key) {
            extract_messages(nested, role, timestamp, messages);
        }
    }
    // ChatGPT exports use opaque mapping IDs rather than a JSON array.
    for key in ["mapping", "nodes"] {
        if let Some(Value::Object(records)) = object.get(key) {
            for record in records.values() {
                extract_messages(record, role, timestamp, messages);
            }
        }
    }
}

fn text_content(value: &Value) -> Option<String> {
    match value {
        Value::String(text) => Some(text.clone()),
        Value::Array(parts) => {
            let text = parts.iter().filter_map(text_content).collect::<Vec<_>>().join("\n");
            (!text.is_empty()).then_some(text)
        }
        Value::Object(object) => object
            .get("text")
            .or_else(|| object.get("content"))
            .or_else(|| object.get("parts"))
            .or_else(|| object.get("value"))
            .and_then(text_content),
        _ => None,
    }
}

fn timestamp(object: &Map<String, Value>) -> Option<i64> {
    object.get("ts").or_else(|| object.get("ts_ms")).or_else(|| object.get("timestamp")).and_then(
        |value| {
            value.as_i64().or_else(|| {
                let text = value.as_str()?;
                text.parse().ok().or_else(|| {
                    let parsed = time::OffsetDateTime::parse(
                        text,
                        &time::format_description::well_known::Rfc3339,
                    )
                    .ok()?;
                    (parsed.unix_timestamp_nanos() / 1_000_000).try_into().ok()
                })
            })
        },
    )
}

fn string_field<'a>(object: &'a Map<String, Value>, names: &[&str]) -> Option<&'a str> {
    names.iter().find_map(|name| object.get(*name).and_then(Value::as_str))
}

fn map_role(role: &str) -> Option<Role> {
    match role.to_ascii_lowercase().as_str() {
        "user" | "human" => Some(Role::User),
        "assistant" | "agent" => Some(Role::Assistant),
        "system" | "developer" => Some(Role::System),
        "tool" | "tool_result" | "tool-result" | "function" => Some(Role::Tool),
        "subagent" => Some(Role::Subagent),
        _ => None,
    }
}

fn map_event_type(event_type: &str) -> Option<Role> {
    match event_type {
        "user" | "user_message" | "human" => Some(Role::User),
        "assistant" | "agent_message" => Some(Role::Assistant),
        "system" => Some(Role::System),
        "tool" | "tool_result" => Some(Role::Tool),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn content_blocks_are_joined() {
        let value = serde_json::json!({
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": "one"},
                {"type": "output_text", "text": "two"}
            ]
        });
        let mut messages = Vec::new();
        extract_messages(&value, None, None, &mut messages);
        assert_eq!(messages[0].content, "one\ntwo");
    }
}
