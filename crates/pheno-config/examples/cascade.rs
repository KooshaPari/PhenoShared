//! Multi-source cascade example for pheno-config.
//!
//! Demonstrates the 5-layer 12-factor cascade using the public API:
//!   1. Hard-coded defaults (from `ConfigBuilder::new()`)
//!   2. `defaults.toml` shipped with the binary (TOML file)
//!   3. `/etc/myapp/config.toml` (system-wide; optional, ignored if absent)
//!   4. `./config.toml` (per-deployment; optional, ignored if absent)
//!   5. Environment variables (highest priority, overlaid via `merge`)
//!
//! Layers 2–4 cascade together: each present TOML file is loaded
//! and merged onto the previous layer; absent layers are silently
//! ignored (`IoError` is the only swallowed variant; parse errors
//! are still fatal). Layer 5 is applied last via `Config::merge`
//! over a partial env-loaded `Config`, which only overrides fields
//! the env actually sets.
//!
//! Run with:
//!   cargo run --example cascade
//!
//! Try overrides:
//!   PHENO_CONFIG_PORT=9090 cargo run --example cascade

use pheno_config::{load_from_toml_file, new_secret, Config, ConfigError};

/// Load layer 2/3/4 with cascade semantics: try each TOML path in
/// order, merging successive loads onto the previous config. Missing
/// files are ignored (treated as an absent layer). Returns the merged
/// `Config` or `None` if every layer was absent.
fn load_cascade(paths: &[&std::path::Path]) -> Result<Option<Config>, ConfigError> {
    let mut merged: Option<Config> = None;
    for path in paths {
        match load_from_toml_file(path) {
            Ok(cfg) => {
                merged = match merged {
                    None => Some(cfg),
                    Some(mut base) => {
                        base.merge(&cfg);
                        Some(base)
                    }
                };
            }
            Err(ConfigError::IoError(_)) => {
                // Layer absent — that's fine; the cascade treats
                // "file not found" as "no value from this layer".
                continue;
            }
            Err(e) => return Err(e),
        }
    }
    Ok(merged)
}

/// Load layer 5: env vars with prefix `PHENO_CONFIG`. Missing required
/// fields are tolerated (defaults to empty / 0 / []); the merge step
/// in `main` keeps file values where the env is silent.
fn load_env_partial() -> Result<Config, ConfigError> {
    // The public `load_from_env` requires URL and DB_PATH. To get a
    // partial (overlay-only) view we synthesize the same shape from
    // the public surface by attempting the full load and on error
    // constructing a stub. This mirrors what `combine` does
    // internally while tolerating missing required fields.
    pheno_config::load_from_env("PHENO_CONFIG").or_else(|_| {
        Ok(Config {
            url: std::env::var("PHENO_CONFIG_URL").unwrap_or_default(),
            port: std::env::var("PHENO_CONFIG_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(0),
            log_level: std::env::var("PHENO_CONFIG_LOG_LEVEL").unwrap_or_default(),
            db_path: std::env::var("PHENO_CONFIG_DB_PATH").unwrap_or_default(),
            feature_flags: std::env::var("PHENO_CONFIG_FEATURE_FLAGS")
                .unwrap_or_default()
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(str::to_owned)
                .collect(),
            secret_value: std::env::var("PHENO_CONFIG_SECRET_TOKEN")
                .ok()
                .filter(|value| !value.is_empty())
                .map(new_secret),
        })
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Layers 2/3/4: TOML cascade (defaults, system-wide, per-deployment).
    let layers = [
        std::path::Path::new("defaults.toml"),
        std::path::Path::new("/etc/myapp/config.toml"),
        std::path::Path::new("config.toml"),
    ];
    let file_cfg = load_cascade(&layers)?;

    // Layer 5: env vars (highest priority). Merged onto whatever
    // the file cascade produced, or used as the only source if no
    // file layer was present.
    let env_cfg = load_env_partial()?;
    let config: Config = match file_cfg {
        None => env_cfg,
        Some(mut base) => {
            base.merge(&env_cfg);
            base
        }
    };

    println!("Resolved config: {:#?}", config);

    // Show which layer won for each field.
    println!("\nField provenance:");
    println!("  port = {} (env overrides > file > default)", config.port);

    Ok(())
}
