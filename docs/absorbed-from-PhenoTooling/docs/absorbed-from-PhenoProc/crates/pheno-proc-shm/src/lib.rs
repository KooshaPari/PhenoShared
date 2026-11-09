//! Shared memory IPC for PhenoProc

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use thiserror::Error;

/// Shared memory error
#[derive(Debug, Error)]
pub enum ShmError {
    #[error("shared memory not found: {0}")]
    NotFound(String),
    #[error("shared memory already exists: {0}")]
    AlreadyExists(String),
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
    pub fn create(name: &str, size: usize) -> Result<Self, ShmError> {
        Ok(Self {
            name: name.to_string(),
            data: vec![0; size],
        })
    }

    pub fn open(name: &str) -> Result<Self, ShmError> {
        Ok(Self {
            name: name.to_string(),
            data: vec![0; 4096],
        })
    }

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

    pub fn read(&self, offset: usize, len: usize) -> Result<Vec<u8>, ShmError> {
        if offset + len > self.data.len() {
            return Err(ShmError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "read exceeds buffer size",
            )));
        }
        Ok(self.data[offset..offset + len].to_vec())
    }

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
    pub fn new() -> Self {
        Self {
            segments: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn create(&self, name: &str, size: usize) -> Result<Arc<Mutex<SharedMemory>>, ShmError> {
        let mut segments = self.segments.lock().unwrap();
        if segments.contains_key(name) {
            return Err(ShmError::AlreadyExists(name.to_string()));
        }
        let shm = Arc::new(Mutex::new(SharedMemory::create(name, size)?));
        segments.insert(name.to_string(), shm.clone());
        Ok(shm)
    }

    pub fn open(&self, name: &str) -> Result<Arc<Mutex<SharedMemory>>, ShmError> {
        let segments = self.segments.lock().unwrap();
        segments
            .get(name)
            .cloned()
            .ok_or_else(|| ShmError::NotFound(name.to_string()))
    }

    pub fn remove(&self, name: &str) -> Result<(), ShmError> {
        let mut segments = self.segments.lock().unwrap();
        segments
            .remove(name)
            .ok_or_else(|| ShmError::NotFound(name.to_string()))?;
        Ok(())
    }

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

    #[test]
    fn test_shm_open_default_size() {
        let shm = SharedMemory::open("foo").unwrap();
        assert_eq!(shm.size(), 4096);
    }

    #[test]
    fn test_shm_size() {
        let shm = SharedMemory::create("x", 256).unwrap();
        assert_eq!(shm.size(), 256);
    }

    #[test]
    fn test_shm_write_out_of_bounds() {
        let mut shm = SharedMemory::create("x", 16).unwrap();
        let big = vec![0u8; 32];
        let res = shm.write(0, &big);
        assert!(matches!(res, Err(ShmError::Io(_))));
    }

    #[test]
    fn test_shm_write_offset_past_end() {
        let mut shm = SharedMemory::create("x", 16).unwrap();
        let res = shm.write(8, b"abcdefghij");
        assert!(res.is_err());
    }

    #[test]
    fn test_shm_read_out_of_bounds() {
        let shm = SharedMemory::create("x", 16).unwrap();
        let res = shm.read(0, 32);
        assert!(matches!(res, Err(ShmError::Io(_))));
    }

    #[test]
    fn test_shm_read_at_offset() {
        let mut shm = SharedMemory::create("x", 32).unwrap();
        shm.write(4, b"abcd").unwrap();
        let buf = shm.read(4, 4).unwrap();
        assert_eq!(buf, b"abcd".to_vec());

        // Zeros outside the written region.
        let zeros = shm.read(0, 4).unwrap();
        assert_eq!(zeros, vec![0u8; 4]);
    }

    #[test]
    fn test_shm_error_display() {
        let err1 = ShmError::NotFound("foo".to_string());
        assert!(format!("{}", err1).contains("foo"));
        assert!(format!("{}", err1).contains("not found"));

        let err2 = ShmError::AlreadyExists("bar".to_string());
        assert!(format!("{}", err2).contains("bar"));
        assert!(format!("{}", err2).contains("already exists"));
    }

    #[test]
    fn test_shm_registry_default() {
        let registry = ShmRegistry::default();
        assert!(registry.list().is_empty());
    }

    #[test]
    fn test_shm_registry_duplicate_create() {
        let registry = ShmRegistry::new();
        registry.create("dup", 64).unwrap();
        let res = registry.create("dup", 64);
        assert!(matches!(res, Err(ShmError::AlreadyExists(_))));
    }

    #[test]
    fn test_shm_registry_open_missing() {
        let registry = ShmRegistry::new();
        let res = registry.open("missing");
        assert!(matches!(res, Err(ShmError::NotFound(_))));
    }

    #[test]
    fn test_shm_registry_remove_ok_and_missing() {
        let registry = ShmRegistry::new();
        registry.create("rem", 8).unwrap();
        registry.remove("rem").unwrap();
        assert!(registry.list().is_empty());

        let res = registry.remove("rem");
        assert!(matches!(res, Err(ShmError::NotFound(_))));
    }

    #[test]
    fn test_shm_registry_shared_arc_state() {
        let registry = ShmRegistry::new();
        let h1 = registry.create("shared", 16).unwrap();
        let h2 = registry.open("shared").unwrap();
        // The two handles point to the same segment.
        assert!(Arc::ptr_eq(&h1, &h2));

        h1.lock().unwrap().write(0, b"X").unwrap();
        let got = h2.lock().unwrap().read(0, 1).unwrap();
        assert_eq!(got, b"X".to_vec());
    }
}
