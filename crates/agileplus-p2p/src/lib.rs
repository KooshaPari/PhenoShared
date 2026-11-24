//! agileplus-p2p — Peer-to-peer sync via Tailscale and NATS.
//!
//! Provides:
//! - Peer discovery via the Tailscale local API UNIX socket (`discovery`)
//! - Persistent device identity (`device`)
//! - Event replication over NATS JetStream (`replication`)
//! - Vector-clock-based synchronisation (`vector_clock`)
//!
//! Traceability: WP16 / T095-T099

pub mod device;
pub mod discovery;
pub mod error;
pub mod replication;
pub mod vector_clock;

pub use device::{get_local_device, register_device, DeviceNode, DeviceStore, InMemoryDeviceStore};
#[cfg(unix)]
pub use discovery::{discover_peers, PeerInfo, PeerStatus};
#[cfg(not(unix))]
pub use discovery::{PeerInfo, PeerStatus};
pub use error::{ConnectionError, PeerDiscoveryError, SyncError};
pub use replication::{replicate_events, EventBatch, ReplicationResult};
pub use vector_clock::{sync_with_peer, SyncResult, SyncVector};
