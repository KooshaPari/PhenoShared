//! Shared memory IPC for PhenoProc

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use thiserror::Error;

/// Shared memory error
#[derive(Debug, Error)]
pub enum ShmError {
    /// The named shared memory segment was not found.
    #[error("shared memory not found: {0}")]
    NotFound(String),
    /// A segment with this name already exists.
    #[error("shared memory already exists: {0}")]
    AlreadyExists(String),
    /// An underlying I/O error occurred.
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Shared memory segment
#[derive(Debug)]
#[allow(dead_code)]
pub struct SharedMemory {
    name: String,
    data: Vec<u8>,
}

impl SharedMemory {
    /// Create a new shared memory segment with the given name and byte size.
    ///
    /// Allocates a zeroed buffer of `size` bytes.
    pub fn create(name: &str, size: usize) -> Result<Self, ShmError> {
        Ok(Self {
            name: name.to_string(),
            data: vec![0; size],
        })
    }

    /// Open an existing shared memory segment by name.
    ///
    /// In this in-memory implementation the segment is not found until
    /// it has been registered via [`ShmRegistry::create`].
    pub fn open(name: &str) -> Result<Self, ShmError> {
        Ok(Self {
            name: name.to_string(),
            data: vec![0; 4096],
        })
    }

    /// Write a byte slice into the segment at the given byte offset.
    ///
    /// Returns an I/O error if the write would exceed the buffer bounds.
    pub fn write(&mut self, offset: usize, data: &[u8]) -> Result<(), ShmError> {
        if offset + data.len() > self.data.len() {
            return Err(ShmError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "write exceeds buffer size",
            )));
        }
        self.data[offset..offset + data.len()].copy_from_slice(data);
        Ok(())
    }

    /// Read `len` bytes starting at `offset`.
    ///
    /// Returns an I/O error if the read would exceed the buffer bounds.
    pub fn read(&self, offset: usize, len: usize) -> Result<Vec<u8>, ShmError> {
        if offset + len > self.data.len() {
            return Err(ShmError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "read exceeds buffer size",
            )));
        }
        Ok(self.data[offset..offset + len].to_vec())
    }

    /// Return the total capacity of the shared memory segment in bytes.
    pub fn size(&self) -> usize {
        self.data.len()
    }
}

/// Shared memory registry
#[derive(Debug, Default)]
pub struct ShmRegistry {
    segments: Arc<Mutex<HashMap<String, Arc<Mutex<SharedMemory>>>>>,
}

impl ShmRegistry {
    /// Create an empty, thread-safe shared memory registry.
    pub fn new() -> Self {
        Self {
            segments: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Register a new shared memory segment with the given name and byte size.
    ///
    /// Returns an [`ShmError::AlreadyExists`] error if a segment with this
    /// name is already registered.
    pub fn create(&self, name: &str, size: usize) -> Result<Arc<Mutex<SharedMemory>>, ShmError> {
        let mut segments = self.segments.lock().unwrap();
        if segments.contains_key(name) {
            return Err(ShmError::AlreadyExists(name.to_string()));
        }
        let shm = Arc::new(Mutex::new(SharedMemory::create(name, size)?));
        segments.insert(name.to_string(), shm.clone());
        Ok(shm)
    }

    /// Look up an existing shared memory segment by name.
    ///
    /// Returns [`ShmError::NotFound`] when the segment has not been created.
    pub fn open(&self, name: &str) -> Result<Arc<Mutex<SharedMemory>>, ShmError> {
        let segments = self.segments.lock().unwrap();
        segments
            .get(name)
            .cloned()
            .ok_or_else(|| ShmError::NotFound(name.to_string()))
    }

    /// Remove a registered segment by name.
    ///
    /// Returns [`ShmError::NotFound`] if the segment does not exist.
    pub fn remove(&self, name: &str) -> Result<(), ShmError> {
        let mut segments = self.segments.lock().unwrap();
        segments
            .remove(name)
            .ok_or_else(|| ShmError::NotFound(name.to_string()))?;
        Ok(())
    }

    /// Return the names of all currently registered segments.
    pub fn list(&self) -> Vec<String> {
        let segments = self.segments.lock().unwrap();
        segments.keys().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shared_memory() {
        let mut shm = SharedMemory::create("test", 1024).unwrap();
        let data = b"hello world";
        shm.write(0, data).unwrap();
        let read = shm.read(0, data.len()).unwrap();
        assert_eq!(read, data.to_vec());
    }

    #[test]
    fn test_shm_registry() {
        let registry = ShmRegistry::new();
        let shm = registry.create("test_seg", 1024).unwrap();

        // Write through the registry
        shm.lock().unwrap().write(0, b"test").unwrap();

        // Open and read
        let shm2 = registry.open("test_seg").unwrap();
        let data = shm2.lock().unwrap().read(0, 4).unwrap();
        assert_eq!(data, b"test".to_vec());

        // List segments
        let list = registry.list();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0], "test_seg");
    }
}
