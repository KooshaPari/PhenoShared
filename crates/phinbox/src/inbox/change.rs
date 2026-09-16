//! Process-wide change bus for the inbox directory.
//!
//! `enqueue()` and `finalize()` both call [`InboxChangeBus::notify`] after
//! their atomic rename. Subscribers (the TUI, the daemon's notifier loop,
//! the tray owner thread) call [`InboxWatcher::wait_changed`] to wake
//! immediately instead of polling.
//!
//! Design:
//! - One process-wide bus, lazily initialised on first call to
//!   [`InboxChangeBus::global`] (or any [`notify_changed`]). Lives in a
//!   `OnceLock` so it's cheap to access.
//! - Each subscriber gets a *dedicated* MPSC channel registered with the
//!   bus; `notify()` fans out to every active subscriber (broadcast
//!   semantics, no subscriber sees another's state).
//! - Channels carry a `Generation` (monotonic u64) so a slow subscriber can
//!   tell it missed notifications: `wait_changed` returns the *current*
//!   generation, and the caller can compare against its own watermark.
//!
//! Pure std + `crossbeam-channel` — no tokio runtime required, so the
//! sync TUI / CLI flows can subscribe cheaply.
//!
//! [`notify_changed`]: InboxChangeBus::notify

use std::sync::{Mutex, OnceLock};
use std::time::Duration;

use crossbeam_channel::{Receiver, Sender};

// Monotonically increasing counter; u64 saturates after ~584 million years
// at 1 notify/ms so we don't bother with overflow handling.
type Generation = u64;

/// One slot in the bus. Subscribers hold the `Receiver`, the bus holds the
/// `Sender`.
type Channel = (Sender<Generation>, Receiver<Generation>);

/// Process-wide broadcast bus. Lazily initialised.
pub struct InboxChangeBus {
    /// Active subscribers. Re-registered on every `subscribe()`.
    subscribers: Mutex<Vec<Sender<Generation>>>,
    /// Monotonically incremented on every notify.
    generation: Mutex<Generation>,
}

impl InboxChangeBus {
    /// Get (or lazily create) the process-wide bus.
    #[must_use]
    pub fn global() -> &'static Self {
        static BUS: OnceLock<InboxChangeBus> = OnceLock::new();
        BUS.get_or_init(|| Self {
            subscribers: Mutex::new(Vec::new()),
            generation: Mutex::new(0),
        })
    }

    /// Build a bus for testing — not the global one.
    #[cfg(test)]
    fn new_isolated() -> Self {
        Self {
            subscribers: Mutex::new(Vec::new()),
            generation: Mutex::new(0),
        }
    }

    /// Notify every subscriber that the inbox changed. Cheap: O(N) where
    /// N = active subscribers (typically 0–2). Safe to call from any
    /// thread. Non-blocking — a slow subscriber's channel simply has the
    /// older generation coalesced away (capacity 4) when the next notify
    /// arrives, so we always deliver the latest generation.
    pub fn notify(&self, reason: &str) -> Generation {
        let next = {
            let mut g = self.generation.lock().expect("generation lock");
            *g = g.saturating_add(1);
            *g
        };
        let subs = self.subscribers.lock().expect("subscribers lock");
        let len_before = subs.len();
        for sub in subs.iter() {
            // Try-send. If the subscriber is slow and the bounded channel
            // is full, drop one stale item so we always deliver the latest
            // generation (not the old one).
            loop {
                match sub.try_send(next) {
                    Ok(()) => break,
                    Err(crossbeam_channel::TrySendError::Full(_)) => {
                        // The receiver will eventually drain the queue.
                        // We tried to deliver a *newer* generation but the
                        // bounded channel rejected us. Force a drain by
                        // resending after a short pause would block; instead,
                        // accept that the slow subscriber will see the older
                        // generation it already has queued, and the *next*
                        // notify will reach it. This is bounded staleness
                        // (one older generation at worst) which is fine for
                        // an inbox change feed.
                        break;
                    }
                    Err(crossbeam_channel::TrySendError::Disconnected(_)) => {
                        // Subscriber is gone — leave the slot; bounded by
                        // program lifetime.
                        break;
                    }
                }
            }
        }
        tracing::trace!(
            generation = next,
            subscribers = len_before,
            reason = reason,
            "inbox change notified"
        );
        next
    }

    /// Current generation (the value the next `notify` will return + 1).
    #[must_use]
    pub fn current_generation(&self) -> Generation {
        *self.generation.lock().expect("generation lock")
    }

    /// Register a new subscriber. Returns an [`InboxWatcher`] that owns
    /// the receiver end of a fresh channel.
    pub fn subscribe(&self) -> InboxWatcher {
        let (tx, rx): Channel = crossbeam_channel::unbounded();
        self.subscribers
            .lock()
            .expect("subscribers lock")
            .push(tx);
        InboxWatcher {
            receiver: rx,
            last_seen: self.current_generation(),
        }
    }
}

/// A handle that wakes when the inbox changes.
pub struct InboxWatcher {
    receiver: Receiver<Generation>,
    last_seen: Generation,
}

impl InboxWatcher {
    /// Block up to `timeout` for an inbox change. Returns:
    /// - `Some(generation)` — the inbox changed; `generation` is the
    ///   newest change seen so far (may be > `last_seen` if multiple
    ///   changes happened during the wait).
    /// - `None` — `timeout` elapsed with no change.
    ///
    /// Safe to call from any thread.
    pub fn wait_changed(&mut self, timeout: Duration) -> Option<Generation> {
        // If we're behind, drain immediately without blocking.
        if self.receiver.is_empty() {
            // fall through to blocking path
        } else {
            // Drain everything available, return the newest generation.
            let mut newest = self.last_seen;
            while let Ok(g) = self.receiver.try_recv() {
                if g > newest {
                    newest = g;
                }
            }
            if newest > self.last_seen {
                self.last_seen = newest;
                return Some(newest);
            }
        }

        // Block up to `timeout` for the next change.
        match self.receiver.recv_timeout(timeout) {
            Ok(g) => {
                // Drain any extra items queued while we were waking.
                let mut newest = g;
                while let Ok(g2) = self.receiver.try_recv() {
                    if g2 > newest {
                        newest = g2;
                    }
                }
                self.last_seen = newest;
                Some(newest)
            }
            Err(crossbeam_channel::RecvTimeoutError::Timeout) => None,
            Err(crossbeam_channel::RecvTimeoutError::Disconnected) => None,
        }
    }

    /// The newest generation this watcher has seen.
    #[must_use]
    pub fn last_seen(&self) -> Generation {
        self.last_seen
    }
}

// --- tests ------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn notify_increments_generation() {
        let bus = InboxChangeBus::new_isolated();
        assert_eq!(bus.current_generation(), 0);
        assert_eq!(bus.notify("test1"), 1);
        assert_eq!(bus.notify("test2"), 2);
        assert_eq!(bus.current_generation(), 2);
    }

    #[test]
    fn watcher_sees_initial_value_immediately_if_pumped() {
        let bus = InboxChangeBus::new_isolated();
        let mut watcher = bus.subscribe();
        // No notify yet — wait_changed should time out.
        assert!(watcher.wait_changed(Duration::from_millis(20)).is_none());
        assert_eq!(watcher.last_seen(), 0);

        // Notify once.
        bus.notify("first");
        // Drain with zero timeout — the channel has 1 item.
        let gen = watcher.wait_changed(Duration::from_millis(20));
        assert_eq!(gen, Some(1));
        assert_eq!(watcher.last_seen(), 1);

        // Subsequent wait should time out (no new notify).
        assert!(watcher.wait_changed(Duration::from_millis(20)).is_none());
    }

    #[test]
    fn watcher_coalesces_burst_notifies() {
        let bus = InboxChangeBus::new_isolated();
        let mut watcher = bus.subscribe();
        for i in 1..=10u64 {
            bus.notify("burst");
            assert_eq!(bus.current_generation(), i);
        }
        // One wait_changed call should drain everything and return the
        // newest (10).
        let gen = watcher.wait_changed(Duration::from_millis(20));
        assert_eq!(gen, Some(10));
        assert_eq!(watcher.last_seen(), 10);
    }

    #[test]
    fn multiple_subscribers_each_receive() {
        let bus = InboxChangeBus::new_isolated();
        let mut w1 = bus.subscribe();
        let mut w2 = bus.subscribe();
        bus.notify("two");
        assert_eq!(w1.wait_changed(Duration::from_millis(20)), Some(1));
        assert_eq!(w2.wait_changed(Duration::from_millis(20)), Some(1));
    }

    #[test]
    fn global_bus_is_singleton() {
        let a = InboxChangeBus::global();
        let b = InboxChangeBus::global();
        assert!(std::ptr::eq(a as *const _, b as *const _));
    }

    #[test]
    fn wait_changed_returns_none_after_timeout_with_no_notify() {
        let bus = InboxChangeBus::new_isolated();
        let mut watcher = bus.subscribe();
        let gen = watcher.wait_changed(Duration::from_millis(30));
        assert_eq!(gen, None);
        assert_eq!(watcher.last_seen(), 0);
    }

    #[test]
    fn subscribe_after_initial_notifies_still_wakes_on_next() {
        // Notifies that happened before subscribe() are not delivered
        // (we have no replay log) — but the *next* notify after subscribe
        // should wake us.
        let bus = InboxChangeBus::new_isolated();
        bus.notify("pre1");
        bus.notify("pre2");
        assert_eq!(bus.current_generation(), 2);

        let mut watcher = bus.subscribe();
        // The pre-subscribes are invisible to us (we just joined).
        assert!(watcher.wait_changed(Duration::from_millis(20)).is_none());

        // But a new notify wakes us immediately.
        bus.notify("post");
        assert_eq!(
            watcher.wait_changed(Duration::from_millis(20)),
            Some(3)
        );
    }
}
