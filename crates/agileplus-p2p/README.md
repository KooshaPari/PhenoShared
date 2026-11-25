# agileplus-p2p

![MSRV](https://img.shields.io/badge/MSRV-1.86-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

Peer-to-peer sync via Tailscale and NATS. This crate covers peer discovery, persistent device identity, event replication, and vector-clock synchronization.

## Public API Index

- `device::{DeviceNode, DeviceStore, InMemoryDeviceStore, get_local_device, register_device}` - device identity and registration.
- `discovery::{PeerInfo, PeerStatus}` - peer metadata and liveness state.
- `discovery::discover_peers` - Unix-only Tailscale local API peer discovery.
- `error::{ConnectionError, PeerDiscoveryError, SyncError}` - P2P connection, discovery, and sync errors.
- `replication::{EventBatch, ReplicationResult, replicate_events}` - NATS event replication.
- `vector_clock::{SyncResult, SyncVector, sync_with_peer}` - vector-clock synchronization.

## Build

```bash
cargo build -p agileplus-p2p
```

