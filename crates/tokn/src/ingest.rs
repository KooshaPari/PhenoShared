use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde_json::Value;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command as ProcessCommand;
use std::time::{Instant, UNIX_EPOCH};

use crate::cli::{IngestArgs, IngestProvider};
use crate::models::*;
use crate::utils::*;

pub fn run_ingest(args: IngestArgs) -> Result<()> {
    let ingest_started_at = Utc::now();
    let ingest_timer = Instant::now();

    let providers = resolve_ingest_providers(&args.providers);

    if let Some(parent) = args.output.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let mut output_opts = OpenOptions::new();
    output_opts.create(true).write(true);
    if args.append {
        output_opts.append(true);
    } else {
        output_opts.truncate(true);
    }
    let output_file = output_opts
        .open(&args.output)
        .with_context(|| format!("opening {:?}", args.output))?;
    let mut writer = BufWriter::new(output_file);

    let mut total_emitted = 0usize;
    let mut deduped_total = 0usize;
    let mut dedupe_seen = args.dedupe_by_request.then(HashSet::new);
    let mut stats: BTreeMap<String, IngestStats> = BTreeMap::new();
    let mut incremental_skipped_sources = 0usize;
    let mut checkpoint = if let Some(path) = args.state_file.as_ref() {
        load_ingest_checkpoint(path)?
    } else {
        BTreeMap::new()
    };

    for provider in providers {
        let provider_name = ingest_provider_name(provider).to_string();
        let mut provider_stats = IngestStats::default();
        let sources = discover_provider_sources(provider);
        for source in sources {
            if args.limit.is_some_and(|limit| total_emitted >= limit) {
                break;
            }
            let source_key = source.to_string_lossy().to_string();
            let source_mtime = source_mtime_unix(&source);
            if args.incremental
                && source_mtime.is_some_and(|mtime| {
                    checkpoint
                        .get(&source_key)
                        .is_some_and(|saved| mtime <= *saved)
                })
            {
                incremental_skipped_sources += 1;
                continue;
            }
            let mut ctx = IngestEmitCtx {
                since: args.since,
                limit: args.limit,
                total_emitted: &mut total_emitted,
                deduped_total: &mut deduped_total,
                dedupe_seen: dedupe_seen.as_mut(),
                writer: &mut writer,
                stats: &mut provider_stats,
            };
            ingest_source_file(provider, &source, &mut ctx)?;
            if args.state_file.is_some() {
                if let Some(mtime) = source_mtime {
                    checkpoint.insert(source_key, mtime);
                }
            }
        }
        stats.insert(provider_name, provider_stats);
    }

    writer.flush()?;
    if let Some(path) = args.state_file.as_ref() {
        write_ingest_checkpoint(path, &checkpoint)?;
    }

    let ingest_finished_at = Utc::now();
    let ingest_duration_ms = ingest_timer.elapsed().as_millis();
    let summary = IngestSummary {
        providers: stats.clone(),
        incremental_sources_skipped: if args.incremental {
            incremental_skipped_sources
        } else {
            0
        },
        emitted_total: total_emitted,
        deduped_total,
        output: args.output.display().to_string(),
        started_at: ingest_started_at,
        finished_at: ingest_finished_at,
        duration_ms: ingest_duration_ms,
    };

    if let Some(path) = args.summary_json_path.as_ref() {
        write_ingest_summary(path, &summary)?;
    }

    eprintln!("ingest summary:");
    for (provider, provider_stats) in &stats {
        eprintln!(
            "  {} scanned={} emitted={} skipped={}",
            provider, provider_stats.scanned, provider_stats.emitted, provider_stats.skipped
        );
    }
    if args.incremental {
        eprintln!(
            "  incremental_sources_skipped={}",
            incremental_skipped_sources
        );
    }
    eprintln!("  output={}", summary.output);
    eprintln!("  emitted_total={}", summary.emitted_total);
    eprintln!("  deduped_total={}", summary.deduped_total);

    Ok(())
}

pub fn write_ingest_summary(path: &Path, summary: &IngestSummary) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating summary directory {:?}", parent))?;
        }
    }
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, summary)
        .with_context(|| format!("writing ingest summary {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing ingest summary newline {:?}", path))?;
    Ok(())
}

pub fn ingest_provider_name(provider: IngestProvider) -> &'static str {
    match provider {
        IngestProvider::Claude => "claude",
        IngestProvider::Codex => "codex",
        IngestProvider::Proxyapi => "proxyapi",
        IngestProvider::Cursor => "cursor",
        IngestProvider::Droid => "droid",
    }
}

pub fn ingest_default_model(provider: IngestProvider) -> &'static str {
    match provider {
        IngestProvider::Claude => "claude-sonnet-4-5",
        IngestProvider::Codex => "gpt-5",
        IngestProvider::Proxyapi => "proxyapi-default",
        IngestProvider::Cursor => "cursor-codex-latest",
        IngestProvider::Droid => "factory-droid-latest",
    }
}

pub fn discover_provider_sources(provider: IngestProvider) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let Some(home) = home_dir() else {
        return out;
    };

    match provider {
        IngestProvider::Claude => {
            collect_files_by_ext(&home.join(".claude").join("projects"), &["jsonl"], &mut out);
        }
        IngestProvider::Codex => {
            collect_files_by_ext(&home.join(".codex").join("sessions"), &["jsonl"], &mut out);
        }
        IngestProvider::Proxyapi => {
            collect_files_by_ext(
                &home.join(".cliproxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".cliproxyapi").join("logs"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".proxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".proxyapi").join("logs"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".config").join("cliproxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".config").join("proxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".local").join("share").join("cliproxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".local").join("share").join("proxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".cache").join("cliproxyapi"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home
                    .join("Library")
                    .join("Application Support")
                    .join("CLIProxyAPI"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join("Library").join("Logs").join("CLIProxyAPI"),
                &["json", "jsonl", "ndjson", "log", "txt"],
                &mut out,
            );
        }
        IngestProvider::Cursor => {
            collect_files_by_ext(&home.join(".cursor"), &["json", "jsonl", "log"], &mut out);
            collect_files_by_ext(
                &home
                    .join("Library")
                    .join("Application Support")
                    .join("Cursor")
                    .join("workspaceStorage"),
                &["json", "jsonl", "log"],
                &mut out,
            );
            collect_files_by_ext(
                &home.join(".cursor"),
                &["sqlite", "sqlite3", "db"],
                &mut out,
            );
            collect_files_by_ext(
                &home
                    .join("Library")
                    .join("Application Support")
                    .join("Cursor")
                    .join("workspaceStorage"),
                &["sqlite", "sqlite3", "db"],
                &mut out,
            );
        }
        IngestProvider::Droid => {
            collect_files_by_ext(
                &home.join(".factory").join("sessions"),
                &["json", "jsonl"],
                &mut out,
            );
        }
    }

    out.sort();
    out.dedup();
    out
}

pub fn collect_files_by_ext(root: &Path, exts: &[&str], out: &mut Vec<PathBuf>) {
    if !root.exists() {
        return;
    }
    let ext_set: HashSet<String> = exts.iter().map(|ext| ext.to_ascii_lowercase()).collect();
    for entry in walkdir::WalkDir::new(root)
        .into_iter()
        .filter_map(Result::ok)
    {
        if !entry.file_type().is_file() {
            continue;
        }
        if entry
            .path()
            .extension()
            .and_then(|s| s.to_str())
            .map(|s| ext_set.contains(&s.to_ascii_lowercase()))
            .unwrap_or(false)
        {
            out.push(entry.path().to_path_buf());
        }
    }
}

pub fn ingest_source_file(
    provider: IngestProvider,
    source: &Path,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let ext = source
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if ext == "jsonl" || ext == "log" {
        ingest_jsonl_like(provider, source, ctx)
    } else if ext == "json" {
        ingest_json_file(provider, source, ctx)
    } else if provider == IngestProvider::Cursor
        && (ext == "sqlite" || ext == "sqlite3" || ext == "db")
    {
        ingest_sqlite_best_effort(provider, source, ctx)
    } else {
        Ok(())
    }
}

pub fn ingest_jsonl_like(
    provider: IngestProvider,
    source: &Path,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let mut reader =
        BufReader::new(File::open(source).with_context(|| format!("opening {:?}", source))?);
    let mut line = String::new();
    loop {
        line.clear();
        let bytes = reader.read_line(&mut line)?;
        if bytes == 0 {
            break;
        }
        if ctx.limit_reached() {
            break;
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(value) = serde_json::from_str::<Value>(trimmed) {
            ingest_value_tree(provider, source, &value, ctx)?;
        } else {
            ctx.stats.scanned += 1;
            ctx.stats.skipped += 1;
        }
    }
    Ok(())
}

pub fn ingest_json_file(
    provider: IngestProvider,
    source: &Path,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let value: Value = match serde_json::from_reader(
        File::open(source).with_context(|| format!("opening {:?}", source))?,
    ) {
        Ok(value) => value,
        Err(_) => {
            ctx.stats.scanned += 1;
            ctx.stats.skipped += 1;
            return Ok(());
        }
    };
    ingest_value_tree(provider, source, &value, ctx)
}

pub fn ingest_sqlite_best_effort(
    provider: IngestProvider,
    source: &Path,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let emitted_before = *ctx.total_emitted;
    if provider == IngestProvider::Cursor {
        ingest_cursor_sqlite_table_backed(source, ctx)?;
        if *ctx.total_emitted > emitted_before || ctx.limit_reached() {
            return Ok(());
        }
    }
    ingest_sqlite_raw_json_fallback(provider, source, ctx)
}

pub fn ingest_sqlite_raw_json_fallback(
    provider: IngestProvider,
    source: &Path,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let mut bytes = Vec::new();
    match File::open(source).and_then(|mut file| file.read_to_end(&mut bytes)) {
        Ok(_) => {}
        Err(_) => return Ok(()),
    }
    let text = String::from_utf8_lossy(&bytes);
    for json in extract_json_objects(&text) {
        if ctx.limit_reached() {
            break;
        }
        ingest_sqlite_json_candidate(provider, source, &json, ctx)?;
    }
    Ok(())
}

#[derive(Debug, Clone)]
pub struct CursorSqliteColumn {
    pub name: String,
    pub declared_type: String,
    pub pk_ordinal: i64,
}

pub fn ingest_cursor_sqlite_table_backed(source: &Path, ctx: &mut IngestEmitCtx<'_>) -> Result<()> {
    let Some(table_names) = sqlite_list_tables(source) else {
        return Ok(());
    };
    for table_name in table_names {
        if ctx.limit_reached() {
            break;
        }
        let Some(columns) = sqlite_table_columns(source, &table_name) else {
            continue;
        };
        let selected_columns = select_cursor_sqlite_columns(&columns);
        if selected_columns.is_empty() {
            continue;
        }
        let (query, fallback_query) =
            build_cursor_sqlite_select_query(&table_name, &selected_columns, &columns);
        let rows = sqlite_query_rows(source, &query).or_else(|| {
            fallback_query
                .as_deref()
                .and_then(|fallback| sqlite_query_rows(source, fallback))
        });
        let Some(rows) = rows else {
            continue;
        };
        for row in rows {
            if ctx.limit_reached() {
                break;
            }
            let Value::Object(map) = row else {
                continue;
            };
            let row_value = Value::Object(map.clone());
            ingest_sqlite_candidate_value(IngestProvider::Cursor, source, &row_value, ctx)?;
            if ctx.limit_reached() {
                break;
            }
            for column_name in &selected_columns {
                if ctx.limit_reached() {
                    break;
                }
                let Some(column_value) = map.get(column_name) else {
                    continue;
                };
                if let Some(text) = sqlite_value_to_candidate_text(column_value) {
                    ingest_sqlite_text_with_fallback(IngestProvider::Cursor, source, &text, ctx)?;
                }
            }
        }
    }
    Ok(())
}

pub fn sqlite_list_tables(source: &Path) -> Option<Vec<String>> {
    let rows = sqlite_query_rows(
        source,
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';",
    )?;
    let mut names = Vec::new();
    for row in rows {
        if let Some(name) = row
            .as_object()
            .and_then(|map| map.get("name"))
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|name| !name.is_empty())
        {
            names.push(name.to_string());
        }
    }
    names.sort_by_key(|name| (cursor_sqlite_table_rank(name), name.to_ascii_lowercase()));
    names.dedup();
    Some(names)
}

pub fn sqlite_table_columns(source: &Path, table_name: &str) -> Option<Vec<CursorSqliteColumn>> {
    let pragma = format!(
        "PRAGMA table_info({});",
        quote_sqlite_identifier(table_name)
    );
    let rows = sqlite_query_rows(source, &pragma)?;
    let mut columns = Vec::new();
    for row in rows {
        let Some(map) = row.as_object() else {
            continue;
        };
        let Some(name) = map
            .get("name")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|name| !name.is_empty())
        else {
            continue;
        };
        let declared_type = map
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        let pk_ordinal = map
            .get("pk")
            .and_then(value_to_u64)
            .map(|v| v as i64)
            .unwrap_or(0);
        columns.push(CursorSqliteColumn {
            name: name.to_string(),
            declared_type,
            pk_ordinal,
        });
    }
    Some(columns)
}

pub fn select_cursor_sqlite_columns(columns: &[CursorSqliteColumn]) -> Vec<String> {
    let mut selected: Vec<String> = columns
        .iter()
        .filter(|column| cursor_sqlite_column_selected(column))
        .map(|column| column.name.clone())
        .collect();
    selected.sort_by_key(|name| {
        (
            cursor_sqlite_column_rank(name),
            name.to_ascii_lowercase(),
            name.len(),
        )
    });
    selected.dedup();
    selected
}

pub fn cursor_sqlite_table_rank(table_name: &str) -> usize {
    let lowered = table_name.to_ascii_lowercase();
    if lowered.contains("usage") || lowered.contains("token") {
        return 0;
    }
    if lowered.contains("prompt") || lowered.contains("chat") || lowered.contains("message") {
        return 1;
    }
    if lowered.contains("event") || lowered.contains("request") || lowered.contains("telemetry") {
        return 2;
    }
    3
}

pub fn cursor_sqlite_column_selected(column: &CursorSqliteColumn) -> bool {
    let name = column.name.to_ascii_lowercase();
    let declared = column.declared_type.to_ascii_lowercase();
    if declared.contains("blob") {
        return false;
    }
    let textish = declared.is_empty()
        || declared.contains("text")
        || declared.contains("char")
        || declared.contains("clob")
        || declared.contains("json");
    let payload_like = [
        "payload", "json", "body", "data", "record", "event", "message", "request", "response",
        "content", "value", "metadata",
    ]
    .iter()
    .any(|needle| name.contains(needle));
    let usage_like = [
        "token",
        "prompt",
        "completion",
        "cache",
        "tool",
        "model",
        "timestamp",
        "created",
        "date",
        "workspace",
        "session",
        "conversation",
        "usage",
        "metric",
    ]
    .iter()
    .any(|needle| name.contains(needle))
        || name == "id"
        || name.ends_with("_id")
        || name.ends_with("id");
    payload_like || usage_like || textish
}

pub fn cursor_sqlite_column_rank(column_name: &str) -> usize {
    let lowered = column_name.to_ascii_lowercase();
    if lowered.contains("payload") || lowered.contains("json") {
        return 0;
    }
    if lowered.contains("token")
        || lowered.contains("prompt")
        || lowered.contains("completion")
        || lowered.contains("usage")
    {
        return 1;
    }
    if lowered.contains("timestamp")
        || lowered.contains("created")
        || lowered.contains("date")
        || lowered.contains("time")
    {
        return 2;
    }
    if lowered.contains("model")
        || lowered.contains("workspace")
        || lowered.contains("session")
        || lowered.contains("conversation")
        || lowered == "id"
        || lowered.ends_with("_id")
    {
        return 3;
    }
    4
}

pub fn build_cursor_sqlite_select_query(
    table_name: &str,
    selected_columns: &[String],
    table_columns: &[CursorSqliteColumn],
) -> (String, Option<String>) {
    let select_columns = selected_columns
        .iter()
        .map(|name| quote_sqlite_identifier(name))
        .collect::<Vec<_>>()
        .join(", ");
    let not_null_predicate = selected_columns
        .iter()
        .map(|name| format!("{} IS NOT NULL", quote_sqlite_identifier(name)))
        .collect::<Vec<_>>()
        .join(" OR ");
    let table_ident = quote_sqlite_identifier(table_name);
    let mut pk_columns: Vec<&CursorSqliteColumn> = table_columns
        .iter()
        .filter(|column| column.pk_ordinal > 0)
        .collect();
    pk_columns.sort_by_key(|column| (column.pk_ordinal, column.name.to_ascii_lowercase()));
    let order_clause = if pk_columns.is_empty() {
        "rowid".to_string()
    } else {
        pk_columns
            .iter()
            .map(|column| quote_sqlite_identifier(&column.name))
            .collect::<Vec<_>>()
            .join(", ")
    };
    let primary_query = format!(
        "SELECT {select_columns} FROM {table_ident} WHERE {not_null_predicate} ORDER BY {order_clause};"
    );
    let fallback_query = if pk_columns.is_empty() {
        Some(format!(
            "SELECT {select_columns} FROM {table_ident} WHERE {not_null_predicate};"
        ))
    } else {
        None
    };
    (primary_query, fallback_query)
}

pub fn quote_sqlite_identifier(identifier: &str) -> String {
    format!("\"{}\"", identifier.replace('"', "\"\""))
}

pub fn sqlite_query_rows(source: &Path, sql: &str) -> Option<Vec<Value>> {
    let output = ProcessCommand::new("sqlite3")
        .arg("-readonly")
        .arg("-json")
        .arg(source)
        .arg(sql)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let parsed = serde_json::from_slice::<Value>(&output.stdout).ok()?;
    parsed.as_array().cloned()
}

pub fn sqlite_value_to_candidate_text(value: &Value) -> Option<String> {
    match value {
        Value::String(text) => {
            let trimmed = text.trim();
            (!trimmed.is_empty()).then_some(trimmed.to_string())
        }
        Value::Object(_) | Value::Array(_) => Some(value.to_string()),
        _ => None,
    }
}

pub fn ingest_sqlite_text_with_fallback(
    provider: IngestProvider,
    source: &Path,
    text: &str,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return Ok(());
    }
    if let Ok(value) = serde_json::from_str::<Value>(trimmed) {
        match &value {
            Value::Object(_) => {
                ingest_sqlite_candidate_value(provider, source, &value, ctx)?;
                return Ok(());
            }
            Value::Array(items) => {
                for item in items {
                    if ctx.limit_reached() {
                        break;
                    }
                    ingest_sqlite_candidate_value(provider, source, item, ctx)?;
                }
                return Ok(());
            }
            _ => {}
        }
    }
    for json in extract_json_objects(trimmed) {
        if ctx.limit_reached() {
            break;
        }
        ingest_sqlite_json_candidate(provider, source, &json, ctx)?;
    }
    Ok(())
}

pub fn ingest_sqlite_json_candidate(
    provider: IngestProvider,
    source: &Path,
    json: &str,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let value = match serde_json::from_str::<Value>(json) {
        Ok(value) => value,
        Err(_) => {
            ctx.stats.scanned += 1;
            ctx.stats.skipped += 1;
            return Ok(());
        }
    };
    ingest_sqlite_candidate_value(provider, source, &value, ctx)
}

pub fn ingest_sqlite_candidate_value(
    provider: IngestProvider,
    source: &Path,
    value: &Value,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    ctx.stats.scanned += 1;
    if let Some(event) = normalize_ingest_record(provider, source, value) {
        if ctx.since.is_some_and(|since_ts| event.timestamp < since_ts) {
            return Ok(());
        }
        ctx.emit_event(&event)?;
    } else {
        ctx.stats.skipped += 1;
    }
    Ok(())
}

pub fn ingest_value_tree(
    provider: IngestProvider,
    source: &Path,
    root: &Value,
    ctx: &mut IngestEmitCtx<'_>,
) -> Result<()> {
    let mut records = Vec::new();
    collect_object_nodes(root, &mut records);
    if records.is_empty() && root.is_object() {
        records.push(root);
    }
    for value in records {
        if ctx.limit_reached() {
            break;
        }
        ctx.stats.scanned += 1;
        if let Some(event) = normalize_ingest_record(provider, source, value) {
            if ctx.since.is_some_and(|since_ts| event.timestamp < since_ts) {
                continue;
            }
            ctx.emit_event(&event)?;
        } else {
            ctx.stats.skipped += 1;
        }
    }
    Ok(())
}

pub fn collect_object_nodes<'a>(value: &'a Value, out: &mut Vec<&'a Value>) {
    match value {
        Value::Object(map) => {
            out.push(value);
            for child in map.values() {
                collect_object_nodes(child, out);
            }
        }
        Value::Array(items) => {
            for item in items {
                collect_object_nodes(item, out);
            }
        }
        _ => {}
    }
}

pub fn normalize_ingest_record(
    provider: IngestProvider,
    source: &Path,
    value: &Value,
) -> Option<UsageEvent> {
    let usage =
        extract_provider_token_usage(provider, value).unwrap_or_else(|| extract_token_usage(value));
    if usage.total() == 0 {
        return None;
    }
    let timestamp =
        extract_provider_timestamp(provider, value).or_else(|| extract_timestamp(value))?;
    let model = extract_provider_model(provider, value)
        .or_else(|| extract_string_by_keys(value, &["model", "model_name", "modelId", "engine"]))
        .unwrap_or_else(|| ingest_default_model(provider).to_string());
    let session_id = extract_provider_session_id(provider, value)
        .or_else(|| {
            extract_string_by_keys(
                value,
                &[
                    "session_id",
                    "sessionId",
                    "conversation_id",
                    "conversationId",
                    "chat_id",
                    "id",
                ],
            )
        })
        .unwrap_or_else(|| format!("{}:{}", source.display(), timestamp.timestamp_millis()));
    Some(UsageEvent {
        provider: ingest_provider_name(provider).to_string(),
        model,
        session_id,
        timestamp,
        usage,
    })
}

pub fn extract_provider_token_usage(provider: IngestProvider, value: &Value) -> Option<TokenUsage> {
    let usage = match provider {
        IngestProvider::Claude => TokenUsage {
            input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "input_tokens"],
                    &["event", "message", "usage", "input_tokens"],
                    &["request", "usage", "input_tokens"],
                ],
            )
            .unwrap_or(0),
            output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "output_tokens"],
                    &["event", "message", "usage", "output_tokens"],
                    &["request", "usage", "output_tokens"],
                ],
            )
            .unwrap_or(0),
            cache_write_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "cache_creation_input_tokens"],
                    &["event", "message", "usage", "cache_creation_input_tokens"],
                    &["request", "usage", "cache_creation_input_tokens"],
                ],
            )
            .unwrap_or(0),
            cache_read_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "cache_read_input_tokens"],
                    &["event", "message", "usage", "cache_read_input_tokens"],
                    &["request", "usage", "cache_read_input_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "tool_input_tokens"],
                    &["event", "message", "usage", "tool_input_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["message", "usage", "tool_output_tokens"],
                    &["event", "message", "usage", "tool_output_tokens"],
                ],
            )
            .unwrap_or(0),
        },
        IngestProvider::Codex => TokenUsage {
            input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["response", "usage", "prompt_tokens"],
                    &["result", "usage", "prompt_tokens"],
                    &["payload", "usage", "prompt_tokens"],
                ],
            )
            .unwrap_or(0),
            output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["response", "usage", "completion_tokens"],
                    &["result", "usage", "completion_tokens"],
                    &["payload", "usage", "completion_tokens"],
                ],
            )
            .unwrap_or(0),
            cache_write_tokens: extract_u64_by_paths(
                value,
                &[
                    &[
                        "response",
                        "usage",
                        "prompt_tokens_details",
                        "cached_write_tokens",
                    ],
                    &[
                        "result",
                        "usage",
                        "prompt_tokens_details",
                        "cached_write_tokens",
                    ],
                ],
            )
            .unwrap_or(0),
            cache_read_tokens: extract_u64_by_paths(
                value,
                &[
                    &[
                        "response",
                        "usage",
                        "prompt_tokens_details",
                        "cached_tokens",
                    ],
                    &["result", "usage", "prompt_tokens_details", "cached_tokens"],
                    &["payload", "usage", "prompt_tokens_details", "cached_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["response", "usage", "tool_input_tokens"],
                    &["result", "usage", "tool_input_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["response", "usage", "tool_output_tokens"],
                    &["result", "usage", "tool_output_tokens"],
                ],
            )
            .unwrap_or(0),
        },
        IngestProvider::Proxyapi => {
            let input_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "input_tokens"],
                    &["usage", "prompt_tokens"],
                    &["usage_record", "usage", "input_tokens"],
                    &["usage_record", "usage", "prompt_tokens"],
                    &["management", "usage", "input_tokens"],
                    &["management", "usage", "prompt_tokens"],
                    &["token_usage", "input_tokens"],
                    &["token_usage", "prompt_tokens"],
                    &["metrics", "tokens", "input"],
                    &["metrics", "tokens", "prompt"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.input_tokens",
                        "llm.usage.prompt_tokens",
                        "proxyapi.usage.input_tokens",
                        "usage.input_tokens",
                        "prompt_tokens",
                        "input_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            let output_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "output_tokens"],
                    &["usage", "completion_tokens"],
                    &["usage_record", "usage", "output_tokens"],
                    &["usage_record", "usage", "completion_tokens"],
                    &["management", "usage", "output_tokens"],
                    &["management", "usage", "completion_tokens"],
                    &["token_usage", "output_tokens"],
                    &["token_usage", "completion_tokens"],
                    &["metrics", "tokens", "output"],
                    &["metrics", "tokens", "completion"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.output_tokens",
                        "llm.usage.completion_tokens",
                        "proxyapi.usage.output_tokens",
                        "usage.output_tokens",
                        "completion_tokens",
                        "output_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            let cache_write_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "cache_write_tokens"],
                    &["usage_record", "usage", "cache_write_tokens"],
                    &["management", "usage", "cache_write_tokens"],
                    &["token_usage", "cache_write_tokens"],
                    &["metrics", "tokens", "cache", "write"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.cache_write_tokens",
                        "proxyapi.usage.cache_write_tokens",
                        "cache_write_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            let cache_read_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "cache_read_tokens"],
                    &["usage_record", "usage", "cache_read_tokens"],
                    &["management", "usage", "cache_read_tokens"],
                    &["token_usage", "cache_read_tokens"],
                    &["metrics", "tokens", "cache", "read"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.cache_read_tokens",
                        "proxyapi.usage.cache_read_tokens",
                        "cache_read_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            let tool_input_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "tool_input_tokens"],
                    &["usage_record", "usage", "tool_input_tokens"],
                    &["management", "usage", "tool_input_tokens"],
                    &["token_usage", "tool_input_tokens"],
                    &["metrics", "tokens", "tools", "input"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.tool_input_tokens",
                        "proxyapi.usage.tool_input_tokens",
                        "tool_input_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            let tool_output_tokens = extract_u64_by_paths(
                value,
                &[
                    &["usage", "tool_output_tokens"],
                    &["usage_record", "usage", "tool_output_tokens"],
                    &["management", "usage", "tool_output_tokens"],
                    &["token_usage", "tool_output_tokens"],
                    &["metrics", "tokens", "tools", "output"],
                ],
            )
            .or_else(|| {
                extract_proxyapi_attribute_u64(
                    value,
                    &[
                        "gen_ai.usage.tool_output_tokens",
                        "proxyapi.usage.tool_output_tokens",
                        "tool_output_tokens",
                    ],
                )
            })
            .unwrap_or(0);
            TokenUsage {
                input_tokens,
                output_tokens,
                cache_write_tokens,
                cache_read_tokens,
                tool_input_tokens,
                tool_output_tokens,
            }
        }
        IngestProvider::Cursor => TokenUsage {
            input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "prompt"],
                    &["metrics", "tokens", "prompt"],
                    &["tokens", "prompt"],
                ],
            )
            .unwrap_or(0),
            output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "completion"],
                    &["metrics", "tokens", "completion"],
                    &["tokens", "completion"],
                ],
            )
            .unwrap_or(0),
            cache_write_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "cache", "write"],
                    &["metrics", "tokens", "cache", "write"],
                    &["tokens", "cache", "write"],
                ],
            )
            .unwrap_or(0),
            cache_read_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "cache", "read"],
                    &["metrics", "tokens", "cache", "read"],
                    &["tokens", "cache", "read"],
                ],
            )
            .unwrap_or(0),
            tool_input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "tooling", "input"],
                    &["metrics", "tokens", "tooling", "input"],
                    &["tokens", "tooling", "input"],
                ],
            )
            .unwrap_or(0),
            tool_output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["record", "tokens", "tooling", "output"],
                    &["metrics", "tokens", "tooling", "output"],
                    &["tokens", "tooling", "output"],
                ],
            )
            .unwrap_or(0),
        },
        IngestProvider::Droid => TokenUsage {
            input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "tokens", "user"],
                    &["metrics", "tokens", "user"],
                    &["usage", "user_tokens"],
                ],
            )
            .unwrap_or(0),
            output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "tokens", "assistant"],
                    &["metrics", "tokens", "assistant"],
                    &["usage", "assistant_tokens"],
                ],
            )
            .unwrap_or(0),
            cache_write_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "cache", "create"],
                    &["metrics", "cache", "create"],
                    &["usage", "cache_create_tokens"],
                ],
            )
            .unwrap_or(0),
            cache_read_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "cache", "read"],
                    &["metrics", "cache", "read"],
                    &["usage", "cache_read_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_input_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "tools", "input"],
                    &["metrics", "tools", "input"],
                    &["usage", "tools_input_tokens"],
                ],
            )
            .unwrap_or(0),
            tool_output_tokens: extract_u64_by_paths(
                value,
                &[
                    &["session", "metrics", "tools", "output"],
                    &["metrics", "tools", "output"],
                    &["usage", "tools_output_tokens"],
                ],
            )
            .unwrap_or(0),
        },
    };
    (usage.total() > 0).then_some(usage)
}

pub fn extract_provider_timestamp(
    provider: IngestProvider,
    value: &Value,
) -> Option<DateTime<Utc>> {
    let paths: &[&[&str]] = match provider {
        IngestProvider::Claude => &[
            &["message", "created_at"],
            &["event", "created_at"],
            &["request", "started_at"],
        ],
        IngestProvider::Codex => &[
            &["response", "created_at"],
            &["result", "created_at"],
            &["event_time_ms"],
        ],
        IngestProvider::Proxyapi => &[
            &["timestamp"],
            &["time"],
            &["created_at"],
            &["createdAt"],
            &["recorded_at"],
            &["usage_record", "timestamp"],
            &["usage_record", "created_at"],
            &["management", "timestamp"],
            &["management", "created_at"],
            &["event", "timestamp"],
            &["metrics", "timestamp"],
            &["span", "start_time"],
            &["span", "end_time"],
            &["start_time"],
            &["end_time"],
            &["otel", "startTimeUnixNano"],
            &["otel", "endTimeUnixNano"],
            &["startTimeUnixNano"],
            &["endTimeUnixNano"],
        ],
        IngestProvider::Cursor => &[
            &["recorded_at"],
            &["record", "timestamp_ms"],
            &["metrics", "timestamp"],
        ],
        IngestProvider::Droid => &[
            &["session", "started_at"],
            &["session", "metrics", "timestamp"],
            &["metrics", "timestamp"],
        ],
    };
    for path in paths {
        if let Some(found) = find_value_by_path(value, path) {
            if provider == IngestProvider::Proxyapi {
                if let Some(parsed) = parse_proxyapi_timestamp_value(found) {
                    return Some(parsed);
                }
            } else if let Some(parsed) = parse_timestamp_value(found) {
                return Some(parsed);
            }
        }
    }
    if provider == IngestProvider::Proxyapi {
        return extract_proxyapi_attribute_timestamp(
            value,
            &[
                "proxyapi.timestamp",
                "gen_ai.timestamp",
                "event.timestamp",
                "usage.timestamp",
            ],
        );
    }
    None
}

pub fn extract_provider_model(provider: IngestProvider, value: &Value) -> Option<String> {
    let paths: &[&[&str]] = match provider {
        IngestProvider::Claude => &[&["message", "model"], &["request", "model"]],
        IngestProvider::Codex => &[&["response", "model"], &["result", "model"]],
        IngestProvider::Proxyapi => &[
            &["model"],
            &["usage_record", "model"],
            &["management", "model"],
            &["request", "model"],
            &["response", "model"],
            &["resource", "model"],
        ],
        IngestProvider::Cursor => &[&["record", "agent", "model"], &["agent", "model"]],
        IngestProvider::Droid => &[&["session", "agent_model"], &["agent", "model"]],
    };
    extract_string_by_paths(value, paths).or_else(|| {
        if provider == IngestProvider::Proxyapi {
            extract_proxyapi_attribute_string(
                value,
                &[
                    "gen_ai.request.model",
                    "llm.request.model",
                    "proxyapi.model",
                    "model",
                ],
            )
        } else {
            None
        }
    })
}

pub fn extract_provider_session_id(provider: IngestProvider, value: &Value) -> Option<String> {
    let paths: &[&[&str]] = match provider {
        IngestProvider::Claude => &[
            &["message", "session_id"],
            &["message", "conversation_id"],
            &["request", "session_id"],
        ],
        IngestProvider::Codex => &[
            &["response", "session_id"],
            &["result", "session_id"],
            &["rollout_id"],
        ],
        IngestProvider::Proxyapi => &[
            &["session_id"],
            &["sessionId"],
            &["usage_record", "session_id"],
            &["usage_record", "sessionId"],
            &["management", "session_id"],
            &["management", "sessionId"],
            &["request_id"],
            &["requestId"],
        ],
        IngestProvider::Cursor => &[
            &["record", "workspace_id"],
            &["record", "session_id"],
            &["workspace_id"],
        ],
        IngestProvider::Droid => &[&["session", "id"], &["session", "session_id"], &["run_id"]],
    };
    let direct = extract_string_by_paths(value, paths);
    if provider == IngestProvider::Proxyapi {
        direct
            .or_else(|| {
                extract_proxyapi_attribute_string(
                    value,
                    &[
                        "proxyapi.session_id",
                        "gen_ai.session.id",
                        "session.id",
                        "user.id",
                    ],
                )
            })
            .or_else(|| {
                extract_string_by_paths(
                    value,
                    &[&["trace_id"], &["traceId"], &["span_id"], &["spanId"]],
                )
            })
    } else {
        direct
    }
}

pub fn parse_proxyapi_timestamp_value(value: &Value) -> Option<DateTime<Utc>> {
    if let Some(num) = value_to_u64(value) {
        return parse_epoch_auto(num);
    }
    if let Some(num) = value.as_i64().filter(|raw| *raw > 0) {
        return parse_epoch_auto(num as u64);
    }
    if let Some(text) = value
        .as_str()
        .map(str::trim)
        .filter(|text| !text.is_empty())
    {
        if let Ok(num) = text.parse::<u64>() {
            return parse_epoch_auto(num);
        }
        if let Ok(parsed) = DateTime::parse_from_rfc3339(text) {
            return Some(parsed.with_timezone(&Utc));
        }
    }
    None
}

pub fn parse_epoch_auto(raw: u64) -> Option<DateTime<Utc>> {
    if raw >= 1_000_000_000_000_000_000 {
        let nanos = i64::try_from(raw).ok()?;
        return Some(DateTime::<Utc>::from_timestamp_nanos(nanos));
    }
    if raw >= 1_000_000_000_000_000 {
        return DateTime::<Utc>::from_timestamp_micros(raw as i64);
    }
    if raw >= 1_000_000_000_000 {
        return DateTime::<Utc>::from_timestamp_millis(raw as i64);
    }
    DateTime::<Utc>::from_timestamp(raw as i64, 0)
}

pub fn extract_proxyapi_attribute_u64(value: &Value, keys: &[&str]) -> Option<u64> {
    let attributes = extract_proxyapi_attributes(value);
    for key in keys {
        if let Some(found) = attributes.get(*key).and_then(value_to_u64) {
            return Some(found);
        }
    }
    None
}

pub fn extract_proxyapi_attribute_string(value: &Value, keys: &[&str]) -> Option<String> {
    let attributes = extract_proxyapi_attributes(value);
    for key in keys {
        if let Some(found) = attributes.get(*key).and_then(|attr| {
            attr.as_str()
                .map(str::trim)
                .filter(|text| !text.is_empty())
                .map(ToString::to_string)
        }) {
            return Some(found);
        }
    }
    None
}

pub fn extract_proxyapi_attribute_timestamp(value: &Value, keys: &[&str]) -> Option<DateTime<Utc>> {
    let attributes = extract_proxyapi_attributes(value);
    for key in keys {
        if let Some(found) = attributes
            .get(*key)
            .and_then(parse_proxyapi_timestamp_value)
        {
            return Some(found);
        }
    }
    None
}

pub fn extract_proxyapi_attributes(value: &Value) -> HashMap<String, Value> {
    let mut out = HashMap::new();
    let mut nodes = Vec::new();
    collect_object_nodes(value, &mut nodes);
    for node in nodes {
        let Some(attributes) = node.get("attributes").and_then(Value::as_array) else {
            continue;
        };
        for entry in attributes {
            let Some(entry_obj) = entry.as_object() else {
                continue;
            };
            let Some(key) = entry_obj
                .get("key")
                .and_then(Value::as_str)
                .map(str::trim)
                .filter(|key| !key.is_empty())
            else {
                continue;
            };
            let Some(raw_value) = entry_obj.get("value") else {
                continue;
            };
            out.insert(key.to_string(), unwrap_otel_attribute_value(raw_value));
        }
    }
    out
}

pub fn unwrap_otel_attribute_value(value: &Value) -> Value {
    let Some(map) = value.as_object() else {
        return value.clone();
    };
    for key in [
        "stringValue",
        "intValue",
        "doubleValue",
        "boolValue",
        "value",
    ] {
        if let Some(inner) = map.get(key) {
            return inner.clone();
        }
    }
    value.clone()
}

pub fn extract_string_by_paths(value: &Value, paths: &[&[&str]]) -> Option<String> {
    for path in paths {
        if let Some(found) = find_value_by_path(value, path) {
            if let Some(text) = found.as_str() {
                if !text.trim().is_empty() {
                    return Some(text.to_string());
                }
            }
        }
    }
    None
}

pub fn extract_u64_by_paths(value: &Value, paths: &[&[&str]]) -> Option<u64> {
    for path in paths {
        if let Some(found) = find_value_by_path(value, path) {
            if let Some(parsed) = value_to_u64(found) {
                return Some(parsed);
            }
        }
    }
    None
}

pub fn find_value_by_path<'a>(value: &'a Value, path: &[&str]) -> Option<&'a Value> {
    let mut current = value;
    for key in path {
        let next = current.as_object()?.get(*key)?;
        current = next;
    }
    Some(current)
}

pub fn extract_token_usage(value: &Value) -> TokenUsage {
    TokenUsage {
        input_tokens: extract_u64_by_keys(
            value,
            &[
                "input_tokens",
                "prompt_tokens",
                "input",
                "inputTokenCount",
                "promptTokenCount",
            ],
        )
        .unwrap_or(0),
        output_tokens: extract_u64_by_keys(
            value,
            &[
                "output_tokens",
                "completion_tokens",
                "output",
                "outputTokenCount",
                "completionTokenCount",
            ],
        )
        .unwrap_or(0),
        cache_write_tokens: extract_u64_by_keys(
            value,
            &[
                "cache_write_tokens",
                "cache_creation_input_tokens",
                "cacheWriteTokens",
            ],
        )
        .unwrap_or(0),
        cache_read_tokens: extract_u64_by_keys(
            value,
            &[
                "cache_read_tokens",
                "cache_read_input_tokens",
                "cached_tokens",
                "cacheReadTokens",
            ],
        )
        .unwrap_or(0),
        tool_input_tokens: extract_u64_by_keys(
            value,
            &[
                "tool_input_tokens",
                "tool_call_input_tokens",
                "toolInputTokens",
            ],
        )
        .unwrap_or(0),
        tool_output_tokens: extract_u64_by_keys(
            value,
            &[
                "tool_output_tokens",
                "tool_call_output_tokens",
                "toolOutputTokens",
            ],
        )
        .unwrap_or(0),
    }
}

pub fn extract_timestamp(value: &Value) -> Option<DateTime<Utc>> {
    let candidates = [
        "timestamp",
        "created_at",
        "createdAt",
        "time",
        "date",
        "datetime",
        "event_time",
        "started_at",
    ];
    for key in candidates {
        if let Some(raw) = find_key_value(value, key) {
            if let Some(parsed) = parse_timestamp_value(raw) {
                return Some(parsed);
            }
        }
    }
    None
}

pub fn parse_timestamp_value(value: &Value) -> Option<DateTime<Utc>> {
    if let Some(text) = value.as_str() {
        if let Ok(ts) = DateTime::parse_from_rfc3339(text) {
            return Some(ts.with_timezone(&Utc));
        }
    } else if let Some(num) = value.as_i64() {
        if num > 1_000_000_000_000 {
            return DateTime::<Utc>::from_timestamp_millis(num);
        }
        return DateTime::<Utc>::from_timestamp(num, 0);
    } else if let Some(num) = value.as_u64() {
        if num > 1_000_000_000_000 {
            return DateTime::<Utc>::from_timestamp_millis(num as i64);
        }
        return DateTime::<Utc>::from_timestamp(num as i64, 0);
    }
    None
}

pub fn extract_string_by_keys(value: &Value, keys: &[&str]) -> Option<String> {
    for key in keys {
        if let Some(found) = find_key_value(value, key) {
            if let Some(text) = found.as_str() {
                if !text.trim().is_empty() {
                    return Some(text.to_string());
                }
            }
        }
    }
    None
}

pub fn extract_u64_by_keys(value: &Value, keys: &[&str]) -> Option<u64> {
    for key in keys {
        if let Some(found) = find_key_value(value, key) {
            if let Some(parsed) = value_to_u64(found) {
                return Some(parsed);
            }
        }
    }
    None
}

pub fn value_to_u64(value: &Value) -> Option<u64> {
    if let Some(v) = value.as_u64() {
        return Some(v);
    }
    if let Some(v) = value.as_i64() {
        return (v >= 0).then_some(v as u64);
    }
    if let Some(v) = value.as_f64() {
        return (v >= 0.0).then_some(v.round() as u64);
    }
    if let Some(v) = value.as_str() {
        if let Ok(parsed) = v.trim().parse::<u64>() {
            return Some(parsed);
        }
    }
    None
}

pub fn find_key_value<'a>(value: &'a Value, key: &str) -> Option<&'a Value> {
    match value {
        Value::Object(map) => {
            if let Some(found) = map.get(key) {
                return Some(found);
            }
            for child in map.values() {
                if let Some(found) = find_key_value(child, key) {
                    return Some(found);
                }
            }
            None
        }
        Value::Array(items) => {
            for item in items {
                if let Some(found) = find_key_value(item, key) {
                    return Some(found);
                }
            }
            None
        }
        _ => None,
    }
}

pub fn extract_json_objects(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut depth = 0usize;
    let mut in_string = false;
    let mut escape = false;
    let mut start = None;
    for (idx, ch) in text.char_indices() {
        if in_string {
            if escape {
                escape = false;
                continue;
            }
            if ch == '\\' {
                escape = true;
                continue;
            }
            if ch == '"' {
                in_string = false;
            }
            continue;
        }
        if ch == '"' {
            in_string = true;
            continue;
        }
        if ch == '{' {
            if depth == 0 {
                start = Some(idx);
            }
            depth += 1;
        } else if ch == '}' {
            if depth == 0 {
                continue;
            }
            depth -= 1;
            if depth == 0 {
                if let Some(start_idx) = start {
                    out.push(text[start_idx..=idx].to_string());
                }
                start = None;
            }
        }
    }
    out
}

pub fn home_dir() -> Option<PathBuf> {
    env::var_os("HOME").map(PathBuf::from)
}

pub fn source_mtime_unix(path: &Path) -> Option<u64> {
    let modified = fs::metadata(path).ok()?.modified().ok()?;
    modified
        .duration_since(UNIX_EPOCH)
        .ok()
        .map(|duration| duration.as_secs())
}

pub fn load_ingest_checkpoint(path: &Path) -> Result<BTreeMap<String, u64>> {
    if !path.exists() {
        return Ok(BTreeMap::new());
    }
    serde_json::from_reader(File::open(path).with_context(|| format!("opening {:?}", path))?)
        .with_context(|| format!("parsing checkpoint {:?}", path))
}

pub fn write_ingest_checkpoint(path: &Path, checkpoint: &BTreeMap<String, u64>) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating checkpoint directory {:?}", parent))?;
        }
    }
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, checkpoint)
        .with_context(|| format!("writing checkpoint {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing checkpoint newline {:?}", path))?;
    Ok(())
}
