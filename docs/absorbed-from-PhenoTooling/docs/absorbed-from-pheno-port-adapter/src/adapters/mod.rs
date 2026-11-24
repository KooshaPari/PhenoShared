//! Concrete [`PortAdapter`] implementations for the most common transports.
//!
//! Two adapters are shipped in-tree for the connection-shaped ports:
//!
//! - [`tcp::TcpAdapter`] — connects to a `host:port` endpoint via
//!   [`std::net::TcpStream`].
//! - [`unix::UnixAdapter`] — connects to a filesystem path endpoint via
//!   [`std::os::unix::net::UnixStream`] (Unix-only; the module is gated on
//!   `cfg(unix)` and compiles to an empty module on other targets so the crate
//!   stays buildable on every platform).
//!
//! Both adapters follow the same pattern: the active stream is held in an
//! interior `Mutex<Option<…>>` so the synchronous [`PortAdapter`] methods
//! (which take `&self`, not `&mut self`) can mutate the connection state
//! safely. The [`Connection`] handle returned to callers only carries the
//! endpoint string as an opaque id; the concrete stream lives inside the
//! adapter and is dropped on [`PortAdapter::disconnect`].
//!
//! Time-port adapters (v12-06) live alongside the connection adapters:
//!
//! - [`system_clock::SystemClock`] — production adapter for
//!   [`crate::ports::HexTimePort`]; reads `Instant::now()` and
//!   `SystemTime::now()`.
//! - [`mock_clock::MockClock`] — frozen test double for
//!   [`crate::ports::HexTimePort`]; wall-clock nanos and monotonic instant
//!   are decoupled so tests can assert time-based invariants without
//!   sleeping.

pub mod tcp;

#[cfg(unix)]
pub mod unix;

pub mod mock_clock;
pub mod system_clock;
