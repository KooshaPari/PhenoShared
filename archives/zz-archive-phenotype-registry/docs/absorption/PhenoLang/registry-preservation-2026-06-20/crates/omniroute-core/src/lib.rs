//! # OmniRoute Core
//!
//! The core Rust engine for OmniRoute - an intelligent routing layer for LLM requests.
//!
//! ## Features
//!
//! - **Multi-Provider Support**: Route requests to OpenAI, Anthropic, local models, and more
//! - **Streaming**: Full support for streaming responses
//! - **Provider Abstraction**: Clean trait-based architecture for adding new providers
//! - **Middleware Stack**: Tower-based middleware for logging, rate limiting, and more
//!
//! ## Architecture
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                      OmniRoute Core                         │
//! ├─────────────────────────────────────────────────────────────┤
//! │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
//! │  │   Router    │  │ Middleware  │  │  Provider Registry  │  │
//! │  │             │  │   Stack     │  │                     │  │
//! │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
//! │         │                │                      │            │
//! │         └────────────────┴──────────────────────┘            │
//! │                          │                                     │
//! │         ┌────────────────┴────────────────┐                   │
//! │         │                                 │                   │
//! │  ┌──────▼──────┐  ┌──────────┐  ┌───────▼───────┐             │
//! │  │   OpenAI    │  │ Anthropic│  │    Custom     │             │
//! │  │  Provider   │  │ Provider │  │   Providers   │             │
//! │  └─────────────┘  └──────────┘  └───────────────┘             │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## Example
//!
//! ```rust,no_run
//! use omniroute_core::{Router, ChatRequest, Message};
//! use omniroute_core::providers::LLMProvider;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let router = Router::new();
//! let request = ChatRequest {
//!     model: "gpt-4".to_string(),
//!     messages: vec![Message::user("Hello!")],
//!     stream: false,
//!     temperature: None,
//!     max_tokens: None,
//!     top_p: None,
//!     frequency_penalty: None,
//!     presence_penalty: None,
//!     stop: None,
//!     tools: None,
//!     tool_choice: None,
//!     response_format: None,
//!     seed: None,
//!     user: None,
//! };
//! // Route and process the request
//! # Ok(())
//! # }
//! ```

pub mod error;
pub mod http;
pub mod observability;
pub mod providers;
pub mod router;
pub mod types;

pub use error::{Error, Result};
pub use http::{start, AppState, ServerConfig, ServerState};
pub use router::Router;
pub use types::*;
