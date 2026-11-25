//! Observability traits

/// Counter metrics trait
pub trait CounterMetrics: Send + Sync {
    /// Increment counter
    fn increment(&self, name: &str, value: u64);
}

/// Metrics hook trait
pub trait MetricsHook: Send + Sync {
    /// Record metric
    fn record(&self, name: &str, value: f64);
}

/// No-op metrics implementation
#[derive(Debug, Clone, Copy, Default)]
pub struct NoOpMetrics;

impl CounterMetrics for NoOpMetrics {
    fn increment(&self, _name: &str, _value: u64) {}
}

impl MetricsHook for NoOpMetrics {
    fn record(&self, _name: &str, _value: f64) {}
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    #[derive(Debug, Default)]
    struct CountingCounter;

    impl CounterMetrics for CountingCounter {
        fn increment(&self, _name: &str, _value: u64) {}
    }

    #[derive(Debug, Default)]
    struct RecordingHook {
        last_name: std::sync::Mutex<Option<String>>,
        last_value: std::sync::Mutex<f64>,
        calls: AtomicU64,
    }

    impl MetricsHook for RecordingHook {
        fn record(&self, name: &str, value: f64) {
            *self.last_name.lock().unwrap() = Some(name.to_string());
            *self.last_value.lock().unwrap() = value;
            self.calls.fetch_add(1, Ordering::SeqCst);
        }
    }

    #[test]
    fn noop_increment_does_nothing() {
        let m: Box<dyn CounterMetrics> = Box::new(NoOpMetrics);
        m.increment("any", 5);
        // No panic, no state.
    }

    #[test]
    fn noop_record_does_nothing() {
        let m: Box<dyn MetricsHook> = Box::new(NoOpMetrics);
        m.record("any", 1.5);
        // No panic, no state.
    }

    #[test]
    fn noop_default_works() {
        let _ = NoOpMetrics::default();
    }

    #[test]
    fn counter_trait_dispatch_via_dyn() {
        let counter: Box<dyn CounterMetrics> = Box::new(CountingCounter);
        counter.increment("requests", 1);
        counter.increment("requests", 2);
    }

    #[test]
    fn hook_trait_dispatch_via_dyn() {
        let hook = RecordingHook::default();
        let dyn_hook: Box<dyn MetricsHook> = Box::new(hook);
        dyn_hook.record("latency_ms", 12.5);
        // The trait object compiled and dispatched — verify object-safety compiles.
        fn assert_send_sync<T: Send + Sync + ?Sized>() {}
        assert_send_sync::<dyn CounterMetrics>();
        assert_send_sync::<dyn MetricsHook>();
    }

    #[test]
    fn recording_hook_captures_values() {
        let hook = RecordingHook::default();
        hook.record("metric_a", 1.0);
        hook.record("metric_b", 2.0);
        assert_eq!(hook.calls.load(Ordering::SeqCst), 2);
        assert_eq!(*hook.last_name.lock().unwrap(), Some("metric_b".to_string()));
        assert_eq!(*hook.last_value.lock().unwrap(), 2.0_f64);
    }
}
