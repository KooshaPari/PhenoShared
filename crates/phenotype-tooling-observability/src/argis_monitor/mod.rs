//! argis-monitor: Observable Integration substrate for bifrost-extensions.
//!
//! Implements Tenet 4 of the bifrost-extensions charter: "Extension behavior
//! is fully observable. Metrics, logs, and traces flow through the same
//! pipeline as core components."
//!
//! Architecture:
//!
//! ```text
//!   Bifrost gateway
//!        |  HTTP /health, /v1/chat/completions
//!        v
//!   argis-monitor poller  --(every poll_interval)-->  Bifrost gateway
//!        |
//!        v
//!   SLO burn-rate calculator  (slo.rs)
//!        |
//!        v
//!   Prometheus exposition  -->  /metrics on :9090  (axum)
//! ```
//!
//! Absorbed from `zz-argis-extensions` branch
//! `wip/argis-monitor-metaalerts-20260806` (9,310 Rust lines, 41 files).
//!
//! ## Module inventory
//!
//! | Module | Purpose |
//! |--------|---------|
//! | `alerts` | Alert rules + evaluator (firing, resolution, cooldown) |
//! | `auth` | Bearer token cache for protected gateways |
//! | `aws_sigv4` | AWS SigV4 request signing (SNS / EventBridge targets) |
//! | `config` | YAML/TOML configuration types |
//! | `dashboard` | Grafana dashboard JSON loader + validation |
//! | `exporter` | Prometheus `ExporterHandle` (scrape-side) |
//! | `metrics` | Prometheus metric families with typed label sets |
//! | `poller` | Async HTTP poll loop per target with SLO tracking |
//! | `push` | Prometheus Pushgateway exporter (push-side) |
//! | `ring_buffer` | Sliding-window ring buffer for SLO samples |
//! | `slo` | Multi-window burn-rate computation |
//! | `state_store` | SQLite-backed persistent alert state |
//! | `suppression` | Alert suppression windows (recurring + one-shot) |
//! | `target` | Per-target polling configuration |
//! | `webhook` | Webhook delivery for alert payloads |

pub mod alerts;
pub mod auth;
pub mod aws_sigv4;
pub mod config;
pub mod dashboard;
pub mod exporter;
pub mod metrics;
pub mod poller;
pub mod push;
pub mod ring_buffer;
pub mod slo;
pub mod state_store;
pub mod suppression;
pub mod target;
pub mod webhook;

pub use alerts::{AlertPayload, AlertRule, AlertState, AlertStateTracker, Decision, MetaAlertRule, Severity, WebhookTarget};
pub use dashboard::{load_and_summarize, DashboardSummary};
pub use push::{push_to, run_pusher, PushError};
pub use state_store::{AlertHistoryRow, StateStore, TrackerSnapshot, StateStoreError};
pub use suppression::{is_suppressed, Day, WindowSpec};
pub use auth::BearerTokenCache;
pub use aws_sigv4::{sign_request_headers, SignError};
pub use config::{Config, SLO};
pub use ring_buffer::{Bucket, RingBuffer};
pub use target::Target;
pub use webhook::{deliver_all, DeliveryReport};
pub use metrics::{Outcome, Sample};
pub use poller::{Monitor, PollError, PollOutcome};
pub use slo::{burn_rate, BurnWindow};

/// Re-export of the crate version (matches `Cargo.toml`).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
