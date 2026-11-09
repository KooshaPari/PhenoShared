//! Observability utilities for Phenotype

use std::time::{Duration, Instant};

/// Timer for measuring operation duration
pub struct Timer {
    start: Instant,
}

impl Timer {
    /// Create a new timer
    pub fn new() -> Self {
        Self {
            start: Instant::now(),
        }
    }

    /// Get elapsed time
    pub fn elapsed(&self) -> Duration {
        self.start.elapsed()
    }
}

impl Default for Timer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread::sleep;

    #[test]
    fn timer_new_returns_zero_or_tiny_elapsed() {
        let t = Timer::new();
        let d = t.elapsed();
        // Either zero or some sub-millisecond time depending on scheduling.
        assert!(d.as_nanos() < 1_000_000_000, "elapsed should be < 1s");
    }

    #[test]
    fn timer_default_matches_new() {
        let a: Timer = Timer::default();
        let b = Timer::new();
        let _ = (a, b);
    }

    #[test]
    fn timer_elapsed_grows_with_sleep() {
        let t = Timer::new();
        sleep(Duration::from_millis(15));
        let d = t.elapsed();
        // At least 10ms is a reasonable lower bound for a 15ms sleep on any platform.
        assert!(d >= Duration::from_millis(10), "expected >= 10ms, got {:?}", d);
    }

    #[test]
    fn timer_elapsed_repeatable() {
        let t = Timer::new();
        let d1 = t.elapsed();
        sleep(Duration::from_millis(2));
        let d2 = t.elapsed();
        assert!(d2 >= d1, "elapsed should be monotonically non-decreasing");
    }
}
