//! Integration tests for pheno-proc-shm
//!
//! Tests SharedMemory read/write, ShmRegistry CRUD, and edge cases.

use pheno_proc_shm::*;

// ---------------------------------------------------------------------------
// SharedMemory basics
// ---------------------------------------------------------------------------

#[test]
fn test_shared_memory_create_and_size() {
    let shm = SharedMemory::create("test", 2048).unwrap();
    assert_eq!(shm.size(), 2048);
}

#[test]
fn test_shared_memory_write_read() {
    let mut shm = SharedMemory::create("test", 1024).unwrap();
    shm.write(0, b"hello world").unwrap();
    let data = shm.read(0, 11).unwrap();
    assert_eq!(data, b"hello world");
}

#[test]
fn test_shared_memory_write_read_offset() {
    let mut shm = SharedMemory::create("test", 1024).unwrap();
    shm.write(100, b"offset data").unwrap();
    let data = shm.read(100, 11).unwrap();
    assert_eq!(data, b"offset data");
}

#[test]
fn test_shared_memory_write_exceeds_bounds() {
    let mut shm = SharedMemory::create("test", 64).unwrap();
    let result = shm.write(60, b"too long");
    assert!(result.is_err());
}

#[test]
fn test_shared_memory_read_exceeds_bounds() {
    let shm = SharedMemory::create("test", 64).unwrap();
    let result = shm.read(60, 10);
    assert!(result.is_err());
}

#[test]
fn test_shared_memory_empty_write() {
    let mut shm = SharedMemory::create("test", 64).unwrap();
    shm.write(0, b"").unwrap();
    let data = shm.read(0, 0).unwrap();
    assert!(data.is_empty());
}

// ---------------------------------------------------------------------------
// ShmRegistry CRUD
// ---------------------------------------------------------------------------

#[test]
fn test_shm_registry_create_and_open() {
    let registry = ShmRegistry::new();
    let shm = registry.create("seg1", 512).unwrap();
    shm.lock().unwrap().write(0, b"test").unwrap();

    let opened = registry.open("seg1").unwrap();
    let data = opened.lock().unwrap().read(0, 4).unwrap();
    assert_eq!(data, b"test");
}

#[test]
fn test_shm_registry_duplicate_create_fails() {
    let registry = ShmRegistry::new();
    registry.create("seg", 256).unwrap();
    let result = registry.create("seg", 256);
    assert!(result.is_err());
}

#[test]
fn test_shm_registry_open_nonexistent_fails() {
    let registry = ShmRegistry::new();
    let result = registry.open("nope");
    assert!(result.is_err());
}

#[test]
fn test_shm_registry_remove() {
    let registry = ShmRegistry::new();
    registry.create("seg", 256).unwrap();
    registry.remove("seg").unwrap();

    let result = registry.open("seg");
    assert!(result.is_err());
}

#[test]
fn test_shm_registry_remove_nonexistent_fails() {
    let registry = ShmRegistry::new();
    let result = registry.remove("nope");
    assert!(result.is_err());
}

#[test]
fn test_shm_registry_list() {
    let registry = ShmRegistry::new();
    assert!(registry.list().is_empty());

    registry.create("alpha", 128).unwrap();
    registry.create("beta", 256).unwrap();

    let mut list = registry.list();
    list.sort();
    assert_eq!(list, vec!["alpha".to_string(), "beta".to_string()]);
}

#[test]
fn test_shm_registry_create_open_remove_lifecycle() {
    let registry = ShmRegistry::new();

    // Create
    let shm = registry.create("lifecycle", 1024).unwrap();
    shm.lock().unwrap().write(0, b"lifecycle data").unwrap();

    // Open and read
    let opened = registry.open("lifecycle").unwrap();
    let data = opened
        .lock()
        .unwrap()
        .read(0, b"lifecycle data".len())
        .unwrap();
    assert_eq!(data, b"lifecycle data");

    // List
    assert_eq!(registry.list().len(), 1);

    // Remove
    registry.remove("lifecycle").unwrap();
    assert!(registry.list().is_empty());
}

// ---------------------------------------------------------------------------
// Multiple segments
// ---------------------------------------------------------------------------

#[test]
fn test_shm_registry_multiple_segments() {
    let registry = ShmRegistry::new();

    for i in 0..10 {
        let name = format!("seg-{i}");
        let shm = registry.create(&name, 256).unwrap();
        shm.lock()
            .unwrap()
            .write(0, format!("data-{i}").as_bytes())
            .unwrap();
    }

    assert_eq!(registry.list().len(), 10);

    for i in 0..10 {
        let name = format!("seg-{i}");
        let opened = registry.open(&name).unwrap();
        let expected = format!("data-{i}");
        let data = opened.lock().unwrap().read(0, expected.len()).unwrap();
        assert_eq!(data, format!("data-{i}").as_bytes());
    }
}
