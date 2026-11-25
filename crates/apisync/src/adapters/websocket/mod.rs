//! WebSocket adapter for real-time bidirectional communication.
//!
//! Provides a WebSocket server that handles real-time updates for the
//! `Item` domain model, together with connection management, message framing,
//! and broadcasting.

mod server;

pub use server::*;
