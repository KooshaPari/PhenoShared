//! Integration tests for pheno-proc-queue
//!
//! Tests priority ordering, concurrent access, lifecycle management, and stats.

use pheno_proc_queue::*;
use std::sync::Arc;

// ---------------------------------------------------------------------------
// Priority ordering under load
// ---------------------------------------------------------------------------

#[test]
fn test_priority_ordering_full_spectrum() {
    let queue = InMemoryQueueAdapter::new();

    // Enqueue in reverse priority order
    queue.enqueue("low-1".into(), Priority::Low, None);
    queue.enqueue("low-2".into(), Priority::Low, None);
    queue.enqueue("normal-1".into(), Priority::Normal, None);
    queue.enqueue("high-1".into(), Priority::High, None);
    queue.enqueue("critical-1".into(), Priority::Critical, None);
    queue.enqueue("normal-2".into(), Priority::Normal, None);

    assert_eq!(queue.length(), 6);

    // Critical first
    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::Critical);
    assert_eq!(item.command, "critical-1");

    // High second
    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::High);

    // Then normal (FIFO within same priority)
    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::Normal);
    assert_eq!(item.command, "normal-1");

    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::Normal);
    assert_eq!(item.command, "normal-2");

    // Then low
    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::Low);
    assert_eq!(item.command, "low-1");

    let item = queue.dequeue().unwrap();
    assert_eq!(item.priority, Priority::Low);
    assert_eq!(item.command, "low-2");

    assert!(queue.is_empty());
}

// ---------------------------------------------------------------------------
// QueueItem lifecycle
// ---------------------------------------------------------------------------

#[test]
fn test_queue_item_lifecycle() {
    let queue = InMemoryQueueAdapter::new();
    let item = queue.enqueue("lifecycle-cmd".into(), Priority::Normal, None);
    assert_eq!(item.status, QueueStatus::Queued);
    assert!(item.wait_time().is_none()); // Not yet processing

    // Start processing
    queue
        .update_status(&item.id, QueueStatus::Processing)
        .unwrap();
    let updated = queue.get(&item.id).unwrap();
    assert_eq!(updated.status, QueueStatus::Processing);
    assert!(updated.started_at.is_some());
    assert!(updated.wait_time().is_some()); // Now wait_time is meaningful
    assert!(updated.duration().is_none());

    // Complete
    queue
        .update_status(&item.id, QueueStatus::Completed)
        .unwrap();
    let final_item = queue.get(&item.id).unwrap();
    assert_eq!(final_item.status, QueueStatus::Completed);
    assert!(final_item.duration().is_some());
}

#[test]
fn test_queue_item_fail() {
    let mut item = QueueItem::new("fail-cmd".into(), Priority::High);
    item.start();
    item.fail();
    assert_eq!(item.status, QueueStatus::Failed);
    assert!(item.completed_at.is_some());
}

// ---------------------------------------------------------------------------
// Concurrent enqueue/dequeue via Arc
// ---------------------------------------------------------------------------

#[test]
fn test_concurrent_enqueue_dequeue() {
    let queue = Arc::new(InMemoryQueueAdapter::new());

    // Enqueue 100 items
    for i in 0..100 {
        let priority = match i % 4 {
            0 => Priority::Critical,
            1 => Priority::High,
            2 => Priority::Normal,
            _ => Priority::Low,
        };
        queue.enqueue(format!("cmd-{i}"), priority, None);
    }

    assert_eq!(queue.length(), 100);

    // Verify stats
    let stats = queue.stats();
    assert_eq!(stats.total, 100);
    assert_eq!(stats.queued, 100);

    // Dequeue all
    let mut dequeued = Vec::new();
    while let Some(item) = queue.dequeue() {
        dequeued.push(item);
    }
    assert_eq!(dequeued.len(), 100);

    // Verify ordering: all critical first, then high, normal, low
    let crits: Vec<_> = dequeued
        .iter()
        .filter(|i| i.priority == Priority::Critical)
        .collect();
    let highs: Vec<_> = dequeued
        .iter()
        .filter(|i| i.priority == Priority::High)
        .collect();
    assert_eq!(crits.len(), 25);
    assert_eq!(highs.len(), 25);

    // Critical items should all come before high items
    let last_crit_idx = dequeued
        .iter()
        .rposition(|i| i.priority == Priority::Critical)
        .unwrap();
    let first_high_idx = dequeued
        .iter()
        .position(|i| i.priority == Priority::High)
        .unwrap();
    assert!(last_crit_idx < first_high_idx);
}

// ---------------------------------------------------------------------------
// Stats accuracy
// ---------------------------------------------------------------------------

#[test]
fn test_stats_accuracy_through_lifecycle() {
    let queue = InMemoryQueueAdapter::new();

    // 3 items: one processing, one queued, one completed
    let item1 = queue.enqueue("a".into(), Priority::Normal, None);
    let _item2 = queue.enqueue("b".into(), Priority::Normal, None);
    let item3 = queue.enqueue("c".into(), Priority::Normal, None);

    // 1 processing
    queue
        .update_status(&item1.id, QueueStatus::Processing)
        .unwrap();

    // 1 completed
    queue
        .update_status(&item3.id, QueueStatus::Completed)
        .unwrap();

    let stats = queue.stats();
    assert_eq!(stats.queued, 1);
    assert_eq!(stats.processing, 1);
    assert_eq!(stats.completed, 1);
    assert_eq!(stats.failed, 0);
    assert_eq!(stats.total, 3);

    assert_eq!(
        stats.to_string(),
        "QueueStats { queued: 1, processing: 1, completed: 1, failed: 0, total: 3 }"
    );
}

// ---------------------------------------------------------------------------
// Cleanup and clear
// ---------------------------------------------------------------------------

#[test]
fn test_cleanup_completed() {
    let queue = InMemoryQueueAdapter::new();

    let item1 = queue.enqueue("a".into(), Priority::Normal, None);
    let item2 = queue.enqueue("b".into(), Priority::Normal, None);
    let item3 = queue.enqueue("c".into(), Priority::Normal, None);

    queue
        .update_status(&item1.id, QueueStatus::Completed)
        .unwrap();
    queue.update_status(&item3.id, QueueStatus::Failed).unwrap();

    let removed = queue.cleanup_completed();
    assert_eq!(removed, 2);

    let remaining = queue.list_all();
    assert_eq!(remaining.len(), 1);
    assert_eq!(remaining[0].id, item2.id);
}

#[test]
fn test_clear() {
    let queue = InMemoryQueueAdapter::new();
    for i in 0..50 {
        queue.enqueue(format!("cmd-{i}"), Priority::Normal, None);
    }
    assert_eq!(queue.length(), 50);

    queue.clear();
    assert!(queue.is_empty());
    assert_eq!(queue.list_all().len(), 0);
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

#[test]
fn test_metadata_roundtrip() {
    let queue = InMemoryQueueAdapter::new();
    let meta = serde_json::json!({"key": "value", "num": 42});
    let item = queue.enqueue("cmd".into(), Priority::Normal, Some(meta.clone()));

    let retrieved = queue.get(&item.id).unwrap();
    assert_eq!(retrieved.metadata.unwrap(), meta);
}

// ---------------------------------------------------------------------------
// Priority parse and display
// ---------------------------------------------------------------------------

#[test]
fn test_priority_from_str() {
    assert_eq!("critical".parse::<Priority>().unwrap(), Priority::Critical);
    assert_eq!("high".parse::<Priority>().unwrap(), Priority::High);
    assert_eq!("normal".parse::<Priority>().unwrap(), Priority::Normal);
    assert_eq!("low".parse::<Priority>().unwrap(), Priority::Low);
    assert!("invalid".parse::<Priority>().is_err());
}

#[test]
fn test_priority_display() {
    assert_eq!(Priority::Critical.to_string(), "critical");
    assert_eq!(Priority::High.to_string(), "high");
    assert_eq!(Priority::Normal.to_string(), "normal");
    assert_eq!(Priority::Low.to_string(), "low");
}

// ---------------------------------------------------------------------------
// QueueStatus display
// ---------------------------------------------------------------------------

#[test]
fn test_queue_status_display() {
    assert_eq!(QueueStatus::Queued.to_string(), "queued");
    assert_eq!(QueueStatus::Processing.to_string(), "processing");
    assert_eq!(QueueStatus::Completed.to_string(), "completed");
    assert_eq!(QueueStatus::Failed.to_string(), "failed");
    assert_eq!(QueueStatus::Dequeued.to_string(), "dequeued");
}

// ---------------------------------------------------------------------------
// List by status
// ---------------------------------------------------------------------------

#[test]
fn test_list_by_status() {
    let queue = InMemoryQueueAdapter::new();

    let item1 = queue.enqueue("a".into(), Priority::Normal, None);
    let item2 = queue.enqueue("b".into(), Priority::Normal, None);
    let item3 = queue.enqueue("c".into(), Priority::Normal, None);

    queue
        .update_status(&item1.id, QueueStatus::Processing)
        .unwrap();
    queue
        .update_status(&item3.id, QueueStatus::Completed)
        .unwrap();

    let queued = queue.list_by_status(QueueStatus::Queued);
    assert_eq!(queued.len(), 1);
    assert_eq!(queued[0].id, item2.id);

    let processing = queue.list_by_status(QueueStatus::Processing);
    assert_eq!(processing.len(), 1);

    let completed = queue.list_by_status(QueueStatus::Completed);
    assert_eq!(completed.len(), 1);
}

// ---------------------------------------------------------------------------
// Update nonexistent item
// ---------------------------------------------------------------------------

#[test]
fn test_update_nonexistent_item() {
    let queue = InMemoryQueueAdapter::new();
    let result = queue.update_status("nonexistent", QueueStatus::Completed);
    assert!(result.is_err());
}
