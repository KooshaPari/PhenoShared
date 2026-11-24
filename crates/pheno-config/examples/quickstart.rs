//! Quickstart example for pheno-config.
//!
//! Demonstrates the 12-factor config cascade: defaults → TOML file → env vars.
//!
//! Run with:
//!   cargo run --example quickstart
//!
//! Override with env (e.g.):
//!   PHENO_CONFIG_PORT=9090 PHENO_CONFIG_URL=https://override PHENO_CONFIG_DB_PATH=/tmp/x.db \
//!     cargo run --example quickstart
//!
//! Create a config.toml in the same directory:
//!   url = "https://localhost"
//!   port = 8080
//!   log_level = "info"
//!   db_path = "/var/lib/local.db"
//!   feature_flags = []

use pheno_config::{combine, ConfigBuilder};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Try TOML file first (if present).
    // 2. Then env vars via combine() — file is the source of truth for
    //    required fields, env overlays. This is the canonical
    //    12-factor cascade using the v0.2 public API.
    // 3. Fall back to a pure-builder config if no file is present.
    let toml_path = std::path::Path::new("config.toml");
    let config: pheno_config::Config = if toml_path.exists() {
        // combine() reads the TOML file and overlays env vars matching
        // the PHENO_CONFIG_* prefix.
        combine(toml_path, "PHENO_CONFIG")?
    } else {
        ConfigBuilder::new()
            .url("https://quickstart.example.com")
            .db_path("/var/lib/quickstart.db")
            .build()?
    };

    println!("Loaded config: {:#?}", config);
    println!("Port: {}", config.port);
    println!("URL: {}", config.url);
    println!("DB path: {}", config.db_path);

    Ok(())
}
