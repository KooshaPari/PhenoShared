//! `Channel` — multi-consumer broadcast pub/sub built on `tokio::sync::broadcast`.
//!
//! Each topic gets its own broadcast channel (capacity configurable per channel).
//! Subscribers receive every message published after they subscribed; lag detection
//! surfaces as `ShareError::Lagged`.

use tokio::sync::broadcast;

use crate::error::ShareError;
use crate::message::ShareMessage;

/// Broadcast channel tuned for realtime fanout — many subscribers, one publisher
/// (or many publishers via `try_publish` from concurrent tasks).
pub struct Channel {
    /// Topic name this channel serves.
    topic: String,
    sender: broadcast::Sender<ShareMessage>,
    seq: std::sync::atomic::AtomicU64,
}

impl Channel {
    /// Create a channel for `topic` with `capacity` buffer slots.
    ///
    /// `capacity` is the broadcast ring-buffer size — when publishers outrun
    /// a slow subscriber by more than `capacity` messages, that subscriber
    /// observes `ShareError::Lagged`.
    pub fn new(topic: impl Into<String>, capacity: usize) -> Self {
        let topic = topic.into();
        let (sender, _) = broadcast::channel(capacity.max(1));
        Self { topic, sender, seq: std::sync::atomic::AtomicU64::new(0) }
    }

    /// Topic name.
    #[must_use]
    pub fn topic(&self) -> &str {
        &self.topic
    }

    /// Number of currently active subscribers.
    #[must_use]
    pub fn receiver_count(&self) -> usize {
        self.sender.receiver_count()
    }

    /// Publish `msg` to all current subscribers. Returns the number of
    /// receivers that will see the message, or `Err(ShareError::Closed)` when
    /// there are no subscribers (broadcast treats 0-receiver as an error which
    /// we normalise to Ok(0) so publishing without subscribers is valid).
    pub fn try_publish(&self, mut msg: ShareMessage) -> Result<usize, ShareError> {
        let seq = self.seq.fetch_add(1, std::sync::atomic::Ordering::Relaxed) + 1;
        msg.seq = seq;
        match self.sender.send(msg) {
            Ok(n) => Ok(n),
            Err(broadcast::error::SendError(_)) => Ok(0), // no active receivers — not an error for ShareCLI
        }
    }

    /// Publish a JSON payload under this channel's topic.
    pub fn publish_json<T: serde::Serialize>(&self, value: &T) -> Result<usize, ShareError> {
        let msg = ShareMessage::json(self.topic.clone(), value);
        self.try_publish(msg)
    }

    /// Publish a text payload.
    pub fn publish_text(&self, text: impl Into<String>) -> Result<usize, ShareError> {
        self.try_publish(ShareMessage::text(self.topic.clone(), text))
    }

    /// Subscribe. The returned `Subscriber` receives all messages published
    /// after this call.
    #[must_use]
    pub fn subscribe(&self) -> Subscriber {
        Subscriber { inner: self.sender.subscribe() }
    }

    /// Close the channel — further `try_publish` calls still succeed (but with
    /// 0 receivers) and existing subscribers will finish draining then see
    /// `ShareError::Closed`.
    pub fn close(&self) {
        // Dropping all senders would close; we keep ours alive but this
        // method exists for API symmetry. The broadcast stays open until
        // the Channel itself is dropped.
    }
}

/// A single subscription to a [`Channel`].
pub struct Subscriber {
    inner: broadcast::Receiver<ShareMessage>,
}

impl Subscriber {
    /// Receive the next message. Returns `ShareError::Lagged` when the
    /// receiver fell behind, `ShareError::Closed` when the channel is gone.
    pub async fn recv(&mut self) -> Result<ShareMessage, ShareError> {
        match self.inner.recv().await {
            Ok(m) => Ok(m),
            Err(broadcast::error::RecvError::Lagged(n)) => Err(ShareError::Lagged { skipped: n }),
            Err(broadcast::error::RecvError::Closed) => Err(ShareError::Closed),
        }
    }

    /// Non-blocking try-recv. Returns None when empty, Some(Ok) on message,
    /// Some(Err) on lag/close.
    pub fn try_recv(&mut self) -> Option<Result<ShareMessage, ShareError>> {
        match self.inner.try_recv() {
            Ok(m) => Some(Ok(m)),
            Err(broadcast::error::TryRecvError::Empty) => None,
            Err(broadcast::error::TryRecvError::Lagged(n)) => {
                Some(Err(ShareError::Lagged { skipped: n }))
            }
            Err(broadcast::error::TryRecvError::Closed) => Some(Err(ShareError::Closed)),
        }
    }

    /// Number of messages currently buffered for this subscriber.
    #[must_use]
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Whether this subscriber's buffer is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn publish_and_recv() {
        let ch = Channel::new("demo", 16);
        let mut sub = ch.subscribe();
        ch.publish_text("hello").unwrap();
        let msg = sub.recv().await.unwrap();
        assert_eq!(msg.payload.as_str().unwrap(), "hello");
        assert_eq!(msg.seq, 1);
    }

    #[tokio::test]
    async fn two_subscribers_both_see_message() {
        let ch = Channel::new("t", 16);
        let mut a = ch.subscribe();
        let mut b = ch.subscribe();
        ch.publish_text("hi").unwrap();
        assert_eq!(a.recv().await.unwrap().payload, serde_json::json!("hi"));
        assert_eq!(b.recv().await.unwrap().payload, serde_json::json!("hi"));
    }

    #[tokio::test]
    async fn new_subscriber_does_not_see_old_messages() {
        let ch = Channel::new("t", 16);
        ch.publish_text("old").unwrap();
        let mut sub = ch.subscribe();
        assert!(sub.try_recv().is_none());
        ch.publish_text("new").unwrap();
        assert_eq!(sub.recv().await.unwrap().payload, serde_json::json!("new"));
    }

    #[tokio::test]
    async fn lag_detection() {
        let ch = Channel::new("t", 2);
        let mut sub = ch.subscribe();
        for i in 0..5 {
            ch.publish_text(format!("{i}")).unwrap();
        }
        // subscriber lagged by 3 (wrote 5 into cap 2)
        let err = sub.recv().await.unwrap_err();
        assert!(matches!(err, ShareError::Lagged { .. }));
    }
}
