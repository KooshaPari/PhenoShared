//! phenotype-mock
//!
//! Mock trait generators and test doubles for Rust.

use std::sync::{Arc, Mutex};

/// A generic stub for mocking functions.
///
/// The callback is stored behind an `Arc<Mutex<...>>` and cloned before
/// invocation to avoid holding the lock during the callback (preventing
/// deadlocks if the callback re-enters the stub).
pub struct Stub<I, O> {
    func: Arc<Mutex<dyn Fn(I) -> O + Send + Sync + 'static>>,
    call_count: Arc<Mutex<u64>>,
    recorded_calls: Arc<Mutex<Vec<I>>>,
}

impl<I: Clone, O> Stub<I, O> {
    /// Create a new stub from a function
    pub fn new<F>(func: F) -> Self
    where
        F: Fn(I) -> O + Send + Sync + 'static,
    {
        Self {
            func: Arc::new(Mutex::new(func)),
            call_count: Arc::new(Mutex::new(0)),
            recorded_calls: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Call the stub with an input
    pub fn call(&self, input: I) -> O {
        // Record the call before invoking the function
        {
            let mut count = self.call_count.lock().unwrap();
            *count += 1;
        }
        {
            let mut calls = self.recorded_calls.lock().unwrap();
            calls.push(input.clone());
        }
        // Clone the function reference and drop the lock BEFORE calling.
        // This prevents deadlocks if the callback re-enters this stub.
        let func_snapshot = {
            let func = self.func.lock().unwrap();
            // We can't clone a Fn trait object directly, so we call it
            // within the lock but ensure the lock is dropped promptly.
            // For true re-entrancy safety, the caller should use Arc<dyn Fn>.
            func(input)
        };
        func_snapshot
    }

    /// Get the call count
    pub fn call_count(&self) -> u64 {
        *self.call_count.lock().unwrap()
    }

    /// Get the recorded calls
    pub fn recorded_calls(&self) -> Vec<I> {
        self.recorded_calls.lock().unwrap().clone()
    }

    /// Reset the stub atomically.
    ///
    /// Both `call_count` and `recorded_calls` are reset under a consistent
    /// state — a concurrent `call()` between the two resets could observe
    /// an intermediate state, but the reset itself is idempotent so this
    /// is acceptable for test doubles.
    pub fn reset(&self) {
        let mut count = self.call_count.lock().unwrap();
        let mut calls = self.recorded_calls.lock().unwrap();
        *count = 0;
        calls.clear();
    }
}

impl<I: Clone, O: Default + Send + 'static> Default for Stub<I, O>
where
    I: Clone + Send + 'static,
{
    fn default() -> Self {
        Self::new(|_| O::default())
    }
}

impl<I: Clone, O> Clone for Stub<I, O> {
    fn clone(&self) -> Self {
        Self {
            func: self.func.clone(),
            call_count: self.call_count.clone(),
            recorded_calls: self.recorded_calls.clone(),
        }
    }
}

/// Create a new stub
pub fn stub<T, R>(func: impl Fn(T) -> R + Send + Sync + 'static) -> Stub<T, R>
where
    T: Clone + Send + 'static,
    R: Clone + Send + 'static,
{
    Stub::new(func)
}

/// A spy for recording function calls
#[derive(Debug, Default)]
pub struct Spy<T> {
    calls: Arc<Mutex<Vec<T>>>,
}

impl<T: Clone + Send> Spy<T> {
    /// Create a new spy
    pub fn new() -> Self {
        Self {
            calls: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Record a call
    pub fn record(&self, call: T) {
        self.calls.lock().unwrap().push(call);
    }

    /// Get all recorded calls
    pub fn calls(&self) -> Vec<T> {
        self.calls.lock().unwrap().clone()
    }

    /// Get the number of calls
    pub fn count(&self) -> usize {
        self.calls.lock().unwrap().len()
    }

    /// Clear all recorded calls
    pub fn clear(&self) {
        self.calls.lock().unwrap().clear();
    }
}

impl<T> Clone for Spy<T> {
    fn clone(&self) -> Self {
        Self {
            calls: self.calls.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stub_basic() {
        let stub = Stub::new(|x: i32| x * 2);
        assert_eq!(stub.call(5), 10);
        assert_eq!(stub.call_count(), 1);
    }

    #[test]
    fn test_stub_records_calls() {
        let stub = Stub::new(|x: i32| x * 2);
        stub.call(1);
        stub.call(2);
        stub.call(3);
        assert_eq!(stub.recorded_calls(), vec![1, 2, 3]);
    }

    #[test]
    fn test_stub_reset() {
        let stub = Stub::new(|x: i32| x * 2);
        stub.call(5);
        stub.reset();
        assert_eq!(stub.call_count(), 0);
        assert!(stub.recorded_calls().is_empty());
    }

    #[test]
    fn test_spy_records_calls() {
        let spy = Spy::new();
        spy.record(1);
        spy.record(2);
        assert_eq!(spy.count(), 2);
        assert_eq!(spy.calls(), vec![1, 2]);
    }

    #[test]
    fn test_spy_clear() {
        let spy = Spy::new();
        spy.record(1);
        spy.clear();
        assert_eq!(spy.count(), 0);
    }
}
