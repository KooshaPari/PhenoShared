//! Phenotype configuration core library
//!
//! Defines the canonical `PhenoProcConfig` struct that consolidates all
//! configuration keys previously hardcoded across the PhenoProc workspace.
//! Each key has a documented default; values can be overridden via config
//! files (TOML/YAML/JSON) or environment variables (prefix `PHENOPROC_`).

pub use config::Config;
pub use phenoproc::PhenoProcConfig;

pub mod config;
pub mod phenoproc;
