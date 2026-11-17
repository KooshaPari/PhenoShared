//! Chaos test suite for the Helios CLI harness.
//!
//! Each submodule exercises a different failure domain:
//!
//! - `test_resilience` -- network partitions, degradation, retries, circuit
//!   breakers, and timeouts.
//! - `fault_injection` -- random errors, latency injection, resource exhaustion,
//!   and graceful degradation.

pub mod fault_injection;
pub mod test_resilience;
