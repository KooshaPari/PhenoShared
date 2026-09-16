use async_trait::async_trait;
use logkit::adapters::sinks::{BoundedSink, Sink};
use logkit::{Level, LogEntry, LogError};
use std::future::{poll_fn, Future};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::task::Poll;
use tokio::sync::Notify;

#[derive(Clone, Default)]
struct HeldSink {
    started: Arc<Notify>,
    release: Arc<Notify>,
    flushed: Arc<AtomicBool>,
}

#[async_trait]
impl Sink for HeldSink {
    async fn write(&self, _: &LogEntry) -> Result<(), LogError> {
        self.started.notify_one();
        self.release.notified().await;
        Ok(())
    }
    async fn flush(&self) -> Result<(), LogError> {
        self.flushed.store(true, Ordering::SeqCst);
        Ok(())
    }
}

#[tokio::test]
async fn flush_waits_for_previously_started_write_on_another_permit() {
    let inner = HeldSink::default();
    let sink = BoundedSink::new(inner.clone(), 2);
    let writer = sink.clone();
    let write =
        tokio::spawn(async move { writer.write(&LogEntry::new(Level::Info, "pending")).await });
    inner.started.notified().await;
    let mut flush = Box::pin(sink.flush());
    let was_pending = poll_fn(|cx| Poll::Ready(flush.as_mut().poll(cx).is_pending())).await;
    inner.release.notify_one();
    write.await.unwrap().unwrap();
    assert!(was_pending, "flush completed before prior write finished");
    assert!(!inner.flushed.load(Ordering::SeqCst));
    flush.await.unwrap();
    assert!(inner.flushed.load(Ordering::SeqCst));
}

#[tokio::test]
async fn cancelled_write_releases_capacity_and_flush_guard() {
    let inner = HeldSink::default();
    let sink = BoundedSink::new(inner.clone(), 1);
    let writer = sink.clone();
    let write =
        tokio::spawn(async move { writer.write(&LogEntry::new(Level::Info, "cancelled")).await });
    inner.started.notified().await;
    let entry = LogEntry::new(Level::Info, "next");
    let mut next = Box::pin(sink.write(&entry));
    assert!(poll_fn(|cx| Poll::Ready(next.as_mut().poll(cx).is_pending())).await);
    write.abort();
    assert!(write.await.unwrap_err().is_cancelled());
    inner.release.notify_one();
    next.await.unwrap();
    sink.flush().await.unwrap();
    assert!(inner.flushed.load(Ordering::SeqCst));
}

struct FailingFlush;
#[async_trait]
impl Sink for FailingFlush {
    async fn write(&self, _: &LogEntry) -> Result<(), LogError> {
        Ok(())
    }
    async fn flush(&self) -> Result<(), LogError> {
        Err(LogError::Io("flush failed".into()))
    }
}

#[tokio::test]
async fn flush_error_propagates_and_releases_guard() {
    let sink = BoundedSink::new(FailingFlush, 1);
    assert!(matches!(sink.flush().await, Err(LogError::Io(s)) if s == "flush failed"));
    sink.write(&LogEntry::new(Level::Info, "after error"))
        .await
        .unwrap();
}
