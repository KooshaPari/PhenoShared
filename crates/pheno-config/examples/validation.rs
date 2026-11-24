//! Validation example for pheno-config.
//!
//! Shows how the crate surfaces structured errors when input is
//! invalid. `pheno_config::ConfigError` is a 3-variant enum
//! (`MissingField`, `ParseError`, `IoError`) and `ConfigBuilder::build`
//! produces `MissingField` for any unset required field (`URL`,
//! `DB_PATH`); the env-loader additionally produces `ParseError` for
//! malformed values (e.g. non-numeric `PORT`).
//!
//! Run with:
//!   cargo run --example validation

use pheno_config::{load_from_env, ConfigBuilder, ConfigError};

/// A tiny inline validator mirroring the spirit of the planned v0.3
/// `Validate` trait (ADR-038 follow-up): it consumes a built `Config`
/// and applies domain-specific rules. Until the trait lands,
/// consumers either inline this or copy it into their own crate.
fn validate(cfg: &pheno_config::Config) -> Result<(), ConfigError> {
    if cfg.port < 1024 {
        return Err(ConfigError::ParseError {
            field: "PORT".to_owned(),
            message: format!("port must be >= 1024 (non-privileged), got {}", cfg.port),
        });
    }
    if cfg.log_level.is_empty() {
        return Err(ConfigError::MissingField("LOG_LEVEL".to_owned()));
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // --- Case 1: a hand-built Config that passes validation.
    let good = ConfigBuilder::new()
        .url("https://good.example.com")
        .db_path("/var/lib/good.db")
        .port(8080)
        .log_level("info")
        .build()?;
    validate(&good)?;
    println!("✓ Good config: {:#?}", good);

    // --- Case 2: a hand-built Config that fails validation.
    let bad = ConfigBuilder::new()
        .url("https://bad.example.com")
        .db_path("/var/lib/bad.db")
        .port(80) // < 1024 → Validate rejects
        .log_level("info")
        .build()?;
    match validate(&bad) {
        Err(ConfigError::ParseError { field, message }) => {
            eprintln!("✗ Validation failed on {}: {}", field, message);
        }
        other => panic!("expected ParseError, got {other:?}"),
    }

    // --- Case 3: env-loading surface (with no env vars set,
    // MissingField surfaces). Demonstrates the structured-error
    // contract callers actually receive.
    std::env::remove_var("VALIDATION_DEMO_URL");
    std::env::remove_var("VALIDATION_DEMO_DB_PATH");
    match load_from_env("VALIDATION_DEMO") {
        Err(ConfigError::MissingField(field)) => {
            eprintln!("✗ Missing required env var: {}", field);
        }
        other => panic!("expected MissingField, got {other:?}"),
    }

    Ok(())
}
