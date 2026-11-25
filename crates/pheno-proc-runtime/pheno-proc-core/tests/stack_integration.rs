//! Cross-crate integration tests exercising the full pheno-proc stack.
//!
//! These tests verify that the orchestration layer correctly coordinates
//! queue, dedup, shared-memory, and lock subsystems working together.

use pheno_proc_dedup::{DedupFilter, InMemoryLockAdapter, LockStatus};
use pheno_proc_queue::{InMemoryQueueAdapter, Priority, QueueStatus};
use pheno_proc_shm::ShmRegistry;
use std::sync::Arc;
use std::thread;
use std::time::Duration;

// ---------------------------------------------------------------------------
// 1. Queue + Dedup pipeline
// ---------------------------------------------------------------------------

/// Enqueue commands through the queue, verify dedup filter catches duplicates
/// before they enter the queue.
#[test]
fn queue_dedup_pipeline() {
    let queue = InMemoryQueueAdapter::new();
    let mut dedup = DedupFilter::<String>::new();

    let commands = vec!["build", "test", "deploy", "build", "test", "lint"];
    let mut enqueued = Vec::new();

    for cmd in &commands {
        // Simulate gatekeeper: only enqueue if dedup filter accepts it.
        if dedup.check_and_insert(cmd.to_string()) {
            let item = queue.enqueue(cmd.to_string(), Priority::Normal, None);
            enqueued.push(item);
        }
    }

    // "build" and "test" appear twice but only the first occurrence passes.
    assert_eq!(enqueued.len(), 4); // build, test, deploy, lint
    assert_eq!(queue.length(), 4);

    // Verify order matches insertion of unique commands.
    let names: Vec<String> = enqueued.iter().map(|i| i.command.clone()).collect();
    assert_eq!(names, vec!["build", "test", "deploy", "lint"]);
}

// ---------------------------------------------------------------------------
// 2. SharedMemory + Queue result passing
// ---------------------------------------------------------------------------

/// Use shared memory to pass results between queue consumers.
#[test]
fn shm_queue_result_passing() {
    let queue = InMemoryQueueAdapter::new();
    let registry = ShmRegistry::new();

    // Worker 1: enqueue a task, then store result in shared memory.
    let item = queue.enqueue("compute_hash".to_string(), Priority::Normal, None);
    let _dequeued = queue.dequeue().expect("queue should not be empty");
    let result_data = b"sha256:abc123";

    let segment = registry.create("result_1", 1024).unwrap();
    segment.lock().unwrap().write(0, result_data).unwrap();

    // Worker 2: read result from shared memory.
    let segment = registry.open("result_1").unwrap();
    let read_back = segment.lock().unwrap().read(0, result_data.len()).unwrap();
    assert_eq!(read_back, result_data);

    // Mark task as completed in queue.
    queue
        .update_status(&item.id, QueueStatus::Completed)
        .unwrap();

    let completed = queue.list_by_status(QueueStatus::Completed);
    assert_eq!(completed.len(), 1);
    assert_eq!(completed[0].id, item.id);
}

// ---------------------------------------------------------------------------
// 3. Lock adapter + Queue coordination
// ---------------------------------------------------------------------------

/// Use command locks to prevent duplicate command execution while the queue
/// processes tasks.
#[test]
fn lock_queue_coordination() {
    let queue = InMemoryQueueAdapter::new();
    let lock_adapter = InMemoryLockAdapter::new();
    let mut dedup = DedupFilter::<String>::new();

    let cmd = "deploy prod".to_string();
    let cmd_hash = format!("{:x}", cmd.len()); // simple hash stand-in
    let pid_a: u32 = 1001;
    let pid_b: u32 = 2002;

    // Gatekeeper passes dedup check.
    assert!(dedup.check_and_insert(cmd.clone()));

    // Worker A acquires lock and enqueues.
    let _lock = lock_adapter.acquire(&cmd_hash, pid_a, None).unwrap();
    queue.enqueue(cmd.clone(), Priority::High, None);

    // Worker B tries to acquire same lock -- should fail.
    let result = lock_adapter.acquire(&cmd_hash, pid_b, None);
    assert!(result.is_err());

    // Worker A processes and releases lock.
    let item = queue.dequeue().unwrap();
    queue
        .update_status(&item.id, QueueStatus::Completed)
        .unwrap();
    lock_adapter.release(&cmd_hash, pid_a).unwrap();

    // After release, Worker B can acquire.
    let lock_b = lock_adapter.acquire(&cmd_hash, pid_b, None).unwrap();
    assert_eq!(lock_b.pid, pid_b);
    assert!(lock_b.is_locked());
}

// ---------------------------------------------------------------------------
// 4. Full workflow simulation
// ---------------------------------------------------------------------------

/// End-to-end: register commands, enqueue unique ones, process them,
/// store results in shared memory, and verify dedup prevents re-execution.
#[test]
fn full_workflow_simulation() {
    let queue = InMemoryQueueAdapter::new();
    let mut dedup = DedupFilter::<String>::new();
    let lock_adapter = InMemoryLockAdapter::new();
    let registry = ShmRegistry::new();

    let commands = vec!["fetch", "transform", "load", "fetch", "transform"];

    // Phase 1: Deduplicate and enqueue.
    let mut enqueued_ids = Vec::new();
    for cmd in &commands {
        if dedup.check_and_insert(cmd.to_string()) {
            let item = queue.enqueue(cmd.to_string(), Priority::Normal, None);
            enqueued_ids.push(item.id.clone());
        }
    }
    assert_eq!(enqueued_ids.len(), 3); // fetch, transform, load

    // Phase 2: Process each command.
    let mut results = Vec::new();
    for id in &enqueued_ids {
        let mut item = queue.get(id).expect("item should exist").clone();
        assert_eq!(item.status, QueueStatus::Queued);

        // Acquire lock to prevent duplicate execution.
        let cmd_hash = format!("h_{}", item.command);
        let _lock = lock_adapter.acquire(&cmd_hash, 100, None).unwrap();

        // Start processing.
        item.start();
        queue
            .update_status(&item.id, QueueStatus::Processing)
            .unwrap();

        // Simulate work: store result in shared memory.
        let seg_name = format!("res_{}", item.command);
        let seg = registry.create(&seg_name, 256).unwrap();
        let payload = format!("done:{}", item.command);
        seg.lock().unwrap().write(0, payload.as_bytes()).unwrap();

        // Complete processing.
        queue
            .update_status(&item.id, QueueStatus::Completed)
            .unwrap();
        lock_adapter.release(&cmd_hash, 100).unwrap();

        // Read back from shared memory.
        let seg = registry.open(&seg_name).unwrap();
        let data = seg.lock().unwrap().read(0, payload.len()).unwrap();
        results.push(String::from_utf8(data).unwrap());
    }

    assert_eq!(results.len(), 3);
    assert_eq!(results[0], "done:fetch");
    assert_eq!(results[1], "done:transform");
    assert_eq!(results[2], "done:load");

    // Phase 3: Verify dedup prevents re-enqueue of duplicate commands.
    for cmd in &["fetch", "transform", "load"] {
        assert!(!dedup.check_and_insert(cmd.to_string()));
    }

    // Queue stats reflect final state.
    let stats = queue.stats();
    assert_eq!(stats.queued, 0);
    assert_eq!(stats.completed, 3);
}

// ---------------------------------------------------------------------------
// 5. Concurrent queue + dedup
// ---------------------------------------------------------------------------

/// Multiple threads enqueue and check dedup simultaneously to verify
/// thread-safety of the combined subsystems.
#[test]
fn concurrent_queue_dedup() {
    let queue = Arc::new(InMemoryQueueAdapter::new());
    let dedup = Arc::new(std::sync::Mutex::new(DedupFilter::<String>::new()));

    let mut handles = Vec::new();
    let commands_per_thread = vec![
        vec!["a", "b", "c"],
        vec!["b", "c", "d"],
        vec!["a", "d", "e"],
    ];

    for cmds in commands_per_thread {
        let q = Arc::clone(&queue);
        let d = Arc::clone(&dedup);
        handles.push(thread::spawn(move || {
            let mut accepted = 0;
            for cmd in cmds {
                let mut filter = d.lock().unwrap();
                if filter.check_and_insert(cmd.to_string()) {
                    drop(filter); // release lock before enqueuing
                    q.enqueue(cmd.to_string(), Priority::Normal, None);
                    accepted += 1;
                }
            }
            accepted
        }));
    }

    let accepted_counts: Vec<usize> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    let total_accepted: usize = accepted_counts.iter().sum();

    // Unique commands across all threads: a, b, c, d, e = 5
    assert_eq!(total_accepted, 5);
    assert_eq!(queue.length(), 5);

    // Verify all unique commands are present.
    let names: Vec<String> = queue.list_all().into_iter().map(|i| i.command).collect();
    for expected in &["a", "b", "c", "d", "e"] {
        assert!(
            names.contains(&expected.to_string()),
            "missing command {expected}"
        );
    }
}

// ---------------------------------------------------------------------------
// 6. Lock + Queue lifecycle
// ---------------------------------------------------------------------------

/// Acquire lock, enqueue, process, release lock, verify state consistency.
#[test]
fn lock_queue_lifecycle() {
    let queue = InMemoryQueueAdapter::new();
    let lock_adapter = InMemoryLockAdapter::with_ttl(Duration::from_secs(30));
    let mut dedup = DedupFilter::<String>::new();
    let registry = ShmRegistry::new();

    let cmd = "run_migration";
    let cmd_hash = "migration_hash";

    // Step 1: Dedup check.
    assert!(dedup.check_and_insert(cmd.to_string()));

    // Step 2: Acquire lock.
    let lock = lock_adapter
        .acquire(cmd_hash, 42, Some("/tmp/output".to_string()))
        .unwrap();
    assert_eq!(lock.status, LockStatus::Locked);
    assert!(lock.is_locked());
    assert_eq!(lock.output_path.as_deref(), Some("/tmp/output"));

    // Step 3: Enqueue.
    let item = queue.enqueue(cmd.to_string(), Priority::Critical, None);
    assert_eq!(item.priority, Priority::Critical);
    assert_eq!(queue.length(), 1);

    // Step 4: Process -- dequeue, store result, complete.
    let dequeued = queue.dequeue().unwrap();
    assert_eq!(dequeued.command, cmd);

    queue
        .update_status(&dequeued.id, QueueStatus::Processing)
        .unwrap();
    let seg = registry.create("migration_result", 512).unwrap();
    seg.lock().unwrap().write(0, b"migration_ok").unwrap();

    queue
        .update_status(&dequeued.id, QueueStatus::Completed)
        .unwrap();

    // Step 5: Release lock.
    lock_adapter.release(cmd_hash, 42).unwrap();
    let released = lock_adapter.get(cmd_hash).unwrap();
    assert_eq!(released.status, LockStatus::Released);
    assert!(!released.is_locked());

    // Step 6: Verify full state consistency.
    assert!(queue.is_empty()); // all dequeued
    let stats = queue.stats();
    assert_eq!(stats.completed, 1);
    assert_eq!(stats.queued, 0);

    let data = seg.lock().unwrap().read(0, 12).unwrap();
    assert_eq!(data, b"migration_ok");

    // Step 7: Dedup prevents re-execution.
    assert!(!dedup.check_and_insert(cmd.to_string()));
}
