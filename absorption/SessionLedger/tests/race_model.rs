//! Loom-lite race model: bounded channel + cooperative cancellation.
//!
//! Models the daemon watcher contract (`scan_once` + bounded `mpsc` +
//! `CancellationToken`) with `std::sync::mpsc::sync_channel` and an
//! `AtomicBool` cancel flag. Assertions are conservation / capacity based —
//! no wall-clock sleeps — so the suite stays CI-safe under
//! `.github/workflows/race-smoke.yml` repeats.
//!
//! Soft loom smoke for a tiny cancel/capacity model lives in
//! `tests/loom_model.rs` (`RUSTFLAGS='--cfg loom'`, `.github/workflows/loom-smoke.yml`).
//! Loom permutation checkers add `bounded_try_send_respects_capacity` and related
//! models under `.github/workflows/loom-permutation.yml`; full tokio daemon ports
//! of this `sync_channel` graph remain unpaid.
//! See `docs/ops/concurrency-safety.md`.

use std::collections::HashSet;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::mpsc::{sync_channel, TrySendError};
use std::sync::{Arc, Barrier};
use std::thread;

const CAPACITY: usize = 4;
const CAPACITY_U32: u32 = 4;
const PRODUCERS: usize = 4;
const ITEMS_PER_PRODUCER: u32 = 16;

/// Producer half of the model: stop on cancel, never block on a full channel.
fn try_produce(
    tx: &std::sync::mpsc::SyncSender<u32>,
    cancel: &AtomicBool,
    ids: impl IntoIterator<Item = u32>,
) -> usize {
    let mut sent = 0usize;
    for id in ids {
        if cancel.load(Ordering::Acquire) {
            break;
        }
        match tx.try_send(id) {
            Ok(()) => sent += 1,
            Err(TrySendError::Full(_)) => {
                // Backpressure without blocking: mirrors `select!` losing the
                // send arm when cancel wins, without introducing sleeps.
                if cancel.load(Ordering::Acquire) {
                    break;
                }
                break;
            }
            Err(TrySendError::Disconnected(_)) => break,
        }
    }
    sent
}

#[test]
fn cancel_before_enqueue_emits_nothing() {
    let (tx, rx) = sync_channel::<u32>(CAPACITY);
    let cancel = AtomicBool::new(true);

    let sent = try_produce(&tx, &cancel, 0..10);
    drop(tx);

    assert_eq!(sent, 0, "pre-cancelled producer must not enqueue");
    assert!(rx.try_recv().is_err(), "receiver must see an empty channel after pre-cancel");
}

#[test]
fn bounded_capacity_is_respected_then_cancel_drains_exactly() {
    let (tx, rx) = sync_channel::<u32>(CAPACITY);
    let cancel = AtomicBool::new(false);

    let sent = try_produce(&tx, &cancel, 0..(CAPACITY_U32 * 4));
    assert_eq!(sent, CAPACITY, "try_send must stop at capacity without blocking");

    // Further enqueues fail while full; cancel then forbids retries.
    assert!(matches!(tx.try_send(99), Err(TrySendError::Full(_))));
    cancel.store(true, Ordering::Release);
    assert_eq!(try_produce(&tx, &cancel, 100..110), 0);

    drop(tx);
    let mut drained = Vec::new();
    while let Ok(v) = rx.recv() {
        drained.push(v);
    }
    assert_eq!(drained.len(), CAPACITY);
    assert_eq!(drained, (0..CAPACITY_U32).collect::<Vec<_>>());
}

#[test]
fn concurrent_producers_conserve_messages_under_cancel() {
    let (tx, rx) = sync_channel::<u32>(CAPACITY);
    let cancel = Arc::new(AtomicBool::new(false));
    let start = Arc::new(Barrier::new(PRODUCERS + 1));
    let sent_total = Arc::new(AtomicUsize::new(0));

    let handles: Vec<_> = (0..PRODUCERS)
        .map(|producer| {
            let tx = tx.clone();
            let cancel = Arc::clone(&cancel);
            let start = Arc::clone(&start);
            let sent_total = Arc::clone(&sent_total);
            thread::spawn(move || {
                start.wait();
                let base =
                    u32::try_from(producer).expect("producer index fits u32") * ITEMS_PER_PRODUCER;
                let ids = (0..ITEMS_PER_PRODUCER).map(|i| base + i);
                let local = try_produce(&tx, &cancel, ids);
                sent_total.fetch_add(local, Ordering::Relaxed);
                local
            })
        })
        .collect();

    // Release producers, then cancel without sleeping — race window is real
    // but the conservation assert below is timing-independent.
    start.wait();
    cancel.store(true, Ordering::Release);
    drop(tx);

    let mut received = Vec::new();
    while let Ok(v) = rx.recv() {
        received.push(v);
    }

    let per_worker: Vec<usize> =
        handles.into_iter().map(|h| h.join().expect("producer must not panic")).collect();
    let expected = sent_total.load(Ordering::Relaxed);
    assert_eq!(
        per_worker.iter().sum::<usize>(),
        expected,
        "per-worker sent counts must match atomic total"
    );
    assert_eq!(
        received.len(),
        expected,
        "every successfully enqueued id must be drained exactly once"
    );

    let unique: HashSet<_> = received.iter().copied().collect();
    assert_eq!(unique.len(), received.len(), "message ids must be unique across producers");
    // Outstanding buffered messages cannot exceed the sync_channel capacity
    // at any instant; total drained can exceed capacity because the consumer
    // ran concurrently with producers before drop(tx). Cap the loose bound by
    // the theoretical max producers could try_send before cancel/backpressure.
    assert!(
        received.len() <= CAPACITY * PRODUCERS,
        "drained count {} exceeds producer×capacity bound",
        received.len()
    );
}
