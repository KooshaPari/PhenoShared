//! Lightweight typed pub/sub bus for integration tests and simple fan-out.
//!
//! This API is intentionally smaller than [`EventBus`]: publishers send plain
//! payloads and subscribers receive them on a channel without envelope metadata.

use crate::EventBusError;
use tokio::sync::broadcast;

/// Marker trait for typed bus payloads.
pub trait Event: Clone + Send + Sync + 'static {
    /// Stable event name used for logging and routing conventions.
    fn event_name(&self) -> &'static str;
}

/// In-memory broadcast bus with bounded fan-out.
pub struct Bus<T: Event> {
    sender: broadcast::Sender<T>,
}

/// Subscription handle returned by [`Bus::subscribe`].
pub struct BusReceiver<T: Event> {
    receiver: broadcast::Receiver<T>,
}

impl<T: Event> Bus<T> {
    /// Create a bus that buffers up to `capacity` undelivered events.
    pub fn new(capacity: usize) -> Self {
        let (sender, _) = broadcast::channel(capacity.max(1));
        Self { sender }
    }

    /// Subscribe to all published events.
    pub fn subscribe(&self) -> BusReceiver<T> {
        BusReceiver {
            receiver: self.sender.subscribe(),
        }
    }

    /// Publish an event to all current subscribers.
    pub async fn publish(&self, event: T) -> Result<(), EventBusError> {
        self.sender
            .send(event)
            .map_err(|e| EventBusError::Publish(e.to_string()))?;
        Ok(())
    }
}

impl<T: Event> BusReceiver<T> {
    /// Wait for the next published event.
    pub async fn recv(&mut self) -> Result<T, broadcast::error::RecvError> {
        self.receiver.recv().await
    }
}
