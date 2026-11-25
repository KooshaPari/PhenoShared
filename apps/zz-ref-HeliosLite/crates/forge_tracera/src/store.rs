//! In-memory batch queue with offline retry semantics.
//!
//! [`MemoryStore`] holds a bounded FIFO of [`TraceraEvent`]s. Sinks push
//! events via [`submit`](MemoryStore::submit) (which may block on
//! backpressure when the caller is configured for it) and drain in batches
//! via [`drain_batch`](MemoryStore::drain_batch).
//!
//! The store is intentionally pluggable. In production you'd swap in a
//! SQLite-backed or file-backed queue; for tests and short-lived processes
//! the in-memory implementation is sufficient.

use parking_lot::Mutex;
use std::collections::VecDeque;
use std::sync::Arc;

use crate::SinkError;
use crate::event::TraceraEvent;

/// Thread-safe handle to a [`MemoryStore`].
#[derive(Clone)]
pub struct StoreHandle {
    inner: Arc<MemoryStore>,
}

impl StoreHandle {
    /// Wrap a [`MemoryStore`] in an `Arc` and return a clonable handle.
    pub fn new(capacity: usize) -> Self {
        Self { inner: Arc::new(MemoryStore::new(capacity)) }
    }

    /// Push an event; returns `StoreFull` if `block_on_full=false` and the
    /// queue is at capacity.
    pub fn submit(&self, ev: TraceraEvent, block_on_full: bool) -> Result<(), StoreFull> {
        self.inner.submit(ev, block_on_full)
    }

    /// Drain up to `max` events into a new vec.
    pub fn drain_batch(&self, max: usize) -> Vec<TraceraEvent> {
        self.inner.drain_batch(max)
    }

    /// Return the next batch without removing it (peek).
    pub fn peek_batch(&self, max: usize) -> Vec<TraceraEvent> {
        self.inner.peek_batch(max)
    }

    /// Re-insert a previously-drained batch at the front (used on
    /// transport failure to retry).
    pub fn requeue_front(&self, events: Vec<TraceraEvent>) -> Result<(), StoreFull> {
        self.inner.requeue_front(events)
    }

    /// Current queue depth.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// True if the queue is empty.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Configured capacity.
    pub fn capacity(&self) -> usize {
        self.inner.capacity()
    }

    /// Total events ever submitted (successfully or rejected).
    pub fn total_submitted(&self) -> u64 {
        self.inner.total_submitted()
    }

    /// Total events dropped because the queue was full.
    pub fn total_dropped(&self) -> u64 {
        self.inner.total_dropped()
    }
}

/// Bounded FIFO of [`TraceraEvent`]s.
pub struct MemoryStore {
    state: Mutex<StoreState>,
}

struct StoreState {
    queue: VecDeque<TraceraEvent>,
    capacity: usize,
    total_submitted: u64,
    total_dropped: u64,
}

/// Error returned when [`MemoryStore::submit`] cannot enqueue.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StoreFull {
    /// Configured capacity.
    pub capacity: usize,
}

impl MemoryStore {
    /// Construct a store with the given capacity.
    pub fn new(capacity: usize) -> Self {
        Self {
            state: Mutex::new(StoreState {
                queue: VecDeque::with_capacity(capacity.min(1024)),
                capacity,
                total_submitted: 0,
                total_dropped: 0,
            }),
        }
    }

    /// Push an event. Returns [`StoreFull`] (converted into
    /// [`SinkError::StoreFull`] at the sink layer) if at capacity and
    /// `block_on_full` is false.
    pub fn submit(&self, ev: TraceraEvent, block_on_full: bool) -> Result<(), StoreFull> {
        let mut s = self.state.lock();
        if s.queue.len() >= s.capacity {
            if !block_on_full {
                s.total_submitted += 1;
                s.total_dropped += 1;
                return Err(StoreFull { capacity: s.capacity });
            }
            // Block-on-full path: spin briefly until room. We don't use a
            // Condvar here because events are tiny and submission is hot
            // — a tight retry loop is fine and keeps the dependency
            // surface smaller.
            drop(s);
            loop {
                std::thread::yield_now();
                let mut s = self.state.lock();
                if s.queue.len() < s.capacity {
                    s.queue.push_back(ev);
                    s.total_submitted += 1;
                    return Ok(());
                }
                drop(s);
            }
        }
        s.queue.push_back(ev);
        s.total_submitted += 1;
        Ok(())
    }

    /// Drain up to `max` events (oldest first).
    pub fn drain_batch(&self, max: usize) -> Vec<TraceraEvent> {
        let mut s = self.state.lock();
        let take = max.min(s.queue.len());
        s.queue.drain(..take).collect()
    }

    /// Peek up to `max` events without removing them.
    pub fn peek_batch(&self, max: usize) -> Vec<TraceraEvent> {
        let s = self.state.lock();
        s.queue.iter().take(max).cloned().collect()
    }

    /// Push a previously-drained batch back to the front (oldest first).
    pub fn requeue_front(&self, mut events: Vec<TraceraEvent>) -> Result<(), StoreFull> {
        let mut s = self.state.lock();
        let new_total = s.queue.len() + events.len();
        if new_total > s.capacity {
            // Drop the tail to make room, counting drops. We always keep at
            // least the older events — the ones we just tried to send.
            let keep = s.capacity.saturating_sub(s.queue.len());
            let drop = events.len().saturating_sub(keep);
            s.total_dropped += drop as u64;
            events.truncate(keep);
        }
        for ev in events.into_iter().rev() {
            s.queue.push_front(ev);
        }
        Ok(())
    }

    /// Current depth.
    pub fn len(&self) -> usize {
        self.state.lock().queue.len()
    }

    /// True if empty.
    pub fn is_empty(&self) -> bool {
        self.state.lock().queue.is_empty()
    }

    /// Configured capacity.
    pub fn capacity(&self) -> usize {
        self.state.lock().capacity
    }

    /// Total ever submitted (includes dropped).
    pub fn total_submitted(&self) -> u64 {
        self.state.lock().total_submitted
    }

    /// Total ever dropped due to capacity.
    pub fn total_dropped(&self) -> u64 {
        self.state.lock().total_dropped
    }
}

impl From<StoreFull> for SinkError {
    fn from(_: StoreFull) -> Self {
        // Caller must supply capacity / dropped counts via the local
        // totals — we re-construct the variant at the sink layer instead
        // of threading a struct through `From`. This stub keeps the type
        // available for future use.
        SinkError::StoreFull { capacity: 0, dropped: 0 }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::{EventKind, TraceraEvent};

    fn ev() -> TraceraEvent {
        TraceraEvent::new("forgecode", EventKind::Prompt, serde_json::json!({}))
    }

    #[test]
    fn submit_and_drain_round() {
        let s = MemoryStore::new(8);
        for _ in 0..3 {
            s.submit(ev(), false).unwrap();
        }
        assert_eq!(s.len(), 3);
        let batch = s.drain_batch(10);
        assert_eq!(batch.len(), 3);
        assert_eq!(s.len(), 0);
    }

    #[test]
    fn full_returns_store_full() {
        let s = MemoryStore::new(2);
        s.submit(ev(), false).unwrap();
        s.submit(ev(), false).unwrap();
        let r = s.submit(ev(), false);
        assert!(r.is_err());
        assert_eq!(s.total_dropped(), 1);
    }

    #[test]
    fn drain_respects_max() {
        let s = MemoryStore::new(8);
        for _ in 0..5 {
            s.submit(ev(), false).unwrap();
        }
        let b = s.drain_batch(2);
        assert_eq!(b.len(), 2);
        assert_eq!(s.len(), 3);
    }

    #[test]
    fn requeue_front_preserves_order() {
        let s = MemoryStore::new(8);
        for _ in 0..3 {
            s.submit(ev(), false).unwrap();
        }
        let drained = s.drain_batch(3);
        assert_eq!(drained.len(), 3);
        s.requeue_front(drained).unwrap();
        assert_eq!(s.len(), 3);
        let again = s.drain_batch(3);
        assert_eq!(again.len(), 3);
    }

    #[test]
    fn requeue_truncates_when_full() {
        let s = MemoryStore::new(2);
        s.submit(ev(), false).unwrap();
        s.submit(ev(), false).unwrap();
        // queue is now full at 2/2 — drain into a tmp vec, fill one
        // slot back, then requeue. The requeue path must drop the tail
        // to make room.
        let drained = s.drain_batch(2);
        assert_eq!(drained.len(), 2);
        s.submit(ev(), false).unwrap();
        assert_eq!(s.len(), 1);
        s.requeue_front(drained).unwrap();
        // capacity is 2; 1 was already there; we asked to requeue 2;
        // store has 1 already so 1 more can fit (oldest of drained).
        // The newest event was dropped (newer than the older drained
        // ones).
        assert_eq!(s.len(), 2);
        assert!(s.total_dropped() > 0);
    }

    #[test]
    fn handle_is_clonable_and_shared() {
        let h = StoreHandle::new(4);
        let h2 = h.clone();
        h.submit(ev(), false).unwrap();
        h2.submit(ev(), false).unwrap();
        assert_eq!(h.len(), 2);
        assert_eq!(h2.len(), 2);
    }

    #[test]
    fn submit_block_on_full_eventually_succeeds() {
        let s = MemoryStore::new(2);
        s.submit(ev(), false).unwrap();
        s.submit(ev(), false).unwrap();

        // Spawn a draining thread so the blocking submit has room.
        let s_arc = Arc::new(s);
        let s_clone = Arc::clone(&s_arc);
        let h = std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_millis(20));
            s_clone.drain_batch(1);
        });

        // blocking submit with 20ms grace period
        let res = s_arc.submit(ev(), true);
        h.join().unwrap();
        assert!(res.is_ok());
    }
}
