//! PhenoTerminal - Terminal utilities for the Pheno ecosystem
//!
//! Migrated from zz-rich-cli-kit/klipdot (disposition #108).
//! Provides terminal interception, clipboard handling, image processing,
//! shell hooks, and service management for CLI/TUI applications.

pub mod clipboard;
pub mod config;
pub mod error;
pub mod image_preview;
pub mod image_processor;
pub mod installer;
pub mod interceptor;
pub mod service;
pub mod shell_hooks;
pub mod stdout_monitor;

pub use error::{Error, Result};
