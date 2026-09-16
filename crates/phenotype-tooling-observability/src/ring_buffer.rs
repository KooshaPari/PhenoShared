//! Time-bucketed ring buffer for sliding-window metrics.
//!
//! Replaces cumulative counters with a proper sliding window. Each bucket holds
//! `(success_count, failure_count)` for a fixed time slice (default 60s). The
//! ring is large enough to cover the longest SLO window (24h = 1440 buckets).
//!
//! Memory: 1440 * (16 bytes per bucket) = ~23 KB per target. Acceptable
//! for the in-process substrate.
//!
//! Absorbed from argis-monitor (slice 2: ring-buffer sliding windows).

use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// A single time-bucketed sample.
#[derive(Debug, Clone, Copy, Default)]
pub struct Bucket {
    pub success: u64,
    pub failure: u64,
}

impl Bucket {
    /// Total observations in this bucket.
    pub fn total(&self) -> u64 {
        self.success + self.failure
    }
}

/// A fixed-size ring of buckets, one per `bucket_size_secs`. The ring advances
/// automatically on `record()` based on the wall-clock timestamp.
pub struct RingBuffer {
    buckets: Vec<Bucket>,
    bucket_size_secs: u64,
    /// The unix-second timestamp of the most recent bucket boundary.
    head_ts: u64,
}

impl RingBuffer {
    /// Create a ring covering `total_window_secs`. Bucket size defaults to 60s.
    /// `now_secs` is the initial wall-clock timestamp; pass it explicitly so
    /// test fixtures and runtime both work without ambiguity.
    pub fn new(total_window_secs: u64, now_secs: u64) -> Self {
        Self::with_bucket_size(total_window_secs, 60, now_secs)
    }

    /// Create a ring with an explicit bucket size.
    pub fn with_bucket_size(total_window_secs: u64, bucket_size_secs: u64, now_secs: u64) -> Self {
        assert!(bucket_size_secs > 0, "bucket_size_secs must be > 0");
        let n_buckets = (total_window_secs / bucket_size_secs).max(1) as usize;
        Self {
            buckets: vec![Bucket::default(); n_buckets],
            bucket_size_secs,
            head_ts: Self::boundary_for(bucket_size_secs, now_secs),
        }
    }

    fn boundary_for(bucket_size_secs: u64, now_secs: u64) -> u64 {
        (now_secs / bucket_size_secs) * bucket_size_secs
    }

    /// Number of buckets in the ring.
    pub fn len(&self) -> usize {
        self.buckets.len()
    }

    /// True if the ring has zero buckets.
    pub fn is_empty(&self) -> bool {
        self.buckets.is_empty()
    }

    /// Record a single outcome, advancing the ring if the wall clock has moved.
    pub fn record(&mut self, success: bool, now_secs: u64) {
        self.advance(now_secs);
        let last = self
            .buckets
            .last_mut()
            .expect("ring is non-empty by construction");
        if success {
            last.success += 1;
        } else {
            last.failure += 1;
        }
    }

    /// Compute `(successes, failures)` over the trailing `window_secs`.
    /// Buckets older than the window are excluded; the most-recent bucket
    /// is included even if partially filled.
    pub fn window(&self, window_secs: u64, now_secs: u64) -> (u64, u64) {
        let now_boundary = self.boundary(now_secs);
        let cutoff = now_boundary.saturating_sub(window_secs);
        let mut success = 0u64;
        let mut failure = 0u64;
        let len = self.buckets.len() as u64;
        for (i, b) in self.buckets.iter().enumerate() {
            let age = (len - 1 - i as u64) * self.bucket_size_secs;
            let ts = now_boundary.saturating_sub(age);
            if ts >= cutoff {
                success += b.success;
                failure += b.failure;
            }
        }
        (success, failure)
    }

    fn advance(&mut self, now_secs: u64) {
        let target = self.boundary(now_secs);
        if target <= self.head_ts {
            return;
        }
        let stride = target - self.head_ts;
        let n = self.buckets.len() as u64;
        let step = (stride / self.bucket_size_secs).min(n);
        for _ in 0..step {
            let first = self.buckets.remove(0);
            self.buckets
                .push(Bucket { success: 0, failure: 0 });
            let _ = first;
        }
        self.head_ts = target;
    }

    fn boundary(&self, now_secs: u64) -> u64 {
        Self::boundary_for(self.bucket_size_secs, now_secs)
    }

    /// Time slice one bucket covers, in seconds.
    pub fn bucket_size_secs(&self) -> u64 {
        self.bucket_size_secs
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ring_starts_empty() {
        let rb = RingBuffer::new(3600, 0);
        assert_eq!(rb.len(), 60);
        let (s, f) = rb.window(3600, 0);
        assert_eq!(s + f, 0);
    }

    #[test]
    fn record_increments_latest_bucket() {
        let mut rb = RingBuffer::new(3600, 0);
        rb.record(true, 1000);
        rb.record(false, 1000);
        rb.record(true, 1000);
        let (s, f) = rb.window(3600, 1000);
        assert_eq!(s, 2);
        assert_eq!(f, 1);
    }

    #[test]
    fn window_excludes_old_buckets() {
        let mut rb = RingBuffer::with_bucket_size(3600, 60, 0);
        rb.record(true, 0);
        rb.record(true, 1800);
        let (s, _f) = rb.window(60, 1800);
        assert_eq!(
            s, 1,
            "expected only the latest record in the trailing 60s window"
        );
        let (s_all, _f) = rb.window(30 * 60, 1800);
        assert_eq!(s_all, 2, "30-minute window should include both records");
    }

    #[test]
    fn window_24h_covers_full_ring() {
        let mut rb = RingBuffer::with_bucket_size(3600 * 24, 3600, 0);
        for i in 0..24u64 {
            rb.record(true, i * 3600);
        }
        let (s, f) = rb.window(3600 * 24, 24 * 3600);
        assert_eq!(s, 24);
        assert_eq!(f, 0);
    }

    #[test]
    fn huge_stride_discards_old_history() {
        let mut rb = RingBuffer::with_bucket_size(3600, 60, 0);
        rb.record(true, 0);
        rb.record(true, 100 * 365 * 24 * 3600);
        let (s, _f) = rb.window(3600, 100 * 365 * 24 * 3600);
        assert_eq!(s, 1, "only the latest record should survive a huge stride");
    }
}
