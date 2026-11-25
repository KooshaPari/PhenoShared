//! Shared UI components for the `sl-viewer` Dioxus app.
//!
//! Three tabs:
//! - **Bundles** — browse compiled continuation bundles
//! - **History** — session history timeline
//! - **Unfinished** — work that may need to be resumed
//! - **Memory** — wiki/docs view of distilled memories
//!
//! Compiled for both desktop (`dioxus-desktop`) and web (`dioxus-web`) via
//! Cargo feature flags.  The platform-specific entry points in `main.rs` call
//! [`App`] regardless of renderer.

pub mod app;
pub mod async_states;
pub mod bundle_diff;
pub mod bundle_list;
pub mod cli_help;
pub mod command_palette;
pub mod corpus_cta;
pub mod corpus_loader;
pub mod corpus_paths;
pub mod corpus_tab;
pub mod daemon_source;
pub mod daemon_url;
pub mod detail_pane;
pub mod fixture;
pub mod help_overlay;
pub mod history_tab;
pub mod live_feed;
pub mod memory_tab;
#[cfg(feature = "desktop")]
pub mod menu;
pub mod mock_data;
#[cfg(feature = "parquet")]
pub mod parquet_source;
pub mod replay_view;
pub mod search_view;
pub mod session_list;
pub mod session_transcript;
pub mod settings;
pub mod settings_tab;
pub mod theme;
pub mod timeline;
pub mod tokens;
pub mod unfinished_tab;
pub mod web_exports;

pub use app::App;
pub use async_states::{ContentSkeleton, ErrorState, LoadingState, SkeletonLayout};
pub use corpus_loader::{load_sessions, DataSource};
pub use session_list::SessionList;
pub use settings::{DefaultTab, Settings};
