//! `phenoctl` CLI backed by the real Configra runtime library.

use std::path::PathBuf;

use anyhow::{anyhow, Context, Result};
use clap::{Parser, Subcommand};
use config_schema::ConfigSchema;
use serde::{Deserialize, Serialize};
use serde_json::{self, Map, Value};
use settly::adapters::sources::{CliSource, EnvSource, FileSource};
use settly::application::builder::ConfigBuilder;
use settly::crypto::{decrypt_from_file, encrypt, HotReloader};
use settly::domain::{Config, ConfigValue, Layer, LayerPriority, LayerStack, Source};
use tokio::sync::broadcast;

#[derive(Debug, Parser)]
#[command(name = "phenoctl", version, about = "Configra config operations CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Print one merged config value (`get <key>`).
    Get {
        key: String,
        #[arg(short, long, value_name = "PATH")]
        file: Vec<PathBuf>,
        #[arg(long, default_value_t = false)]
        env: bool,
    },

    /// Set one merged config value (`set <key> <val>`) and print the result.
    Set {
        key: String,
        val: String,
        #[arg(short, long, value_name = "PATH")]
        file: Vec<PathBuf>,
        #[arg(long, default_value_t = false)]
        env: bool,
        #[arg(long, value_name = "PATH")]
        output: Option<PathBuf>,
    },

    /// Validate merged config with `ConfigSchema::validate`.
    Validate {
        #[arg(short, long, value_name = "PATH")]
        file: Vec<PathBuf>,
        #[arg(long, default_value_t = false)]
        env: bool,
        #[arg(short, long, value_name = "PATH")]
        schema: PathBuf,
    },

    /// Encrypt a JSON payload with AES-256-GCM (`encrypt`).
    Encrypt {
        input: PathBuf,
        output: PathBuf,
        #[arg(short, long)]
        passphrase: String,
        #[arg(long, default_value = "")]
        aad: String,
    },

    /// Decrypt a `.enc` payload with AES-256-GCM (`decrypt`).
    Decrypt {
        input: PathBuf,
        #[arg(short, long, value_name = "PATH")]
        output: Option<PathBuf>,
        #[arg(short, long)]
        passphrase: String,
    },

    /// Watch an encrypted config file for reloads.
    Watch {
        #[arg(short, long, value_name = "PATH")]
        file: PathBuf,
        #[arg(short, long)]
        passphrase: String,
        /// Exit after initial read.
        #[arg(long, default_value_t = false)]
        once: bool,
    },

    /// Show layer merge order used by `LayerStack`.
    Layers {
        #[arg(short, long, value_name = "PATH")]
        file: Vec<PathBuf>,
        #[arg(long, default_value_t = false)]
        env: bool,
    },
}

#[derive(Debug, Serialize, Deserialize)]
struct CliSchemaFile {
    fields: Vec<SchemaFieldArg>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SchemaFieldArg {
    name: String,
    #[serde(default)]
    required: bool,
    #[serde(default = "default_type_hint")]
    type_hint: String,
}

fn default_type_hint() -> String {
    "string".to_string()
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    let result = match cli.command {
        Command::Get { key, file, env } => {
            let config = load_config(&file, env, &[]).await?;
            let value = config
                .get(&key)
                .ok_or_else(|| anyhow!("missing key: {key}"))?;
            println!("{}", config_value_to_json(value));
            Ok(())
        }
        Command::Set {
            key,
            val,
            file,
            env,
            output,
        } => {
            let mut config = load_config(&file, env, &[]).await?;
            config.set(key, parse_value(&val));
            let merged = flatten_config_to_value(&config);
            let rendered = serde_json::to_string_pretty(&merged)?;
            if let Some(path) = output {
                std::fs::write(path, rendered).context("write output config")?;
            } else {
                println!("{rendered}");
            }
            Ok(())
        }
        Command::Validate { file, env, schema } => {
            let config = load_config(&file, env, &[]).await?;
            let schema = read_schema(schema)?;
            let payload = flatten_config_for_schema(&flatten_config_to_value(&config));
            schema.validate(&payload)?;
            println!("valid");
            Ok(())
        }
        Command::Encrypt {
            input,
            output,
            passphrase,
            aad,
        } => {
            let raw = std::fs::read_to_string(&input).context("read plaintext input")?;
            let payload: Value = serde_json::from_str(&raw).unwrap_or(Value::String(raw));
            let envelope = encrypt(passphrase.as_bytes(), &payload, aad.as_bytes())
                .context("encrypt payload")?;
            let bytes = envelope.encode();
            std::fs::write(&output, bytes).context("write encrypted payload")?;
            Ok(())
        }
        Command::Decrypt {
            input,
            output,
            passphrase,
        } => {
            let payload: Value = decrypt_from_file::<Value>(&input, passphrase.as_bytes())
                .context("decrypt payload")?;
            let rendered = serde_json::to_string(&payload)?;
            if let Some(path) = output {
                std::fs::write(path, rendered).context("write decrypted payload")?;
            } else {
                println!("{rendered}");
            }
            Ok(())
        }
        Command::Watch {
            file,
            passphrase,
            once,
        } => {
            let (watcher, current) =
                HotReloader::<Value>::open(&file, passphrase.as_bytes()).context("start watch")?;
            let rendered = serde_json::to_string_pretty(&current)?;
            println!("{rendered}");
            if once {
                return Ok(());
            }

            let mut rx = watcher.subscribe();
            loop {
                match rx.recv().await {
                    Ok(event) => {
                        let rendered = serde_json::to_string_pretty(&event.config)?;
                        println!("{rendered}");
                    }
                    Err(broadcast::error::RecvError::Closed) => break,
                    Err(broadcast::error::RecvError::Lagged(_)) => continue,
                }
            }
            Ok(())
        }
        Command::Layers { file, env } => {
            let stack = build_layer_stack(&file, env).await?;
            for (index, layer) in stack.layers().iter().enumerate() {
                println!(
                    "{}: name={} priority={:?} source={}",
                    index + 1,
                    layer.name,
                    layer.priority,
                    layer_source(layer),
                );
                println!("   keys: {}", config_key_count(&layer.config));
            }
            Ok(())
        }
    };

    match result {
        Ok(()) => Ok(()),
        Err(err) => {
            eprintln!("{err}");
            Err(err)
        }
    }
}

async fn load_config(
    paths: &[PathBuf],
    include_env: bool,
    cli_args: &[(&str, &str)],
) -> Result<Config> {
    let mut builder = ConfigBuilder::new();

    for (index, path) in paths.iter().enumerate() {
        let priority = priority_for_file(index);
        builder = builder
            .with_source(FileSource::new(path.to_string_lossy()), priority)
            .await?;
    }

    if include_env {
        builder = builder.with_env();
    }

    let mut cli_source = CliSource::new();
    for (key, value) in cli_args {
        cli_source = cli_source.with_arg(*key, *value);
    }
    builder = builder.with_source(cli_source, LayerPriority::Cli).await?;

    Ok(builder.build()?)
}

fn read_schema(path: PathBuf) -> Result<ConfigSchema> {
    let raw = std::fs::read_to_string(path).context("read schema file")?;
    let spec: CliSchemaFile = serde_json::from_str(&raw).context("parse schema file")?;
    let mut schema = ConfigSchema::new();
    for field in spec.fields {
        schema = schema.field(field.name, field.required, field.type_hint);
    }
    Ok(schema)
}

fn parse_value(raw: &str) -> ConfigValue {
    serde_json::from_str::<Value>(raw)
        .map(json_to_config_value)
        .unwrap_or_else(|_| ConfigValue::from(raw.to_string()))
}

fn json_to_config_value(value: Value) -> ConfigValue {
    match value {
        Value::Null => ConfigValue::Null,
        Value::Bool(value) => ConfigValue::Bool(value),
        Value::Number(value) => ConfigValue::Number(value.as_f64().unwrap_or(0.0)),
        Value::String(value) => ConfigValue::String(value),
        Value::Array(items) => {
            ConfigValue::Array(items.into_iter().map(json_to_config_value).collect())
        }
        Value::Object(map) => ConfigValue::Object(
            map.into_iter()
                .map(|(key, value)| (key, json_to_config_value(value)))
                .collect(),
        ),
    }
}

fn config_value_to_json(value: &ConfigValue) -> Value {
    match value {
        ConfigValue::Null => Value::Null,
        ConfigValue::Bool(value) => Value::Bool(*value),
        ConfigValue::Number(value) => Value::Number(
            serde_json::Number::from_f64(*value).unwrap_or_else(|| serde_json::Number::from(0)),
        ),
        ConfigValue::String(value) => Value::String(value.clone()),
        ConfigValue::Array(values) => {
            Value::Array(values.iter().map(config_value_to_json).collect())
        }
        ConfigValue::Object(values) => {
            let mut map = Map::new();
            for (key, value) in values {
                map.insert(key.clone(), config_value_to_json(value));
            }
            Value::Object(map)
        }
    }
}

fn flatten_config_to_value(config: &Config) -> Value {
    let mut root = Value::Object(Map::new());
    for key in config.keys() {
        if let Some(value) = config.get(key) {
            insert_path(&mut root, key, config_value_to_json(value));
        }
    }
    root
}

fn flatten_for_schema(value: &Value) -> Value {
    if let Value::Object(root) = value {
        let mut out = Map::new();
        for (key, nested) in root {
            flatten_for_schema_recursive(&key.to_string(), nested, &mut out);
        }
        Value::Object(out)
    } else {
        value.clone()
    }
}

fn flatten_for_schema_recursive(prefix: &str, value: &Value, out: &mut Map<String, Value>) {
    if let Value::Object(map) = value {
        out.insert(prefix.to_string(), value.clone());
        for (key, nested) in map {
            let child = format!("{prefix}.{key}");
            flatten_for_schema_recursive(&child, nested, out);
        }
        return;
    }

    out.insert(prefix.to_string(), value.clone());
}

fn flatten_config_for_schema(value: &Value) -> Value {
    flatten_for_schema(value)
}

fn insert_path(target: &mut Value, path: &str, value: Value) {
    let mut current = target.as_object_mut().expect("target must be json object");
    let mut segments = path.split('.').peekable();
    while let Some(segment) = segments.next() {
        if segments.peek().is_none() {
            current.insert(segment.to_string(), value);
            return;
        }

        let next = current
            .entry(segment.to_string())
            .or_insert_with(|| Value::Object(Map::new()));
        if !next.is_object() {
            *next = Value::Object(Map::new());
        }
        current = next.as_object_mut().expect("nested path must be object");
    }
}

async fn build_layer_stack(paths: &[PathBuf], include_env: bool) -> Result<LayerStack> {
    let mut stack = LayerStack::new();

    for (index, path) in paths.iter().enumerate() {
        let priority = priority_for_file(index);
        let config = FileSource::new(path.to_string_lossy().to_string())
            .load()
            .await
            .with_context(|| format!("load config file {}", path.display()))?;
        stack.add(path.to_string_lossy().to_string(), priority, config);
    }

    if include_env {
        let env = EnvSource::new()
            .load()
            .await
            .context("load environment layer")?;
        stack.add("env", LayerPriority::EnvVars, env);
    }

    stack.add(
        "cli",
        LayerPriority::Cli,
        CliSource::new()
            .load()
            .await
            .context("build empty cli layer")?,
    );

    Ok(stack)
}

fn layer_source(layer: &Layer) -> String {
    match layer.name.as_str() {
        "env" => "environment".to_string(),
        "cli" => "cli".to_string(),
        _ => "file".to_string(),
    }
}

fn config_key_count(config: &Config) -> usize {
    config.keys().count()
}

fn priority_for_file(index: usize) -> LayerPriority {
    match index % 5 {
        0 => LayerPriority::Default,
        1 => LayerPriority::Env,
        2 => LayerPriority::Home,
        3 => LayerPriority::Local,
        _ => LayerPriority::EnvVars,
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;

    // --- default_type_hint ---

    #[test]
    fn default_type_hint_returns_string() {
        assert_eq!(default_type_hint(), "string");
    }

    // --- layer_source ---

    #[test]
    fn layer_source_env_name() {
        let layer = Layer::new("env", LayerPriority::EnvVars, Config::default());
        assert_eq!(layer_source(&layer), "environment");
    }

    #[test]
    fn layer_source_cli_name() {
        let layer = Layer::new("cli", LayerPriority::Cli, Config::default());
        assert_eq!(layer_source(&layer), "cli");
    }

    #[test]
    fn layer_source_file_name() {
        let layer = Layer::new("app.json", LayerPriority::Local, Config::default());
        assert_eq!(layer_source(&layer), "file");
    }

    // --- priority_for_file ---

    #[test]
    fn priority_for_file_cycles_over_five_priorities() {
        assert!(matches!(priority_for_file(0), LayerPriority::Default));
        assert!(matches!(priority_for_file(1), LayerPriority::Env));
        assert!(matches!(priority_for_file(2), LayerPriority::Home));
        assert!(matches!(priority_for_file(3), LayerPriority::Local));
        assert!(matches!(priority_for_file(4), LayerPriority::EnvVars));
        // cycles
        assert!(matches!(priority_for_file(5), LayerPriority::Default));
    }

    // --- parse_value ---

    #[test]
    fn parse_value_boolean_true() {
        assert!(matches!(parse_value("true"), ConfigValue::Bool(true)));
    }

    #[test]
    fn parse_value_boolean_false() {
        assert!(matches!(parse_value("false"), ConfigValue::Bool(false)));
    }

    #[test]
    fn parse_value_integer() {
        assert!(
            matches!(parse_value("42"), ConfigValue::Number(n) if (n - 42.0).abs() < f64::EPSILON)
        );
    }

    #[test]
    #[allow(clippy::approx_constant)]
    fn parse_value_float() {
        assert!(matches!(parse_value("3.14"), ConfigValue::Number(n) if (n - 3.14).abs() < 1e-9));
    }

    #[test]
    fn parse_value_string_fallback() {
        assert!(matches!(parse_value("hello"), ConfigValue::String(ref s) if s == "hello"));
    }

    #[test]
    fn parse_value_json_object() {
        let v = parse_value(r#"{"a":1}"#);
        assert!(matches!(v, ConfigValue::Object(_)));
    }

    // --- insert_path ---

    #[test]
    fn insert_path_flat_key() {
        let mut root = json!({});
        insert_path(&mut root, "key", json!("val"));
        assert_eq!(root["key"], json!("val"));
    }

    #[test]
    fn insert_path_nested_key() {
        let mut root = json!({});
        insert_path(&mut root, "a.b.c", json!(99));
        assert_eq!(root["a"]["b"]["c"], json!(99));
    }

    #[test]
    fn insert_path_overwrites_existing() {
        let mut root = json!({"x": "old"});
        insert_path(&mut root, "x", json!("new"));
        assert_eq!(root["x"], json!("new"));
    }
}
