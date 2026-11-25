//! Event bus infrastructure for the SessionLedger daemon.
//!
//! Domain events are emitted at key pipeline milestones and delivered to any
//! number of subscribers.  [`InMemoryEventBus`] uses a
//! [`tokio::sync::broadcast`] channel under the hood so every subscriber
//! receives every published event.
//!
//! # Architecture
//!
//! ```text
//! Producer ──publish──▶ EventBus ──broadcast──▶ Subscriber 1
//!                                        ├────▶ Subscriber 2
//!                                        └────▶ Subscriber N
//! ```

use std::fmt;

use tokio::sync::broadcast;

// ---------------------------------------------------------------------------
// Domain events
// ---------------------------------------------------------------------------

/// A domain event produced during the daemon pipeline.
///
/// Each variant carries a minimal, structured payload that downstream
/// consumers can filter on.  Serialisation is provided via `Debug`; callers
/// that need JSON serialisation can derive `serde::Serialize` on their own
/// wrapper types.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Event {
    /// A new session file was detected by the file-system watcher.
    SessionCreated {
        /// Absolute path to the newly discovered session file.
        path: String,
    },
    /// The ingestion step read raw bytes from a session file.
    IngestReceived {
        /// Source file path that was ingested.
        source: String,
        /// Number of bytes read from the source.
        bytes: u64,
    },
    /// An OKF bundle was successfully exported and written to disk.
    OkfBundleStored {
        /// Absolute path to the written `.okf.json` bundle.
        bundle_path: String,
        /// Number of sessions compiled into the bundle.
        session_count: u32,
    },
    /// A replay operation has been initiated.
    ReplayStarted {
        /// Caller-assigned replay identifier.
        replay_id: String,
        /// Path of the session being replayed.
        target_session: String,
    },
    /// A replay operation has completed.
    ReplayCompleted {
        /// Same replay identifier that was emitted in `ReplayStarted`.
        replay_id: String,
        /// Total number of events replayed.
        events_replayed: u64,
    },
}

impl fmt::Display for Event {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Event::SessionCreated { path } => write!(f, "SessionCreated({path})"),
            Event::IngestReceived { source, bytes } => {
                write!(f, "IngestReceived({source}, {bytes} bytes)")
            }
            Event::OkfBundleStored {
                bundle_path,
                session_count,
            } => write!(f, "OkfBundleStored({bundle_path}, {session_count} sessions)"),
            Event::ReplayStarted {
                replay_id,
                target_session,
            } => write!(f, "ReplayStarted({replay_id}, {target_session})"),
            Event::ReplayCompleted {
                replay_id,
                events_replayed,
            } => write!(f, "ReplayCompleted({replay_id}, {events_replayed} events)"),
        }
    }
}

// ---------------------------------------------------------------------------
// EventBus trait
// ---------------------------------------------------------------------------

/// Asynchronous event bus abstraction.
///
/// Producers call [`publish`](EventBus::publish) and every active subscriber
/// receives the event.  Implementations decide the delivery semantics (fan-out
/// to all subscribers, first-responder, etc.).
pub trait EventBus: Send + Sync {
    /// Publish an event to all current subscribers.
    fn publish(&self, event: Event);

    /// Return a receiver that yields subsequent events.
    ///
    /// The returned receiver is a *clone* of the underlying broadcast
    /// subscriber — callers may store and poll it independently.
    fn subscribe(&self) -> broadcast::Receiver<Event>;
}

// ---------------------------------------------------------------------------
// InMemoryEventBus
// ---------------------------------------------------------------------------

/// An in-process event bus backed by [`tokio::sync::broadcast`].
///
/// Clone this and hand clones to multiple producers / subscribers.
/// All instances sharing the same underlying broadcast sender will see
/// every published event.
#[derive(Debug, Clone)]
pub struct InMemoryEventBus {
    tx: broadcast::Sender<Event>,
}

impl InMemoryEventBus {
    /// Create a new in-memory event bus with the given channel capacity.
    ///
    /// `capacity` determines how many messages are buffered before lagging
    /// subscribers are disconnected.  A capacity of 256 is a sensible
    /// default for the daemon's pipeline throughput.
    pub fn new(capacity: usize) -> Self {
        let (tx, _) = broadcast::channel(capacity);
        Self { tx }
    }

    /// Return the number of currently active subscribers.
    pub fn subscriber_count(&self) -> usize {
        self.tx.receiver_count()
    }
}

impl Default for InMemoryEventBus {
    fn default() -> Self {
        Self::new(256)
    }
}

impl EventBus for InMemoryEventBus {
    fn publish(&self, event: Event) {
        // Ignore send errors — they only happen when there are zero
        // receivers, which is a valid idle state.
        let _ = self.tx.send(event);
    }

    fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.tx.subscribe()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// Helper: create a bus, subscribe, publish one event, assert delivery.
    fn publish_and_receive(event: Event) {
        let bus = InMemoryEventBus::new(16);
        let mut rx = bus.subscribe();
        bus.publish(event.clone());
        let received = rx.try_recv().expect("expected one event");
        assert_eq!(received, event);
    }

    #[test]
    fn session_created_display() {
        let ev = Event::SessionCreated {
            path: "/tmp/sessions/s1.jsonl".into(),
        };
        assert_eq!(
            ev.to_string(),
            "SessionCreated(/tmp/sessions/s1.jsonl)"
        );
    }

    #[test]
    fn ingest_received_display() {
        let ev = Event::IngestReceived {
            source: "/data/s.jsonl".into(),
            bytes: 4096,
        };
        assert_eq!(ev.to_string(), "IngestReceived(/data/s.jsonl, 4096 bytes)");
    }

    #[test]
    fn okf_bundle_stored_display() {
        let ev = Event::OkfBundleStored {
            bundle_path: "/out/bundle.okf.json".into(),
            session_count: 3,
        };
        assert_eq!(
            ev.to_string(),
            "OkfBundleStored(/out/bundle.okf.json, 3 sessions)"
        );
    }

    #[test]
    fn replay_started_display() {
        let ev = Event::ReplayStarted {
            replay_id: "rp-001".into(),
            target_session: "/data/s.jsonl".into(),
        };
        assert_eq!(ev.to_string(), "ReplayStarted(rp-001, /data/s.jsonl)");
    }

    #[test]
    fn replay_completed_display() {
        let ev = Event::ReplayCompleted {
            replay_id: "rp-001".into(),
            events_replayed: 128,
        };
        assert_eq!(ev.to_string(), "ReplayCompleted(rp-001, 128 events)");
    }

    #[test]
    fn in_memory_bus_delivers_to_subscriber() {
        let ev = Event::SessionCreated {
            path: "/sessions/a.jsonl".into(),
        };
        publish_and_receive(ev);
    }

    #[test]
    fn in_memory_bus_multiple_subscribers() {
        let bus = InMemoryEventBus::new(16);
        let mut rx1 = bus.subscribe();
        let mut rx2 = bus.subscribe();

        assert_eq!(bus.subscriber_count(), 2);

        let ev = Event::IngestReceived {
            source: "/s.jsonl".into(),
            bytes: 1024,
        };
        bus.publish(ev.clone());

        assert_eq!(rx1.try_recv().unwrap(), ev);
        assert_eq!(rx2.try_recv().unwrap(), ev);
    }

    #[test]
    fn in_memory_bus_preserves_order() {
        let bus = InMemoryEventBus::new(64);
        let mut rx = bus.subscribe();

        let ev1 = Event::SessionCreated {
            path: "/1.jsonl".into(),
        };
        let ev2 = Event::OkfBundleStored {
            bundle_path: "/out.okf.json".into(),
            session_count: 1,
        };

        bus.publish(ev1.clone());
        bus.publish(ev2.clone());

        assert_eq!(rx.try_recv().unwrap(), ev1);
        assert_eq!(rx.try_recv().unwrap(), ev2);
    }

    #[test]
    fn in_memory_bus_lagged_receiver_returns_error() {
        let bus = InMemoryEventBus::new(2); // very small capacity
        let mut rx = bus.subscribe();

        // Publish more events than the capacity to lag the receiver.
        for i in 0..10 {
            bus.publish(Event::ReplayCompleted {
                replay_id: format!("r{i}"),
                events_replayed: i,
            });
        }

        // The receiver should have lagged.
        let result = rx.try_recv();
        assert!(result.is_err(), "expected lag error from small buffer");
    }

    #[test]
    fn default_capacity_is_256() {
        let bus = InMemoryEventBus::default();
        // Just verify construction succeeds and bus is usable.
        let mut rx = bus.subscribe();
        bus.publish(Event::SessionCreated {
            path: "/x.jsonl".into(),
        });
        assert!(rx.try_recv().is_ok());
    }
}
