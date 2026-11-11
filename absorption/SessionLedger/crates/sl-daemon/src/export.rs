//! `sl export` and `sl summary` — bundle metadata formatting.
//!
//! All rendering functions are pure (no I/O) so they can be unit-tested without
//! a running daemon or real OKF files on disk.

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// OKF bundle metadata (only the fields we care about)
// ---------------------------------------------------------------------------

/// Subset of an OKF document used for export / summary.
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct BundleMeta {
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub token_count: u64,
    #[serde(default)]
    pub message_count: u64,
    /// User-authored turns projected from graph-native intent entities.
    #[serde(default)]
    pub user_turn_count: u64,
    #[serde(default)]
    pub duration_ms: u64,
    /// Free-form tags array, if present.
    #[serde(default)]
    pub tags: Vec<String>,
}

impl BundleMeta {
    /// Extract metadata from a raw OKF JSON value using best-effort field
    /// mapping across the various OKF shapes produced by session-ledger.
    pub fn from_value(v: &serde_json::Value) -> Self {
        let get_str = |key: &str| -> String {
            v.get(key)
                .or_else(|| {
                    v.pointer(&format!("/metadata/{key}"))
                        .or_else(|| v.pointer(&format!("/header/{key}")))
                })
                .and_then(|x| x.as_str())
                .unwrap_or_default()
                .to_owned()
        };
        let get_u64 = |key: &str| -> u64 {
            v.get(key)
                .or_else(|| {
                    v.pointer(&format!("/metadata/{key}"))
                        .or_else(|| v.pointer(&format!("/header/{key}")))
                })
                .and_then(|x| x.as_u64())
                .unwrap_or(0)
        };

        // session_id: top-level or nested under "metadata"/"header"
        let session_id = {
            let s = get_str("session_id");
            if s.is_empty() {
                let id = get_str("id");
                if id.is_empty() {
                    v.get("source_id")
                        .or_else(|| v.pointer("/provenance/source_id"))
                        .and_then(|x| x.as_str())
                        .unwrap_or_default()
                        .to_owned()
                } else {
                    id
                }
            } else {
                s
            }
        };
        // created_at: multiple possible key names
        let created_at = {
            let s = get_str("created_at");
            if s.is_empty() {
                get_str("timestamp")
            } else {
                s
            }
        };
        // model
        let model = {
            let s = get_str("model");
            if s.is_empty() {
                get_str("model_id")
            } else {
                s
            }
        };
        // token_count: may be nested under usage
        let token_count = {
            let n = get_u64("token_count");
            if n == 0 {
                v.pointer("/usage/total_tokens").and_then(|x| x.as_u64()).unwrap_or(0)
            } else {
                n
            }
        };
        let message_count = get_u64("message_count");
        let user_turn_count = v
            .get("entities")
            .and_then(|entities| entities.as_array())
            .map(|entities| {
                entities
                    .iter()
                    .filter(|entity| entity.get("type").and_then(|kind| kind.as_str()) == Some("intent"))
                    .filter_map(|entity| entity.pointer("/properties/user_turn_count").and_then(|count| count.as_u64()))
                    .fold(0u64, |total, count| total.saturating_add(count))
            })
            .unwrap_or_default();
        let duration_ms = get_u64("duration_ms");
        let tags = v
            .get("tags")
            .and_then(|x| x.as_array())
            .map(|arr| arr.iter().filter_map(|t| t.as_str().map(str::to_owned)).collect())
            .unwrap_or_default();

        Self {
            session_id,
            created_at,
            model,
            token_count,
            message_count,
            user_turn_count,
            duration_ms,
            tags,
        }
    }
}

// ---------------------------------------------------------------------------
// Export formats
// ---------------------------------------------------------------------------

/// Output format for `sl export`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExportFormat {
    Csv,
    Markdown,
    Json,
}

impl std::str::FromStr for ExportFormat {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "csv" => Ok(Self::Csv),
            "md" | "markdown" => Ok(Self::Markdown),
            "json" => Ok(Self::Json),
            other => Err(format!("unknown format {other:?}; expected csv, md, or json")),
        }
    }
}

/// Render a slice of [`BundleMeta`] as CSV.
///
/// Emits a header row followed by one data row per bundle. Fields containing
/// commas or quotes are properly quoted per RFC 4180.
pub fn render_csv(metas: &[BundleMeta]) -> String {
    let mut out = String::new();
    out.push_str("session_id,created_at,model,token_count,message_count,user_turn_count,duration_ms,tags\n");
    for m in metas {
        let tags = m.tags.join(";");
        out.push_str(&csv_field(&m.session_id));
        out.push(',');
        out.push_str(&csv_field(&m.created_at));
        out.push(',');
        out.push_str(&csv_field(&m.model));
        out.push(',');
        out.push_str(&m.token_count.to_string());
        out.push(',');
        out.push_str(&m.message_count.to_string());
        out.push(',');
        out.push_str(&m.user_turn_count.to_string());
        out.push(',');
        out.push_str(&m.duration_ms.to_string());
        out.push(',');
        out.push_str(&csv_field(&tags));
        out.push('\n');
    }
    out
}

fn csv_field(s: &str) -> String {
    if s.contains(',') || s.contains('"') || s.contains('\n') {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_owned()
    }
}

/// Render a slice of [`BundleMeta`] as a Markdown table-per-bundle document.
///
/// Each bundle becomes a two-column `| field | value |` table; bundles are
/// separated by a `---` horizontal rule.
pub fn render_markdown(metas: &[BundleMeta]) -> String {
    let mut out = String::new();
    for (i, m) in metas.iter().enumerate() {
        if i > 0 {
            out.push_str("\n---\n\n");
        }
        out.push_str("| Field | Value |\n");
        out.push_str("|---|---|\n");
        md_row(&mut out, "session_id", &m.session_id);
        md_row(&mut out, "created_at", &m.created_at);
        md_row(&mut out, "model", &m.model);
        md_row(&mut out, "token_count", &m.token_count.to_string());
        md_row(&mut out, "message_count", &m.message_count.to_string());
        md_row(&mut out, "user_turn_count", &m.user_turn_count.to_string());
        md_row(&mut out, "duration_ms", &m.duration_ms.to_string());
        md_row(&mut out, "tags", &m.tags.join(", "));
        out.push('\n');
    }
    out
}

fn md_row(out: &mut String, field: &str, value: &str) {
    out.push_str(&format!("| {field} | {value} |\n"));
}

/// Render a slice of [`BundleMeta`] as a JSON array.
pub fn render_json(metas: &[BundleMeta]) -> String {
    // Re-serialize as a JSON array.  We derive Serialize separately.
    let values: Vec<serde_json::Value> = metas
        .iter()
        .map(|m| {
            serde_json::json!({
                "session_id": m.session_id,
                "created_at": m.created_at,
                "model": m.model,
                "token_count": m.token_count,
                "message_count": m.message_count,
                "user_turn_count": m.user_turn_count,
                "duration_ms": m.duration_ms,
                "tags": m.tags,
            })
        })
        .collect();
    serde_json::to_string_pretty(&values).unwrap_or_else(|_| "[]".to_owned())
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

/// Aggregate statistics across a collection of bundles.
#[derive(Debug, Default)]
pub struct Summary {
    pub bundle_count: usize,
    pub total_tokens: u64,
    pub avg_tokens: f64,
    pub total_messages: u64,
    pub avg_messages: f64,
    pub most_used_model: String,
    pub earliest: String,
    pub latest: String,
}

/// Compute a [`Summary`] from a slice of [`BundleMeta`].
pub fn compute_summary(metas: &[BundleMeta]) -> Summary {
    if metas.is_empty() {
        return Summary::default();
    }

    let bundle_count = metas.len();
    let total_tokens: u64 = metas.iter().map(|m| m.token_count).sum();
    let total_messages: u64 = metas.iter().map(|m| m.message_count).sum();
    let avg_tokens = total_tokens as f64 / bundle_count as f64;
    let avg_messages = total_messages as f64 / bundle_count as f64;

    // Most-used model via frequency count.
    let mut model_counts: std::collections::HashMap<&str, usize> = std::collections::HashMap::new();
    for m in metas {
        if !m.model.is_empty() {
            *model_counts.entry(m.model.as_str()).or_insert(0) += 1;
        }
    }
    let most_used_model = model_counts
        .into_iter()
        .max_by_key(|(_, c)| *c)
        .map(|(m, _)| m.to_owned())
        .unwrap_or_default();

    // Date range (lexicographic — works for ISO-8601 strings).
    let dates: Vec<&str> =
        metas.iter().map(|m| m.created_at.as_str()).filter(|s| !s.is_empty()).collect();
    let earliest = dates.iter().min().copied().unwrap_or("").to_owned();
    let latest = dates.iter().max().copied().unwrap_or("").to_owned();

    Summary {
        bundle_count,
        total_tokens,
        avg_tokens,
        total_messages,
        avg_messages,
        most_used_model,
        earliest,
        latest,
    }
}

/// Format a [`Summary`] as human-readable text.
pub fn render_summary(s: &Summary) -> String {
    format!(
        "Bundles:        {}\nTotal tokens:   {}\nAvg tokens:     {:.1}\nTotal messages: {}\nAvg messages:   {:.1}\nTop model:      {}\nDate range:     {} — {}\n",
        s.bundle_count,
        s.total_tokens,
        s.avg_tokens,
        s.total_messages,
        s.avg_messages,
        if s.most_used_model.is_empty() { "(unknown)" } else { &s.most_used_model },
        if s.earliest.is_empty() { "?" } else { &s.earliest },
        if s.latest.is_empty() { "?" } else { &s.latest },
    )
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_metas() -> Vec<BundleMeta> {
        vec![
            BundleMeta {
                session_id: "sess-001".into(),
                created_at: "2024-01-01T00:00:00Z".into(),
                model: "claude-3-sonnet".into(),
                token_count: 1000,
                message_count: 10,
                user_turn_count: 3,
                duration_ms: 500,
                tags: vec!["rust".into(), "test".into()],
            },
            BundleMeta {
                session_id: "sess-002".into(),
                created_at: "2024-01-02T00:00:00Z".into(),
                model: "claude-3-sonnet".into(),
                token_count: 2000,
                message_count: 20,
                user_turn_count: 1,
                duration_ms: 1000,
                tags: vec![],
            },
        ]
    }

    // --- CSV ---

    #[test]
    fn csv_has_header_row() {
        let out = render_csv(&sample_metas());
        assert!(out.starts_with("session_id,created_at,model,"));
    }

    #[test]
    fn csv_has_correct_row_count() {
        let out = render_csv(&sample_metas());
        // 1 header + 2 data rows + trailing newline → 4 lines split
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines.len(), 3); // header + 2 data rows
    }

    #[test]
    fn csv_data_row_contains_expected_values() {
        let out = render_csv(&sample_metas());
        assert!(out.contains("sess-001"));
        assert!(out.contains("claude-3-sonnet"));
        assert!(out.contains("1000"));
        assert!(out.contains("rust;test"));
        assert!(out.contains("user_turn_count"));
        assert!(out.contains(",3,"));
    }

    #[test]
    fn csv_quotes_fields_with_commas() {
        let m = BundleMeta { session_id: "a,b".into(), ..BundleMeta::default() };
        let out = render_csv(&[m]);
        assert!(out.contains("\"a,b\""));
    }

    #[test]
    fn csv_quotes_fields_with_double_quotes() {
        let m = BundleMeta { session_id: r#"say "hi""#.into(), ..BundleMeta::default() };
        let out = render_csv(&[m]);
        assert!(out.contains(r#""say ""hi"""#));
    }

    #[test]
    fn csv_empty_slice_is_only_header() {
        let out = render_csv(&[]);
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines.len(), 1);
    }

    // --- Markdown ---

    #[test]
    fn markdown_contains_table_header() {
        let out = render_markdown(&sample_metas());
        assert!(out.contains("| Field | Value |"));
    }

    #[test]
    fn markdown_contains_separator_between_bundles() {
        let out = render_markdown(&sample_metas());
        assert!(out.contains("\n---\n"));
    }

    #[test]
    fn markdown_single_bundle_no_separator() {
        let out = render_markdown(&sample_metas()[..1]);
        // The horizontal rule between bundles is "\n---\n"; table header
        // separator "|---|---|" should still be present but the HR should not.
        assert!(!out.contains("\n---\n"));
    }

    #[test]
    fn markdown_contains_session_id_row() {
        let out = render_markdown(&sample_metas());
        assert!(out.contains("| session_id | sess-001 |"));
    }

    #[test]
    fn markdown_contains_tags() {
        let out = render_markdown(&sample_metas());
        assert!(out.contains("rust, test"));
        assert!(out.contains("| user_turn_count | 3 |"));
    }

    #[test]
    fn markdown_empty_slice_is_empty_string() {
        let out = render_markdown(&[]);
        assert!(out.is_empty());
    }

    // --- JSON ---

    #[test]
    fn json_is_valid_array() {
        let out = render_json(&sample_metas());
        let v: serde_json::Value = serde_json::from_str(&out).expect("valid JSON");
        assert!(v.is_array());
    }

    #[test]
    fn json_array_length_matches() {
        let out = render_json(&sample_metas());
        let arr: Vec<serde_json::Value> = serde_json::from_str(&out).unwrap();
        assert_eq!(arr.len(), 2);
    }

    #[test]
    fn json_contains_expected_fields() {
        let out = render_json(&sample_metas());
        assert!(out.contains("\"session_id\""));
        assert!(out.contains("\"token_count\""));
        assert!(out.contains("\"tags\""));
        assert!(out.contains("\"user_turn_count\""));
        assert!(out.contains("\"user_turn_count\": 3"));
    }

    #[test]
    fn json_empty_slice_is_empty_array() {
        let out = render_json(&[]);
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v.as_array().unwrap().len(), 0);
    }

    // --- Summary ---

    #[test]
    fn summary_bundle_count() {
        let s = compute_summary(&sample_metas());
        assert_eq!(s.bundle_count, 2);
    }

    #[test]
    fn summary_total_tokens() {
        let s = compute_summary(&sample_metas());
        assert_eq!(s.total_tokens, 3000);
    }

    #[test]
    fn summary_avg_tokens() {
        let s = compute_summary(&sample_metas());
        assert!((s.avg_tokens - 1500.0).abs() < 0.01);
    }

    #[test]
    fn summary_most_used_model() {
        let s = compute_summary(&sample_metas());
        assert_eq!(s.most_used_model, "claude-3-sonnet");
    }

    #[test]
    fn summary_date_range() {
        let s = compute_summary(&sample_metas());
        assert_eq!(s.earliest, "2024-01-01T00:00:00Z");
        assert_eq!(s.latest, "2024-01-02T00:00:00Z");
    }

    #[test]
    fn summary_empty_slice_defaults() {
        let s = compute_summary(&[]);
        assert_eq!(s.bundle_count, 0);
        assert_eq!(s.total_tokens, 0);
    }

    #[test]
    fn render_summary_includes_key_fields() {
        let s = compute_summary(&sample_metas());
        let text = render_summary(&s);
        assert!(text.contains("3000"));
        assert!(text.contains("claude-3-sonnet"));
        assert!(text.contains("2024-01-01T00:00:00Z"));
    }

    // --- BundleMeta::from_value ---

    #[test]
    fn from_value_top_level_fields() {
        let v = serde_json::json!({
            "session_id": "s1",
            "model": "gpt-4",
            "token_count": 500,
            "message_count": 5,
            "duration_ms": 200,
            "created_at": "2024-06-01T00:00:00Z",
            "tags": ["a", "b"],
        });
        let m = BundleMeta::from_value(&v);
        assert_eq!(m.session_id, "s1");
        assert_eq!(m.model, "gpt-4");
        assert_eq!(m.token_count, 500);
        assert_eq!(m.tags, vec!["a", "b"]);
    }

    #[test]
    fn from_value_fallback_id_field() {
        let v = serde_json::json!({ "id": "s2" });
        let m = BundleMeta::from_value(&v);
        assert_eq!(m.session_id, "s2");
    }

    #[test]
    fn from_value_usage_nested_tokens() {
        let v = serde_json::json!({ "usage": { "total_tokens": 999 } });
        let m = BundleMeta::from_value(&v);
        assert_eq!(m.token_count, 999);
    }

    #[test]
    fn from_value_projects_graph_okf_identity_and_user_turns() {
        let v = serde_json::json!({
            "okf": "1.0",
            "source_id": "codex-session-1",
            "entities": [
                {
                    "id": "intent-0",
                    "type": "intent",
                    "label": "ship the metadata contract",
                    "properties": { "user_turn_count": 3 }
                }
            ],
            "relations": [],
            "provenance": { "corpus": "codex", "source_id": "codex-session-1" }
        });

        let m = BundleMeta::from_value(&v);
        assert_eq!(m.session_id, "codex-session-1");
        assert_eq!(m.user_turn_count, 3);
        assert_eq!(m.message_count, 0);
        assert!(m.model.is_empty());
        assert!(m.created_at.is_empty());
        assert_eq!(m.token_count, 0);
    }

    #[test]
    fn from_value_saturates_graph_user_turn_counts() {
        let v = serde_json::json!({
            "entities": [
                { "type": "intent", "properties": { "user_turn_count": u64::MAX } },
                { "type": "intent", "properties": { "user_turn_count": 1 } }
            ]
        });

        assert_eq!(BundleMeta::from_value(&v).user_turn_count, u64::MAX);
    }
}
