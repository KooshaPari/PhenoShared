//! Integration tests for pheno-proc-dedup
//!
//! Tests DedupFilter, BloomFilter, CommandLock, and InMemoryLockAdapter.

use pheno_proc_dedup::*;
use std::time::Duration;

// ---------------------------------------------------------------------------
// DedupFilter: insert/check/clear
// ---------------------------------------------------------------------------

#[test]
fn test_dedup_filter_insert_and_check() {
    let mut filter = DedupFilter::new();
    assert!(filter.check_and_insert("hello"));
    assert!(!filter.check_and_insert("hello"));
    assert!(filter.check_and_insert("world"));
    assert_eq!(filter.len(), 2);
    assert!(!filter.is_empty());
}

#[test]
fn test_dedup_filter_clear() {
    let mut filter = DedupFilter::new();
    filter.check_and_insert(1);
    filter.check_and_insert(2);
    assert_eq!(filter.len(), 2);

    filter.clear();
    assert!(filter.is_empty());
    assert_eq!(filter.len(), 0);

    // Can re-insert after clear
    assert!(filter.check_and_insert(1));
}

#[test]
fn test_dedup_filter_with_capacity() {
    let mut filter = DedupFilter::<String>::with_capacity(1000);
    for i in 0..1000 {
        filter.check_and_insert(format!("item-{i}"));
    }
    assert_eq!(filter.len(), 1000);

    // All should be seen
    for i in 0..1000 {
        assert!(!filter.check_and_insert(format!("item-{i}")));
    }
}

#[test]
fn test_dedup_filter_integers() {
    let mut filter = DedupFilter::new();
    for i in 0..100 {
        assert!(filter.check_and_insert(i));
    }
    for i in 0..100 {
        assert!(!filter.check_and_insert(i));
    }
}

// ---------------------------------------------------------------------------
// BloomFilter: add/check/check_and_add
// ---------------------------------------------------------------------------

#[test]
fn test_bloom_filter_basic() {
    let mut filter = BloomFilter::new(1000, 3);

    assert!(!filter.check(b"hello"));
    filter.add(b"hello");
    assert!(filter.check(b"hello"));
}

#[test]
fn test_bloom_filter_check_and_add() {
    let mut filter = BloomFilter::new(1000, 3);

    // First time: not seen
    assert!(!filter.check_and_add(b"item"));
    // Second time: already seen
    assert!(filter.check_and_add(b"item"));
}

#[test]
fn test_bloom_filter_false_positive_rate() {
    let mut filter = BloomFilter::new(10_000, 7);

    // Add 1000 items
    for i in 0..1000 {
        filter.add(format!("item-{i}").as_bytes());
    }

    // Check items that were NOT added
    let mut false_positives = 0;
    for i in 1000..2000 {
        if filter.check(format!("unseen-{i}").as_bytes()) {
            false_positives += 1;
        }
    }

    // With 10k bits and 7 hashes, FP rate should be < 1%
    assert!(
        false_positives < 100,
        "Too many false positives: {false_positives}/1000"
    );
}

#[test]
fn test_bloom_filter_no_false_negatives() {
    let mut filter = BloomFilter::new(1000, 5);
    let items: Vec<String> = (0..100).map(|i| format!("key-{i}")).collect();

    for item in &items {
        filter.add(item.as_bytes());
    }

    // Every added item must be found
    for item in &items {
        assert!(filter.check(item.as_bytes()), "False negative for {item}");
    }
}

// ---------------------------------------------------------------------------
// CommandLock: acquire, release, expiry
// ---------------------------------------------------------------------------

#[test]
fn test_command_lock_acquire_release() {
    let mut lock = CommandLock::new("hash1".into(), 100, None);
    assert!(lock.is_locked());
    assert_eq!(lock.status, LockStatus::Locked);

    lock.release(100).unwrap();
    assert_eq!(lock.status, LockStatus::Released);
}

#[test]
fn test_command_lock_wrong_pid_release() {
    let mut lock = CommandLock::new("hash1".into(), 100, None);
    let result = lock.release(200);
    assert!(result.is_err());
}

#[test]
fn test_command_lock_expiry() {
    let lock = CommandLock::new("hash1".into(), 100, None).with_expiry(Duration::from_millis(1));

    // Wait for expiry
    std::thread::sleep(Duration::from_millis(10));

    // Should report as not locked due to expiry
    assert!(!lock.is_locked());
}

#[test]
fn test_command_lock_acquire_updates_pid() {
    let mut lock = CommandLock::new("hash1".into(), 100, None);
    lock.acquire(200, Some("/output/path".into()));
    assert_eq!(lock.pid, 200);
    assert_eq!(lock.output_path.as_deref(), Some("/output/path"));
}

// ---------------------------------------------------------------------------
// LockStatus display
// ---------------------------------------------------------------------------

#[test]
fn test_lock_status_display() {
    assert_eq!(LockStatus::Locked.to_string(), "locked");
    assert_eq!(LockStatus::Released.to_string(), "released");
    assert_eq!(LockStatus::Expired.to_string(), "expired");
}

// ---------------------------------------------------------------------------
// InMemoryLockAdapter: full lifecycle
// ---------------------------------------------------------------------------

#[test]
fn test_lock_adapter_acquire_release() {
    let adapter = InMemoryLockAdapter::new();

    let lock = adapter.acquire("cmd1", 100, None).unwrap();
    assert!(lock.is_locked());
    assert_eq!(lock.pid, 100);

    adapter.release("cmd1", 100).unwrap();

    let lock = adapter.get("cmd1").unwrap();
    assert!(!lock.is_locked());
}

#[test]
fn test_lock_adapter_duplicate_prevention() {
    let adapter = InMemoryLockAdapter::new();

    adapter.acquire("cmd1", 100, None).unwrap();

    // Different PID should fail
    let result = adapter.acquire("cmd1", 200, None);
    assert!(result.is_err());
}

#[test]
fn test_lock_adapter_same_pid_reacquire() {
    let adapter = InMemoryLockAdapter::new();

    adapter.acquire("cmd1", 100, None).unwrap();
    adapter.release("cmd1", 100).unwrap();

    // Same PID can reacquire
    let result = adapter.acquire("cmd1", 100, None);
    assert!(result.is_ok());
}

#[test]
fn test_lock_adapter_different_commands() {
    let adapter = InMemoryLockAdapter::new();

    adapter.acquire("cmd1", 100, None).unwrap();
    adapter.acquire("cmd2", 200, None).unwrap();
    adapter.acquire("cmd3", 300, None).unwrap();

    let active = adapter.list_active();
    assert_eq!(active.len(), 3);
}

#[test]
fn test_lock_adapter_list_all() {
    let adapter = InMemoryLockAdapter::new();

    adapter.acquire("cmd1", 100, None).unwrap();
    adapter.acquire("cmd2", 200, None).unwrap();
    adapter.release("cmd1", 100).unwrap();

    let all = adapter.list_all();
    assert_eq!(all.len(), 2);

    let active = adapter.list_active();
    assert_eq!(active.len(), 1);
}

#[test]
fn test_lock_adapter_cleanup_expired() {
    let adapter = InMemoryLockAdapter::with_ttl(Duration::from_millis(1));

    adapter.acquire("cmd1", 100, None).unwrap();
    adapter.acquire("cmd2", 200, None).unwrap();

    std::thread::sleep(Duration::from_millis(10));

    let removed = adapter.cleanup_expired();
    assert_eq!(removed, 2);
    assert!(adapter.list_active().is_empty());
}

#[test]
fn test_lock_adapter_clear() {
    let adapter = InMemoryLockAdapter::new();

    for i in 0..10 {
        adapter.acquire(&format!("cmd-{i}"), i, None).unwrap();
    }

    assert_eq!(adapter.list_all().len(), 10);

    adapter.clear();
    assert!(adapter.list_all().is_empty());
}

#[test]
fn test_lock_adapter_release_nonexistent() {
    let adapter = InMemoryLockAdapter::new();
    let result = adapter.release("nope", 100);
    assert!(result.is_err());
}

#[test]
fn test_lock_adapter_with_custom_ttl() {
    let adapter = InMemoryLockAdapter::with_ttl(Duration::from_secs(60));
    let lock = adapter.acquire("cmd1", 100, None).unwrap();
    assert!(lock.expires_at.is_some());
}

#[test]
fn test_lock_adapter_output_path() {
    let adapter = InMemoryLockAdapter::new();
    let lock = adapter
        .acquire("cmd1", 100, Some("/tmp/output.json".into()))
        .unwrap();
    assert_eq!(lock.output_path.as_deref(), Some("/tmp/output.json"));
}
