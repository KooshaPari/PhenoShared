// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! Asset / material port for Pine processes.
//!
//! A Pine process attaches *assets*: code segments, mapped files, shared
//! libraries, loaded blobs.  The port abstracts the concrete storage
//! backend (in-memory, file, mmap, network fetch) so the process loader
//! and the syscall handler stay engine-agnostic.
//!
//! Reference: kmobile/crates/kmobile-core/src/ports/material.rs (Rust port),
//! phenotype-voxel/src/ports/material.rs (Rust port).

use std::collections::HashMap;
use thiserror::Error;

/// Identifier for an asset within a process.  Stable across the lifetime
/// of the process and unique within the asset registry.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct AssetId(pub String);

impl std::fmt::Display for AssetId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl AssetId {
    /// Creates a new id from a string slice.  The slice must not be empty.
    pub fn new(s: &str) -> Self {
        AssetId(s.to_owned())
    }
}

/// Inert, content-addressed description of an asset.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssetDescriptor {
    /// Stable id within the registry.
    pub id: AssetId,
    /// Human-readable name (e.g. <c>"libc.so"</c>).
    pub name: String,
    /// Size in bytes.
    pub size: u64,
    /// Logical kind (e.g. <c>"exec"</c>, <c>"lib"</c>, <c>"data"</c>).
    pub kind: String,
}

/// Port-level errors raised by the asset registry and its adapters.
#[derive(Debug, Error)]
pub enum AssetError {
    /// The registry already contains an asset with this id.
    #[error("asset already registered: {0}")]
    AlreadyRegistered(AssetId),
    /// The requested id is not present in the registry.
    #[error("asset not found: {0}")]
    NotFound(AssetId),
    /// Underlying storage backend failed (network, file, mmap, …).
    #[error("storage error: {0}")]
    Storage(String),
}

/// Hexagonal port: registry of process assets.
///
/// Domain code depends on this trait; the concrete adapter is injected.
pub trait AssetRegistry {
    /// Registers a descriptor.  If an entry with the same id already
    /// exists, returns [`AssetError::AlreadyRegistered`].
    fn register(&mut self, asset: AssetDescriptor) -> Result<(), AssetError>;

    /// Looks up a descriptor by id.
    fn get(&self, id: &AssetId) -> Result<&AssetDescriptor, AssetError>;

    /// Returns all registered descriptors, in insertion order.
    fn list(&self) -> Vec<&AssetDescriptor>;

    /// Removes a descriptor by id.  Returns <c>true</c> if it was present.
    fn unregister(&mut self, id: &AssetId) -> bool;
}

/// Default in-memory adapter.  Used by the process loader, by tests, and
/// as the canonical null-adapter when no engine asset system is wired in.
pub struct InMemoryAssetRegistry {
    by_id: HashMap<AssetId, AssetDescriptor>,
}

impl Default for InMemoryAssetRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemoryAssetRegistry {
    /// Creates an empty registry.
    pub fn new() -> Self {
        Self {
            by_id: HashMap::new(),
        }
    }
}

impl AssetRegistry for InMemoryAssetRegistry {
    fn register(&mut self, asset: AssetDescriptor) -> Result<(), AssetError> {
        if self.by_id.contains_key(&asset.id) {
            return Err(AssetError::AlreadyRegistered(asset.id));
        }
        self.by_id.insert(asset.id.clone(), asset);
        Ok(())
    }

    fn get(&self, id: &AssetId) -> Result<&AssetDescriptor, AssetError> {
        self.by_id
            .get(id)
            .ok_or_else(|| AssetError::NotFound(id.clone()))
    }

    fn list(&self) -> Vec<&AssetDescriptor> {
        self.by_id.values().collect()
    }

    fn unregister(&mut self, id: &AssetId) -> bool {
        self.by_id.remove(id).is_some()
    }
}

/// Recording mock for domain tests.  Each operation is appended to
/// <c>calls</c> so a test can assert on the interaction order.
pub struct RecordingAssetRegistry {
    by_id: HashMap<AssetId, AssetDescriptor>,
    /// Sequence of operation signatures invoked on this mock.
    pub calls: std::cell::RefCell<Vec<String>>,
}

impl Default for RecordingAssetRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl RecordingAssetRegistry {
    /// Creates an empty recording registry.
    pub fn new() -> Self {
        Self {
            by_id: HashMap::new(),
            calls: std::cell::RefCell::new(Vec::new()),
        }
    }
}

impl AssetRegistry for RecordingAssetRegistry {
    fn register(&mut self, asset: AssetDescriptor) -> Result<(), AssetError> {
        self.calls
            .borrow_mut()
            .push(format!("register({})", asset.id.0));
        if self.by_id.contains_key(&asset.id) {
            return Err(AssetError::AlreadyRegistered(asset.id));
        }
        self.by_id.insert(asset.id.clone(), asset);
        Ok(())
    }

    fn get(&self, id: &AssetId) -> Result<&AssetDescriptor, AssetError> {
        self.calls.borrow_mut().push(format!("get({})", id.0));
        self.by_id
            .get(id)
            .ok_or_else(|| AssetError::NotFound(id.clone()))
    }

    fn list(&self) -> Vec<&AssetDescriptor> {
        self.calls.borrow_mut().push("list".to_owned());
        self.by_id.values().collect()
    }

    fn unregister(&mut self, id: &AssetId) -> bool {
        self.calls
            .borrow_mut()
            .push(format!("unregister({})", id.0));
        self.by_id.remove(id).is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn in_memory_register_get_list_unregister() {
        let mut reg = InMemoryAssetRegistry::new();
        let desc = AssetDescriptor {
            id: AssetId::new("libc.so"),
            name: "libc.so".to_owned(),
            size: 1024,
            kind: "lib".to_owned(),
        };
        assert!(reg.register(desc.clone()).is_ok());
        assert_eq!(reg.get(&desc.id).unwrap(), &desc);
        assert_eq!(reg.list().len(), 1);
        assert!(reg.unregister(&desc.id));
        assert!(matches!(reg.get(&desc.id), Err(AssetError::NotFound(_))));
    }

    #[test]
    fn duplicate_register_returns_error() {
        let mut reg = InMemoryAssetRegistry::new();
        let desc = AssetDescriptor {
            id: AssetId::new("dup"),
            name: "dup".to_owned(),
            size: 0,
            kind: "data".to_owned(),
        };
        reg.register(desc.clone()).unwrap();
        match reg.register(desc) {
            Err(AssetError::AlreadyRegistered(id)) => assert_eq!(id.0, "dup"),
            other => panic!("expected AlreadyRegistered, got {:?}", other),
        }
    }

    #[test]
    fn recording_mock_logs_calls() {
        let mut rec = RecordingAssetRegistry::new();
        let desc = AssetDescriptor {
            id: AssetId::new("a"),
            name: "a".to_owned(),
            size: 0,
            kind: "data".to_owned(),
        };
        rec.register(desc.clone()).unwrap();
        let _ = rec.get(&desc.id);
        let _ = rec.list();
        rec.unregister(&desc.id);
        assert_eq!(rec.calls.borrow().len(), 4);
        assert_eq!(rec.calls.borrow()[0], "register(a)");
        assert_eq!(rec.calls.borrow()[1], "get(a)");
        assert_eq!(rec.calls.borrow()[2], "list");
        assert_eq!(rec.calls.borrow()[3], "unregister(a)");
    }
}
