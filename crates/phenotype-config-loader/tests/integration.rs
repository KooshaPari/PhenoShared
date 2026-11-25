use phenotype_config_loader::*;
use std::io::Write;
use tempfile::NamedTempFile;

// ── Shared test config ──────────────────────────────────────────────────────

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
struct AppConfig {
    app_name: String,
    debug: bool,
    database: DatabaseConfig,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
struct DatabaseConfig {
    host: String,
    port: u16,
    pool_size: Option<u32>,
}

// ── ConfigFormat detection ──────────────────────────────────────────────────

#[test]
fn format_detection_toml() {
    assert_eq!(ConfigFormat::from_path("c.toml"), Some(ConfigFormat::Toml));
}

#[test]
fn format_detection_yaml() {
    assert_eq!(ConfigFormat::from_path("c.yaml"), Some(ConfigFormat::Yaml));
}

#[test]
fn format_detection_yml() {
    assert_eq!(ConfigFormat::from_path("c.yml"), Some(ConfigFormat::Yaml));
}

#[test]
fn format_detection_json() {
    assert_eq!(ConfigFormat::from_path("c.json"), Some(ConfigFormat::Json));
}

#[test]
fn format_detection_txt_returns_none() {
    assert_eq!(ConfigFormat::from_path("c.txt"), None);
}

#[test]
fn format_detection_unknown_returns_none() {
    assert_eq!(ConfigFormat::from_path("c.unknown"), None);
}

// ── parse_config complex nested ─────────────────────────────────────────────

#[test]
fn parse_complex_toml() {
    let toml_str = r#"
app_name = "agent"
debug = true

[database]
host = "localhost"
port = 5432
pool_size = 10
"#;
    let cfg: AppConfig = parse_config(toml_str, ConfigFormat::Toml).unwrap();
    assert_eq!(cfg.app_name, "agent");
    assert!(cfg.debug);
    assert_eq!(cfg.database.host, "localhost");
    assert_eq!(cfg.database.port, 5432);
    assert_eq!(cfg.database.pool_size, Some(10));
}

#[test]
fn parse_complex_json() {
    let json_str = r#"{
        "app_name": "agent",
        "debug": false,
        "database": { "host": "db.prod", "port": 3306, "pool_size": 25 }
    }"#;
    let cfg: AppConfig = parse_config(json_str, ConfigFormat::Json).unwrap();
    assert_eq!(cfg.app_name, "agent");
    assert!(!cfg.debug);
    assert_eq!(cfg.database.host, "db.prod");
    assert_eq!(cfg.database.port, 3306);
}

#[test]
fn parse_complex_yaml() {
    let yaml_str = r#"
app_name: agent
debug: true
database:
  host: 127.0.0.1
  port: 9999
  pool_size: 5
"#;
    let cfg: AppConfig = parse_config(yaml_str, ConfigFormat::Yaml).unwrap();
    assert_eq!(cfg.app_name, "agent");
    assert!(cfg.debug);
    assert_eq!(cfg.database.host, "127.0.0.1");
    assert_eq!(cfg.database.port, 9999);
}

// ── parse_config error handling ─────────────────────────────────────────────

#[test]
fn parse_invalid_toml() {
    let err = parse_config::<AppConfig>("[[[invalid", ConfigFormat::Toml);
    assert!(err.is_err());
    assert!(matches!(err.unwrap_err(), ConfigError::Toml(_)));
}

#[test]
fn parse_invalid_json() {
    let err = parse_config::<AppConfig>("{bad json}", ConfigFormat::Json);
    assert!(err.is_err());
    assert!(matches!(err.unwrap_err(), ConfigError::Json(_)));
}

#[test]
fn parse_invalid_yaml() {
    let err = parse_config::<AppConfig>(":\n  :\n    \t\tinvalid:", ConfigFormat::Yaml);
    assert!(err.is_err());
    assert!(matches!(err.unwrap_err(), ConfigError::Yaml(_)));
}

// ── load_from_file ──────────────────────────────────────────────────────────

#[test]
fn load_from_file_toml() {
    let mut f = NamedTempFile::with_suffix(".toml").unwrap();
    write!(
        f,
        r#"app_name = "from-file"
debug = true
[database]
host = "h"
port = 1
"#
    )
    .unwrap();
    let cfg: AppConfig = load_from_file(f.path()).unwrap();
    assert_eq!(cfg.app_name, "from-file");
}

#[test]
fn load_from_file_json() {
    let mut f = NamedTempFile::with_suffix(".json").unwrap();
    write!(
        f,
        r#"{{"app_name": "json-file", "debug": false, "database": {{"host": "j", "port": 2}}}}"#
    )
    .unwrap();
    let cfg: AppConfig = load_from_file(f.path()).unwrap();
    assert_eq!(cfg.app_name, "json-file");
}

#[test]
fn load_from_file_yaml() {
    let mut f = NamedTempFile::with_suffix(".yaml").unwrap();
    write!(
        f,
        "app_name: yaml-file\ndebug: true\ndatabase:\n  host: y\n  port: 3\n"
    )
    .unwrap();
    let cfg: AppConfig = load_from_file(f.path()).unwrap();
    assert_eq!(cfg.app_name, "yaml-file");
}

#[test]
fn load_from_file_nonexistent() {
    let err = load_from_file::<AppConfig, _>("/tmp/__nonexistent_config__.toml");
    assert!(err.is_err());
    assert!(matches!(err.unwrap_err(), ConfigError::Io(_)));
}

#[test]
fn load_from_file_unsupported_extension() {
    let mut f = NamedTempFile::new().unwrap();
    let path = f.path().with_extension("xyz");
    write!(f, "data").unwrap();
    // Rename to .xyz extension
    std::fs::rename(f.path(), &path).unwrap();
    let err = load_from_file::<AppConfig, _>(&path);
    assert!(err.is_err());
    assert!(matches!(
        err.unwrap_err(),
        ConfigError::UnsupportedFormat(_)
    ));
    // Cleanup
    let _ = std::fs::remove_file(&path);
}

// ── ConfigLoader builder ────────────────────────────────────────────────────

#[test]
fn config_loader_with_file() {
    let mut f = NamedTempFile::with_suffix(".toml").unwrap();
    write!(
        f,
        r#"app_name = "loader"
debug = true
[database]
host = "l"
port = 4
"#
    )
    .unwrap();
    let cfg: AppConfig = ConfigLoader::new()
        .with_file(f.path().to_str().unwrap())
        .load()
        .unwrap();
    assert_eq!(cfg.app_name, "loader");
}

#[test]
fn config_loader_no_source_error() {
    #[derive(Debug, serde::Deserialize)]
    struct Empty {}
    let err = ConfigLoader::<Empty>::new().load();
    assert!(err.is_err());
    assert!(matches!(err.unwrap_err(), ConfigError::NotFound(_)));
}

// ── merge_configs ───────────────────────────────────────────────────────────

#[test]
fn merge_two_json_sources() {
    let src1 = r#"{"app_name": "v1", "debug": false}"#.to_string();
    let src2 = r#"{"database": {"host": "merged", "port": 9999}}"#.to_string();
    let cfg: AppConfig =
        merge_configs(vec![(src1, ConfigFormat::Json), (src2, ConfigFormat::Json)]).unwrap();
    assert_eq!(cfg.app_name, "v1");
    assert_eq!(cfg.database.host, "merged");
    assert_eq!(cfg.database.port, 9999);
}

#[test]
fn merge_later_source_overrides() {
    let src1 =
        r#"{"app_name": "old", "debug": false, "database": {"host": "h", "port": 1}}"#.to_string();
    let src2 = r#"{"app_name": "new"}"#.to_string();
    let cfg: AppConfig =
        merge_configs(vec![(src1, ConfigFormat::Json), (src2, ConfigFormat::Json)]).unwrap();
    assert_eq!(cfg.app_name, "new");
}

// ── ConfigError display ─────────────────────────────────────────────────────

#[test]
fn config_error_display_all_variants() {
    let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "gone");
    let e = ConfigError::Io(io_err);
    assert!(e.to_string().contains("gone"));

    let e = ConfigError::Yaml("bad yaml".into());
    assert!(e.to_string().contains("bad yaml"));

    let e = ConfigError::UnsupportedFormat(".log".into());
    assert!(e.to_string().contains(".log"));

    let e = ConfigError::NotFound("missing".into());
    assert!(e.to_string().contains("missing"));
}

#[test]
fn config_error_toml_display() {
    let toml_err = toml::from_str::<AppConfig>("[[[bad").unwrap_err();
    let e = ConfigError::Toml(toml_err);
    assert!(!e.to_string().is_empty());
}

#[test]
fn config_error_json_display() {
    let json_err = serde_json::from_str::<AppConfig>("not json").unwrap_err();
    let e = ConfigError::Json(json_err);
    assert!(!e.to_string().is_empty());
}
