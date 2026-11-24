//! Web export corpus loader.
//!
//! Provides ingestion for sessions exported by web-based assistant clients
//! (ChatGPT, Claude, Gemini). Web exports are typically downloaded manually
//! from each vendor's "export" page and land in the user's `~/Downloads` folder
//! as JSON or ZIP archives.
//!
//! The module exposes a single entry point (`load_web_export_corpus`) plus a
//! discovery helper (`web_export_roots_with_env`) that resolves the set of
//! provider roots visible to the running process.

#![cfg_attr(not(test), allow(dead_code))]

use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};

use session_ledger::domain::session::{Corpus, Session};

/// The web assistant whose export we're reading.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WebExportProvider {
    ChatGpt,
    Claude,
    Gemini,
}

impl WebExportProvider {
    /// Human-readable label, used in error messages and the UI.
    pub fn label(self) -> &'static str {
        match self {
            WebExportProvider::ChatGpt => "ChatGPT",
            WebExportProvider::Claude => "Claude",
            WebExportProvider::Gemini => "Gemini",
        }
    }

    /// The `Corpus` variant this provider maps to.
    pub fn corpus(self) -> Corpus {
        match self {
            WebExportProvider::ChatGpt => Corpus::ChatGptWeb,
            WebExportProvider::Claude => Corpus::ClaudeWeb,
            WebExportProvider::Gemini => Corpus::GeminiWeb,
        }
    }

    /// The default subdirectory under `~/Downloads` for this provider's exports.
    pub fn default_subdir(self) -> &'static str {
        match self {
            WebExportProvider::ChatGpt => "ChatGPT",
            WebExportProvider::Claude => "Claude",
            WebExportProvider::Gemini => "Gemini",
        }
    }
}

/// Resolve the set of web-export roots visible to this process.
///
/// If `explicit` is `Some`, it must be a `:`-separated list of paths; those
/// paths become roots (one each, with provider inferred by directory name).
/// If `None`, defaults to `<home>/Downloads/{ChatGPT,Claude,Gemini}`.
pub fn web_export_roots_with_env(
    home: &Path,
    explicit: Option<OsString>,
) -> Vec<(WebExportProvider, PathBuf)> {
    let explicit_list: Vec<PathBuf> = match explicit {
        Some(s) => std::env::split_paths(&s).collect(),
        None => Vec::new(),
    };

    let defaults = [
        (
            WebExportProvider::ChatGpt,
            home.join("Downloads").join(WebExportProvider::ChatGpt.default_subdir()),
        ),
        (
            WebExportProvider::Claude,
            home.join("Downloads").join(WebExportProvider::Claude.default_subdir()),
        ),
        (
            WebExportProvider::Gemini,
            home.join("Downloads").join(WebExportProvider::Gemini.default_subdir()),
        ),
    ];

    if !explicit_list.is_empty() {
        explicit_list
            .into_iter()
            .map(|p| {
                let provider = match p.file_name().and_then(|s| s.to_str()) {
                    Some("ChatGPT") | Some("chatgpt") => WebExportProvider::ChatGpt,
                    Some("Claude") | Some("claude") => WebExportProvider::Claude,
                    _ => WebExportProvider::Gemini,
                };
                (provider, p)
            })
            .collect()
    } else {
        defaults.into_iter().filter(|(_, p)| p.exists()).collect()
    }
}

/// Read every export file under `path` and append parsed sessions to `sessions`.
///
/// Returns the number of sessions successfully parsed.
pub fn load_web_export_corpus(
    path: &Path,
    provider: WebExportProvider,
    sessions: &mut Vec<Session>,
) -> Result<usize, String> {
    let corpus = provider.corpus();
    let label = provider.label();
    let mut loaded = 0usize;

    let entries = fs::read_dir(path)
        .map_err(|e| format!("could not read {label} export root {}: {e}", path.display()))?;

    for entry in entries.flatten() {
        let entry_path = entry.path();
        if entry_path.is_dir() {
            // recurse one level into per-conversation subfolders
            loaded += load_web_export_corpus(&entry_path, provider, sessions)?;
            continue;
        }

        // only attempt files we recognise as JSON exports
        let ext = entry_path.extension().and_then(|s| s.to_str()).unwrap_or_default();
        if !matches!(ext, "json") {
            continue;
        }

        let raw = match fs::read_to_string(&entry_path) {
            Ok(s) => s,
            Err(e) => {
                eprintln!(
                    "warning: skipping unreadable {label} export {}: {e}",
                    entry_path.display()
                );
                continue;
            }
        };

        match parse_web_export(&raw, corpus) {
            Some(s) => {
                sessions.push(s);
                loaded += 1;
            }
            None => {
                eprintln!(
                    "warning: {label} export {} did not match expected schema",
                    entry_path.display()
                );
            }
        }
    }

    Ok(loaded)
}

fn parse_web_export(raw: &str, corpus: Corpus) -> Option<Session> {
    // Vendors use slightly different JSON shapes. We accept both:
    //   { "id": "...", "title": "...", "messages": [{role, content, ts_ms?}, ...] }
    //   { "conversation_id": "...", "mapping": { "<node_id>": {message: {author, content}} } }
    //
    // The minimal common schema is the first; the second is folded into it
    // by treating each non-empty mapping node as a flat message list.

    let value: serde_json::Value = serde_json::from_str(raw).ok()?;
    let title = value
        .get("title")
        .or_else(|| value.get("name"))
        .and_then(|v| v.as_str())
        .map(str::to_owned);

    let id = value
        .get("id")
        .or_else(|| value.get("conversation_id"))
        .and_then(|v| v.as_str())
        .map(str::to_owned)
        .unwrap_or_else(|| {
            // last-resort id: hash the first 32 chars of the raw text
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut h = DefaultHasher::new();
            raw.hash(&mut h);
            format!("{:x}", h.finish())
        });

    let messages: Vec<session_ledger::domain::session::Message> =
        if let Some(arr) = value.get("messages").and_then(|m| m.as_array()) {
            arr.iter()
                .filter_map(|m| {
                    let role = m.get("role").and_then(|v| v.as_str()).and_then(parse_role)?;
                    let content =
                        m.get("content").and_then(|v| v.as_str()).unwrap_or_default().to_owned();
                    let ts_ms = m.get("ts_ms").and_then(|v| v.as_i64());
                    Some(session_ledger::domain::session::Message { role, content, ts_ms })
                })
                .collect()
        } else if let Some(map) = value.get("mapping").and_then(|m| m.as_object()) {
            map.values()
                .filter_map(|node| {
                    let msg = node.get("message")?;
                    let role = msg
                        .get("author")
                        .and_then(|a| a.get("role"))
                        .and_then(|v| v.as_str())
                        .and_then(parse_role)?;
                    let content = msg
                        .get("content")
                        .map(|c| match c {
                            serde_json::Value::String(s) => s.clone(),
                            serde_json::Value::Array(parts) => parts
                                .iter()
                                .filter_map(|p| {
                                    p.get("text").and_then(|v| v.as_str()).map(String::from)
                                })
                                .collect::<Vec<_>>()
                                .join("\n"),
                            _ => String::new(),
                        })
                        .unwrap_or_default();
                    let ts_ms = msg.get("create_time").and_then(|v| v.as_f64().map(|f| f as i64));
                    Some(session_ledger::domain::session::Message { role, content, ts_ms })
                })
                .collect()
        } else {
            Vec::new()
        };

    Some(Session { id, corpus, cwd: None, title, messages })
}

fn parse_role(s: &str) -> Option<session_ledger::domain::session::Role> {
    use session_ledger::domain::session::Role;
    let lower = s.to_ascii_lowercase();
    let role = match lower.as_str() {
        "user" | "human" => Role::User,
        "assistant" | "chatgpt" | "model" | "claude" | "gemini" => Role::Assistant,
        "tool" | "function" => Role::Tool,
        "system" => Role::System,
        // ChatGPT exports use "node" entries for assistant turns; treat those as
        // assistant for compatibility.
        "node" => Role::Assistant,
        _ => return None,
    };
    Some(role)
}
